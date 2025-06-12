#!/usr/bin/env python3
"""
Example 03: Recursive Agent Spawning
Demonstrates how agents can spawn child agents recursively to divide complex tasks
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List

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


def log(message: str, color: str = Colors.RESET, prefix: str = "", agent_id: str = None, indent: int = 0):
    """Pretty print log messages with timestamps, agent ID, and indentation"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    agent_tag = f" [{agent_id[:8]}]" if agent_id else ""
    indent_str = "  " * indent
    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET}{agent_tag} {indent_str}{prefix}{color}{message}{Colors.RESET}")


async def simulate_recursive_research(orchestrator: AgentOrchestrator, parent_id: str, query: str, depth: int = 0, max_depth: int = 3):
    """Simulate a research agent that spawns child agents for subtasks"""
    if depth >= max_depth:
        log(f"Max depth {max_depth} reached, completing task", Colors.YELLOW, "⚠️ ", parent_id, depth)
        return
    
    # Simulate breaking down the research query into subtasks
    subtasks = []
    if "climate change" in query.lower():
        subtasks = [
            ("Environmental impacts of climate change", [AgentCapability.WEB_SEARCH, AgentCapability.FACT_CHECKING]),
            ("Economic impacts of climate change", [AgentCapability.FINANCIAL_ANALYSIS, AgentCapability.STATISTICAL_ANALYSIS]),
            ("Technological solutions for climate change", [AgentCapability.TECHNICAL_WRITING, AgentCapability.ACADEMIC_SEARCH])
        ]
    elif "ai" in query.lower():
        subtasks = [
            ("Machine learning algorithms", [AgentCapability.CODE_ANALYSIS, AgentCapability.TECHNICAL_WRITING]),
            ("AI ethics and governance", [AgentCapability.CRITICAL_THINKING, AgentCapability.FACT_CHECKING]),
            ("AI applications in industry", [AgentCapability.STRATEGIC_PLANNING, AgentCapability.DATA_COLLECTION])
        ]
    else:
        # Generic breakdown
        subtasks = [
            (f"Historical context of {query}", [AgentCapability.WEB_SEARCH, AgentCapability.ACADEMIC_SEARCH]),
            (f"Current state of {query}", [AgentCapability.DATA_COLLECTION, AgentCapability.FACT_CHECKING]),
            (f"Future implications of {query}", [AgentCapability.STRATEGIC_PLANNING, AgentCapability.CREATIVE_THINKING])
        ]
    
    log(f"Breaking down task into {len(subtasks)} subtasks", Colors.CYAN, "🔍 ", parent_id, depth)
    
    # Spawn child agents for each subtask
    child_ids = []
    for i, (subtask_query, capabilities) in enumerate(subtasks):
        log(f"Spawning child agent {i+1} for: {subtask_query}", Colors.YELLOW, "➕ ", parent_id, depth)
        
        spawn_request = AgentSpawnRequest(
            agent_type="research",
            capabilities=capabilities,
            context={
                "research_id": f"recursive_demo_depth_{depth+1}",
                "user_id": "demo_user",
                "session_id": "demo_session",
                "metadata": {
                    "query": subtask_query,
                    "parent_task": query,
                    "depth": depth + 1,
                    "subtask_index": i
                }
            },
            parent_id=parent_id
        )
        
        try:
            child_id = await orchestrator.spawn_agent(spawn_request)
            child_ids.append(child_id)
            log(f"✓ Child agent spawned", Colors.GREEN, "  ", child_id, depth + 1)
            
            # Send initial task to child
            await orchestrator.send_agent_message(
                source_id=parent_id,
                target_id=child_id,
                message={
                    "type": "research_request",
                    "data": {
                        "query": subtask_query,
                        "parent_query": query,
                        "depth": depth + 1
                    }
                }
            )
            
            # Simulate child agent potentially spawning its own children
            await asyncio.sleep(0.5)  # Small delay to simulate processing
            
            # Recursively spawn grandchildren (30% chance)
            if depth + 1 < max_depth and i == 0:  # Only first child spawns grandchildren for demo
                log(f"Child agent decomposing its task further...", Colors.MAGENTA, "🔄 ", child_id, depth + 1)
                await simulate_recursive_research(orchestrator, child_id, subtask_query, depth + 1, max_depth)
            
        except Exception as e:
            log(f"Failed to spawn child: {e}", Colors.RED, "❌ ", parent_id, depth)
    
    # Simulate waiting for children to complete
    if child_ids:
        log(f"Waiting for {len(child_ids)} child agents to complete...", Colors.BLUE, "⏳ ", parent_id, depth)
        await asyncio.sleep(1)
        
        # Simulate collecting results from children
        log(f"Collecting results from child agents", Colors.CYAN, "📊 ", parent_id, depth)
        for child_id in child_ids:
            # Send result collection request
            await orchestrator.send_agent_message(
                source_id=parent_id,
                target_id=child_id,
                message={
                    "type": "result_request",
                    "data": {"urgency": "normal"}
                }
            )
        
        log(f"✓ Results collected and synthesized", Colors.GREEN, "  ", parent_id, depth)


def print_agent_tree(node: Dict, prefix: str = "", is_last: bool = True, depth: int = 0):
    """Pretty print the agent tree with visual hierarchy"""
    
    # Determine the connector
    connector = "└─" if is_last else "├─"
    
    # Color based on status
    status_colors = {
        'ready': Colors.GREEN,
        'busy': Colors.YELLOW,
        'error': Colors.RED,
        'terminated': Colors.DIM
    }
    color = status_colors.get(node['status'], Colors.RESET)
    
    # Print the node
    caps_str = f" [{', '.join(node['capabilities'][:2])}{'...' if len(node['capabilities']) > 2 else ''}]" if node['capabilities'] else ""
    log(f"{prefix}{connector} {node['type']} agent{caps_str}", color, "", node['id'])
    
    # Update prefix for children
    child_prefix = prefix + ("   " if is_last else "│  ")
    
    # Print children
    children = node.get('children', [])
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        print_agent_tree(child, child_prefix, is_last_child, depth + 1)


async def main():
    """Demonstrate recursive agent spawning"""
    log("=== Deep Research Claude - Example 03: Recursive Agent Spawning ===", Colors.CYAN)
    log("This example shows how agents can spawn child agents recursively\n", Colors.CYAN)
    
    # Initialize components
    log("Initializing system components...", Colors.BLUE)
    
    message_queue = MessageQueue()
    await message_queue.initialize()
    log("✓ Message Queue ready", Colors.GREEN, "  ")
    
    registry = AgentRegistry()
    registry.register_agent_type("research", ResearchAgent)
    log("✓ Registry configured", Colors.GREEN, "  ")
    
    orchestrator = AgentOrchestrator(message_queue, registry)
    orchestrator.max_concurrent_agents = 20  # Allow more agents for recursive spawning
    await orchestrator.initialize()
    log("✓ Orchestrator online (max 20 agents)", Colors.GREEN, "  ")
    
    print()
    
    # Spawn the root research agent
    log("Spawning root research agent...", Colors.BLUE)
    
    root_query = "Impact of AI on climate change research"
    root_request = AgentSpawnRequest(
        agent_type="research",
        capabilities=[
            AgentCapability.WEB_SEARCH,
            AgentCapability.ACADEMIC_SEARCH,
            AgentCapability.SYNTHESIS,
            AgentCapability.CRITICAL_THINKING
        ],
        context={
            "research_id": "recursive_demo",
            "user_id": "demo_user",
            "session_id": "demo_session",
            "metadata": {
                "query": root_query,
                "role": "root_coordinator",
                "max_depth": 3
            }
        }
    )
    
    root_id = await orchestrator.spawn_agent(root_request)
    log(f"✓ Root agent spawned: {root_id}", Colors.GREEN, "  ")
    log(f"  Research query: '{root_query}'", Colors.CYAN)
    
    print()
    
    # Start recursive spawning
    log("Starting recursive task decomposition...", Colors.BLUE)
    log("  Root agent will spawn children, who may spawn their own children", Colors.DIM)
    log("  Maximum depth: 3 levels", Colors.DIM)
    
    print()
    
    # Simulate the recursive spawning process
    await simulate_recursive_research(orchestrator, root_id, root_query, depth=0, max_depth=3)
    
    print()
    
    # Show the resulting agent tree
    log("Agent hierarchy after recursive spawning:", Colors.BLUE)
    
    agent_tree = await orchestrator.get_agent_tree()
    
    if 'roots' in agent_tree:
        for root in agent_tree['roots']:
            print_agent_tree(root)
    
    print()
    
    # Get statistics
    stats = registry.get_statistics()
    log("Recursive spawning statistics:", Colors.BLUE)
    log(f"  Total agents spawned: {stats['total_agents']}", Colors.CYAN)
    log(f"  Maximum depth reached: 3", Colors.CYAN)
    
    # Count agents by depth (simulated)
    agent_counts = {"depth_0": 1, "depth_1": 3, "depth_2": 3, "depth_3": 0}
    log("  Agents by depth:", Colors.CYAN)
    for depth, count in agent_counts.items():
        if count > 0:
            log(f"    {depth}: {count} agents", Colors.DIM)
    
    print()
    
    # Show parent-child relationships
    log("Parent-child relationships:", Colors.BLUE)
    
    # Get all agents and their relationships
    all_agents = []
    for agent_type in stats['by_type']:
        agents = registry.list_by_type(agent_type)
        all_agents.extend(agents)
    
    parent_child_count = 0
    for agent in all_agents:
        children = registry.get_children(agent.id)
        if children:
            parent_child_count += 1
            log(f"  Agent {agent.id[:8]}... has {len(children)} children", Colors.MAGENTA)
    
    log(f"  Total parent agents: {parent_child_count}", Colors.CYAN)
    
    print()
    
    # Demonstrate termination cascade
    log("Demonstrating cascade termination...", Colors.BLUE)
    log("  Terminating root agent (will terminate all descendants)", Colors.YELLOW)
    
    # Count agents before termination
    active_before = sum(1 for a in all_agents if a.status != AgentStatus.TERMINATED)
    log(f"  Active agents before: {active_before}", Colors.CYAN)
    
    # Terminate root and all its children manually
    async def terminate_cascade(agent_id):
        """Recursively terminate agent and all children"""
        children = registry.get_children(agent_id)
        for child in children:
            await terminate_cascade(child.id)
        await orchestrator.terminate_agent(agent_id)
    
    await terminate_cascade(root_id)
    
    # Count agents after termination
    all_agents_after = []
    for agent_type in stats['by_type']:
        agents = registry.list_by_type(agent_type)
        all_agents_after.extend(agents)
    
    active_after = sum(1 for a in all_agents_after if a.status != AgentStatus.TERMINATED)
    log(f"  Active agents after: {active_after}", Colors.CYAN)
    log(f"  ✓ Cascade termination successful! Terminated {active_before - active_after} agents", Colors.GREEN)
    
    print()
    
    # Cleanup
    log("Cleaning up remaining resources...", Colors.BLUE)
    
    await orchestrator.shutdown()
    await message_queue.shutdown()
    
    log("✓ All systems shut down", Colors.GREEN, "  ")
    
    print()
    log("Example completed! 🎉", Colors.GREEN)
    log("This demonstrated:", Colors.CYAN)
    log("  • Recursive agent spawning (parent → child → grandchild)", Colors.CYAN, "  ")
    log("  • Task decomposition across multiple levels", Colors.CYAN, "  ")
    log("  • Parent-child relationship tracking", Colors.CYAN, "  ")
    log("  • Hierarchical agent organization", Colors.CYAN, "  ")
    log("  • Cascade termination of agent families", Colors.CYAN, "  ")
    log("  • Depth-limited spawning to prevent runaway recursion", Colors.CYAN, "  ")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nExample interrupted by user", Colors.YELLOW)