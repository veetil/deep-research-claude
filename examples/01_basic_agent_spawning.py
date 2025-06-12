#!/usr/bin/env python3
"""
Example 01: Basic Agent Spawning
Demonstrates spawning a single agent and watching it process messages
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.orchestrator import AgentOrchestrator, AgentSpawnRequest
from src.core.message_queue import MessageQueue
from src.core.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.agents.base import AgentCapability


# ANSI color codes for pretty output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log(message: str, color: str = Colors.RESET, prefix: str = ""):
    """Pretty print log messages with timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET} {prefix}{color}{message}{Colors.RESET}")


async def main():
    """Demonstrate basic agent spawning and message passing"""
    log("=== Deep Research Claude - Example 01: Basic Agent Spawning ===", Colors.CYAN)
    log("This example shows how to spawn a research agent and send it a task\n", Colors.CYAN)
    
    # Step 1: Initialize core components
    log("Step 1: Initializing core components...", Colors.BLUE)
    
    message_queue = MessageQueue()
    await message_queue.initialize()
    log("✓ Message Queue initialized", Colors.GREEN, "  ")
    
    registry = AgentRegistry()
    registry.register_agent_type("research", ResearchAgent)
    log("✓ Agent Registry initialized", Colors.GREEN, "  ")
    log("✓ Research Agent type registered", Colors.GREEN, "  ")
    
    orchestrator = AgentOrchestrator(message_queue, registry)
    await orchestrator.initialize()
    log("✓ Orchestrator initialized", Colors.GREEN, "  ")
    
    print()  # Empty line for readability
    
    # Step 2: Spawn a research agent
    log("Step 2: Spawning a Research Agent...", Colors.BLUE)
    
    spawn_request = AgentSpawnRequest(
        agent_type="research",
        capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.MULTILINGUAL],
        context={
            "research_id": "demo_research_001",
            "user_id": "demo_user",
            "session_id": "demo_session"
        }
    )
    
    log(f"  Agent Type: {spawn_request.agent_type}", Colors.YELLOW)
    log(f"  Capabilities: {[cap.value for cap in spawn_request.capabilities]}", Colors.YELLOW)
    log("  Spawning agent...", Colors.YELLOW)
    
    agent_id = await orchestrator.spawn_agent(spawn_request)
    log(f"✓ Agent spawned successfully! ID: {agent_id}", Colors.GREEN, "  ")
    
    print()
    
    # Step 3: Check agent status
    log("Step 3: Checking agent status...", Colors.BLUE)
    
    agent = registry.get(agent_id)
    if agent:
        log(f"  Agent ID: {agent.id}", Colors.MAGENTA)
        log(f"  Agent Type: {agent.agent_type}", Colors.MAGENTA)
        log(f"  Status: {agent.status.value}", Colors.MAGENTA)
        log(f"  Capabilities: {[cap.value for cap in agent.capabilities]}", Colors.MAGENTA)
    
    print()
    
    # Step 4: Send a research request
    log("Step 4: Sending a research request to the agent...", Colors.BLUE)
    
    research_query = "What are the latest advancements in quantum computing?"
    log(f"  Research Query: '{research_query}'", Colors.YELLOW)
    
    await orchestrator.send_agent_message(
        source_id="orchestrator",
        target_id=agent_id,
        message={
            "type": "research_request",
            "data": {
                "query": research_query,
                "parameters": {
                    "depth": "normal",
                    "max_sources": 5
                }
            }
        }
    )
    
    log("✓ Research request sent!", Colors.GREEN, "  ")
    
    # Give the agent time to process
    log("  Waiting for agent to process request...", Colors.YELLOW)
    await asyncio.sleep(2)
    
    print()
    
    # Step 5: Check agent metrics
    log("Step 5: Checking agent metrics...", Colors.BLUE)
    
    metrics = await agent.get_metrics()
    log("  Agent Metrics:", Colors.MAGENTA)
    log(f"    - Uptime: {metrics['uptime']:.2f} seconds", Colors.MAGENTA)
    log(f"    - Status: {metrics['status']}", Colors.MAGENTA)
    log(f"    - Message Queue Size: {metrics['message_queue_size']}", Colors.MAGENTA)
    log(f"    - Last Activity: {metrics['last_activity']}", Colors.MAGENTA)
    
    # Get custom metrics
    custom_metrics = metrics.get('custom_metrics', {})
    if custom_metrics:
        log("  Research Metrics:", Colors.MAGENTA)
        log(f"    - Total Tasks: {custom_metrics.get('total_tasks', 0)}", Colors.MAGENTA)
        log(f"    - Sources Consulted: {custom_metrics.get('sources_consulted', 0)}", Colors.MAGENTA)
        log(f"    - Findings Count: {custom_metrics.get('findings_count', 0)}", Colors.MAGENTA)
    
    print()
    
    # Step 6: Check message queue statistics
    log("Step 6: Checking message queue statistics...", Colors.BLUE)
    
    queue_stats = await message_queue.get_queue_stats()
    log("  Queue Statistics:", Colors.CYAN)
    log(f"    - Total Topics: {queue_stats['total_topics']}", Colors.CYAN)
    log(f"    - Total Subscribers: {queue_stats['total_subscribers']}", Colors.CYAN)
    log(f"    - Dead Letters: {queue_stats['dead_letters']}", Colors.CYAN)
    
    if queue_stats['topics']:
        log("  Active Topics:", Colors.CYAN)
        for topic, stats in queue_stats['topics'].items():
            log(f"    - {topic}: {stats['queue_size']} messages, {stats['subscribers']} subscribers", Colors.CYAN)
    
    print()
    
    # Step 7: View agent tree
    log("Step 7: Viewing agent hierarchy...", Colors.BLUE)
    
    agent_tree = await orchestrator.get_agent_tree()
    log("  Agent Tree:", Colors.GREEN)
    
    def print_tree(node, indent="    "):
        log(f"{indent}├─ Agent: {node['id'][:8]}... ({node['type']})", Colors.GREEN)
        log(f"{indent}│  Status: {node['status']}", Colors.GREEN)
        log(f"{indent}│  Capabilities: {', '.join(node['capabilities'])}", Colors.GREEN)
        for child in node.get('children', []):
            print_tree(child, indent + "   ")
    
    if 'roots' in agent_tree:
        for root in agent_tree['roots']:
            print_tree(root)
    
    print()
    
    # Step 8: Cleanup
    log("Step 8: Cleaning up...", Colors.BLUE)
    
    await orchestrator.terminate_agent(agent_id)
    log("✓ Agent terminated", Colors.GREEN, "  ")
    
    await orchestrator.shutdown()
    log("✓ Orchestrator shut down", Colors.GREEN, "  ")
    
    await message_queue.shutdown()
    log("✓ Message queue shut down", Colors.GREEN, "  ")
    
    print()
    log("Example completed successfully! 🎉", Colors.GREEN)
    log("This demonstrated basic agent lifecycle: spawn → configure → send message → monitor → terminate", Colors.CYAN)


if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nExample interrupted by user", Colors.YELLOW)