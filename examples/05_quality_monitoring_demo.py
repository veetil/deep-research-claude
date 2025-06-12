#!/usr/bin/env python3
"""
Example 05: Agent Quality Monitoring Demo
Demonstrates the SPCT-based quality monitoring and improvement system
"""
import asyncio
import sys
import os
from datetime import datetime
import random

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.agent_factory import AgentFactory
from src.agents.quality_monitor import AgentQualityMonitor, ImprovementType
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


# Mock managers
class MockCLIManager:
    async def execute(self, prompt: str):
        return {"response": "Mock response", "tokens": random.randint(100, 500)}


class MockMemoryManager:
    async def get_context(self, task_id: str):
        return {"previous_research": "Previous findings..."}


class MockBudgetManager:
    async def can_proceed(self, agent_id: str):
        return True
    
    async def record_usage(self, agent_id: str, tokens: int):
        pass


def create_mock_agent_result(quality_level: str = "high") -> AgentResult:
    """Create mock agent results with varying quality"""
    if quality_level == "high":
        return AgentResult(
            success=True,
            content="High quality research with comprehensive analysis...",
            sources=[
                {"name": "Nature", "url": "nature.com", "metadata": {"peer_reviewed": True, "year": 2024}},
                {"name": "Science", "url": "science.org", "metadata": {"peer_reviewed": True, "year": 2023}},
                {"name": "NEJM", "url": "nejm.org", "metadata": {"peer_reviewed": True, "year": 2024}}
            ],
            tokens_used=300
        )
    elif quality_level == "medium":
        return AgentResult(
            success=True,
            content="Research findings with some limitations...",
            sources=[
                {"name": "Wikipedia", "url": "wikipedia.org", "metadata": {"peer_reviewed": False}},
                {"name": "Blog Post", "url": "blog.com", "metadata": {"peer_reviewed": False}}
            ],
            tokens_used=200
        )
    else:  # low
        return AgentResult(
            success=random.choice([True, False]),
            content="Limited findings...",
            sources=[],
            tokens_used=100
        )


async def main():
    """Demonstrate quality monitoring functionality"""
    log("=== Deep Research Claude - Example 05: Quality Monitoring Demo ===", Colors.CYAN)
    log("This example shows SPCT-based quality monitoring and improvement\n", Colors.CYAN)
    
    # Initialize components
    log("Initializing quality monitoring system...", Colors.BLUE)
    
    factory = AgentFactory()
    monitor = AgentQualityMonitor()
    
    # Create mock managers
    cli_manager = MockCLIManager()
    memory_manager = MockMemoryManager()
    budget_manager = MockBudgetManager()
    
    log("✓ Quality monitor initialized", Colors.GREEN, "  ")
    log("✓ Agent factory ready", Colors.GREEN, "  ")
    
    print()
    
    # Create different types of agents
    log("Creating agents for quality testing...", Colors.BLUE)
    
    agents = []
    agent_configs = [
        ("research", "research_001", "high"),
        ("scientific", "scientific_001", "high"),
        ("medical", "medical_001", "medium"),
        ("tester", "tester_001", "low")
    ]
    
    for agent_type, agent_id, quality in agent_configs:
        agent = factory.create_agent(
            agent_type=agent_type,
            agent_id=agent_id,
            cli_manager=cli_manager,
            memory_manager=memory_manager,
            budget_manager=budget_manager
        )
        agents.append((agent, quality))
        log(f"  Created {agent_type} agent: {agent_id}", Colors.GREEN)
    
    print()
    
    # Simulate task execution with varying quality
    log("Simulating task execution with varying quality...", Colors.BLUE)
    
    for i in range(3):
        log(f"\nRound {i+1} of task execution:", Colors.YELLOW)
        
        for agent, base_quality in agents:
            # Create task
            task = Task(
                id=f"task_{agent.id}_{i}",
                query=f"Research query for {agent.role} agent",
                parameters={"iteration": i}
            )
            
            # Mock execution with varying quality
            quality_variation = random.choice([base_quality, base_quality, "medium"])
            mock_result = create_mock_agent_result(quality_variation)
            
            # Override execute_with_monitoring
            async def mock_exec(p):
                return mock_result
            agent.execute_with_monitoring = mock_exec
            
            # Add some latency variation
            if i == 2 and agent.role == "medical":
                # Simulate slow response
                async def slow_execute(p):
                    await asyncio.sleep(0.5)
                    return mock_result
                agent.execute_with_monitoring = slow_execute
            
            # Execute task
            result = await agent.execute(task)
            
            # Log execution
            status = "✓" if result.success else "✗"
            status_color = Colors.GREEN if result.success else Colors.RED
            log(f"    {status} {agent.role}: Q={result.quality_score:.2f}, T={result.execution_time_ms:.0f}ms", 
                status_color, "  ")
    
    print()
    
    # Generate quality reports
    log("Generating quality reports for all agents...", Colors.BLUE)
    print()
    
    for agent, _ in agents:
        report = await monitor.monitor_agent_quality(agent)
        
        # Display report
        log(f"Quality Report: {agent.role.upper()} Agent ({agent.id})", Colors.MAGENTA)
        log("─" * 60, Colors.DIM)
        
        # Metrics
        log("Metrics:", Colors.CYAN, "  ")
        log(f"Success Rate: {report.success_rate:.1%}", Colors.DIM, "    ")
        log(f"Avg Latency: {report.average_latency_ms:.0f}ms", Colors.DIM, "    ")
        log(f"Avg Quality: {report.average_quality:.2f}", Colors.DIM, "    ")
        log(f"Task Count: {report.task_count}", Colors.DIM, "    ")
        
        # Threshold check
        threshold_color = Colors.GREEN if report.meets_threshold else Colors.RED
        threshold_status = "PASS" if report.meets_threshold else "FAIL"
        log(f"Quality Status: {threshold_status} (threshold: {report.threshold})", 
            threshold_color, "  ")
        
        # Recommendations
        if report.recommendations:
            log("Recommendations:", Colors.YELLOW, "  ")
            for i, rec in enumerate(report.recommendations[:3], 1):
                log(f"{i}. {rec.description}", Colors.DIM, "    ")
                log(f"   Priority: {'⭐' * rec.priority} ({rec.priority}/5)", Colors.DIM, "     ")
                log(f"   Impact: +{rec.estimated_impact:.1%} quality", Colors.DIM, "     ")
        
        print()
    
    # System-wide quality summary
    log("Generating system-wide quality summary...", Colors.BLUE)
    
    system_summary = await monitor.get_system_quality_summary([a for a, _ in agents])
    
    log("\nSystem Quality Summary", Colors.MAGENTA)
    log("─" * 60, Colors.DIM)
    
    system_metrics = system_summary['system_metrics']
    log(f"Total Agents: {system_summary['total_agents']}", Colors.CYAN, "  ")
    log(f"Total Tasks: {system_summary['total_tasks']}", Colors.CYAN, "  ")
    log(f"System Success Rate: {system_metrics['average_success_rate']:.1%}", Colors.CYAN, "  ")
    log(f"System Quality Score: {system_metrics['average_quality']:.2f}", Colors.CYAN, "  ")
    log(f"Agents Meeting Threshold: {system_metrics['agents_meeting_threshold']}/{system_summary['total_agents']}", 
        Colors.CYAN, "  ")
    
    # Top system recommendations
    if system_summary['top_recommendations']:
        log("\nTop System-Wide Recommendations:", Colors.YELLOW)
        for i, rec_info in enumerate(system_summary['top_recommendations'][:3], 1):
            rec = rec_info['recommendation']
            log(f"{i}. [{rec_info['agent_role']}] {rec['description']}", Colors.DIM, "  ")
    
    print()
    
    # Demonstrate trend analysis
    log("Demonstrating trend analysis...", Colors.BLUE)
    
    # Execute more tasks to build history
    research_agent = agents[0][0]  # Get research agent
    
    log("  Executing 5 more tasks with improving quality...", Colors.YELLOW)
    for i in range(5):
        task = Task(
            id=f"trend_task_{i}",
            query="Trend analysis task",
            parameters={}
        )
        
        # Gradually improve quality
        if i < 2:
            mock_result = create_mock_agent_result("medium")
        else:
            mock_result = create_mock_agent_result("high")
        
        async def trend_exec(p):
            return mock_result
        research_agent.execute_with_monitoring = trend_exec
        await research_agent.execute(task)
    
    # Get updated report with trends
    trend_report = await monitor.monitor_agent_quality(research_agent)
    
    log("\n  Trend Analysis:", Colors.CYAN)
    if trend_report.trends:
        quality_improving = trend_report.trends.get('quality_improving', False)
        quality_trend = "📈 Improving" if quality_improving else "📉 Declining"
        log(f"    Quality Trend: {quality_trend}", Colors.GREEN if quality_improving else Colors.RED)
        
        latency_improving = trend_report.trends.get('latency_improving', False)
        latency_trend = "📈 Faster" if latency_improving else "📉 Slower"
        log(f"    Latency Trend: {latency_trend}", Colors.GREEN if latency_improving else Colors.RED)
    
    print()
    
    # Show quality thresholds for different agent types
    log("Agent Type Quality Thresholds:", Colors.BLUE)
    
    for agent_type in ['research', 'scientific', 'medical', 'legal', 'financial']:
        threshold = monitor.quality_thresholds.get(agent_type, 0.8)
        bar_length = int(threshold * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        log(f"  {agent_type:<12} [{bar}] {threshold:.0%}", Colors.CYAN)
    
    print()
    
    log("Example completed! 🎉", Colors.GREEN)
    log("This demonstrated:", Colors.CYAN)
    log("  • Agent quality metrics tracking", Colors.CYAN, "  ")
    log("  • Quality threshold checking", Colors.CYAN, "  ")
    log("  • Improvement recommendations", Colors.CYAN, "  ")
    log("  • System-wide quality analysis", Colors.CYAN, "  ")
    log("  • Trend analysis over time", Colors.CYAN, "  ")
    log("  • Quality standards by agent type", Colors.CYAN, "  ")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nExample interrupted by user", Colors.YELLOW)