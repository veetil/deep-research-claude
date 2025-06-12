"""
Main entry point for the Agent Orchestrator service
"""
import asyncio
import os
import signal
import sys
from typing import Optional

from src.core.orchestrator import AgentOrchestrator
from src.core.message_queue import MessageQueue, MessageBus
from src.core.registry import AgentRegistry

# Import all agent types
from src.agents.research_agent import ResearchAgent


class OrchestratorService:
    """Main orchestrator service"""
    
    def __init__(self):
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.message_queue: Optional[MessageQueue] = None
        self.message_bus: Optional[MessageBus] = None
        self.registry: Optional[AgentRegistry] = None
        self._running = False
        
    async def initialize(self):
        """Initialize all components"""
        print("Initializing Deep Research Claude Orchestrator...")
        
        # Initialize message queue
        self.message_queue = MessageQueue()
        await self.message_queue.initialize()
        print("✓ Message queue initialized")
        
        # Initialize message bus
        self.message_bus = MessageBus(self.message_queue)
        await self.message_bus.initialize()
        print("✓ Message bus initialized")
        
        # Initialize agent registry
        self.registry = AgentRegistry()
        self._register_agent_types()
        print("✓ Agent registry initialized")
        
        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(
            message_queue=self.message_queue,
            agent_registry=self.registry
        )
        await self.orchestrator.initialize()
        print("✓ Orchestrator initialized")
        
        # Set max concurrent agents from environment
        max_agents = int(os.getenv('MAX_CONCURRENT_AGENTS', '50'))
        self.orchestrator.max_concurrent_agents = max_agents
        print(f"✓ Max concurrent agents set to {max_agents}")
        
        self._running = True
        print("\n🚀 Deep Research Claude Orchestrator is ready!")
        
    def _register_agent_types(self):
        """Register all available agent types"""
        # Register research agent
        self.registry.register_agent_type("research", ResearchAgent)
        
        # TODO: Register other agent types as they are implemented
        # self.registry.register_agent_type("analysis", AnalysisAgent)
        # self.registry.register_agent_type("synthesis", SynthesisAgent)
        # self.registry.register_agent_type("judge", JudgeAgent)
        # etc.
        
    async def run(self):
        """Run the orchestrator service"""
        print("\n📊 Starting orchestrator service loop...")
        
        # Subscribe to system messages
        await self._setup_message_handlers()
        
        # Main service loop
        while self._running:
            try:
                # Check system health
                health = await self.orchestrator.check_agent_health()
                
                # Log health status periodically
                if health["unhealthy_agents"] > 0:
                    print(f"⚠️  Health check: {health['healthy_agents']} healthy, "
                          f"{health['unhealthy_agents']} unhealthy agents")
                
                # Sleep for a bit
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def _setup_message_handlers(self):
        """Setup message handlers for system operations"""
        # Handle agent spawn requests
        async def handle_spawn_request(data):
            try:
                from src.core.orchestrator import AgentSpawnRequest
                request = AgentSpawnRequest(**data)
                agent_id = await self.orchestrator.spawn_agent(request)
                return {"success": True, "agent_id": agent_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        await self.message_bus.handle_request("spawn_agent", handle_spawn_request)
        
        # Handle agent status queries
        async def handle_status_query(data):
            agent_tree = await self.orchestrator.get_agent_tree()
            return {"agents": agent_tree}
        
        await self.message_bus.handle_request("get_agent_status", handle_status_query)
        
    async def shutdown(self):
        """Shutdown the orchestrator service"""
        print("\n🛑 Shutting down orchestrator service...")
        self._running = False
        
        if self.orchestrator:
            await self.orchestrator.shutdown()
            print("✓ Orchestrator shutdown complete")
        
        if self.message_queue:
            await self.message_queue.shutdown()
            print("✓ Message queue shutdown complete")
        
        print("👋 Goodbye!")


async def main():
    """Main entry point"""
    service = OrchestratorService()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        print(f"\n📍 Received signal {sig}")
        asyncio.create_task(service.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize service
        await service.initialize()
        
        # Run service
        await service.run()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await service.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())