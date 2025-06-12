"""
Base Agent classes and enums for the multi-agent system
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class AgentCapability(Enum):
    """Capabilities that agents can have"""
    # Research capabilities
    WEB_SEARCH = "web_search"
    ACADEMIC_SEARCH = "academic_search"
    DATA_COLLECTION = "data_collection"
    
    # Analysis capabilities
    ANALYSIS = "analysis"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    
    # Synthesis capabilities
    SYNTHESIS = "synthesis"
    SUMMARIZATION = "summarization"
    REPORT_GENERATION = "report_generation"
    
    # Language capabilities
    TRANSLATION = "translation"
    MULTILINGUAL = "multilingual"
    
    # Specialized capabilities
    FACT_CHECKING = "fact_checking"
    CRITICAL_THINKING = "critical_thinking"
    CREATIVE_THINKING = "creative_thinking"
    FINANCIAL_ANALYSIS = "financial_analysis"
    STRATEGIC_PLANNING = "strategic_planning"
    
    # Technical capabilities
    CODE_ANALYSIS = "code_analysis"
    TECHNICAL_WRITING = "technical_writing"
    
    # Quality control
    QUALITY_ASSURANCE = "quality_assurance"
    JUDGING = "judging"


class AgentStatus(Enum):
    """Status of an agent"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentPriority(Enum):
    """Priority levels for agents"""
    LOW = 1
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class AgentMessage:
    """Message passed between agents"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_agent_id: str = ""
    target_agent_id: Optional[str] = None
    message_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: AgentPriority = AgentPriority.MEDIUM
    requires_response: bool = False
    correlation_id: Optional[str] = None


@dataclass
class AgentContext:
    """Context for agent execution"""
    research_id: str
    user_id: str
    session_id: str
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, agent_type: str, capabilities: List[AgentCapability]):
        self.id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = AgentStatus.INITIALIZING
        self.parent_id: Optional[str] = None
        self.children_ids: Set[str] = set()
        self.context: Optional[AgentContext] = None
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.can_spawn_children = True
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def initialize(self, context: Dict[str, Any]):
        """Initialize the agent with context"""
        self.context = AgentContext(**context) if not isinstance(context, AgentContext) else context
        self.status = AgentStatus.READY
        self._running = True
        # Start message processing
        self._task = asyncio.create_task(self._process_messages())
        await self.on_initialize()
    
    async def terminate(self):
        """Terminate the agent"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = AgentStatus.TERMINATED
        await self.on_terminate()
    
    async def pause(self):
        """Pause agent execution"""
        self.status = AgentStatus.PAUSED
        await self.on_pause()
    
    async def resume(self):
        """Resume agent execution"""
        self.status = AgentStatus.READY
        await self.on_resume()
    
    async def restart(self):
        """Restart the agent"""
        await self.terminate()
        await self.initialize(self.context.__dict__ if self.context else {})
    
    async def receive_message(self, message: AgentMessage):
        """Receive a message from another agent"""
        await self.message_queue.put(message)
        self.last_activity = datetime.now(timezone.utc)
    
    async def send_message(self, target_agent_id: str, message_type: str, 
                          payload: Dict[str, Any], requires_response: bool = False) -> Optional[str]:
        """Send a message to another agent"""
        message = AgentMessage(
            source_agent_id=self.id,
            target_agent_id=target_agent_id,
            message_type=message_type,
            payload=payload,
            requires_response=requires_response
        )
        
        # This will be implemented by the orchestrator
        await self._send_message_internal(message)
        return message.id if requires_response else None
    
    async def broadcast_message(self, message_type: str, payload: Dict[str, Any],
                              capability_filter: Optional[AgentCapability] = None):
        """Broadcast a message to multiple agents"""
        message = AgentMessage(
            source_agent_id=self.id,
            message_type=message_type,
            payload=payload
        )
        
        await self._broadcast_message_internal(message, capability_filter)
    
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        if self.status in [AgentStatus.ERROR, AgentStatus.TERMINATED]:
            return False
        
        # Check if message processing is working
        if self.message_queue.qsize() > 100:  # Backlog too large
            return False
        
        # Check if agent is responsive
        return await self.on_health_check()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            "agent_id": self.id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "uptime": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            "message_queue_size": self.message_queue.qsize(),
            "last_activity": self.last_activity.isoformat(),
            "custom_metrics": await self.get_custom_metrics()
        }
    
    async def _process_messages(self):
        """Process incoming messages"""
        while self._running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                if self.status == AgentStatus.PAUSED:
                    # Re-queue message if paused
                    await self.message_queue.put(message)
                    await asyncio.sleep(0.1)
                    continue
                
                # Set status to busy while processing
                previous_status = self.status
                self.status = AgentStatus.BUSY
                
                try:
                    # Process the message
                    await self.process_message(message)
                except Exception as e:
                    await self.on_error(e, message)
                finally:
                    # Restore previous status
                    self.status = previous_status
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.status = AgentStatus.ERROR
                await self.on_error(e)
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    async def process_message(self, message: AgentMessage):
        """Process an incoming message"""
        pass
    
    @abstractmethod
    async def on_initialize(self):
        """Called when agent is initialized"""
        pass
    
    @abstractmethod
    async def on_terminate(self):
        """Called when agent is terminated"""
        pass
    
    @abstractmethod
    async def on_pause(self):
        """Called when agent is paused"""
        pass
    
    @abstractmethod
    async def on_resume(self):
        """Called when agent is resumed"""
        pass
    
    @abstractmethod
    async def on_health_check(self) -> bool:
        """Perform agent-specific health check"""
        pass
    
    @abstractmethod
    async def on_error(self, error: Exception, message: Optional[AgentMessage] = None):
        """Handle errors"""
        pass
    
    @abstractmethod
    async def get_custom_metrics(self) -> Dict[str, Any]:
        """Get agent-specific metrics"""
        pass
    
    # Internal methods (to be connected to orchestrator)
    
    async def _send_message_internal(self, message: AgentMessage):
        """Internal method to send message via orchestrator"""
        # This will be injected by the orchestrator
        raise NotImplementedError("Message sending must be handled by orchestrator")
    
    async def _broadcast_message_internal(self, message: AgentMessage, 
                                        capability_filter: Optional[AgentCapability]):
        """Internal method to broadcast message via orchestrator"""
        # This will be injected by the orchestrator
        raise NotImplementedError("Message broadcasting must be handled by orchestrator")