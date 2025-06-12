#!/usr/bin/env python3
"""
Debug test
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Starting debug test...")

try:
    from src.plugins import AgentPlugin
    print("✓ Import AgentPlugin successful")
    
    # Create a simple plugin
    plugin = AgentPlugin(
        name="test_plugin",
        version="1.0.0",
        agents=["TestAgent"],
        tools=["test_tool"],
        config={"key": "value"}
    )
    print("✓ Plugin created")
    print(f"  Status: {plugin.status}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("Debug test complete")