"""
Test suite for advanced memory manager
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.memory.advanced_memory_manager import (
    AdvancedMemoryManager, MemoryItem, ShortTermMemory, 
    LongTermVectorMemory, SharedRedisMemory
)
from src.memory.event_sourcing import Event, EventType


@pytest.mark.asyncio
async def test_memory_manager_initialization():
    """Test memory manager initialization."""
    manager = AdvancedMemoryManager()
    
    assert manager.event_store is not None
    assert manager.audit_trail is not None
    assert manager.predictive_cache is not None
    assert manager.short_term is not None
    assert manager.long_term is not None
    assert manager.shared is not None


@pytest.mark.asyncio
async def test_remember_operation():
    """Test storing memories."""
    manager = AdvancedMemoryManager()
    
    await manager.remember(
        key="test_memory",
        value="Important information",
        metadata={"category": "test"},
        actor="test_agent"
    )
    
    # Check event was stored
    assert len(manager.event_store.events) == 1
    event = manager.event_store.events[0]
    assert event.type == EventType.MEMORY_WRITE
    assert event.actor == "test_agent"
    assert event.data['value'] == "Important information"


@pytest.mark.asyncio
async def test_recall_operation():
    """Test recalling memories."""
    manager = AdvancedMemoryManager()
    
    # Store some memories
    await manager.remember(
        key="quantum_research",
        value="Quantum computing breakthrough",
        metadata={"field": "physics"},
        actor="research_agent"
    )
    
    # Recall
    results = await manager.recall(
        query="quantum",
        actor="analysis_agent",
        context={"include_shared": True}
    )
    
    assert len(results) >= 1
    assert any("quantum" in str(item.value).lower() for item in results)


@pytest.mark.asyncio
async def test_time_travel():
    """Test time travel functionality."""
    manager = AdvancedMemoryManager()
    
    # Store initial value
    await manager.remember(
        key="evolving_data",
        value="Version 1",
        metadata={},
        actor="test"
    )
    
    # Get time after first write
    time1 = datetime.now(timezone.utc)
    
    # Wait a bit and update
    await asyncio.sleep(0.1)
    
    # Store update as new event
    event2 = Event(
        id=manager.audit_trail.generate_event_id(),
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_UPDATE,
        aggregate_id="evolving_data",
        data={'key': 'evolving_data', 'value': 'Version 2'},
        actor="test",
        metadata={}
    )
    await manager.event_store.append(event2)
    
    # Time travel to first version
    past_value = await manager.time_travel("evolving_data", time1)
    assert past_value == "Version 1"
    
    # Current value should be Version 2
    current_state = await manager.event_store.replay_events("evolving_data")
    assert current_state.current_value == "Version 2"


@pytest.mark.asyncio
async def test_memory_timeline():
    """Test getting memory timeline."""
    manager = AdvancedMemoryManager()
    
    # Create multiple events for same key
    for i in range(3):
        await manager.remember(
            key="tracked_data",
            value=f"Value {i}",
            metadata={},
            actor=f"agent_{i}"
        )
    
    # Get timeline
    timeline = await manager.get_memory_timeline("tracked_data")
    assert len(timeline) == 3
    
    # Timeline should be in order
    for i, event in enumerate(timeline):
        assert event.data['value'] == f"Value {i}"


@pytest.mark.asyncio
async def test_embedding_generation():
    """Test embedding generation."""
    manager = AdvancedMemoryManager()
    
    # Generate embeddings for different texts
    embed1 = await manager.generate_embedding("Hello world")
    embed2 = await manager.generate_embedding("Hello world")
    embed3 = await manager.generate_embedding("Different text")
    
    # Same text should produce same embedding
    assert embed1 == embed2
    
    # Different text should produce different embedding
    assert embed1 != embed3
    
    # Check embedding properties
    assert len(embed1) == 32
    assert all(isinstance(x, float) for x in embed1)


@pytest.mark.asyncio
async def test_short_term_memory():
    """Test short-term memory operations."""
    stm = ShortTermMemory(capacity=3)
    
    # Add items
    for i in range(5):
        await stm.set(f"key{i}", f"value{i}")
    
    # Should only keep last 3
    assert len(stm.memory) == 3
    assert "key2" in stm.memory
    assert "key3" in stm.memory
    assert "key4" in stm.memory
    
    # Search
    results = await stm.search("value3")
    assert len(results) == 1
    assert results[0].value == "value3"


@pytest.mark.asyncio
async def test_long_term_vector_memory():
    """Test long-term vector memory."""
    ltm = LongTermVectorMemory()
    
    # Store with embeddings
    await ltm.store(
        key="doc1",
        value="Machine learning document",
        embedding=[0.1] * 32,
        metadata={"type": "ml"}
    )
    
    await ltm.store(
        key="doc2",
        value="Quantum physics paper",
        embedding=[0.2] * 32,
        metadata={"type": "physics"}
    )
    
    # Search with similar embedding
    results = await ltm.search([0.15] * 32, k=1)
    assert len(results) == 1
    # Should return doc1 as it's closer to 0.15


@pytest.mark.asyncio
async def test_cosine_similarity():
    """Test cosine similarity calculation."""
    ltm = LongTermVectorMemory()
    
    # Test identical vectors
    vec1 = [1.0, 0.0, 0.0]
    similarity1 = ltm._cosine_similarity(vec1, vec1)
    assert abs(similarity1 - 1.0) < 0.001
    
    # Test orthogonal vectors
    vec2 = [0.0, 1.0, 0.0]
    similarity2 = ltm._cosine_similarity(vec1, vec2)
    assert abs(similarity2) < 0.001
    
    # Test opposite vectors
    vec3 = [-1.0, 0.0, 0.0]
    similarity3 = ltm._cosine_similarity(vec1, vec3)
    assert abs(similarity3 + 1.0) < 0.001


@pytest.mark.asyncio
async def test_shared_memory():
    """Test shared memory operations."""
    shared = SharedRedisMemory()
    
    # Add some data
    shared.shared_storage["shared1"] = MemoryItem(
        key="shared1",
        value="Shared knowledge",
        timestamp=datetime.now(timezone.utc),
        metadata={}
    )
    
    # Search
    results = await shared.search("shared")
    assert len(results) == 1
    assert results[0].value == "Shared knowledge"


@pytest.mark.asyncio
async def test_memory_stats():
    """Test memory statistics."""
    manager = AdvancedMemoryManager()
    
    # Add some data
    await manager.remember("key1", "value1", {}, "agent1")
    await manager.remember("key2", "value2", {}, "agent2")
    
    stats = manager.get_stats()
    
    assert stats['event_count'] == 2
    assert stats['aggregate_count'] == 2
    assert 'cache_stats' in stats
    assert stats['short_term_size'] == 2
    assert stats['long_term_size'] == 2


@pytest.mark.asyncio
async def test_apply_retention_policy():
    """Test retention policy application."""
    manager = AdvancedMemoryManager()
    
    # This should not raise an error
    await manager.apply_retention_policy()
    
    # Should complete without issues
    assert True


@pytest.mark.asyncio
async def test_predictive_cache_integration():
    """Test predictive cache integration with memory manager."""
    manager = AdvancedMemoryManager()
    
    # Store and immediately recall
    await manager.remember("cached_key", "cached_value", {}, "agent1")
    
    # First recall might be a miss
    results1 = await manager.recall("cached_key", "agent2")
    
    # Second recall should potentially hit cache
    results2 = await manager.recall("cached_key", "agent3")
    
    # Both should return results
    assert len(results1) > 0
    assert len(results2) > 0


# Import asyncio for sleep
import asyncio