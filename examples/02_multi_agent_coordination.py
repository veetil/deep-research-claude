#!/usr/bin/env python3
"""
Example 02: Multi-Agent Coordination
Demonstrates spawning multiple agents in parallel and coordinating them
"""
import asyncio
import sys
import os
from datetime import datetime
import random

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.orchestrator import AgentOrchestrator, AgentSpawnRequest
from src.core.message_queue import MessageQueue
from src.core.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.agents.base import AgentCapability, AgentStatus


# ANSI color codes
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def log(message: str, color: str = Colors.RESET, prefix: str = "", agent_id: str = None):
    """Pretty print log messages with timestamps and optional agent ID"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    agent_tag = f" [{agent_id[:8]}]" if agent_id else ""
    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET}{agent_tag} {prefix}{color}{message}{Colors.RESET}")


async def monitor_agent_messages(message_queue: MessageQueue, duration: int = 5):
    """Monitor messages being passed between agents"""
    messages_seen = []
    
    async def message_monitor(message):
        """Callback for monitoring messages"""
        messages_seen.append({
            'source': message.payload.get('source', 'unknown'),
            'target': message.payload.get('target', 'unknown'),
            'type': message.payload.get('type', 'unknown'),
            'timestamp': datetime.now()
        })
    
    # Subscribe to all agent topics
    await message_queue.subscribe("agent.*", message_monitor)
    
    # Monitor for specified duration
    await asyncio.sleep(duration)
    
    return messages_seen


async def main():
    """Demonstrate multi-agent coordination"""
    log("=== Deep Research Claude - Example 02: Multi-Agent Coordination ===", Colors.CYAN)
    log("This example shows multiple agents working together on research tasks\n", Colors.CYAN)
    
    # Initialize components
    log("Initializing system components...", Colors.BLUE)
    
    message_queue = MessageQueue()
    await message_queue.initialize()
    log("✓ Message Queue ready", Colors.GREEN, "  ")
    
    registry = AgentRegistry()
    registry.register_agent_type("research", ResearchAgent)
    log("✓ Registry configured", Colors.GREEN, "  ")
    
    orchestrator = AgentOrchestrator(message_queue, registry)
    orchestrator.max_concurrent_agents = 10  # Allow up to 10 agents
    await orchestrator.initialize()
    log("✓ Orchestrator online (max 10 agents)", Colors.GREEN, "  ")
    
    print()
    
    # Spawn multiple research agents with different specializations
    log("Spawning specialized research agents...", Colors.BLUE)
    
    agent_configs = [
        {
            "type": "research",
            "capabilities": [AgentCapability.WEB_SEARCH, AgentCapability.DATA_COLLECTION],
            "context": {
                "research_id": "multi_agent_demo",
                "user_id": "demo_user",
                "session_id": "demo_session",
                "metadata": {"specialization": "general_web", "name": "Web Researcher"}
            }
        },
        {
            "type": "research",
            "capabilities": [AgentCapability.ACADEMIC_SEARCH, AgentCapability.FACT_CHECKING],
            "context": {
                "research_id": "multi_agent_demo",
                "user_id": "demo_user",
                "session_id": "demo_session",
                "metadata": {"specialization": "academic", "name": "Academic Researcher"}
            }
        },
        {
            "type": "research",
            "capabilities": [AgentCapability.MULTILINGUAL, AgentCapability.TRANSLATION],
            "context": {
                "research_id": "multi_agent_demo",
                "user_id": "demo_user",
                "session_id": "demo_session",
                "metadata": {"specialization": "multilingual", "name": "Language Specialist"}
            }
        }
    ]
    
    # Spawn agents in parallel
    log("  Spawning 3 specialized agents in parallel...", Colors.YELLOW)
    start_time = asyncio.get_event_loop().time()
    
    agent_ids = await orchestrator.spawn_agents_parallel(agent_configs)
    
    spawn_time = asyncio.get_event_loop().time() - start_time
    log(f"✓ All agents spawned in {spawn_time:.3f} seconds!", Colors.GREEN, "  ")
    
    # Display spawned agents
    for i, (agent_id, config) in enumerate(zip(agent_ids, agent_configs)):
        agent = registry.get(agent_id)
        if agent:
            name = config['context']['metadata']['name']
            caps = [cap.value for cap in agent.capabilities]
            log(f"  Agent {i+1}: {name}", Colors.MAGENTA, "  ", agent_id)
            log(f"    Capabilities: {', '.join(caps)}", Colors.DIM, "      ")
    
    print()
    
    # Start message monitoring in background
    monitor_task = asyncio.create_task(monitor_agent_messages(message_queue, duration=10))
    
    # Demonstrate capability-based discovery
    log("Testing capability-based agent discovery...", Colors.BLUE)
    
    # Find agents with specific capabilities
    web_search_agents = await orchestrator.find_agents_by_capability(AgentCapability.WEB_SEARCH)
    log(f"  Found {len(web_search_agents)} agents with WEB_SEARCH capability", Colors.YELLOW)
    
    academic_agents = await orchestrator.find_agents_by_capability(AgentCapability.ACADEMIC_SEARCH)
    log(f"  Found {len(academic_agents)} agents with ACADEMIC_SEARCH capability", Colors.YELLOW)
    
    multilingual_agents = await orchestrator.find_agents_by_capability(AgentCapability.MULTILINGUAL)
    log(f"  Found {len(multilingual_agents)} agents with MULTILINGUAL capability", Colors.YELLOW)
    
    print()
    
    # Send coordinated research task
    log("Sending coordinated research task...", Colors.BLUE)
    
    research_topic = "Impact of AI on climate change research"
    log(f"  Topic: '{research_topic}'", Colors.CYAN)
    log("  Assigning subtasks to specialized agents:", Colors.YELLOW)
    
    # Task 1: General web research
    if web_search_agents:
        agent = web_search_agents[0]
        await orchestrator.send_agent_message(
            source_id="orchestrator",
            target_id=agent.id,
            message={
                "type": "research_request",
                "data": {
                    "query": f"{research_topic} - recent news and developments",
                    "parameters": {"focus": "news", "time_range": "1year"}
                }
            }
        )
        log("    → Web Researcher: Recent news and developments", Colors.GREEN, "", agent.id)
    
    # Task 2: Academic research
    if academic_agents:
        agent = academic_agents[0]
        await orchestrator.send_agent_message(
            source_id="orchestrator",
            target_id=agent.id,
            message={
                "type": "research_request",
                "data": {
                    "query": f"{research_topic} - peer-reviewed studies",
                    "parameters": {"focus": "academic", "peer_reviewed": True}
                }
            }
        )
        log("    → Academic Researcher: Peer-reviewed studies", Colors.GREEN, "", agent.id)
    
    # Task 3: International perspectives
    if multilingual_agents:
        agent = multilingual_agents[0]
        await orchestrator.send_agent_message(
            source_id="orchestrator",
            target_id=agent.id,
            message={
                "type": "research_request",
                "data": {
                    "query": f"{research_topic} - international perspectives",
                    "parameters": {"languages": ["en", "zh", "es", "fr"], "focus": "global"}
                }
            }
        )
        log("    → Language Specialist: International perspectives", Colors.GREEN, "", agent.id)
    
    print()
    
    # Simulate agent work and inter-agent communication
    log("Agents working on research tasks...", Colors.BLUE)
    
    # Broadcast a coordination message
    await orchestrator.broadcast_message(
        source_id="orchestrator",
        message={
            "type": "coordination",
            "data": {
                "instruction": "Share preliminary findings with other agents",
                "deadline": "5_seconds"
            }
        }
    )
    log("  Broadcast sent: Request for preliminary findings", Colors.YELLOW)
    
    # Wait for agents to process
    for i in range(5):
        await asyncio.sleep(1)
        log(f"  Processing... ({i+1}/5 seconds)", Colors.DIM)
    
    print()
    
    # Check agent health
    log("Performing health check on all agents...", Colors.BLUE)
    
    health_report = await orchestrator.check_agent_health()
    log(f"  Total agents: {health_report['total_agents']}", Colors.CYAN)
    log(f"  Healthy agents: {health_report['healthy_agents']} ✓", Colors.GREEN)
    log(f"  Unhealthy agents: {health_report['unhealthy_agents']}", 
        Colors.RED if health_report['unhealthy_agents'] > 0 else Colors.GREEN)
    
    if health_report['recovery_attempted']:
        log(f"  Recovery attempted for: {len(health_report['recovery_attempted'])} agents", Colors.YELLOW)
    
    print()
    
    # Display agent tree showing relationships
    log("Current agent hierarchy:", Colors.BLUE)
    
    agent_tree = await orchestrator.get_agent_tree()
    
    def print_agent(node, indent="  "):
        status_color = Colors.GREEN if node['status'] == 'ready' else Colors.YELLOW
        log(f"{indent}├─ {node['type']} agent [{node['id'][:8]}...]", status_color)
        log(f"{indent}│  Status: {node['status']}", Colors.DIM)
        for child in node.get('children', []):
            print_agent(child, indent + "│  ")
    
    if 'roots' in agent_tree:
        for root in agent_tree['roots']:
            print_agent(root)
    
    print()
    
    # Get message monitoring results
    messages = await monitor_task
    
    if messages:
        log(f"Message activity summary ({len(messages)} messages exchanged):", Colors.BLUE)
        
        # Count message types
        message_types = {}
        for msg in messages:
            msg_type = msg['type']
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        for msg_type, count in message_types.items():
            log(f"  {msg_type}: {count} messages", Colors.CYAN)
    
    print()
    
    # Demonstrate coordinated shutdown
    log("Coordinating system shutdown...", Colors.BLUE)
    
    # Get current stats before shutdown
    stats = registry.get_statistics()
    log(f"  System statistics:", Colors.YELLOW)
    log(f"    Total agents spawned: {stats['total_agents']}", Colors.CYAN)
    log(f"    By type: {stats['by_type']}", Colors.CYAN)
    log(f"    By status: {stats['by_status']}", Colors.CYAN)
    
    # Terminate all agents
    log("  Terminating all agents...", Colors.YELLOW)
    for agent_id in agent_ids:
        await orchestrator.terminate_agent(agent_id)
        log(f"    ✓ Agent {agent_id[:8]}... terminated", Colors.DIM)
    
    # Shutdown
    await orchestrator.shutdown()
    await message_queue.shutdown()
    
    log("✓ All systems shut down gracefully", Colors.GREEN, "  ")
    
    print()
    log("Example completed! 🎉", Colors.GREEN)
    log("This demonstrated:", Colors.CYAN)
    log("  • Parallel agent spawning", Colors.CYAN, "  ")
    log("  • Capability-based discovery", Colors.CYAN, "  ")
    log("  • Coordinated task assignment", Colors.CYAN, "  ")
    log("  • Inter-agent messaging", Colors.CYAN, "  ")
    log("  • Health monitoring", Colors.CYAN, "  ")
    log("  • Graceful shutdown", Colors.CYAN, "  ")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nExample interrupted by user", Colors.YELLOW)