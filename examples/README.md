# Deep Research Claude - Examples

This directory contains example scripts demonstrating key features of the Deep Research Claude multi-agent system. Each example includes detailed logging to show what's happening beyond simple "test passed" messages.

## Running the Examples

Make sure you have the project dependencies installed:

```bash
cd deep-research-claude
pip install -r requirements.txt
```

Then run any example:

```bash
python examples/01_basic_agent_spawning.py
python examples/02_multi_agent_coordination.py
python examples/03_recursive_agent_spawning.py
```

## Example Descriptions

### 01_basic_agent_spawning.py
**Basic Agent Lifecycle**

Demonstrates the fundamental operations of spawning a single agent and managing its lifecycle:
- Spawning a research agent with specific capabilities
- Sending research requests
- Monitoring agent status and metrics
- Checking message queue statistics
- Viewing agent hierarchy
- Graceful termination

**Key concepts shown:**
- Agent initialization
- Message passing
- Status monitoring
- Clean shutdown

### 02_multi_agent_coordination.py
**Multi-Agent Collaboration**

Shows how multiple specialized agents work together on a complex research task:
- Spawning multiple agents in parallel
- Capability-based agent discovery
- Coordinated task assignment
- Inter-agent messaging and broadcast
- Health monitoring and recovery
- System-wide statistics

**Key concepts shown:**
- Parallel operations
- Agent specialization
- Task coordination
- Health checks
- Message activity tracking

### 03_recursive_agent_spawning.py
**Hierarchical Task Decomposition**

Demonstrates the powerful recursive spawning feature where agents create child agents:
- Root agent spawning children for subtasks
- Children spawning their own children (grandchildren)
- Multi-level task decomposition
- Parent-child relationship tracking
- Cascade termination of agent families
- Depth-limited recursion

**Key concepts shown:**
- Recursive spawning
- Task decomposition
- Agent hierarchies
- Relationship tracking
- Cascade operations

## Output Features

All examples include:
- **Colored output** for easy reading
- **Timestamps** showing when each action occurs
- **Agent IDs** to track individual agents
- **Progress indicators** showing ongoing operations
- **Status symbols** (✓, ❌, ⏳, etc.) for quick visual feedback
- **Hierarchical formatting** for tree structures
- **Summary statistics** at the end

## Understanding the Logs

### Color Coding
- 🔵 **Blue**: Major steps and phases
- 🟢 **Green**: Successful operations
- 🟡 **Yellow**: Warnings or in-progress operations
- 🔴 **Red**: Errors or failures
- 🟣 **Magenta**: Agent-specific information
- 🔷 **Cyan**: System information and summaries

### Log Structure
```
[HH:MM:SS.mmm] [agent-id] <indent> <prefix-emoji> <color>message</color>
```

- **Timestamp**: Shows millisecond precision
- **Agent ID**: First 8 characters of the agent's UUID (when applicable)
- **Indentation**: Shows hierarchy/nesting level
- **Prefix emoji**: Quick visual indicator of the operation type
- **Colored message**: The actual log content

## Extending the Examples

To create your own example:

1. Copy the basic structure from any example
2. Import the necessary components
3. Initialize the core systems (MessageQueue, Registry, Orchestrator)
4. Implement your specific scenario
5. Add detailed logging with colors and timestamps
6. Include cleanup at the end

## Common Patterns

### Initialization
```python
message_queue = MessageQueue()
await message_queue.initialize()

registry = AgentRegistry()
registry.register_agent_type("research", ResearchAgent)

orchestrator = AgentOrchestrator(message_queue, registry)
await orchestrator.initialize()
```

### Agent Spawning
```python
spawn_request = AgentSpawnRequest(
    agent_type="research",
    capabilities=[AgentCapability.WEB_SEARCH],
    context={"key": "value"}
)
agent_id = await orchestrator.spawn_agent(spawn_request)
```

### Message Sending
```python
await orchestrator.send_agent_message(
    source_id="orchestrator",
    target_id=agent_id,
    message={"type": "request", "data": {...}}
)
```

### Cleanup
```python
await orchestrator.terminate_agent(agent_id)
await orchestrator.shutdown()
await message_queue.shutdown()
```

## Troubleshooting

If examples fail to run:

1. **Module not found**: Ensure you're running from the project root directory
2. **Async errors**: Make sure you're using Python 3.11+
3. **Import errors**: Check that all dependencies are installed
4. **Permission errors**: Ensure you have write permissions for log output

## Next Steps

After running these examples, you can:
- Modify them to test different scenarios
- Create new examples for specific use cases
- Use them as templates for integration tests
- Reference them when building applications using the system