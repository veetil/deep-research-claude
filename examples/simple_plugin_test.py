#!/usr/bin/env python3
"""
Simple test to verify plugin system works
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.plugins import PluginSystem, AgentPlugin

async def main():
    print("Testing plugin system...")
    
    # Create plugin system
    plugin_system = PluginSystem()
    print("✓ Plugin system created")
    
    # Create a simple plugin
    plugin = AgentPlugin(
        name="test_plugin",
        version="1.0.0",
        agents=["TestAgent"],
        tools=["test_tool"],
        config={"key": "value"}
    )
    print("✓ Plugin created")
    
    # Register it
    await plugin_system.register(plugin)
    print("✓ Plugin registered")
    
    # Check if registered
    if plugin_system.is_registered("test_plugin"):
        print("✓ Plugin found in registry")
    
    # List plugins
    plugins = plugin_system.list_plugins()
    print(f"✓ Plugins: {plugins}")
    
    # Shutdown
    await plugin_system.shutdown()
    print("✓ Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())