"""
Deep Research Claude - Multi-agent AI research system
"""

__version__ = "0.1.0"
__author__ = "Deep Research Team"

# Core components
from src.core.orchestrator import AgentOrchestrator, AgentSpawnRequest
from src.core.message_queue import MessageQueue, MessageBus
from src.core.registry import AgentRegistry, AgentDiscoveryService

# Base agent classes
from src.agents.base import (
    BaseAgent,
    AgentCapability,
    AgentStatus,
    AgentPriority,
    AgentMessage,
    AgentContext
)

# Agent implementations
from src.agents.research_agent import ResearchAgent

__all__ = [
    # Core
    'AgentOrchestrator',
    'AgentSpawnRequest',
    'MessageQueue',
    'MessageBus',
    'AgentRegistry',
    'AgentDiscoveryService',
    
    # Base classes
    'BaseAgent',
    'AgentCapability',
    'AgentStatus',
    'AgentPriority',
    'AgentMessage',
    'AgentContext',
    
    # Agents
    'ResearchAgent',
]