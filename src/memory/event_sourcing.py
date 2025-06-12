"""
Event sourcing system for comprehensive audit trail and time travel capabilities
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import json
import asyncio
from collections import defaultdict


class EventType(Enum):
    """Types of events that can occur in the memory system."""
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    MEMORY_DELETE = "memory_delete"
    MEMORY_UPDATE = "memory_update"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_EVICT = "cache_evict"


@dataclass
class Event:
    """Immutable event representing a change in the system."""
    id: str
    timestamp: datetime
    type: EventType
    aggregate_id: str
    data: Dict[str, Any]
    actor: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps({
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'type': self.type.value,
            'aggregate_id': self.aggregate_id,
            'data': self.data,
            'actor': self.actor,
            'metadata': self.metadata
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        return cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            type=EventType(data['type']),
            aggregate_id=data['aggregate_id'],
            data=data['data'],
            actor=data['actor'],
            metadata=data.get('metadata', {})
        )


@dataclass
class AggregateState:
    """Current state of an aggregate after applying events."""
    aggregate_id: str
    events: List[Event]
    current_value: Any
    version: int


class EventStore:
    """
    Event store for managing events with replay and time travel capabilities.
    """
    
    def __init__(self):
        self.events: List[Event] = []
        self.event_streams: Dict[str, List[Event]] = defaultdict(list)
        self.snapshots: Dict[str, AggregateState] = {}
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def append(self, event: Event) -> None:
        """
        Append an event to the store.
        
        Args:
            event: The event to append
        """
        async with self._lock:
            # Store event
            self.events.append(event)
            self.event_streams[event.aggregate_id].append(event)
            
            # Publish to subscribers
            await self.publish_event(event)
            
            # Update snapshot if needed
            if len(self.event_streams[event.aggregate_id]) % 100 == 0:
                await self.create_snapshot(event.aggregate_id)
    
    async def replay_events(self, aggregate_id: str) -> AggregateState:
        """
        Replay all events for an aggregate to reconstruct its current state.
        
        Args:
            aggregate_id: The aggregate to replay
            
        Returns:
            The current state of the aggregate
        """
        events = self.event_streams.get(aggregate_id, [])
        
        # Start from snapshot if available
        if aggregate_id in self.snapshots:
            state = self.snapshots[aggregate_id]
            # Apply events after snapshot
            if state.events:
                last_snapshot_time = state.events[-1].timestamp
                recent_events = [e for e in events if e.timestamp > last_snapshot_time]
            else:
                recent_events = events
        else:
            state = AggregateState(aggregate_id, [], None, 0)
            recent_events = events
        
        # Apply events
        for event in recent_events:
            state = await self.apply_event(state, event)
        
        return state
    
    async def apply_event(self, state: AggregateState, event: Event) -> AggregateState:
        """
        Apply an event to an aggregate state.
        
        Args:
            state: Current state
            event: Event to apply
            
        Returns:
            Updated state
        """
        state.events.append(event)
        state.version += 1
        
        if event.type == EventType.MEMORY_WRITE:
            state.current_value = event.data.get('value')
        elif event.type == EventType.MEMORY_UPDATE:
            if isinstance(state.current_value, dict) and isinstance(event.data.get('value'), dict):
                state.current_value.update(event.data['value'])
            else:
                state.current_value = event.data.get('value')
        elif event.type == EventType.MEMORY_DELETE:
            state.current_value = None
        
        # For other event types that modify the value
        elif hasattr(event, 'data') and 'value' in event.data:
            state.current_value = event.data['value']
        
        return state
    
    async def get_state_at(self, aggregate_id: str, timestamp: datetime) -> AggregateState:
        """
        Get the state of an aggregate at a specific point in time.
        
        Args:
            aggregate_id: The aggregate ID
            timestamp: The point in time
            
        Returns:
            The state at that time
        """
        events = [e for e in self.event_streams.get(aggregate_id, []) 
                 if e.timestamp <= timestamp]
        state = AggregateState(aggregate_id, [], None, 0)
        
        for event in events:
            state = await self.apply_event(state, event)
        
        return state
    
    async def create_snapshot(self, aggregate_id: str) -> None:
        """
        Create a snapshot of the current state.
        
        Args:
            aggregate_id: The aggregate to snapshot
        """
        state = await self.replay_events(aggregate_id)
        self.snapshots[aggregate_id] = state
    
    def subscribe(self, aggregate_id: str, handler: Callable) -> None:
        """
        Subscribe to events for a specific aggregate.
        
        Args:
            aggregate_id: The aggregate to subscribe to
            handler: Async function to handle events
        """
        self.subscribers[aggregate_id].append(handler)
    
    def unsubscribe(self, aggregate_id: str, handler: Callable) -> None:
        """
        Unsubscribe from events.
        
        Args:
            aggregate_id: The aggregate to unsubscribe from
            handler: The handler to remove
        """
        if handler in self.subscribers[aggregate_id]:
            self.subscribers[aggregate_id].remove(handler)
    
    async def publish_event(self, event: Event) -> None:
        """
        Publish event to all subscribers.
        
        Args:
            event: The event to publish
        """
        handlers = self.subscribers.get(event.aggregate_id, [])
        
        # Use asyncio.gather to call all handlers concurrently
        if handlers:
            await asyncio.gather(
                *[handler(event) for handler in handlers],
                return_exceptions=True
            )
    
    def get_events_by_type(self, event_type: EventType, 
                          limit: Optional[int] = None) -> List[Event]:
        """
        Get events by type.
        
        Args:
            event_type: The type of events to retrieve
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        matching = [e for e in self.events if e.type == event_type]
        
        if limit:
            return matching[-limit:]
        return matching
    
    def get_events_by_actor(self, actor: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> List[Event]:
        """
        Get events by actor within a time range.
        
        Args:
            actor: The actor who created the events
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of matching events
        """
        events = [e for e in self.events if e.actor == actor]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events