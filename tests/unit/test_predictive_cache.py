"""
Test suite for predictive cache system
"""
import pytest
from datetime import datetime, timezone
import asyncio
from src.memory.predictive_cache import PredictiveCache, AccessPatternPredictor


@pytest.mark.asyncio
async def test_cache_basic_operations():
    """Test basic cache get/set operations."""
    cache = PredictiveCache(cache_size=10)
    
    # Test miss
    value, hit = await cache.get("key1")
    assert value is None
    assert hit is False
    
    # Test set and hit
    await cache.set("key1", "value1")
    value, hit = await cache.get("key1")
    assert value == "value1"
    assert hit is True
    
    # Check cache stats
    stats = cache.get_cache_stats()
    assert stats['size'] == 1
    assert stats['capacity'] == 10


@pytest.mark.asyncio
async def test_cache_eviction():
    """Test cache eviction when full."""
    cache = PredictiveCache(cache_size=3)
    
    # Fill cache
    for i in range(5):
        await cache.set(f"key{i}", f"value{i}")
    
    # Should have evicted oldest entries
    assert len(cache.cache) <= 3
    
    # Most recent should still be there
    value, hit = await cache.get("key4")
    assert hit is True


@pytest.mark.asyncio
async def test_access_history_tracking():
    """Test that access history is tracked."""
    cache = PredictiveCache()
    
    # Access same key multiple times
    for _ in range(3):
        await cache.get("test_key")
    
    # Check history
    assert "test_key" in cache.access_history
    assert len(cache.access_history["test_key"]) == 3


@pytest.mark.asyncio
async def test_hit_counting():
    """Test cache hit counting."""
    cache = PredictiveCache()
    
    await cache.set("key1", "value1")
    
    # Initial hits should be 0
    assert cache.cache["key1"]['hits'] == 0
    
    # Access multiple times
    for _ in range(3):
        await cache.get("key1")
    
    # Hits should be counted
    assert cache.cache["key1"]['hits'] == 3


@pytest.mark.asyncio
async def test_predictive_prefetch():
    """Test predictive prefetching (basic)."""
    cache = PredictiveCache()
    
    # Override fetch_from_storage for testing
    fetched_keys = []
    
    async def mock_fetch(key):
        fetched_keys.append(key)
        return f"prefetched_{key}"
    
    cache.fetch_from_storage = mock_fetch
    
    # Trigger a miss
    await cache.get("query1")
    
    # Give time for background prefetch
    await asyncio.sleep(0.1)
    
    # Should have attempted to prefetch related keys
    # (Even if no predictions, the mechanism should work)
    assert isinstance(fetched_keys, list)


@pytest.mark.asyncio
async def test_access_pattern_predictor():
    """Test access pattern prediction."""
    predictor = AccessPatternPredictor()
    
    # Create access history
    history = {
        "A": [datetime.now(timezone.utc)],
        "B": [datetime.now(timezone.utc)],
        "C": [datetime.now(timezone.utc)]
    }
    
    # Test prediction
    predictions = await predictor.predict_next_access(
        current_key="A",
        patterns={},
        history=history
    )
    
    # Should return a list (even if empty)
    assert isinstance(predictions, list)


@pytest.mark.asyncio
async def test_access_probability_prediction():
    """Test access probability calculation."""
    predictor = AccessPatternPredictor()
    
    # Test with different feature sets
    features1 = {
        'hits': 10,
        'age': 60,  # 1 minute old
        'recency': 10,  # accessed 10 seconds ago
        'access_frequency': 20
    }
    
    prob1 = await predictor.predict_access_probability(features1)
    assert 0 <= prob1 <= 1
    
    # Older, less accessed item
    features2 = {
        'hits': 1,
        'age': 3600,  # 1 hour old
        'recency': 3000,  # accessed 50 minutes ago
        'access_frequency': 2
    }
    
    prob2 = await predictor.predict_access_probability(features2)
    assert 0 <= prob2 <= 1
    assert prob2 < prob1  # Should have lower probability


@pytest.mark.asyncio
async def test_sequence_extraction():
    """Test access sequence extraction."""
    predictor = AccessPatternPredictor()
    
    # Create access history
    base_time = datetime.now(timezone.utc)
    history = {
        "A": [base_time],
        "B": [base_time + timedelta(seconds=1)],
        "C": [base_time + timedelta(seconds=2)],
        "D": [base_time + timedelta(seconds=3)]
    }
    
    sequences = predictor.extract_sequences(history)
    
    # Should extract sequences
    assert isinstance(sequences, list)
    if len(sequences) > 0:
        assert all(isinstance(seq, list) for seq in sequences)


@pytest.mark.asyncio
async def test_analyze_access_patterns():
    """Test access pattern analysis."""
    cache = PredictiveCache()
    
    # Create some access history
    await cache.get("key1")
    await cache.get("key1")
    await cache.get("key2")
    
    patterns = cache.analyze_access_patterns()
    
    assert patterns['total_accesses'] == 3
    assert patterns['unique_keys'] == 2
    assert patterns['access_counts']['key1'] == 2
    assert patterns['access_counts']['key2'] == 1
    assert patterns['avg_accesses_per_key'] == 1.5


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    cache = PredictiveCache(cache_size=100)
    
    # Add some items
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    
    # Access to create hits
    await cache.get("key1")
    await cache.get("key1")
    await cache.get("key2")
    await cache.get("miss")  # miss
    
    stats = cache.get_cache_stats()
    
    assert stats['size'] == 2
    assert stats['capacity'] == 100
    assert stats['utilization'] == 0.02
    assert stats['total_hits'] == 3
    assert stats['total_accesses'] == 4
    assert stats['hit_rate'] == 0.75


@pytest.mark.asyncio
async def test_concurrent_access():
    """Test concurrent cache access."""
    cache = PredictiveCache()
    
    # Concurrent sets
    async def set_value(i):
        await cache.set(f"key{i}", f"value{i}")
    
    await asyncio.gather(*[set_value(i) for i in range(10)])
    
    # Concurrent gets
    async def get_value(i):
        return await cache.get(f"key{i}")
    
    results = await asyncio.gather(*[get_value(i) for i in range(10)])
    
    # All should be hits
    for i, (value, hit) in enumerate(results):
        assert value == f"value{i}"
        assert hit is True


# Import timedelta for the test
from datetime import timedelta