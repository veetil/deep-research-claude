"""
Unit tests for AgentOrchestrator - following London School TDD
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from src.core.orchestrator import AgentOrchestrator, AgentSpawnRequest
from src.agents.base import BaseAgent, AgentCapability, AgentStatus


class TestAgentOrchestrator:
    """Test suite for AgentOrchestrator"""
    
    @pytest.fixture
    def mock_message_queue(self):
        """Create a mock message queue"""
        mock = AsyncMock()
        mock.publish = AsyncMock()
        mock.subscribe = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create a mock agent registry"""
        mock = Mock()
        mock.register = Mock()
        mock.get = Mock()
        mock.list_by_capability = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def orchestrator(self, mock_message_queue, mock_agent_registry):
        """Create an orchestrator instance with mocked dependencies"""
        # Ensure registry has proper mock methods
        mock_agent_registry.get_children = Mock(return_value=[])
        return AgentOrchestrator(
            message_queue=mock_message_queue,
            agent_registry=mock_agent_registry
        )
    
    @pytest.mark.asyncio
    async def test_spawn_single_agent_success(self, orchestrator, mock_agent_registry):
        """Test spawning a single agent successfully"""
        # Arrange
        spawn_request = AgentSpawnRequest(
            agent_type="research",
            capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.ANALYSIS],
            context={"query": "test research"},
            parent_id=None
        )
        
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.id = "agent-123"
        mock_agent.status = AgentStatus.READY
        mock_agent.initialize = AsyncMock()
        
        mock_agent_registry.create_agent = Mock(return_value=mock_agent)
        
        # Act
        result = await orchestrator.spawn_agent(spawn_request)
        
        # Assert
        assert result == "agent-123"
        mock_agent_registry.create_agent.assert_called_once_with(
            agent_type="research",
            capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.ANALYSIS]
        )
        mock_agent.initialize.assert_called_once_with(spawn_request.context)
        mock_agent_registry.register.assert_called_once_with(mock_agent)
    
    @pytest.mark.asyncio
    async def test_spawn_multiple_agents_parallel(self, orchestrator, mock_agent_registry):
        """Test spawning multiple agents in parallel"""
        # Arrange
        agent_configs = [
            {"type": "research", "capabilities": [AgentCapability.WEB_SEARCH]},
            {"type": "analysis", "capabilities": [AgentCapability.ANALYSIS]},
            {"type": "synthesis", "capabilities": [AgentCapability.SYNTHESIS]}
        ]
        
        mock_agents = []
        for i, config in enumerate(agent_configs):
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.id = f"agent-{i}"
            mock_agent.status = AgentStatus.READY
            mock_agent.initialize = AsyncMock()
            mock_agents.append(mock_agent)
        
        mock_agent_registry.create_agent = Mock(side_effect=mock_agents)
        
        # Act
        agent_ids = await orchestrator.spawn_agents_parallel(agent_configs)
        
        # Assert
        assert len(agent_ids) == 3
        assert agent_ids == ["agent-0", "agent-1", "agent-2"]
        assert mock_agent_registry.create_agent.call_count == 3
    
    @pytest.mark.asyncio
    async def test_coordinate_agents_communication(self, orchestrator, mock_message_queue):
        """Test agent coordination through message passing"""
        # Arrange
        source_agent_id = "agent-source"
        target_agent_id = "agent-target"
        message = {
            "type": "research_request",
            "data": {"query": "test query"}
        }
        
        # Act
        await orchestrator.send_agent_message(source_agent_id, target_agent_id, message)
        
        # Assert
        mock_message_queue.publish.assert_called_once()
        published_message = mock_message_queue.publish.call_args[0][0]
        assert published_message["source"] == source_agent_id
        assert published_message["target"] == target_agent_id
        assert published_message["payload"] == message
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self, orchestrator, mock_agent_registry):
        """Test agent lifecycle - create, pause, resume, terminate"""
        # Arrange
        agent_id = "agent-lifecycle"
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.id = agent_id
        mock_agent.status = AgentStatus.READY
        mock_agent.pause = AsyncMock()
        mock_agent.resume = AsyncMock()
        mock_agent.terminate = AsyncMock()
        
        mock_agent_registry.get.return_value = mock_agent
        
        # Act & Assert - Pause
        await orchestrator.pause_agent(agent_id)
        mock_agent.pause.assert_called_once()
        assert mock_agent.status == AgentStatus.PAUSED
        
        # Act & Assert - Resume
        await orchestrator.resume_agent(agent_id)
        mock_agent.resume.assert_called_once()
        assert mock_agent.status == AgentStatus.READY
        
        # Act & Assert - Terminate
        await orchestrator.terminate_agent(agent_id)
        mock_agent.terminate.assert_called_once()
        assert mock_agent.status == AgentStatus.TERMINATED
    
    @pytest.mark.asyncio
    async def test_recursive_agent_spawning(self, orchestrator, mock_agent_registry):
        """Test recursive agent spawning with parent-child relationships"""
        # Arrange
        parent_agent_id = "parent-agent"
        
        # Create parent agent
        parent_agent = Mock(spec=BaseAgent)
        parent_agent.id = parent_agent_id
        parent_agent.can_spawn_children = True
        
        # Create child agent
        child_agent = Mock(spec=BaseAgent)
        child_agent.id = "child-agent"
        child_agent.parent_id = parent_agent_id
        child_agent.initialize = AsyncMock()
        
        mock_agent_registry.get.return_value = parent_agent
        mock_agent_registry.create_agent = Mock(return_value=child_agent)
        
        # Act
        spawn_request = AgentSpawnRequest(
            agent_type="research",
            capabilities=[AgentCapability.WEB_SEARCH],
            context={"inherited": True},
            parent_id=parent_agent_id
        )
        
        child_id = await orchestrator.spawn_agent(spawn_request)
        
        # Assert
        assert child_id == "child-agent"
        assert child_agent.parent_id == parent_agent_id
    
    @pytest.mark.asyncio
    async def test_agent_capability_matching(self, orchestrator, mock_agent_registry):
        """Test finding agents by required capabilities"""
        # Arrange
        research_agent = Mock(id="research-1", capabilities=[AgentCapability.WEB_SEARCH])
        analysis_agent = Mock(id="analysis-1", capabilities=[AgentCapability.ANALYSIS])
        multi_agent = Mock(id="multi-1", capabilities=[
            AgentCapability.WEB_SEARCH, 
            AgentCapability.ANALYSIS
        ])
        
        all_agents = [research_agent, analysis_agent, multi_agent]
        mock_agent_registry.list_by_capability = Mock(side_effect=lambda cap: [
            agent for agent in all_agents if cap in agent.capabilities
        ])
        
        # Act
        web_search_agents = await orchestrator.find_agents_by_capability(
            AgentCapability.WEB_SEARCH
        )
        analysis_agents = await orchestrator.find_agents_by_capability(
            AgentCapability.ANALYSIS
        )
        
        # Assert
        assert len(web_search_agents) == 2
        assert research_agent in web_search_agents
        assert multi_agent in web_search_agents
        
        assert len(analysis_agents) == 2
        assert analysis_agent in analysis_agents
        assert multi_agent in analysis_agents
    
    @pytest.mark.asyncio
    async def test_max_agents_limit(self, orchestrator, mock_agent_registry):
        """Test enforcement of maximum concurrent agents limit"""
        # Arrange
        orchestrator.max_concurrent_agents = 3
        orchestrator.active_agents = {"agent-1", "agent-2", "agent-3"}
        
        spawn_request = AgentSpawnRequest(
            agent_type="research",
            capabilities=[],
            context={}
        )
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Maximum concurrent agents limit reached"):
            await orchestrator.spawn_agent(spawn_request)
    
    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self, orchestrator, mock_agent_registry):
        """Test agent health monitoring and automatic recovery"""
        # Arrange
        unhealthy_agent = Mock(spec=BaseAgent)
        unhealthy_agent.id = "unhealthy-agent"
        unhealthy_agent.status = AgentStatus.ERROR
        unhealthy_agent.health_check = AsyncMock(return_value=False)
        unhealthy_agent.restart = AsyncMock()
        
        healthy_agent = Mock(spec=BaseAgent)
        healthy_agent.id = "healthy-agent"
        healthy_agent.status = AgentStatus.READY
        healthy_agent.health_check = AsyncMock(return_value=True)
        
        mock_agent_registry.list_all = Mock(return_value=[unhealthy_agent, healthy_agent])
        
        # Act
        health_report = await orchestrator.check_agent_health()
        
        # Assert
        assert health_report["total_agents"] == 2
        assert health_report["healthy_agents"] == 1
        assert health_report["unhealthy_agents"] == 1
        assert unhealthy_agent.id in health_report["recovery_attempted"]
        unhealthy_agent.restart.assert_called_once()