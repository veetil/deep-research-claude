"""
Enhanced base agent with SPCT metrics and quality monitoring
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, Set
import uuid
import time


@dataclass
class Task:
    """Represents a task to be executed by an agent"""
    id: str
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentContext:
    """Context for agent execution"""
    research_id: str
    user_id: str
    session_id: str
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from agent execution"""
    success: bool
    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    execution_time_ms: float = 0
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    degraded: bool = False


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking"""
    task_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0
    quality_scores: List[float] = field(default_factory=list)
    tokens_used: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.task_count == 0:
            return 0.0
        return self.success_count / self.task_count
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.task_count == 0:
            return 0.0
        return self.total_latency_ms / self.task_count
    
    @property
    def average_quality(self) -> float:
        """Calculate average quality score"""
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)


class EnhancedBaseAgent(ABC):
    """Base agent with SPCT metrics and quality monitoring"""
    
    # Quality thresholds for different agent types
    QUALITY_THRESHOLDS = {
        'research': 0.85,
        'scientific': 0.90,
        'medical': 0.95,
        'legal': 0.92,
        'financial': 0.93,
        'specifications': 0.90,
        'tester': 0.88,
        'integrator': 0.92,
        'optimizer': 0.85,
        'devops': 0.90
    }
    
    def __init__(self, 
                 agent_id: str,
                 role: str,
                 cli_manager,
                 memory_manager,
                 budget_manager,
                 plugin_config: Optional[Dict] = None):
        self.id = agent_id
        self.role = role
        self.cli = cli_manager
        self.memory = memory_manager
        self.budget = budget_manager
        self.plugin_config = plugin_config or {}
        self.metrics = AgentMetrics()
        self._lock = asyncio.Lock()
    
    async def execute(self, task: Task) -> AgentResult:
        """Execute a task with full monitoring and quality tracking"""
        start_time = time.time()
        
        async with self._lock:
            self.metrics.task_count += 1
        
        try:
            # Check budget
            if not await self.budget.can_proceed(self.id):
                return await self.graceful_degradation(task)
            
            # Get optimized context
            context = await self.get_optimized_context(task)
            
            # Build quality-focused prompt
            prompt = await self.build_quality_prompt(task, context)
            
            # Execute with monitoring
            result = await self.execute_with_monitoring(prompt)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms
            
            # Track metrics
            async with self._lock:
                self.metrics.total_latency_ms += execution_time_ms
                self.metrics.success_count += 1
                self.metrics.tokens_used += result.tokens_used
            
            # Calculate and track quality score
            quality_score = await self.evaluate_quality(result)
            result.quality_score = quality_score
            
            async with self._lock:
                self.metrics.quality_scores.append(quality_score)
            
            # Record budget usage
            await self.budget.record_usage(self.id, result.tokens_used)
            
            return result
            
        except Exception as e:
            async with self._lock:
                self.metrics.error_count += 1
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            async with self._lock:
                self.metrics.total_latency_ms += execution_time_ms
            
            return await self.handle_error(e, task)
    
    @abstractmethod
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        """Build a quality-focused prompt for the task"""
        pass
    
    @abstractmethod
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate the quality of the result (0.0-1.0)"""
        pass
    
    async def get_optimized_context(self, task: Task) -> Dict[str, Any]:
        """Get optimized context for the task"""
        # Default implementation - can be overridden
        return await self.memory.get_context(task.id)
    
    async def execute_with_monitoring(self, prompt: str) -> AgentResult:
        """Execute the prompt with monitoring"""
        # Default implementation - should be overridden
        # This would typically call the CLI manager
        return AgentResult(
            success=True,
            content="Default execution",
            sources=[],
            tokens_used=100
        )
    
    async def graceful_degradation(self, task: Task) -> AgentResult:
        """Handle graceful degradation when resources are limited"""
        # Default implementation - can be overridden
        return AgentResult(
            success=True,
            content="Task completed with reduced resources",
            sources=[],
            tokens_used=50,
            degraded=True
        )
    
    async def handle_error(self, error: Exception, task: Task) -> AgentResult:
        """Handle errors during execution"""
        # Default implementation - can be overridden
        return AgentResult(
            success=False,
            content=f"Error executing task: {str(error)}",
            sources=[],
            tokens_used=0
        )
    
    def get_quality_threshold(self) -> float:
        """Get the quality threshold for this agent type"""
        return self.QUALITY_THRESHOLDS.get(self.role, 0.8)
    
    async def meets_quality_standards(self) -> bool:
        """Check if the agent meets quality standards"""
        return self.metrics.average_quality >= self.get_quality_threshold()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of agent metrics"""
        return {
            'task_count': self.metrics.task_count,
            'success_rate': self.metrics.success_rate,
            'average_latency_ms': self.metrics.average_latency_ms,
            'average_quality': self.metrics.average_quality,
            'tokens_used': self.metrics.tokens_used,
            'meets_quality': self.metrics.average_quality >= self.get_quality_threshold()
        }