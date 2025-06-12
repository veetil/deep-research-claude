"""
Unit tests for enhanced base agent with SPCT metrics
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import asyncio
from typing import Dict, Any, List

from src.agents.enhanced_base import (
    EnhancedBaseAgent,
    AgentMetrics,
    Task,
    AgentResult,
    AgentContext
)
# from src.core.exceptions import BudgetExceededError  # Not implemented yet


class TestAgentMetrics:
    """Test cases for AgentMetrics dataclass"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = AgentMetrics()
        
        assert metrics.task_count == 0
        assert metrics.success_count == 0
        assert metrics.error_count == 0
        assert metrics.total_latency_ms == 0
        assert metrics.quality_scores == []
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = AgentMetrics(task_count=10, success_count=8)
        assert metrics.success_rate == 0.8
        
        # Test zero division
        metrics = AgentMetrics(task_count=0, success_count=0)
        assert metrics.success_rate == 0.0
    
    def test_average_latency_calculation(self):
        """Test average latency calculation"""
        metrics = AgentMetrics(task_count=5, total_latency_ms=500)
        assert metrics.average_latency_ms == 100.0
        
        # Test zero division
        metrics = AgentMetrics(task_count=0, total_latency_ms=0)
        assert metrics.average_latency_ms == 0.0
    
    def test_average_quality_calculation(self):
        """Test average quality score calculation"""
        metrics = AgentMetrics(quality_scores=[0.8, 0.9, 0.7, 0.85])
        assert metrics.average_quality == 0.8125
        
        # Test empty scores
        metrics = AgentMetrics(quality_scores=[])
        assert metrics.average_quality == 0.0


class TestEnhancedBaseAgent:
    """Test cases for EnhancedBaseAgent"""
    
    @pytest.fixture
    def mock_cli_manager(self):
        """Create mock CLI manager"""
        return Mock()
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager"""
        mock = Mock()
        mock.get_context = AsyncMock(return_value={
            "previous_results": ["result1", "result2"]
        })
        return mock
    
    @pytest.fixture
    def mock_budget_manager(self):
        """Create mock budget manager"""
        mock = Mock()
        mock.can_proceed = AsyncMock(return_value=True)
        mock.record_usage = AsyncMock()
        return mock
    
    @pytest.fixture
    def test_agent(self, mock_cli_manager, mock_memory_manager, mock_budget_manager):
        """Create a test agent implementation"""
        class TestAgent(EnhancedBaseAgent):
            async def build_quality_prompt(self, task: Task, context: Dict) -> str:
                return f"Test prompt for task: {task.query}"
            
            async def evaluate_quality(self, result: AgentResult) -> float:
                # Simple quality calculation based on result
                if result.success and result.sources:
                    return 0.9
                elif result.success:
                    return 0.7
                return 0.3
            
            async def get_optimized_context(self, task: Task) -> Dict[str, Any]:
                # Mock context optimization
                return await self.memory.get_context(task.id)
            
            async def execute_with_monitoring(self, prompt: str) -> AgentResult:
                # Mock execution
                return AgentResult(
                    success=True,
                    content="Test result",
                    sources=[{"name": "source1", "url": "http://example.com"}],
                    tokens_used=100
                )
            
            async def graceful_degradation(self, task: Task) -> AgentResult:
                # Mock degradation
                return AgentResult(
                    success=True,
                    content="Degraded result",
                    sources=[],
                    tokens_used=50,
                    degraded=True
                )
            
            async def handle_error(self, error: Exception, task: Task) -> AgentResult:
                # Mock error handling
                return AgentResult(
                    success=False,
                    content=f"Error: {str(error)}",
                    sources=[],
                    tokens_used=0
                )
        
        return TestAgent(
            agent_id="test_agent_001",
            role="test",
            cli_manager=mock_cli_manager,
            memory_manager=mock_memory_manager,
            budget_manager=mock_budget_manager
        )
    
    async def test_successful_task_execution(self, test_agent, mock_budget_manager):
        """Test successful task execution with metrics tracking"""
        task = Task(
            id="task_001",
            query="Test research query",
            parameters={"depth": "normal"}
        )
        
        result = await test_agent.execute(task)
        
        # Verify result
        assert result.success
        assert result.content == "Test result"
        assert len(result.sources) == 1
        assert result.tokens_used == 100
        
        # Verify metrics updated
        assert test_agent.metrics.task_count == 1
        assert test_agent.metrics.success_count == 1
        assert test_agent.metrics.error_count == 0
        assert test_agent.metrics.total_latency_ms > 0
        assert len(test_agent.metrics.quality_scores) == 1
        assert test_agent.metrics.quality_scores[0] == 0.9
        
        # Verify budget recording
        mock_budget_manager.record_usage.assert_called_once_with("test_agent_001", 100)
    
    async def test_budget_exceeded_graceful_degradation(self, test_agent, mock_budget_manager):
        """Test graceful degradation when budget exceeded"""
        # Set budget exceeded
        mock_budget_manager.can_proceed = AsyncMock(return_value=False)
        
        task = Task(
            id="task_002",
            query="Test query with budget exceeded",
            parameters={}
        )
        
        result = await test_agent.execute(task)
        
        # Verify degraded result
        assert result.success
        assert result.content == "Degraded result"
        assert result.degraded
        assert result.tokens_used == 50
        
        # Verify metrics still updated
        assert test_agent.metrics.task_count == 1
        assert test_agent.metrics.success_count == 1
    
    async def test_error_handling_with_metrics(self, test_agent):
        """Test error handling updates metrics correctly"""
        # Make execute_with_monitoring raise an error
        test_agent.execute_with_monitoring = AsyncMock(
            side_effect=Exception("Execution failed")
        )
        
        task = Task(
            id="task_003",
            query="Test query that will fail",
            parameters={}
        )
        
        result = await test_agent.execute(task)
        
        # Verify error result
        assert not result.success
        assert "Error: Execution failed" in result.content
        
        # Verify metrics
        assert test_agent.metrics.task_count == 1
        assert test_agent.metrics.success_count == 0
        assert test_agent.metrics.error_count == 1
    
    async def test_quality_tracking(self, test_agent):
        """Test quality score tracking across multiple tasks"""
        # Execute several tasks with different quality outcomes
        tasks = [
            Task(id=f"task_{i}", query=f"Query {i}", parameters={})
            for i in range(5)
        ]
        
        # Mock different quality scores
        quality_scores = [0.9, 0.8, 0.7, 0.85, 0.95]
        original_evaluate = test_agent.evaluate_quality
        
        async def mock_evaluate(result):
            return quality_scores.pop(0) if quality_scores else 0.5
        
        test_agent.evaluate_quality = mock_evaluate
        
        # Execute tasks
        for task in tasks:
            await test_agent.execute(task)
        
        # Verify quality tracking
        assert test_agent.metrics.task_count == 5
        assert test_agent.metrics.success_count == 5
        assert len(test_agent.metrics.quality_scores) == 5
        assert test_agent.metrics.average_quality == 0.84  # (0.9+0.8+0.7+0.85+0.95)/5
    
    async def test_latency_tracking(self, test_agent):
        """Test latency tracking"""
        # Add delay to execution
        original_execute = test_agent.execute_with_monitoring
        
        async def delayed_execute(prompt):
            await asyncio.sleep(0.1)  # 100ms delay
            return await original_execute(prompt)
        
        test_agent.execute_with_monitoring = delayed_execute
        
        task = Task(id="task_latency", query="Test latency", parameters={})
        await test_agent.execute(task)
        
        # Verify latency tracked (should be at least 100ms)
        assert test_agent.metrics.total_latency_ms >= 100
        assert test_agent.metrics.average_latency_ms >= 100
    
    async def test_plugin_config_handling(self):
        """Test agent handles plugin configuration"""
        plugin_config = {
            "specialization": "medical",
            "api_key": "test_key",
            "quality_threshold": 0.95
        }
        
        class PluginAgent(EnhancedBaseAgent):
            async def build_quality_prompt(self, task: Task, context: Dict) -> str:
                # Use plugin config in prompt
                return f"Specialization: {self.plugin_config.get('specialization')}"
            
            async def evaluate_quality(self, result: AgentResult) -> float:
                return self.plugin_config.get('quality_threshold', 0.8)
        
        agent = PluginAgent(
            agent_id="plugin_agent",
            role="test",
            cli_manager=Mock(),
            memory_manager=Mock(),
            budget_manager=Mock(),
            plugin_config=plugin_config
        )
        
        assert agent.plugin_config == plugin_config
        prompt = await agent.build_quality_prompt(
            Task(id="t1", query="test", parameters={}), {}
        )
        assert "medical" in prompt
    
    async def test_metrics_persistence(self, test_agent):
        """Test metrics persist across multiple executions"""
        tasks = [
            Task(id=f"task_{i}", query=f"Query {i}", parameters={})
            for i in range(3)
        ]
        
        # Execute tasks
        for task in tasks:
            await test_agent.execute(task)
        
        # Verify cumulative metrics
        assert test_agent.metrics.task_count == 3
        assert test_agent.metrics.success_count == 3
        assert test_agent.metrics.success_rate == 1.0
        
        # Make one fail
        test_agent.execute_with_monitoring = AsyncMock(
            side_effect=Exception("Failed")
        )
        
        await test_agent.execute(
            Task(id="fail_task", query="Fail", parameters={})
        )
        
        # Verify updated metrics
        assert test_agent.metrics.task_count == 4
        assert test_agent.metrics.success_count == 3
        assert test_agent.metrics.error_count == 1
        assert test_agent.metrics.success_rate == 0.75
    
    async def test_context_optimization(self, test_agent, mock_memory_manager):
        """Test context optimization is called"""
        task = Task(id="task_ctx", query="Test context", parameters={})
        
        await test_agent.execute(task)
        
        # Verify memory manager was called for context
        mock_memory_manager.get_context.assert_called_once_with("task_ctx")
    
    async def test_concurrent_task_execution(self, test_agent):
        """Test concurrent task execution with proper metrics"""
        tasks = [
            Task(id=f"concurrent_{i}", query=f"Query {i}", parameters={})
            for i in range(5)
        ]
        
        # Execute tasks concurrently
        results = await asyncio.gather(*[
            test_agent.execute(task) for task in tasks
        ])
        
        # Verify all succeeded
        assert all(r.success for r in results)
        
        # Verify metrics are thread-safe
        assert test_agent.metrics.task_count == 5
        assert test_agent.metrics.success_count == 5
        assert len(test_agent.metrics.quality_scores) == 5