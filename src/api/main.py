"""
FastAPI application for Deep Research Claude
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import os

from src.core.message_queue import MessageQueue, MessageBus
from src.core.orchestrator import AgentSpawnRequest
from src.agents.base import AgentCapability

# Create FastAPI app
app = FastAPI(
    title="Deep Research Claude API",
    description="Multi-agent AI research system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
message_queue: Optional[MessageQueue] = None
message_bus: Optional[MessageBus] = None


# Pydantic models for API
class ResearchRequest(BaseModel):
    query: str
    depth: str = "normal"  # "shallow", "normal", "deep", "comprehensive"
    languages: List[str] = ["en"]
    time_limit: Optional[int] = 3600  # seconds
    parameters: Dict[str, Any] = {}


class AgentSpawnRequestModel(BaseModel):
    agent_type: str
    capabilities: List[str]
    context: Dict[str, Any]
    parent_id: Optional[str] = None
    priority: int = 5


class SystemStatus(BaseModel):
    status: str
    active_agents: int
    message_queue_stats: Dict[str, Any]
    uptime: float


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global message_queue, message_bus
    
    # Initialize message queue
    message_queue = MessageQueue()
    await message_queue.initialize()
    
    # Initialize message bus
    message_bus = MessageBus(message_queue)
    await message_bus.initialize()
    
    print("✅ API services initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if message_queue:
        await message_queue.shutdown()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "Deep Research Claude API",
        "status": "online",
        "version": "0.1.0"
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/research", response_model=Dict[str, Any])
async def create_research(request: ResearchRequest):
    """Create a new research task"""
    try:
        # Create context for research
        context = {
            "research_id": f"research_{asyncio.get_event_loop().time()}",
            "user_id": "api_user",  # In production, get from auth
            "session_id": f"session_{asyncio.get_event_loop().time()}",
            "query": request.query,
            "parameters": {
                "depth": request.depth,
                "languages": request.languages,
                "time_limit": request.time_limit,
                **request.parameters
            }
        }
        
        # Request research agent spawn
        spawn_request = {
            "agent_type": "research",
            "capabilities": ["web_search", "multilingual"],
            "context": context
        }
        
        # Send spawn request
        response = await message_bus.request("spawn_agent", spawn_request, timeout=10.0)
        
        if not response or not response.get("success"):
            raise HTTPException(status_code=500, detail="Failed to spawn research agent")
        
        # Send research request to the spawned agent
        agent_id = response["agent_id"]
        research_message = {
            "source": "api",
            "target": agent_id,
            "payload": {
                "type": "research_request",
                "data": {
                    "query": request.query,
                    "parameters": request.parameters
                }
            }
        }
        
        await message_queue.publish(research_message, topic=f"agent.{agent_id}")
        
        return {
            "research_id": context["research_id"],
            "agent_id": agent_id,
            "status": "started",
            "message": "Research task initiated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/spawn", response_model=Dict[str, Any])
async def spawn_agent(request: AgentSpawnRequestModel):
    """Spawn a new agent"""
    try:
        # Convert string capabilities to enum values
        capabilities = []
        for cap_str in request.capabilities:
            try:
                cap = AgentCapability(cap_str)
                capabilities.append(cap)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid capability: {cap_str}"
                )
        
        # Create spawn request
        spawn_data = {
            "agent_type": request.agent_type,
            "capabilities": [cap.value for cap in capabilities],
            "context": request.context,
            "parent_id": request.parent_id,
            "priority": request.priority
        }
        
        # Send spawn request
        response = await message_bus.request("spawn_agent", spawn_data, timeout=10.0)
        
        if not response:
            raise HTTPException(status_code=500, detail="No response from orchestrator")
        
        if not response.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=response.get("error", "Failed to spawn agent")
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/status", response_model=Dict[str, Any])
async def get_agent_status():
    """Get status of all agents"""
    try:
        response = await message_bus.request("get_agent_status", {}, timeout=5.0)
        
        if not response:
            return {"agents": {}, "error": "No response from orchestrator"}
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    try:
        # Get message queue stats
        queue_stats = await message_queue.get_queue_stats()
        
        # Get agent status
        agent_response = await message_bus.request("get_agent_status", {}, timeout=5.0)
        
        # Count active agents
        active_agents = 0
        if agent_response and "agents" in agent_response:
            # Count agents recursively
            def count_agents(node):
                count = 1
                for child in node.get("children", []):
                    count += count_agents(child)
                return count
            
            if "roots" in agent_response["agents"]:
                for root in agent_response["agents"]["roots"]:
                    active_agents += count_agents(root)
            elif agent_response["agents"]:
                active_agents = count_agents(agent_response["agents"])
        
        return SystemStatus(
            status="operational",
            active_agents=active_agents,
            message_queue_stats=queue_stats,
            uptime=asyncio.get_event_loop().time()
        )
        
    except Exception as e:
        return SystemStatus(
            status="error",
            active_agents=0,
            message_queue_stats={},
            uptime=0
        )


@app.websocket("/ws/research/{research_id}")
async def websocket_research_updates(websocket: WebSocket, research_id: str):
    """WebSocket endpoint for real-time research updates"""
    await websocket.accept()
    
    try:
        # Subscribe to research updates
        update_queue = asyncio.Queue()
        
        async def handle_update(message):
            await update_queue.put(message.payload)
        
        await message_queue.subscribe(f"research.{research_id}.updates", handle_update)
        
        # Send updates to client
        while True:
            try:
                update = await asyncio.wait_for(update_queue.get(), timeout=1.0)
                await websocket.send_json(update)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        # Client disconnected
        await message_queue.unsubscribe(f"research.{research_id}.updates", handle_update)
    except Exception as e:
        await websocket.close(code=1000, reason=str(e))


@app.get("/api/capabilities", response_model=List[str])
async def get_available_capabilities():
    """Get list of available agent capabilities"""
    return [cap.value for cap in AgentCapability]


@app.get("/api/agent-types", response_model=List[str])
async def get_agent_types():
    """Get list of available agent types"""
    # In production, this would query the registry
    return [
        "research",
        "analysis", 
        "synthesis",
        "judge",
        "financial",
        "medical",
        "legal",
        "creative",
        "strategic",
        "development",
        "translation",
        "educational"
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)