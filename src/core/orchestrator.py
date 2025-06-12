"""
Agent Orchestrator - Core component for managing multi-agent system
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone
from enum import Enum

from src.agents.base import BaseAgent, AgentCapability, AgentStatus
from src.core.message_queue import MessageQueue
from src.core.registry import AgentRegistry


@dataclass
class AgentSpawnRequest:
    """Request to spawn a new agent"""
    agent_type: str
    capabilities: List[AgentCapability]
    context: Dict[str, Any]
    parent_id: Optional[str] = None
    priority: int = 5  # 1-10, higher is more important


class AgentOrchestrator:
    """Orchestrates the multi-agent system"""
    
    def __init__(self, message_queue: MessageQueue, agent_registry: AgentRegistry):
        self.message_queue = message_queue
        self.agent_registry = agent_registry
        self.active_agents: Set[str] = set()
        self.max_concurrent_agents = 50
        self.spawn_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        
    async def initialize(self):
        """Initialize the orchestrator"""
        self._running = True
        # Start background tasks
        asyncio.create_task(self._process_spawn_queue())
        asyncio.create_task(self._monitor_agent_health())
        
    async def shutdown(self):
        """Shutdown the orchestrator"""
        self._running = False
        # Terminate all agents gracefully
        for agent_id in list(self.active_agents):
            await self.terminate_agent(agent_id)
    
    async def spawn_agent(self, request: AgentSpawnRequest) -> str:
        """Spawn a new agent based on request"""
        # Check agent limit
        if len(self.active_agents) >= self.max_concurrent_agents:
            raise RuntimeError("Maximum concurrent agents limit reached")
        
        # Validate parent if specified
        if request.parent_id:
            parent = self.agent_registry.get(request.parent_id)
            if not parent:
                raise ValueError(f"Parent agent {request.parent_id} not found")
            if not parent.can_spawn_children:
                raise ValueError(f"Parent agent {request.parent_id} cannot spawn children")
        
        # Create agent
        agent = self.agent_registry.create_agent(
            agent_type=request.agent_type,
            capabilities=request.capabilities
        )
        
        # Set parent relationship
        if request.parent_id:
            agent.parent_id = request.parent_id
        
        # Initialize agent with context
        await agent.initialize(request.context)
        
        # Register agent
        self.agent_registry.register(agent)
        self.active_agents.add(agent.id)
        
        # Notify system of new agent
        await self.message_queue.publish({
            "type": "agent_spawned",
            "agent_id": agent.id,
            "agent_type": request.agent_type,
            "parent_id": request.parent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return agent.id
    
    async def spawn_agents_parallel(self, agent_configs: List[Dict[str, Any]]) -> List[str]:
        """Spawn multiple agents in parallel"""
        tasks = []
        for config in agent_configs:
            request = AgentSpawnRequest(
                agent_type=config["type"],
                capabilities=config["capabilities"],
                context=config.get("context", {}),
                parent_id=config.get("parent_id")
            )
            tasks.append(self.spawn_agent(request))
        
        agent_ids = await asyncio.gather(*tasks)
        return agent_ids
    
    async def send_agent_message(self, source_id: str, target_id: str, message: Dict[str, Any]):
        """Send message from one agent to another"""
        envelope = {
            "id": str(uuid.uuid4()),
            "source": source_id,
            "target": target_id,
            "payload": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.message_queue.publish(envelope, topic=f"agent.{target_id}")
    
    async def broadcast_message(self, source_id: str, message: Dict[str, Any], 
                              capability_filter: Optional[AgentCapability] = None):
        """Broadcast message to multiple agents"""
        if capability_filter:
            target_agents = await self.find_agents_by_capability(capability_filter)
        else:
            target_agents = [self.agent_registry.get(aid) for aid in self.active_agents]
        
        tasks = []
        for agent in target_agents:
            if agent and agent.id != source_id:
                tasks.append(self.send_agent_message(source_id, agent.id, message))
        
        await asyncio.gather(*tasks)
    
    async def pause_agent(self, agent_id: str):
        """Pause an agent"""
        agent = self.agent_registry.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        await agent.pause()
        agent.status = AgentStatus.PAUSED
        
        await self.message_queue.publish({
            "type": "agent_paused",
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def resume_agent(self, agent_id: str):
        """Resume a paused agent"""
        agent = self.agent_registry.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        await agent.resume()
        agent.status = AgentStatus.READY
        
        await self.message_queue.publish({
            "type": "agent_resumed",
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def terminate_agent(self, agent_id: str):
        """Terminate an agent"""
        agent = self.agent_registry.get(agent_id)
        if not agent:
            return
        
        # Terminate children first
        children = self.agent_registry.get_children(agent_id)
        for child in children:
            await self.terminate_agent(child.id)
        
        # Terminate the agent
        await agent.terminate()
        agent.status = AgentStatus.TERMINATED
        
        # Clean up
        self.active_agents.discard(agent_id)
        self.agent_registry.unregister(agent_id)
        
        await self.message_queue.publish({
            "type": "agent_terminated",
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def find_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Find all agents with a specific capability"""
        return self.agent_registry.list_by_capability(capability)
    
    async def get_agent_tree(self, root_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get hierarchical view of agent relationships"""
        if root_agent_id:
            root = self.agent_registry.get(root_agent_id)
            if not root:
                return {}
        else:
            # Find all root agents (no parent)
            roots = [
                self.agent_registry.get(aid) 
                for aid in self.active_agents 
                if self.agent_registry.get(aid) and not self.agent_registry.get(aid).parent_id
            ]
            return {
                "roots": [self._build_agent_tree_node(root) for root in roots if root]
            }
        
        return self._build_agent_tree_node(root)
    
    def _build_agent_tree_node(self, agent: BaseAgent) -> Dict[str, Any]:
        """Build tree node for an agent"""
        children = self.agent_registry.get_children(agent.id)
        return {
            "id": agent.id,
            "type": agent.agent_type,
            "status": agent.status.value,
            "capabilities": [cap.value for cap in agent.capabilities],
            "children": [self._build_agent_tree_node(child) for child in children]
        }
    
    async def check_agent_health(self) -> Dict[str, Any]:
        """Check health of all agents"""
        all_agents = self.agent_registry.list_all()
        health_report = {
            "total_agents": len(all_agents),
            "healthy_agents": 0,
            "unhealthy_agents": 0,
            "recovery_attempted": []
        }
        
        for agent in all_agents:
            try:
                is_healthy = await agent.health_check()
                if is_healthy:
                    health_report["healthy_agents"] += 1
                else:
                    health_report["unhealthy_agents"] += 1
                    # Attempt recovery
                    if agent.status == AgentStatus.ERROR:
                        await agent.restart()
                        health_report["recovery_attempted"].append(agent.id)
            except Exception as e:
                health_report["unhealthy_agents"] += 1
                
        return health_report
    
    async def _process_spawn_queue(self):
        """Process agent spawn requests from queue"""
        while self._running:
            try:
                # Get request from queue with timeout
                request = await asyncio.wait_for(
                    self.spawn_queue.get(), 
                    timeout=1.0
                )
                
                # Process spawn request
                try:
                    agent_id = await self.spawn_agent(request)
                    await self.message_queue.publish({
                        "type": "spawn_completed",
                        "agent_id": agent_id,
                        "request_id": request.id if hasattr(request, 'id') else None
                    })
                except Exception as e:
                    await self.message_queue.publish({
                        "type": "spawn_failed",
                        "error": str(e),
                        "request": request
                    })
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Log error but continue processing
                pass
    
    async def _monitor_agent_health(self):
        """Monitor agent health periodically"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                health_report = await self.check_agent_health()
                
                # Publish health report
                await self.message_queue.publish({
                    "type": "health_report",
                    "report": health_report,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            except Exception as e:
                # Log error but continue monitoring
                pass