"""
Agent factory for creating all agent types including plugin-based agents
"""
from typing import Dict, Type, Optional, List, Any
from dataclasses import dataclass

from src.plugins import PluginSystem
from src.agents.enhanced_base import EnhancedBaseAgent, Task, AgentResult
from src.agents.base import BaseAgent  # For compatibility


@dataclass
class AgentTypeInfo:
    """Information about an agent type"""
    name: str
    description: str
    requires_approval: bool = False
    max_tokens: int = 4000
    specialization: str = "general"
    quality_threshold: float = 0.8
    capabilities: List[str] = None


# Core Agent Implementations
class ResearchAgent(EnhancedBaseAgent):
    """General research agent for information gathering"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Research Specialist
        
        Task: {task.query}
        
        Requirements:
        1. Use credible and recent sources
        2. Provide comprehensive coverage
        3. Include multiple perspectives
        4. Cite all sources properly
        5. Fact-check critical information
        
        Context: {context.get('previous_research', 'No previous context')}
        
        Quality Standards:
        - Source credibility > 80%
        - Information recency (prefer last 2 years)
        - Coverage completeness
        - Citation accuracy
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        # Evaluate based on sources, coverage, and accuracy
        quality = 0.0
        
        if result.sources:
            # Check source credibility
            quality += 0.4 * min(len(result.sources) / 5, 1.0)
        
        if result.content:
            # Check content length and structure
            quality += 0.3 * min(len(result.content) / 1000, 1.0)
        
        if result.success:
            quality += 0.3
        
        return min(quality, 1.0)


class ScientificResearchAgent(EnhancedBaseAgent):
    """Agent specialized in scientific and academic research"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Scientific Research Specialist
        
        Task: {task.query}
        
        Requirements:
        1. Prioritize peer-reviewed sources
        2. Include methodology assessment
        3. Evaluate statistical significance
        4. Check for reproducibility
        5. Note any conflicts of interest
        
        Scientific Context: {context.get('scientific_context', 'No previous context')}
        
        Quality Standards:
        - Peer review requirement > 90%
        - Methodology rigor assessment
        - Statistical validity check
        - Reproducibility indicators
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # Check for peer-reviewed sources
        if result.sources:
            peer_reviewed = sum(1 for s in result.sources 
                              if s.get('metadata', {}).get('peer_reviewed', False))
            quality += 0.5 * (peer_reviewed / len(result.sources))
        
        # Additional scientific criteria
        if result.metadata.get('methodology_assessed'):
            quality += 0.2
        
        if result.metadata.get('statistics_verified'):
            quality += 0.2
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


class SpecificationWriterAgent(EnhancedBaseAgent):
    """Agent for writing detailed specifications and requirements"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Specification Writer
        
        Task: {task.query}
        
        You capture full project context—functional requirements, edge cases, 
        constraints—and translate that into modular pseudocode with TDD anchors.
        
        Requirements:
        1. Complete functional requirements
        2. All edge cases identified
        3. Clear constraints and assumptions
        4. Modular design with interfaces
        5. TDD test scenarios included
        
        Project Context: {context.get('project_context', 'No context')}
        
        Output Structure:
        - Executive Summary
        - Functional Requirements
        - Non-Functional Requirements
        - Edge Cases & Error Scenarios
        - Constraints & Assumptions
        - Modular Design
        - Test Scenarios (TDD)
        - Acceptance Criteria
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # Check for required sections
        required_sections = [
            'functional requirements',
            'edge cases',
            'constraints',
            'test scenarios',
            'acceptance criteria'
        ]
        
        content_lower = result.content.lower()
        for section in required_sections:
            if section in content_lower:
                quality += 0.15
        
        # Completeness and structure
        if len(result.content) > 2000:
            quality += 0.15
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


class TesterAgent(EnhancedBaseAgent):
    """Agent specialized in testing and quality assurance"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Testing & QA Specialist
        
        Task: {task.query}
        
        Requirements:
        1. Design comprehensive test cases
        2. Include unit, integration, and e2e tests
        3. Cover edge cases and error scenarios
        4. Performance and security testing
        5. Generate test data and mocks
        
        Code Context: {context.get('code_context', 'No context')}
        
        Test Coverage Goals:
        - Unit test coverage > 90%
        - Integration test coverage > 80%
        - Critical path coverage 100%
        - Edge case coverage > 85%
        
        Output Format:
        - Test Strategy
        - Test Cases (grouped by type)
        - Test Data Requirements
        - Mock Specifications
        - Expected Results
        - Performance Benchmarks
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # Check test coverage
        if result.metadata.get('unit_tests_count', 0) > 0:
            quality += 0.3
        
        if result.metadata.get('integration_tests_count', 0) > 0:
            quality += 0.2
        
        if result.metadata.get('edge_cases_covered', False):
            quality += 0.2
        
        if result.metadata.get('performance_tests', False):
            quality += 0.15
        
        if result.success:
            quality += 0.15
        
        return min(quality, 1.0)


class SystemIntegratorAgent(EnhancedBaseAgent):
    """Agent for system integration and ensuring cohesion"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: System Integrator
        
        Task: {task.query}
        
        You merge the outputs of all modes into a working, tested, production-ready 
        system. You ensure consistency, cohesion, and modularity.
        
        Integration Requirements:
        1. Merge all component outputs
        2. Ensure interface compatibility
        3. Resolve conflicts and dependencies
        4. Maintain architectural consistency
        5. Create integration tests
        
        Components: {context.get('components', [])}
        
        Quality Criteria:
        - Interface compatibility 100%
        - No circular dependencies
        - Consistent error handling
        - Unified logging and monitoring
        - Performance optimization
        
        Deliverables:
        - Integrated system architecture
        - Dependency resolution report
        - Integration test suite
        - Deployment configuration
        - System documentation
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # Integration specific metrics
        if result.metadata.get('interfaces_compatible', False):
            quality += 0.3
        
        if result.metadata.get('no_circular_deps', False):
            quality += 0.2
        
        if result.metadata.get('integration_tests', False):
            quality += 0.2
        
        if result.metadata.get('deployment_ready', False):
            quality += 0.2
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


class OptimizerAgent(EnhancedBaseAgent):
    """Agent for code optimization and refactoring"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: System Optimizer
        
        Task: {task.query}
        
        You refactor, modularize, and improve system performance. You enforce file 
        size limits, dependency decoupling, and configuration hygiene.
        
        Optimization Goals:
        1. Reduce code complexity
        2. Improve performance metrics
        3. Modularize large components
        4. Decouple dependencies
        5. Optimize resource usage
        
        Current Metrics: {context.get('performance_metrics', {})}
        
        Constraints:
        - Max file size: 500 lines
        - Max function complexity: 10
        - Max class methods: 20
        - Dependency coupling < 0.3
        
        Output:
        - Refactoring plan
        - Performance improvements
        - Module breakdown
        - Dependency graph
        - Configuration cleanup
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # Optimization metrics
        if result.metadata.get('complexity_reduced', False):
            quality += 0.25
        
        if result.metadata.get('performance_improved', False):
            quality += 0.25
        
        if result.metadata.get('modularized', False):
            quality += 0.2
        
        if result.metadata.get('dependencies_reduced', False):
            quality += 0.2
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


class DevOpsAgent(EnhancedBaseAgent):
    """Agent for DevOps and infrastructure management"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: DevOps Specialist
        
        Task: {task.query}
        
        You are the DevOps automation and infrastructure specialist responsible for 
        deploying, managing, and orchestrating systems across cloud providers, edge 
        platforms, and internal environments. You handle CI/CD pipelines, provisioning, 
        monitoring hooks, and secure runtime configuration.
        
        Requirements:
        1. Design CI/CD pipelines
        2. Infrastructure as Code (IaC)
        3. Container orchestration
        4. Monitoring and alerting
        5. Security and compliance
        
        Environment: {context.get('environment', 'production')}
        
        Standards:
        - Zero-downtime deployments
        - Automated rollback capability
        - Security scanning in pipeline
        - Performance monitoring
        - Cost optimization
        
        Deliverables:
        - CI/CD pipeline configuration
        - IaC templates (Terraform/CloudFormation)
        - Kubernetes manifests
        - Monitoring dashboards
        - Runbook documentation
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # DevOps specific metrics
        if result.metadata.get('cicd_pipeline', False):
            quality += 0.2
        
        if result.metadata.get('iac_templates', False):
            quality += 0.2
        
        if result.metadata.get('monitoring_setup', False):
            quality += 0.2
        
        if result.metadata.get('security_scanning', False):
            quality += 0.2
        
        if result.metadata.get('documentation', False):
            quality += 0.1
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


class MCPIntegrationAgent(EnhancedBaseAgent):
    """Agent for MCP (Model Context Protocol) integration"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: MCP Integration Specialist
        
        Task: {task.query}
        
        You are the MCP (Model Context Protocol) integration specialist responsible 
        for connecting to and managing external services through MCP interfaces. 
        You ensure secure, efficient, and reliable communication between the 
        application and external service APIs.
        
        Requirements:
        1. Design MCP server implementations
        2. Create secure API connections
        3. Handle authentication and authorization
        4. Implement rate limiting and retries
        5. Create comprehensive error handling
        
        Services to integrate: {context.get('services', [])}
        
        Standards:
        - OAuth 2.0 / API key management
        - Request/response validation
        - Error recovery mechanisms
        - Performance optimization
        - Security best practices
        
        Deliverables:
        - MCP server configuration
        - API client implementations
        - Authentication setup
        - Error handling strategy
        - Integration tests
        - API documentation
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        quality = 0.0
        
        # MCP integration metrics
        if result.metadata.get('api_clients', False):
            quality += 0.2
        
        if result.metadata.get('auth_implemented', False):
            quality += 0.2
        
        if result.metadata.get('error_handling', False):
            quality += 0.2
        
        if result.metadata.get('rate_limiting', False):
            quality += 0.15
        
        if result.metadata.get('tests_included', False):
            quality += 0.15
        
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)


# Additional specialized agents
class PlannerAgent(EnhancedBaseAgent):
    """Strategic planning and task decomposition agent"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Strategic Planner
        
        Task: {task.query}
        
        Break down complex goals into actionable tasks with dependencies,
        timelines, and resource allocation.
        
        Requirements:
        1. Task decomposition
        2. Dependency mapping
        3. Resource estimation
        4. Timeline creation
        5. Risk assessment
        
        Output: Detailed project plan with milestones
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        return 0.85 if result.success else 0.3


class AnalysisAgent(EnhancedBaseAgent):
    """Data analysis and pattern recognition agent"""
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Data Analysis Specialist
        
        Task: {task.query}
        
        Analyze data, identify patterns, and provide insights with
        statistical backing and visualizations.
        
        Requirements:
        1. Statistical analysis
        2. Pattern identification
        3. Trend analysis
        4. Anomaly detection
        5. Visualization recommendations
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        return 0.85 if result.success else 0.3


class AgentFactory:
    """Factory for creating all agent types including plugin-based agents"""
    
    # Core agents (always available)
    CORE_AGENTS = {
        'research': ResearchAgent,
        'scientific': ScientificResearchAgent,
        'specifications': SpecificationWriterAgent,
        'tester': TesterAgent,
        'integrator': SystemIntegratorAgent,
        'optimizer': OptimizerAgent,
        'devops': DevOpsAgent,
        'mcp_integration': MCPIntegrationAgent,
        'planner': PlannerAgent,
        'analysis': AnalysisAgent,
    }
    
    # Agent metadata
    AGENT_INFO = {
        'research': AgentTypeInfo(
            name="Research Agent",
            description="General research and information gathering",
            quality_threshold=0.85
        ),
        'scientific': AgentTypeInfo(
            name="Scientific Research Agent",
            description="Specialized in scientific and academic research",
            quality_threshold=0.90,
            specialization="scientific"
        ),
        'specifications': AgentTypeInfo(
            name="Specification Writer",
            description="Captures requirements and creates detailed specifications",
            quality_threshold=0.90,
            max_tokens=8000
        ),
        'tester': AgentTypeInfo(
            name="Tester Agent",
            description="Testing, QA, and quality assurance specialist",
            quality_threshold=0.88
        ),
        'integrator': AgentTypeInfo(
            name="System Integrator",
            description="Merges outputs into cohesive, production-ready systems",
            quality_threshold=0.92,
            requires_approval=True
        ),
        'optimizer': AgentTypeInfo(
            name="Optimizer Agent",
            description="Refactoring and performance optimization",
            quality_threshold=0.85
        ),
        'devops': AgentTypeInfo(
            name="DevOps Agent",
            description="Infrastructure, deployment, and automation",
            quality_threshold=0.90,
            requires_approval=True
        ),
        'mcp_integration': AgentTypeInfo(
            name="MCP Integration Agent",
            description="External service integration via Model Context Protocol",
            quality_threshold=0.88,
            specialization="integration"
        ),
        'planner': AgentTypeInfo(
            name="Planner Agent",
            description="Strategic planning and task decomposition",
            quality_threshold=0.85
        ),
        'analysis': AgentTypeInfo(
            name="Analysis Agent",
            description="Data analysis and pattern recognition",
            quality_threshold=0.85,
            specialization="analytics"
        ),
    }
    
    def __init__(self, plugin_system: Optional[PluginSystem] = None):
        self.plugin_system = plugin_system
        self.agent_registry = self.CORE_AGENTS.copy()
        
        # Add plugin agents if available
        if plugin_system:
            self.agent_registry.update(plugin_system.agent_registry)
    
    def create_agent(self, 
                     agent_type: str,
                     agent_id: str,
                     cli_manager,
                     memory_manager,
                     budget_manager,
                     **kwargs) -> EnhancedBaseAgent:
        """Create an agent instance"""
        
        agent_class = self.agent_registry.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Check if it's a plugin agent
        plugin_config = None
        if self.plugin_system and agent_type in self.plugin_system.agent_registry:
            # Get plugin configuration
            for plugin in self.plugin_system.plugins.values():
                if hasattr(plugin, 'loaded_agents') and agent_type in plugin.loaded_agents:
                    plugin_config = plugin.config
                    break
        
        return agent_class(
            agent_id=agent_id,
            role=agent_type,
            cli_manager=cli_manager,
            memory_manager=memory_manager,
            budget_manager=budget_manager,
            plugin_config=plugin_config,
            **kwargs
        )
    
    def get_available_agents(self) -> List[str]:
        """Get all available agent types"""
        return list(self.agent_registry.keys())
    
    def get_agent_info(self, agent_type: str) -> AgentTypeInfo:
        """Get information about an agent type"""
        # Check core agents first
        if agent_type in self.AGENT_INFO:
            return self.AGENT_INFO[agent_type]
        
        # Check plugin agents
        if self.plugin_system and agent_type in self.plugin_system.agent_registry:
            # Create info from plugin
            agent_class = self.plugin_system.agent_registry[agent_type]
            return AgentTypeInfo(
                name=agent_type,
                description=agent_class.__doc__ or "Plugin-based agent",
                quality_threshold=getattr(agent_class, 'QUALITY_THRESHOLD', 0.8),
                max_tokens=getattr(agent_class, 'MAX_TOKENS', 4000),
                requires_approval=getattr(agent_class, 'REQUIRES_APPROVAL', False),
                specialization=getattr(agent_class, 'SPECIALIZATION', 'general')
            )
        
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    def get_agent_capabilities(self, agent_type: str) -> Dict[str, Any]:
        """Get capabilities and requirements for an agent type"""
        try:
            info = self.get_agent_info(agent_type)
            return {
                'name': info.name,
                'description': info.description,
                'requires_approval': info.requires_approval,
                'max_tokens': info.max_tokens,
                'specialization': info.specialization,
                'quality_threshold': info.quality_threshold,
                'capabilities': info.capabilities or []
            }
        except ValueError:
            return {}