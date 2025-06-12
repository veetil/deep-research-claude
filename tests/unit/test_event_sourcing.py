"""
Test suite for event sourcing system
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.memory.event_sourcing import (
    EventStore, Event, EventType, AggregateState
)


@pytest.mark.asyncio
async def test_event_store_captures_all_changes():
    """Test that event store captures all changes."""
    event_store = EventStore()
    
    # Create events
    events = [
        Event(
            id="evt-1",
            timestamp=datetime.now(timezone.utc),
            type=EventType.MEMORY_WRITE,
            aggregate_id="memory-1",
            data={"key": "research_1", "value": "quantum computing"},
            actor="agent-research-1"
        ),
        Event(
            id="evt-2",
            timestamp=datetime.now(timezone.utc),
            type=EventType.MEMORY_READ,
            aggregate_id="memory-1",
            data={"key": "research_1"},
            actor="agent-analysis-1"
        )
    ]
    
    # Store events
    for event in events:
        await event_store.append(event)
    
    # Replay events
    state = await event_store.replay_events("memory-1")
    assert len(state.events) == 2
    assert state.current_value == "quantum computing"
    assert state.version == 2
    
    # Time travel
    past_state = await event_store.get_state_at(
        "memory-1", 
        events[0].timestamp
    )
    assert len(past_state.events) == 1
    assert past_state.current_value == "quantum computing"


@pytest.mark.asyncio
async def test_event_serialization():
    """Test event serialization and deserialization."""
    event = Event(
        id="evt-test",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_UPDATE,
        aggregate_id="test-agg",
        data={"key": "test", "value": {"nested": "data"}},
        actor="test-actor",
        metadata={"version": "1.0"}
    )
    
    # Serialize
    json_str = event.to_json()
    
    # Deserialize
    restored = Event.from_json(json_str)
    
    assert restored.id == event.id
    assert restored.type == event.type
    assert restored.aggregate_id == event.aggregate_id
    assert restored.data == event.data
    assert restored.actor == event.actor
    assert restored.metadata == event.metadata


@pytest.mark.asyncio
async def test_event_store_subscriptions():
    """Test event store subscription mechanism."""
    event_store = EventStore()
    received_events = []
    
    # Subscribe to events
    async def handler(event):
        received_events.append(event)
    
    event_store.subscribe("memory-1", handler)
    
    # Append event
    event = Event(
        id="evt-sub",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="memory-1",
        data={"key": "test", "value": "subscription"},
        actor="test"
    )
    
    await event_store.append(event)
    
    # Check handler was called
    assert len(received_events) == 1
    assert received_events[0].id == "evt-sub"


@pytest.mark.asyncio
async def test_event_store_snapshots():
    """Test snapshot creation and usage."""
    event_store = EventStore()
    
    # Create many events to trigger snapshot
    base_time = datetime.now(timezone.utc)
    for i in range(105):  # Snapshot at 100
        event = Event(
            id=f"evt-{i}",
            timestamp=base_time + timedelta(seconds=i),
            type=EventType.MEMORY_UPDATE,
            aggregate_id="memory-snap",
            data={"key": "counter", "value": i},
            actor="test"
        )
        await event_store.append(event)
    
    # Check snapshot exists
    assert "memory-snap" in event_store.snapshots
    
    # Replay should use snapshot
    state = await event_store.replay_events("memory-snap")
    assert state.current_value == 104  # Last value
    assert state.version == 105


@pytest.mark.asyncio
async def test_memory_update_event():
    """Test memory update event handling."""
    event_store = EventStore()
    
    # Initial write
    await event_store.append(Event(
        id="evt-1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="mem-1",
        data={"key": "test", "value": {"field1": "value1"}},
        actor="test"
    ))
    
    # Update
    await event_store.append(Event(
        id="evt-2",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_UPDATE,
        aggregate_id="mem-1",
        data={"key": "test", "value": {"field2": "value2"}},
        actor="test"
    ))
    
    state = await event_store.replay_events("mem-1")
    assert isinstance(state.current_value, dict)
    assert state.current_value == {"field1": "value1", "field2": "value2"}


@pytest.mark.asyncio
async def test_memory_delete_event():
    """Test memory delete event handling."""
    event_store = EventStore()
    
    # Write
    await event_store.append(Event(
        id="evt-1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="mem-del",
        data={"key": "test", "value": "to_delete"},
        actor="test"
    ))
    
    # Delete
    await event_store.append(Event(
        id="evt-2",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_DELETE,
        aggregate_id="mem-del",
        data={"key": "test"},
        actor="test"
    ))
    
    state = await event_store.replay_events("mem-del")
    assert state.current_value is None
    assert state.version == 2


@pytest.mark.asyncio
async def test_cache_events():
    """Test cache hit/miss/evict events."""
    event_store = EventStore()
    
    cache_events = [
        Event(
            id="evt-cache-1",
            timestamp=datetime.now(timezone.utc),
            type=EventType.CACHE_MISS,
            aggregate_id="cache-1",
            data={"key": "search_query", "query": "AI research"},
            actor="cache-system"
        ),
        Event(
            id="evt-cache-2",
            timestamp=datetime.now(timezone.utc),
            type=EventType.CACHE_HIT,
            aggregate_id="cache-1",
            data={"key": "search_query", "query": "AI research"},
            actor="cache-system"
        ),
        Event(
            id="evt-cache-3",
            timestamp=datetime.now(timezone.utc),
            type=EventType.CACHE_EVICT,
            aggregate_id="cache-1",
            data={"key": "old_query", "reason": "LRU"},
            actor="cache-system"
        )
    ]
    
    for event in cache_events:
        await event_store.append(event)
    
    # Get cache events
    cache_stream = event_store.event_streams.get("cache-1", [])
    assert len(cache_stream) == 3
    assert cache_stream[0].type == EventType.CACHE_MISS
    assert cache_stream[1].type == EventType.CACHE_HIT
    assert cache_stream[2].type == EventType.CACHE_EVICT


@pytest.mark.asyncio
async def test_aggregate_state_initialization():
    """Test aggregate state initialization."""
    state = AggregateState(
        aggregate_id="test-agg",
        events=[],
        current_value=None,
        version=0
    )
    
    assert state.aggregate_id == "test-agg"
    assert len(state.events) == 0
    assert state.current_value is None
    assert state.version == 0


@pytest.mark.asyncio
async def test_event_store_multiple_aggregates():
    """Test event store with multiple aggregates."""
    event_store = EventStore()
    
    # Events for different aggregates
    await event_store.append(Event(
        id="evt-a1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="agg-A",
        data={"value": "A"},
        actor="test"
    ))
    
    await event_store.append(Event(
        id="evt-b1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="agg-B",
        data={"value": "B"},
        actor="test"
    ))
    
    # Replay each aggregate
    state_a = await event_store.replay_events("agg-A")
    state_b = await event_store.replay_events("agg-B")
    
    assert state_a.current_value == "A"
    assert state_b.current_value == "B"
    assert len(state_a.events) == 1
    assert len(state_b.events) == 1


@pytest.mark.asyncio
async def test_time_travel_multiple_points():
    """Test time travel to multiple points in history."""
    event_store = EventStore()
    base_time = datetime.now(timezone.utc)
    
    # Create events at different times
    times = []
    for i in range(5):
        timestamp = base_time + timedelta(minutes=i)
        times.append(timestamp)
        
        await event_store.append(Event(
            id=f"evt-{i}",
            timestamp=timestamp,
            type=EventType.MEMORY_WRITE,
            aggregate_id="time-travel",
            data={"value": f"state-{i}"},
            actor="test"
        ))
    
    # Travel to different points
    for i, time_point in enumerate(times):
        state = await event_store.get_state_at("time-travel", time_point)
        assert state.current_value == f"state-{i}"
        assert len(state.events) == i + 1


@pytest.mark.asyncio
async def test_empty_aggregate_replay():
    """Test replaying non-existent aggregate."""
    event_store = EventStore()
    
    state = await event_store.replay_events("non-existent")
    assert state.aggregate_id == "non-existent"
    assert len(state.events) == 0
    assert state.current_value is None
    assert state.version == 0


@pytest.mark.asyncio
async def test_concurrent_event_appends():
    """Test concurrent event appends."""
    event_store = EventStore()
    
    # Create multiple events concurrently
    import asyncio
    
    async def append_event(i):
        await event_store.append(Event(
            id=f"evt-concurrent-{i}",
            timestamp=datetime.now(timezone.utc),
            type=EventType.MEMORY_WRITE,
            aggregate_id="concurrent",
            data={"value": i},
            actor=f"actor-{i}"
        ))
    
    # Append 10 events concurrently
    await asyncio.gather(*[append_event(i) for i in range(10)])
    
    # Check all events were stored
    state = await event_store.replay_events("concurrent")
    assert len(state.events) == 10