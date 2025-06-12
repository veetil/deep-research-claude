"""
Agent quality monitoring and improvement system based on SPCT metrics
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from enum import Enum

from src.agents.enhanced_base import EnhancedBaseAgent, AgentMetrics


class ImprovementType(Enum):
    """Types of improvements that can be suggested"""
    ERROR_HANDLING = "error_handling"
    LATENCY = "latency"
    QUALITY = "quality"
    SOURCE_VALIDATION = "source_validation"
    PROMPT_REFINEMENT = "prompt_refinement"
    RESOURCE_OPTIMIZATION = "resource_optimization"


@dataclass
class ImprovementRecommendation:
    """Recommendation for agent improvement"""
    improvement_type: ImprovementType
    description: str
    priority: int  # 1-5, 5 being highest
    estimated_impact: float  # Expected quality improvement (0-1)
    implementation_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.improvement_type.value,
            'description': self.description,
            'priority': self.priority,
            'estimated_impact': self.estimated_impact,
            'steps': self.implementation_steps
        }


@dataclass
class QualityReport:
    """Comprehensive quality report for an agent"""
    agent_id: str
    agent_role: str
    timestamp: datetime
    success_rate: float
    average_latency_ms: float
    average_quality: float
    meets_threshold: bool
    threshold: float
    task_count: int
    recommendations: List[ImprovementRecommendation] = field(default_factory=list)
    trends: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'agent_role': self.agent_role,
            'timestamp': self.timestamp.isoformat(),
            'metrics': {
                'success_rate': self.success_rate,
                'average_latency_ms': self.average_latency_ms,
                'average_quality': self.average_quality,
                'task_count': self.task_count
            },
            'quality_status': {
                'meets_threshold': self.meets_threshold,
                'threshold': self.threshold,
                'gap': max(0, self.threshold - self.average_quality)
            },
            'recommendations': [rec.to_dict() for rec in self.recommendations],
            'trends': self.trends
        }


class AgentQualityMonitor:
    """Monitors and improves agent quality based on SPCT metrics"""
    
    def __init__(self):
        self.quality_thresholds = {
            'research': 0.85,
            'scientific': 0.90,
            'medical': 0.95,
            'legal': 0.92,
            'financial': 0.93,
            'specifications': 0.90,
            'tester': 0.88,
            'integrator': 0.92,
            'optimizer': 0.85,
            'devops': 0.90,
            'mcp_integration': 0.88,
            'planner': 0.85,
            'analysis': 0.85
        }
        
        self.latency_thresholds = {
            'research': 2000,      # 2 seconds
            'scientific': 3000,    # 3 seconds
            'medical': 3000,       # 3 seconds
            'legal': 3000,         # 3 seconds
            'financial': 2500,     # 2.5 seconds
            'default': 1500        # 1.5 seconds
        }
        
        self.historical_metrics: Dict[str, List[AgentMetrics]] = {}
        self.improvement_history: Dict[str, List[ImprovementRecommendation]] = {}
        self._lock = asyncio.Lock()
    
    async def monitor_agent_quality(self, agent: EnhancedBaseAgent) -> QualityReport:
        """Monitor an agent's quality and generate report"""
        metrics = agent.metrics
        threshold = self.quality_thresholds.get(agent.role, 0.8)
        
        # Calculate current metrics
        success_rate = metrics.success_rate
        avg_latency = metrics.average_latency_ms
        avg_quality = metrics.average_quality
        meets_threshold = avg_quality >= threshold
        
        # Store historical data
        async with self._lock:
            if agent.id not in self.historical_metrics:
                self.historical_metrics[agent.id] = []
            self.historical_metrics[agent.id].append(metrics)
        
        # Calculate trends
        trends = await self._calculate_trends(agent.id)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            agent, metrics, threshold, trends
        )
        
        # Create report
        report = QualityReport(
            agent_id=agent.id,
            agent_role=agent.role,
            timestamp=datetime.now(timezone.utc),
            success_rate=success_rate,
            average_latency_ms=avg_latency,
            average_quality=avg_quality,
            meets_threshold=meets_threshold,
            threshold=threshold,
            task_count=metrics.task_count,
            recommendations=recommendations,
            trends=trends
        )
        
        # Trigger improvements if needed
        if not meets_threshold and recommendations:
            await self.trigger_agent_improvement(agent, report)
        
        return report
    
    async def _calculate_trends(self, agent_id: str) -> Dict[str, Any]:
        """Calculate quality trends for an agent"""
        history = self.historical_metrics.get(agent_id, [])
        if len(history) < 2:
            return {}
        
        # Get recent history (last 10 measurements)
        recent = history[-10:]
        
        # Calculate trends
        quality_trend = []
        latency_trend = []
        success_trend = []
        
        for metrics in recent:
            quality_trend.append(metrics.average_quality)
            latency_trend.append(metrics.average_latency_ms)
            success_trend.append(metrics.success_rate)
        
        # Simple trend calculation (positive = improving)
        def calculate_slope(values: List[float]) -> float:
            if len(values) < 2:
                return 0.0
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            
            numerator = sum((i - x_mean) * (y - y_mean) 
                          for i, y in enumerate(values))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            return numerator / denominator if denominator != 0 else 0.0
        
        return {
            'quality_slope': calculate_slope(quality_trend),
            'latency_slope': calculate_slope(latency_trend),
            'success_slope': calculate_slope(success_trend),
            'quality_improving': calculate_slope(quality_trend) > 0,
            'latency_improving': calculate_slope(latency_trend) < 0,  # Lower is better
            'success_improving': calculate_slope(success_trend) > 0
        }
    
    async def _generate_recommendations(self, 
                                      agent: EnhancedBaseAgent,
                                      metrics: AgentMetrics,
                                      threshold: float,
                                      trends: Dict[str, Any]) -> List[ImprovementRecommendation]:
        """Generate improvement recommendations based on metrics"""
        recommendations = []
        
        # Success rate issues
        if metrics.success_rate < 0.9:
            recommendations.append(ImprovementRecommendation(
                improvement_type=ImprovementType.ERROR_HANDLING,
                description=f"Success rate ({metrics.success_rate:.2%}) below target (90%)",
                priority=5,
                estimated_impact=0.1,
                implementation_steps=[
                    "Add retry logic for transient failures",
                    "Improve error categorization",
                    "Implement circuit breaker pattern",
                    "Add fallback strategies"
                ]
            ))
        
        # Latency issues
        latency_threshold = self.latency_thresholds.get(
            agent.role, 
            self.latency_thresholds['default']
        )
        if metrics.average_latency_ms > latency_threshold:
            recommendations.append(ImprovementRecommendation(
                improvement_type=ImprovementType.LATENCY,
                description=f"Average latency ({metrics.average_latency_ms:.0f}ms) exceeds threshold ({latency_threshold}ms)",
                priority=4,
                estimated_impact=0.05,
                implementation_steps=[
                    "Optimize prompt generation",
                    "Implement response caching",
                    "Use streaming for large responses",
                    "Parallel processing where possible"
                ]
            ))
        
        # Quality issues
        if metrics.average_quality < threshold:
            quality_gap = threshold - metrics.average_quality
            
            # Severe quality issues
            if quality_gap > 0.1:
                recommendations.append(ImprovementRecommendation(
                    improvement_type=ImprovementType.PROMPT_REFINEMENT,
                    description=f"Quality score ({metrics.average_quality:.2f}) significantly below threshold ({threshold})",
                    priority=5,
                    estimated_impact=quality_gap * 0.7,
                    implementation_steps=[
                        "Refine quality prompts with more specific criteria",
                        "Add example outputs to prompts",
                        "Implement multi-step verification",
                        "Increase context window usage"
                    ]
                ))
            
            # Source validation for research agents
            if agent.role in ['research', 'scientific', 'medical', 'legal', 'financial']:
                recommendations.append(ImprovementRecommendation(
                    improvement_type=ImprovementType.SOURCE_VALIDATION,
                    description="Enhance source credibility validation",
                    priority=4,
                    estimated_impact=0.08,
                    implementation_steps=[
                        "Implement source ranking algorithm",
                        "Add peer-review detection",
                        "Verify publication dates",
                        "Cross-reference multiple sources"
                    ]
                ))
        
        # Resource optimization
        if metrics.tokens_used > 0:
            avg_tokens_per_task = metrics.tokens_used / max(metrics.task_count, 1)
            if avg_tokens_per_task > 2000:
                recommendations.append(ImprovementRecommendation(
                    improvement_type=ImprovementType.RESOURCE_OPTIMIZATION,
                    description=f"High token usage ({avg_tokens_per_task:.0f} tokens/task)",
                    priority=3,
                    estimated_impact=0.02,
                    implementation_steps=[
                        "Optimize prompt length",
                        "Use summarization for context",
                        "Implement selective information retrieval",
                        "Cache common responses"
                    ]
                ))
        
        # Trend-based recommendations
        if trends.get('quality_improving') == False:
            recommendations.append(ImprovementRecommendation(
                improvement_type=ImprovementType.QUALITY,
                description="Quality trend declining over time",
                priority=4,
                estimated_impact=0.05,
                implementation_steps=[
                    "Review recent changes",
                    "Analyze failure patterns",
                    "Update training examples",
                    "Refresh knowledge base"
                ]
            ))
        
        # Sort by priority
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def trigger_agent_improvement(self, 
                                      agent: EnhancedBaseAgent,
                                      report: QualityReport) -> None:
        """Trigger improvement actions for an agent"""
        # Log improvement plan
        async with self._lock:
            if agent.id not in self.improvement_history:
                self.improvement_history[agent.id] = []
            self.improvement_history[agent.id].extend(report.recommendations)
        
        # In a real system, this would trigger actual improvements
        # For now, we'll just log the plan
        await self._log_improvement_plan(agent.id, report.recommendations)
    
    async def _log_improvement_plan(self, 
                                   agent_id: str,
                                   recommendations: List[ImprovementRecommendation]) -> None:
        """Log the improvement plan for tracking"""
        # This would integrate with logging/monitoring systems
        print(f"\nImprovement Plan for Agent {agent_id}:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec.description}")
            print(f"   Type: {rec.improvement_type.value}")
            print(f"   Priority: {rec.priority}/5")
            print(f"   Expected Impact: {rec.estimated_impact:.1%}")
            print("   Steps:")
            for step in rec.implementation_steps:
                print(f"   - {step}")
    
    async def get_system_quality_summary(self, 
                                       agents: List[EnhancedBaseAgent]) -> Dict[str, Any]:
        """Get quality summary for all agents in the system"""
        reports = []
        
        for agent in agents:
            report = await self.monitor_agent_quality(agent)
            reports.append(report)
        
        # Calculate system-wide metrics
        total_tasks = sum(r.task_count for r in reports)
        avg_success_rate = sum(r.success_rate * r.task_count for r in reports) / max(total_tasks, 1)
        avg_quality = sum(r.average_quality * r.task_count for r in reports) / max(total_tasks, 1)
        meeting_threshold = sum(1 for r in reports if r.meets_threshold)
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_agents': len(agents),
            'total_tasks': total_tasks,
            'system_metrics': {
                'average_success_rate': avg_success_rate,
                'average_quality': avg_quality,
                'agents_meeting_threshold': meeting_threshold,
                'percentage_meeting_threshold': meeting_threshold / len(agents) if agents else 0
            },
            'agent_reports': [r.to_dict() for r in reports],
            'top_recommendations': self._get_top_system_recommendations(reports)
        }
    
    def _get_top_system_recommendations(self, 
                                       reports: List[QualityReport]) -> List[Dict[str, Any]]:
        """Get top recommendations across all agents"""
        all_recommendations = []
        
        for report in reports:
            for rec in report.recommendations:
                all_recommendations.append({
                    'agent_id': report.agent_id,
                    'agent_role': report.agent_role,
                    'recommendation': rec.to_dict()
                })
        
        # Sort by priority and impact
        all_recommendations.sort(
            key=lambda r: (
                r['recommendation']['priority'],
                r['recommendation']['estimated_impact']
            ),
            reverse=True
        )
        
        return all_recommendations[:10]  # Top 10 system-wide