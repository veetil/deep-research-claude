"""
Unit tests for the plugin system
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import importlib.util
from typing import Dict, List, Type

from src.plugins.plugin_system import PluginSystem, Plugin, AgentPlugin
from src.plugins.exceptions import PluginError, PluginNotFoundError, PluginAlreadyRegisteredError
from src.agents.base import BaseAgent


class TestPluginSystem:
    """Test cases for the plugin system"""
    
    @pytest.fixture
    def plugin_system(self):
        """Create a plugin system instance"""
        return PluginSystem()
    
    @pytest.fixture
    def sample_plugin(self):
        """Create a sample agent plugin"""
        return AgentPlugin(
            name="medical_research",
            version="1.0.0",
            agents=["MedicalResearchAgent", "ClinicalTrialAgent"],
            tools=["pubmed_search", "clinical_guidelines"],
            config={"specialization": "medical", "api_key": "test_key"}
        )
    
    @pytest.fixture
    def mock_agent_class(self):
        """Create a mock agent class"""
        class MockMedicalAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
            
            async def process_message(self, message):
                return {"result": "processed"}
        
        return MockMedicalAgent
    
    async def test_plugin_registration_and_discovery(self, plugin_system, sample_plugin):
        """Test basic plugin registration and discovery"""
        # Register plugin
        await plugin_system.register(sample_plugin)
        
        # Verify registration
        assert plugin_system.is_registered("medical_research")
        assert "medical_research" in plugin_system.list_plugins()
        
        # Verify plugin details
        plugin_info = plugin_system.get_plugin_info("medical_research")
        assert plugin_info["name"] == "medical_research"
        assert plugin_info["version"] == "1.0.0"
        assert plugin_info["status"] == "active"
    
    async def test_agent_type_discovery(self, plugin_system, sample_plugin, mock_agent_class):
        """Test that registered plugins expose their agent types"""
        # Mock the dynamic loading
        sample_plugin.loaded_agents = {
            "MedicalResearchAgent": mock_agent_class,
            "ClinicalTrialAgent": mock_agent_class
        }
        
        await plugin_system.register(sample_plugin)
        
        # Check agent types are available
        agent_types = plugin_system.get_agent_types()
        assert "MedicalResearchAgent" in agent_types
        assert "ClinicalTrialAgent" in agent_types
    
    async def test_tool_registration(self, plugin_system, sample_plugin):
        """Test that plugin tools are registered correctly"""
        await plugin_system.register(sample_plugin)
        
        # Check tools are registered
        tools = plugin_system.get_available_tools()
        assert "pubmed_search" in tools
        assert "clinical_guidelines" in tools
        
        # Check tool namespace
        tool_info = plugin_system.get_tool_info("pubmed_search")
        assert tool_info["plugin"] == "medical_research"
        assert tool_info["full_name"] == "medical_research.pubmed_search"
    
    async def test_duplicate_plugin_registration(self, plugin_system, sample_plugin):
        """Test that duplicate plugin registration fails"""
        await plugin_system.register(sample_plugin)
        
        # Try to register again
        with pytest.raises(PluginAlreadyRegisteredError):
            await plugin_system.register(sample_plugin)
    
    async def test_plugin_lifecycle(self, plugin_system, sample_plugin):
        """Test plugin initialization and shutdown"""
        # Track lifecycle calls
        sample_plugin.initialize = AsyncMock()
        sample_plugin.shutdown = AsyncMock()
        
        # Register (should initialize)
        await plugin_system.register(sample_plugin)
        sample_plugin.initialize.assert_called_once()
        
        # Unregister (should shutdown)
        await plugin_system.unregister("medical_research")
        sample_plugin.shutdown.assert_called_once()
        
        # Verify plugin is removed
        assert not plugin_system.is_registered("medical_research")
    
    async def test_plugin_configuration(self, plugin_system, sample_plugin):
        """Test plugin configuration management"""
        await plugin_system.register(sample_plugin)
        
        # Get plugin configuration
        config = plugin_system.get_plugin_config("medical_research")
        assert config["specialization"] == "medical"
        assert config["api_key"] == "test_key"
        
        # Update configuration
        await plugin_system.update_plugin_config("medical_research", {
            "api_key": "new_key",
            "timeout": 30
        })
        
        updated_config = plugin_system.get_plugin_config("medical_research")
        assert updated_config["api_key"] == "new_key"
        assert updated_config["timeout"] == 30
        assert updated_config["specialization"] == "medical"  # Original preserved
    
    async def test_plugin_dependencies(self, plugin_system):
        """Test plugin dependency management"""
        # Create plugins with dependencies
        base_plugin = AgentPlugin(
            name="base_research",
            version="1.0.0",
            agents=["BaseResearchAgent"],
            tools=["basic_search"],
            config={},
            dependencies=[]
        )
        
        dependent_plugin = AgentPlugin(
            name="advanced_research",
            version="1.0.0",
            agents=["AdvancedResearchAgent"],
            tools=["advanced_search"],
            config={},
            dependencies=["base_research"]
        )
        
        # Try to register dependent plugin first (should fail)
        with pytest.raises(PluginError, match="Missing dependencies"):
            await plugin_system.register(dependent_plugin)
        
        # Register in correct order
        await plugin_system.register(base_plugin)
        await plugin_system.register(dependent_plugin)
        
        # Both should be registered
        assert plugin_system.is_registered("base_research")
        assert plugin_system.is_registered("advanced_research")
    
    async def test_plugin_hot_reload(self, plugin_system, sample_plugin):
        """Test plugin hot reload functionality"""
        await plugin_system.register(sample_plugin)
        
        # Simulate plugin update
        updated_plugin = AgentPlugin(
            name="medical_research",
            version="1.1.0",
            agents=["MedicalResearchAgent", "ClinicalTrialAgent", "DrugInteractionAgent"],
            tools=["pubmed_search", "clinical_guidelines", "drug_database"],
            config={"specialization": "medical", "api_key": "test_key"}
        )
        
        # Hot reload
        await plugin_system.reload_plugin("medical_research", updated_plugin)
        
        # Check updated info
        plugin_info = plugin_system.get_plugin_info("medical_research")
        assert plugin_info["version"] == "1.1.0"
        
        # Check new agent type is available
        agent_types = plugin_system.get_agent_types()
        assert "DrugInteractionAgent" in agent_types
    
    async def test_plugin_error_handling(self, plugin_system):
        """Test plugin error handling"""
        # Create a faulty plugin
        faulty_plugin = AgentPlugin(
            name="faulty_plugin",
            version="1.0.0",
            agents=["NonExistentAgent"],
            tools=["broken_tool"],
            config={}
        )
        
        # Mock initialize to raise error
        faulty_plugin.initialize = AsyncMock(side_effect=Exception("Plugin initialization failed"))
        
        # Registration should fail gracefully
        with pytest.raises(PluginError, match="Failed to initialize plugin"):
            await plugin_system.register(faulty_plugin)
        
        # Plugin should not be registered
        assert not plugin_system.is_registered("faulty_plugin")
    
    async def test_plugin_metrics(self, plugin_system, sample_plugin):
        """Test plugin metrics collection"""
        await plugin_system.register(sample_plugin)
        
        # Get initial metrics
        metrics = plugin_system.get_plugin_metrics("medical_research")
        assert metrics["load_time_ms"] > 0
        assert metrics["agent_count"] == 2
        assert metrics["tool_count"] == 2
        assert metrics["status"] == "active"
        
        # Simulate plugin usage
        await plugin_system.record_plugin_usage("medical_research", "agent_created", {
            "agent_type": "MedicalResearchAgent",
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Check updated metrics
        updated_metrics = plugin_system.get_plugin_metrics("medical_research")
        assert updated_metrics["usage_count"] > 0
    
    async def test_plugin_sandboxing(self, plugin_system, sample_plugin):
        """Test plugin isolation and sandboxing"""
        await plugin_system.register(sample_plugin)
        
        # Each plugin should have isolated namespace
        namespace = plugin_system.get_plugin_namespace("medical_research")
        assert namespace["name"] == "medical_research"
        assert "agents" in namespace
        assert "tools" in namespace
        
        # Plugin should not access other plugin's resources
        another_plugin = AgentPlugin(
            name="financial_research",
            version="1.0.0",
            agents=["FinancialAgent"],
            tools=["market_data"],
            config={}
        )
        await plugin_system.register(another_plugin)
        
        # Verify isolation
        medical_namespace = plugin_system.get_plugin_namespace("medical_research")
        financial_namespace = plugin_system.get_plugin_namespace("financial_research")
        
        assert medical_namespace != financial_namespace
        assert "FinancialAgent" not in medical_namespace["agents"]
    
    async def test_plugin_system_shutdown(self, plugin_system, sample_plugin):
        """Test graceful shutdown of all plugins"""
        # Register multiple plugins
        plugins = []
        for i in range(3):
            plugin = AgentPlugin(
                name=f"test_plugin_{i}",
                version="1.0.0",
                agents=[f"TestAgent{i}"],
                tools=[f"test_tool_{i}"],
                config={}
            )
            plugin.shutdown = AsyncMock()
            plugins.append(plugin)
            await plugin_system.register(plugin)
        
        # Shutdown system
        await plugin_system.shutdown()
        
        # All plugins should be shut down
        for plugin in plugins:
            plugin.shutdown.assert_called_once()
        
        # No plugins should be registered
        assert len(plugin_system.list_plugins()) == 0


class TestAgentPlugin:
    """Test cases for AgentPlugin class"""
    
    async def test_plugin_initialization(self):
        """Test plugin initialization process"""
        plugin = AgentPlugin(
            name="test_plugin",
            version="1.0.0",
            agents=["TestAgent"],
            tools=["test_tool"],
            config={"key": "value"}
        )
        
        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.agents == ["TestAgent"]
        assert plugin.tools == ["test_tool"]
        assert plugin.config == {"key": "value"}
        assert plugin.loaded_agents == {}
        assert plugin.status == "uninitialized"
    
    @patch('importlib.util.find_spec')
    @patch('importlib.util.module_from_spec')
    async def test_dynamic_agent_loading(self, mock_module_from_spec, mock_find_spec):
        """Test dynamic loading of agent classes"""
        # Create mock module and spec
        mock_spec = Mock()
        mock_spec.loader = Mock()
        mock_find_spec.return_value = mock_spec
        
        mock_module = Mock()
        mock_module.TestAgent = type('TestAgent', (BaseAgent,), {})
        mock_module_from_spec.return_value = mock_module
        
        plugin = AgentPlugin(
            name="test_plugin",
            version="1.0.0",
            agents=["TestAgent"],
            tools=[],
            config={}
        )
        
        await plugin.initialize()
        
        # Verify agent was loaded
        assert "TestAgent" in plugin.loaded_agents
        assert plugin.status == "active"
    
    async def test_plugin_validation(self):
        """Test plugin validation"""
        # Test invalid name
        with pytest.raises(ValueError, match="Plugin name cannot be empty"):
            AgentPlugin(name="", version="1.0.0", agents=[], tools=[], config={})
        
        # Test invalid version
        with pytest.raises(ValueError, match="Invalid version format"):
            AgentPlugin(name="test", version="invalid", agents=[], tools=[], config={})
        
        # Test empty agents and tools
        with pytest.raises(ValueError, match="Plugin must provide at least one agent or tool"):
            AgentPlugin(name="test", version="1.0.0", agents=[], tools=[], config={})
    
    async def test_plugin_metadata(self):
        """Test plugin metadata generation"""
        plugin = AgentPlugin(
            name="test_plugin",
            version="1.0.0",
            agents=["TestAgent"],
            tools=["test_tool"],
            config={"key": "value"},
            author="Test Author",
            description="Test plugin description"
        )
        
        metadata = plugin.get_metadata()
        assert metadata["name"] == "test_plugin"
        assert metadata["version"] == "1.0.0"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "Test plugin description"
        assert metadata["agent_count"] == 1
        assert metadata["tool_count"] == 1