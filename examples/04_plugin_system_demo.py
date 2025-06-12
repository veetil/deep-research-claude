#!/usr/bin/env python3
"""
Example 04: Plugin System Demo
Demonstrates how to use the plugin system to extend agent capabilities
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.plugins import PluginSystem, AgentPlugin
from src.agents.agent_factory import AgentFactory
from src.agents.enhanced_base import Task, AgentResult


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


def log(message: str, color: str = Colors.RESET, prefix: str = ""):
    """Pretty print log messages with timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET} {prefix}{color}{message}{Colors.RESET}")


# Mock implementations for the example
class MockCLIManager:
    async def execute(self, prompt: str):
        return {"response": "Mock response", "tokens": 100}


class MockMemoryManager:
    async def get_context(self, task_id: str):
        return {"previous_research": "Previous findings..."}


class MockBudgetManager:
    async def can_proceed(self, agent_id: str):
        return True
    
    async def record_usage(self, agent_id: str, tokens: int):
        pass


async def main():
    """Demonstrate plugin system functionality"""
    log("=== Deep Research Claude - Example 04: Plugin System Demo ===", Colors.CYAN)
    log("This example shows how to create and use plugins to extend agent capabilities\n", Colors.CYAN)
    
    # Step 1: Initialize plugin system
    log("Step 1: Initializing plugin system...", Colors.BLUE)
    plugin_system = PluginSystem()
    log("✓ Plugin system initialized", Colors.GREEN, "  ")
    
    print()
    
    # Step 2: Create a medical research plugin
    log("Step 2: Creating medical research plugin...", Colors.BLUE)
    
    medical_plugin = AgentPlugin(
        name="medical_research",
        version="1.0.0",
        agents=["MedicalResearchAgent", "ClinicalTrialAgent"],
        tools=["pubmed_search", "clinical_guidelines", "drug_interactions"],
        config={
            "specialization": "medical",
            "api_key": "demo_key",
            "peer_review_required": True
        },
        author="Medical AI Team",
        description="Specialized agents for medical and healthcare research"
    )
    
    log(f"  Plugin: {medical_plugin.name} v{medical_plugin.version}", Colors.YELLOW)
    log(f"  Author: {medical_plugin.author}", Colors.YELLOW)
    log(f"  Agents: {', '.join(medical_plugin.agents)}", Colors.YELLOW)
    log(f"  Tools: {', '.join(medical_plugin.tools)}", Colors.YELLOW)
    
    print()
    
    # Step 3: Register the plugin
    log("Step 3: Registering plugin...", Colors.BLUE)
    
    try:
        await plugin_system.register(medical_plugin)
        log("✓ Plugin registered successfully!", Colors.GREEN, "  ")
    except Exception as e:
        log(f"✗ Failed to register plugin: {e}", Colors.RED, "  ")
    
    # Check registration
    if plugin_system.is_registered("medical_research"):
        log("✓ Plugin verified in registry", Colors.GREEN, "  ")
    
    print()
    
    # Step 4: Discover available resources
    log("Step 4: Discovering available resources...", Colors.BLUE)
    
    # List all plugins
    plugins = plugin_system.list_plugins()
    log(f"  Registered plugins: {', '.join(plugins)}", Colors.CYAN)
    
    # Get plugin info
    plugin_info = plugin_system.get_plugin_info("medical_research")
    log("  Plugin details:", Colors.CYAN)
    log(f"    Status: {plugin_info['status']}", Colors.DIM)
    log(f"    Load time: {plugin_info.get('load_time_ms', 0):.2f}ms", Colors.DIM)
    log(f"    Agent count: {plugin_info.get('agent_count', 0)}", Colors.DIM)
    log(f"    Tool count: {plugin_info.get('tool_count', 0)}", Colors.DIM)
    
    # Get available agent types
    agent_types = plugin_system.get_agent_types()
    log(f"  Available agents: {', '.join(agent_types)}", Colors.CYAN)
    
    # Get available tools
    tools = plugin_system.get_available_tools()
    log(f"  Available tools: {', '.join(tools)}", Colors.CYAN)
    
    print()
    
    # Step 5: Create agent factory with plugin system
    log("Step 5: Creating agents with plugin support...", Colors.BLUE)
    
    factory = AgentFactory(plugin_system=plugin_system)
    
    # Get all available agents (core + plugins)
    all_agents = factory.get_available_agents()
    log(f"  Total agent types available: {len(all_agents)}", Colors.MAGENTA)
    
    # Show core vs plugin agents
    core_agents = list(factory.CORE_AGENTS.keys())
    plugin_agents = [a for a in all_agents if a not in core_agents]
    
    log(f"  Core agents: {len(core_agents)}", Colors.MAGENTA)
    log(f"  Plugin agents: {len(plugin_agents)}", Colors.MAGENTA)
    
    print()
    
    # Step 6: Use a plugin-based agent
    log("Step 6: Using a core agent (Research)...", Colors.BLUE)
    
    # Create mock managers
    cli_manager = MockCLIManager()
    memory_manager = MockMemoryManager()
    budget_manager = MockBudgetManager()
    
    # Create a research agent
    research_agent = factory.create_agent(
        agent_type="research",
        agent_id="research_001",
        cli_manager=cli_manager,
        memory_manager=memory_manager,
        budget_manager=budget_manager
    )
    
    log(f"  Created agent: {research_agent.id} (type: {research_agent.role})", Colors.GREEN)
    
    # Execute a task
    task = Task(
        id="task_001",
        query="What are the latest treatments for Type 2 Diabetes?",
        parameters={"depth": "comprehensive"}
    )
    
    log("  Executing research task...", Colors.YELLOW)
    
    # Mock the execution
    async def mock_execute(prompt):
        return AgentResult(
            success=True,
            content="Latest diabetes treatments include SGLT2 inhibitors...",
            sources=[{"name": "Medical Journal", "url": "http://example.com"}],
            tokens_used=150
        )
    
    research_agent.execute_with_monitoring = mock_execute
    
    result = await research_agent.execute(task)
    
    log(f"  ✓ Task completed!", Colors.GREEN)
    log(f"    Success: {result.success}", Colors.DIM)
    log(f"    Quality score: {result.quality_score:.2f}", Colors.DIM)
    log(f"    Tokens used: {result.tokens_used}", Colors.DIM)
    
    print()
    
    # Step 7: Plugin configuration management
    log("Step 7: Managing plugin configuration...", Colors.BLUE)
    
    # Get current config
    current_config = plugin_system.get_plugin_config("medical_research")
    log("  Current configuration:", Colors.CYAN)
    for key, value in current_config.items():
        log(f"    {key}: {value}", Colors.DIM)
    
    # Update configuration
    await plugin_system.update_plugin_config("medical_research", {
        "peer_review_required": False,
        "max_sources": 10
    })
    
    log("  ✓ Configuration updated", Colors.GREEN)
    
    # Verify update
    updated_config = plugin_system.get_plugin_config("medical_research")
    log("  New configuration:", Colors.CYAN)
    for key, value in updated_config.items():
        log(f"    {key}: {value}", Colors.DIM)
    
    print()
    
    # Step 8: Plugin metrics
    log("Step 8: Checking plugin metrics...", Colors.BLUE)
    
    # Record some usage
    await plugin_system.record_plugin_usage("medical_research", "agent_created", {
        "agent_type": "MedicalResearchAgent"
    })
    await plugin_system.record_plugin_usage("medical_research", "tool_used", {
        "tool": "pubmed_search"
    })
    
    # Get metrics
    metrics = plugin_system.get_plugin_metrics("medical_research")
    log("  Plugin metrics:", Colors.CYAN)
    log(f"    Status: {metrics['status']}", Colors.DIM)
    log(f"    Usage count: {metrics['usage_count']}", Colors.DIM)
    log(f"    Load time: {metrics['load_time_ms']:.2f}ms", Colors.DIM)
    log(f"    Agent count: {metrics['agent_count']}", Colors.DIM)
    log(f"    Tool count: {metrics['tool_count']}", Colors.DIM)
    
    print()
    
    # Step 9: Create a second plugin to show dependencies
    log("Step 9: Demonstrating plugin dependencies...", Colors.BLUE)
    
    # Base plugin
    base_plugin = AgentPlugin(
        name="base_research",
        version="1.0.0",
        agents=["BaseResearchAgent"],
        tools=["basic_search"],
        config={},
        description="Base research capabilities"
    )
    
    # Dependent plugin
    advanced_plugin = AgentPlugin(
        name="advanced_research",
        version="1.0.0",
        agents=["AdvancedResearchAgent"],
        tools=["advanced_search"],
        config={},
        dependencies=["base_research"],
        description="Advanced research requiring base capabilities"
    )
    
    # Try to register dependent first (should fail)
    log("  Trying to register dependent plugin first...", Colors.YELLOW)
    try:
        await plugin_system.register(advanced_plugin)
        log("  ✗ Should have failed!", Colors.RED)
    except Exception as e:
        log(f"  ✓ Correctly failed: {e}", Colors.GREEN)
    
    # Register in correct order
    log("  Registering in correct order...", Colors.YELLOW)
    await plugin_system.register(base_plugin)
    log("  ✓ Base plugin registered", Colors.GREEN)
    
    await plugin_system.register(advanced_plugin)
    log("  ✓ Advanced plugin registered", Colors.GREEN)
    
    print()
    
    # Step 10: Plugin hot reload
    log("Step 10: Demonstrating plugin hot reload...", Colors.BLUE)
    
    # Create updated version
    medical_plugin_v2 = AgentPlugin(
        name="medical_research",
        version="1.1.0",
        agents=["MedicalResearchAgent", "ClinicalTrialAgent", "DrugInteractionAgent"],
        tools=["pubmed_search", "clinical_guidelines", "drug_interactions", "fda_database"],
        config={
            "specialization": "medical",
            "api_key": "demo_key",
            "peer_review_required": True,
            "version": "1.1.0"
        },
        author="Medical AI Team",
        description="Enhanced medical research capabilities"
    )
    
    log("  Hot reloading plugin with new version...", Colors.YELLOW)
    await plugin_system.reload_plugin("medical_research", medical_plugin_v2)
    
    # Verify update
    updated_info = plugin_system.get_plugin_info("medical_research")
    log(f"  ✓ Plugin updated to v{updated_info['version']}", Colors.GREEN)
    log(f"  New agent count: {updated_info['agent_count']}", Colors.DIM)
    log(f"  New tool count: {updated_info['tool_count']}", Colors.DIM)
    
    print()
    
    # Step 11: Cleanup
    log("Step 11: Cleaning up...", Colors.BLUE)
    
    # List all plugins before shutdown
    all_plugins = plugin_system.list_plugins()
    log(f"  Active plugins: {', '.join(all_plugins)}", Colors.CYAN)
    
    # Shutdown system
    await plugin_system.shutdown()
    log("✓ Plugin system shut down", Colors.GREEN, "  ")
    
    # Verify cleanup
    remaining = plugin_system.list_plugins()
    log(f"  Remaining plugins: {len(remaining)}", Colors.CYAN)
    
    print()
    log("Example completed! 🎉", Colors.GREEN)
    log("This demonstrated:", Colors.CYAN)
    log("  • Plugin creation and registration", Colors.CYAN, "  ")
    log("  • Resource discovery (agents, tools)", Colors.CYAN, "  ")
    log("  • Configuration management", Colors.CYAN, "  ")
    log("  • Dependency handling", Colors.CYAN, "  ")
    log("  • Hot reload capability", Colors.CYAN, "  ")
    log("  • Metrics tracking", Colors.CYAN, "  ")
    log("  • Graceful shutdown", Colors.CYAN, "  ")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nExample interrupted by user", Colors.YELLOW)