# Deep Research Claude

A multi-agent AI system for comprehensive research using Claude CLI with recursive agent spawning and parallel execution.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend, coming soon)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/deep-research-claude.git
cd deep-research-claude
```

2. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services:
```bash
docker-compose up -d
```

4. Check service health:
```bash
curl http://localhost:3000/health
```

## 🏗️ Architecture

### Core Components

- **Agent Orchestrator**: Manages the lifecycle of all agents
- **Message Queue**: RabbitMQ-based communication between agents  
- **Agent Registry**: Tracks and discovers agents by capabilities
- **API Gateway**: FastAPI-based REST API and WebSocket support

### Agent Types (12 Specialized Agents)

1. **Research Agent** ✅ - Web and academic research
2. **Analysis Agent** 🚧 - Data analysis and pattern recognition
3. **Synthesis Agent** 🚧 - Combining information from multiple sources
4. **Judge Agent** 🚧 - Quality assessment and validation
5. **Financial Agent** 🚧 - Financial analysis and modeling
6. **Medical Agent** 🚧 - Medical research and analysis
7. **Legal Agent** 🚧 - Legal research and compliance
8. **Creative Agent** 🚧 - Creative problem solving
9. **Strategic Agent** 🚧 - Strategic planning and optimization
10. **Development Agent** 🚧 - Technical implementation
11. **Translation Agent** 🚧 - Multi-language support
12. **Educational Agent** 🚧 - Learning and teaching optimization

## 📡 API Usage

### Create a Research Task

```bash
curl -X POST http://localhost:3000/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Impact of quantum computing on cryptography",
    "depth": "comprehensive",
    "languages": ["en", "de", "fr"]
  }'
```

### Spawn an Agent

```bash
curl -X POST http://localhost:3000/api/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "research",
    "capabilities": ["web_search", "academic_search"],
    "context": {
      "research_id": "research_123",
      "user_id": "user_456"
    }
  }'
```

### Get System Status

```bash
curl http://localhost:3000/api/system/status
```

### WebSocket for Real-time Updates

```javascript
const ws = new WebSocket('ws://localhost:3000/ws/research/research_123');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Research update:', update);
};
```

## 🧪 Testing

Run the test suite:

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

## 📊 Monitoring

- **RabbitMQ Management**: http://localhost:15672 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## 🔧 Development

### Project Structure

```
deep-research-claude/
├── src/
│   ├── agents/          # Agent implementations
│   ├── api/            # API endpoints
│   ├── core/           # Core system components
│   ├── memory/         # Memory system (coming soon)
│   └── utils/          # Utilities
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── e2e/           # End-to-end tests
├── config/             # Configuration files
├── docker/             # Docker-related files
└── scripts/            # Utility scripts
```

### Adding a New Agent Type

1. Create agent class in `src/agents/`:
```python
from src.agents.base import BaseAgent, AgentCapability

class YourAgent(BaseAgent):
    def __init__(self, **kwargs):
        capabilities = [AgentCapability.YOUR_CAPABILITY]
        super().__init__(agent_type="your_type", capabilities=capabilities, **kwargs)
    
    async def process_message(self, message):
        # Implement message processing
        pass
```

2. Register in `src/core/main.py`:
```python
self.registry.register_agent_type("your_type", YourAgent)
```

## 🚦 Current Status

- ✅ Core infrastructure implemented
- ✅ Agent orchestration working
- ✅ Message queue system operational
- ✅ Research agent implemented
- ✅ API endpoints available
- ✅ Docker configuration complete
- 🚧 Additional agent types in progress
- 🚧 Memory system implementation pending
- 🚧 Frontend development pending

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/deep-research-claude/issues)
- Documentation: [Wiki](https://github.com/yourusername/deep-research-claude/wiki)