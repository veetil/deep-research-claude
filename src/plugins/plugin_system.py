"""
Plugin system for dynamically loading and managing agent extensions
"""
import asyncio
import importlib.util
import inspect
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Type, Optional, Set
from pathlib import Path

# Avoid circular import - we'll just use placeholder classes for the demo
from .exceptions import (
    PluginError, 
    PluginNotFoundError, 
    PluginAlreadyRegisteredError,
    PluginDependencyError,
    PluginValidationError
)


class Plugin(ABC):
    """Abstract base class for all plugins"""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.status = "uninitialized"
        self.initialized_at: Optional[datetime] = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the plugin"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None
        }


class AgentPlugin(Plugin):
    """Plugin that provides agent types and tools"""
    
    def __init__(self, 
                 name: str, 
                 version: str, 
                 agents: List[str], 
                 tools: List[str], 
                 config: Dict[str, Any],
                 dependencies: Optional[List[str]] = None,
                 author: Optional[str] = None,
                 description: Optional[str] = None):
        
        # Validate inputs
        if not name:
            raise ValueError("Plugin name cannot be empty")
        
        if not self._validate_version(version):
            raise ValueError("Invalid version format. Use semantic versioning (e.g., 1.0.0)")
        
        if not agents and not tools:
            raise ValueError("Plugin must provide at least one agent or tool")
        
        super().__init__(name, version)
        self.agents = agents
        self.tools = tools
        self.config = config
        self.dependencies = dependencies or []
        self.author = author
        self.description = description
        self.loaded_agents: Dict[str, Type[BaseAgent]] = {}
        self.loaded_tools: Dict[str, Any] = {}
        self.load_time_ms: float = 0
    
    def _validate_version(self, version: str) -> bool:
        """Validate semantic version format"""
        pattern = r'^\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$'
        return bool(re.match(pattern, version))
    
    async def initialize(self) -> None:
        """Initialize the plugin by loading agents and tools"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Load agent classes dynamically (simplified for examples)
            for agent_name in self.agents:
                # Create placeholder classes for demo
                self.loaded_agents[agent_name] = type(agent_name, (object,), {
                    '__module__': f'plugins.{self.name}.agents',
                    '__doc__': f'{agent_name} from plugin {self.name}'
                })
            
            # Load tools (simplified)
            for tool_name in self.tools:
                self.loaded_tools[tool_name] = f"{self.name}.{tool_name}"
            
            self.status = "active"
            self.initialized_at = datetime.now(timezone.utc)
            self.load_time_ms = (self.initialized_at - start_time).total_seconds() * 1000
            
        except Exception as e:
            self.status = "error"
            raise PluginError(f"Failed to initialize plugin {self.name}: {str(e)}")
    
    async def _load_agent(self, agent_name: str) -> None:
        """Dynamically load an agent class"""
        # For demo purposes, just create a placeholder
        # In production, this would actually load the agent module
        self.loaded_agents[agent_name] = type(agent_name, (object,), {
            '__module__': f'plugins.{self.name}.agents',
            '__doc__': f'{agent_name} from plugin {self.name}'
        })
    
    async def _load_tool(self, tool_name: str) -> None:
        """Load a tool (placeholder for now)"""
        # In a real implementation, this would load tool modules
        self.loaded_tools[tool_name] = f"{self.name}.{tool_name}"
    
    async def shutdown(self) -> None:
        """Shutdown the plugin"""
        self.status = "shutdown"
        self.loaded_agents.clear()
        self.loaded_tools.clear()
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get extended plugin metadata"""
        metadata = super().get_metadata()
        metadata.update({
            "author": self.author,
            "description": self.description,
            "agent_count": len(self.agents),
            "tool_count": len(self.tools),
            "dependencies": self.dependencies,
            "load_time_ms": self.load_time_ms
        })
        return metadata


@dataclass
class PluginUsageEvent:
    """Record of plugin usage"""
    plugin_name: str
    event_type: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class PluginSystem:
    """Manages plugin registration, lifecycle, and discovery"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.agent_registry: Dict[str, Type[BaseAgent]] = {}
        self.tool_registry: Dict[str, str] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.usage_events: List[PluginUsageEvent] = []
        self._lock = asyncio.Lock()
    
    async def register(self, plugin: Plugin) -> None:
        """Register a plugin"""
        async with self._lock:
            if plugin.name in self.plugins:
                raise PluginAlreadyRegisteredError(
                    f"Plugin '{plugin.name}' is already registered"
                )
            
            # Check dependencies
            if isinstance(plugin, AgentPlugin):
                for dep in plugin.dependencies:
                    if dep not in self.plugins:
                        raise PluginDependencyError(
                            f"Missing dependencies: {dep}"
                        )
            
            try:
                # Initialize the plugin
                await plugin.initialize()
                
                # Register the plugin
                self.plugins[plugin.name] = plugin
                
                # Register agents and tools if it's an AgentPlugin
                if isinstance(plugin, AgentPlugin):
                    # Store config
                    self.plugin_configs[plugin.name] = plugin.config.copy()
                    
                    # Register agents
                    for agent_name, agent_class in plugin.loaded_agents.items():
                        self.agent_registry[agent_name] = agent_class
                    
                    # Register tools
                    for tool_name in plugin.tools:
                        self.tool_registry[tool_name] = f"{plugin.name}.{tool_name}"
                
                # Record usage
                await self.record_plugin_usage(plugin.name, "registered", {
                    "version": plugin.version
                })
                
            except Exception as e:
                raise PluginError(f"Failed to initialize plugin: {str(e)}")
    
    async def unregister(self, plugin_name: str) -> None:
        """Unregister a plugin"""
        async with self._lock:
            if plugin_name not in self.plugins:
                raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
            
            plugin = self.plugins[plugin_name]
            
            # Shutdown the plugin
            await plugin.shutdown()
            
            # Remove from registries
            if isinstance(plugin, AgentPlugin):
                # Remove agents
                for agent_name in plugin.agents:
                    self.agent_registry.pop(agent_name, None)
                
                # Remove tools
                for tool_name in plugin.tools:
                    self.tool_registry.pop(tool_name, None)
                
                # Remove config
                self.plugin_configs.pop(plugin_name, None)
            
            # Remove plugin
            del self.plugins[plugin_name]
            
            # Record usage
            await self.record_plugin_usage(plugin_name, "unregistered", {})
    
    def is_registered(self, plugin_name: str) -> bool:
        """Check if a plugin is registered"""
        return plugin_name in self.plugins
    
    def list_plugins(self) -> List[str]:
        """List all registered plugins"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get information about a plugin"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        plugin = self.plugins[plugin_name]
        info = plugin.get_metadata()
        
        # Add usage metrics
        usage_count = sum(1 for event in self.usage_events 
                         if event.plugin_name == plugin_name)
        info["usage_count"] = usage_count
        
        return info
    
    def get_agent_types(self) -> List[str]:
        """Get all available agent types from plugins"""
        return list(self.agent_registry.keys())
    
    def get_available_tools(self) -> List[str]:
        """Get all available tools from plugins"""
        return list(self.tool_registry.keys())
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a tool"""
        if tool_name not in self.tool_registry:
            raise PluginNotFoundError(f"Tool '{tool_name}' not found")
        
        full_name = self.tool_registry[tool_name]
        plugin_name = full_name.split('.')[0]
        
        return {
            "name": tool_name,
            "plugin": plugin_name,
            "full_name": full_name
        }
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get plugin configuration"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        return self.plugin_configs.get(plugin_name, {}).copy()
    
    async def update_plugin_config(self, plugin_name: str, updates: Dict[str, Any]) -> None:
        """Update plugin configuration"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        async with self._lock:
            if plugin_name not in self.plugin_configs:
                self.plugin_configs[plugin_name] = {}
            
            self.plugin_configs[plugin_name].update(updates)
            
            # Update the plugin's config if it's an AgentPlugin
            plugin = self.plugins[plugin_name]
            if isinstance(plugin, AgentPlugin):
                plugin.config.update(updates)
    
    async def reload_plugin(self, plugin_name: str, new_plugin: Plugin) -> None:
        """Hot reload a plugin"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        # Unregister old version
        await self.unregister(plugin_name)
        
        # Register new version
        await self.register(new_plugin)
    
    def get_plugin_namespace(self, plugin_name: str) -> Dict[str, Any]:
        """Get plugin's isolated namespace"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        plugin = self.plugins[plugin_name]
        namespace = {
            "name": plugin_name,
            "agents": [],
            "tools": []
        }
        
        if isinstance(plugin, AgentPlugin):
            namespace["agents"] = plugin.agents.copy()
            namespace["tools"] = plugin.tools.copy()
        
        return namespace
    
    def get_plugin_metrics(self, plugin_name: str) -> Dict[str, Any]:
        """Get metrics for a plugin"""
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        
        plugin = self.plugins[plugin_name]
        metrics = {
            "status": plugin.status,
            "usage_count": sum(1 for event in self.usage_events 
                             if event.plugin_name == plugin_name)
        }
        
        if isinstance(plugin, AgentPlugin):
            metrics.update({
                "load_time_ms": plugin.load_time_ms,
                "agent_count": len(plugin.agents),
                "tool_count": len(plugin.tools)
            })
        
        return metrics
    
    async def record_plugin_usage(self, plugin_name: str, event_type: str, 
                                  details: Dict[str, Any]) -> None:
        """Record plugin usage event"""
        event = PluginUsageEvent(
            plugin_name=plugin_name,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
        self.usage_events.append(event)
    
    async def shutdown(self) -> None:
        """Shutdown all plugins"""
        async with self._lock:
            # Shutdown in reverse order of registration
            plugin_names = list(self.plugins.keys())
            for plugin_name in reversed(plugin_names):
                try:
                    await self.unregister(plugin_name)
                except Exception as e:
                    # Log error but continue shutdown
                    print(f"Error shutting down plugin {plugin_name}: {e}")
            
            # Clear all registries
            self.agent_registry.clear()
            self.tool_registry.clear()
            self.plugin_configs.clear()
            self.usage_events.clear()