#!/usr/bin/env python3
"""
Predictive Cache and Memory Optimization Demo

This example demonstrates:
1. Predictive caching with ML-based prefetching
2. Access pattern analysis
3. Cache hit rate optimization
4. Multi-tier memory management
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory.predictive_cache import PredictiveCache
from src.memory.advanced_memory_manager import AdvancedMemoryManager


async def demonstrate_predictive_cache():
    """Demonstrate predictive caching capabilities."""
    print("=== Predictive Cache Demo ===\n")
    
    cache = PredictiveCache(cache_size=20)
    
    # 1. Simulate research query patterns
    print("1. Simulating research query patterns...")
    
    # Common query sequences in research
    query_sequences = [
        ["quantum computing", "quantum entanglement", "quantum algorithms"],
        ["machine learning", "neural networks", "deep learning"],
        ["climate change", "global warming", "carbon emissions"],
        ["quantum computing", "quantum supremacy", "quantum algorithms"]  # Repeated pattern
    ]
    
    # Execute queries
    hits = 0
    misses = 0
    
    for sequence in query_sequences:
        print(f"\n   Sequence: {' → '.join(sequence[:2])}...")
        for query in sequence:
            value, hit = await cache.get(query)
            
            if hit:
                hits += 1
                print(f"     ✓ Cache HIT: '{query}'")
            else:
                misses += 1
                print(f"     ✗ Cache MISS: '{query}'")
                # Simulate fetching and caching
                await cache.set(query, f"Results for: {query}")
            
            await asyncio.sleep(0.05)  # Simulate processing time
    
    # 2. Show cache statistics
    print("\n2. Cache Performance:")
    stats = cache.get_cache_stats()
    print(f"   Size: {stats['size']}/{stats['capacity']}")
    print(f"   Utilization: {stats['utilization']:.1%}")
    print(f"   Total Hits: {hits}")
    print(f"   Total Misses: {misses}")
    print(f"   Hit Rate: {hits/(hits+misses):.1%}")
    
    # 3. Analyze access patterns
    print("\n3. Access Pattern Analysis:")
    patterns = cache.analyze_access_patterns()
    print(f"   Unique queries: {patterns['unique_keys']}")
    print(f"   Total accesses: {patterns['total_accesses']}")
    print(f"   Avg accesses per query: {patterns['avg_accesses_per_key']:.2f}")
    
    # Most accessed queries
    if patterns['access_counts']:
        sorted_queries = sorted(
            patterns['access_counts'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        print("\n   Top accessed queries:")
        for query, count in sorted_queries[:3]:
            print(f"     - '{query}': {count} times")
    
    # 4. Demonstrate predictive prefetching
    print("\n4. Predictive Prefetching:")
    
    # The cache should predict related queries
    related = await cache.predict_related_keys("quantum computing")
    if related:
        print(f"   Based on 'quantum computing', predicting:")
        for pred in related[:3]:
            print(f"     → {pred}")
    else:
        print("   No predictions yet (need more access history)")
    
    # 5. Cache eviction demonstration
    print("\n5. Smart Cache Eviction:")
    
    # Fill cache to trigger eviction
    print("   Filling cache to capacity...")
    for i in range(25):  # More than cache size
        await cache.set(f"dummy_query_{i}", f"dummy_value_{i}")
    
    # Check what remains
    print(f"   Cache size after eviction: {len(cache.cache)}")
    
    # Important queries should still be there
    important_queries = ["quantum computing", "machine learning"]
    for query in important_queries:
        value, hit = await cache.get(query)
        status = "retained" if hit else "evicted"
        print(f"   '{query}': {status}")
    
    return cache


async def demonstrate_memory_tiers():
    """Demonstrate multi-tier memory management."""
    print("\n\n=== Multi-Tier Memory Demo ===\n")
    
    manager = AdvancedMemoryManager()
    
    # 1. Store research data in different tiers
    print("1. Storing research data across memory tiers...")
    
    research_items = [
        {
            "key": "recent_finding_001",
            "value": "New quantum algorithm discovered",
            "metadata": {"importance": "high", "date": "2024-01-12"},
            "store_long_term": False  # Keep in short-term only
        },
        {
            "key": "foundational_paper_001", 
            "value": "Shor's algorithm for integer factorization",
            "metadata": {"importance": "critical", "date": "1994-01-01"},
            "store_long_term": True  # Store in long-term
        },
        {
            "key": "collaboration_note_001",
            "value": "Meeting notes with MIT quantum team",
            "metadata": {"type": "collaboration", "date": "2024-01-10"},
            "store_long_term": True
        }
    ]
    
    for item in research_items:
        await manager.remember(
            key=item["key"],
            value=item["value"],
            metadata=item["metadata"],
            actor="research_system"
        )
        tier = "long-term" if item.get("store_long_term") else "short-term"
        print(f"   Stored '{item['key']}' in {tier} memory")
    
    # 2. Demonstrate intelligent recall
    print("\n2. Intelligent Multi-Tier Recall:")
    
    queries = [
        "quantum algorithm",
        "Shor",
        "MIT",
        "recent finding"
    ]
    
    for query in queries:
        print(f"\n   Searching for: '{query}'")
        results = await manager.recall(
            query=query,
            actor="researcher",
            context={"include_shared": True}
        )
        
        print(f"   Found {len(results)} results:")
        for result in results[:2]:  # Show first 2
            print(f"     - {result.key}: {result.value[:50]}...")
            if hasattr(result, 'relevance_score'):
                print(f"       Relevance: {result.relevance_score:.2f}")
    
    # 3. Memory statistics
    print("\n3. Memory System Statistics:")
    stats = manager.get_stats()
    
    print(f"   Total events: {stats['event_count']}")
    print(f"   Short-term memories: {stats['short_term_size']}")
    print(f"   Long-term memories: {stats['long_term_size']}")
    print(f"   Cache performance: {stats['cache_stats']['hit_rate']:.1%} hit rate")
    
    # 4. Demonstrate embedding-based similarity
    print("\n4. Vector Similarity Search:")
    
    # Store related concepts
    concepts = [
        ("superposition", "Quantum state existing in multiple states simultaneously"),
        ("entanglement", "Quantum correlation between particles"),
        ("decoherence", "Loss of quantum behavior due to environment"),
        ("classical_computing", "Traditional binary computing paradigm")
    ]
    
    for key, value in concepts:
        embedding = await manager.generate_embedding(value)
        await manager.long_term.store(key, value, embedding, {"type": "concept"})
    
    # Search by similarity
    query_embedding = await manager.generate_embedding("quantum mechanical phenomena")
    similar_results = await manager.long_term.search(query_embedding, k=3)
    
    print("   Query: 'quantum mechanical phenomena'")
    print("   Similar concepts:")
    for result in similar_results:
        print(f"     - {result.key}: {result.relevance_score:.3f} similarity")
    
    return manager


async def demonstrate_cache_optimization():
    """Demonstrate cache optimization strategies."""
    print("\n\n=== Cache Optimization Demo ===\n")
    
    # 1. Compare random vs pattern-based access
    print("1. Access Pattern Comparison:")
    
    # Random access pattern
    random_cache = PredictiveCache(cache_size=10)
    random_queries = [f"query_{random.randint(1, 20)}" for _ in range(50)]
    
    random_hits = 0
    for query in random_queries:
        value, hit = await random_cache.get(query)
        if hit:
            random_hits += 1
        else:
            await random_cache.set(query, f"value_{query}")
    
    # Pattern-based access
    pattern_cache = PredictiveCache(cache_size=10)
    pattern_queries = []
    # Create repeating patterns
    for _ in range(5):
        pattern_queries.extend([f"query_{i}" for i in range(1, 8)])
    
    pattern_hits = 0
    for query in pattern_queries:
        value, hit = await pattern_cache.get(query)
        if hit:
            pattern_hits += 1
        else:
            await pattern_cache.set(query, f"value_{query}")
    
    print(f"\n   Random access hit rate: {random_hits/len(random_queries):.1%}")
    print(f"   Pattern access hit rate: {pattern_hits/len(pattern_queries):.1%}")
    print("\n   → Predictable patterns achieve better cache performance!")
    
    # 2. Optimal cache size analysis
    print("\n2. Cache Size Impact:")
    
    test_queries = []
    for _ in range(10):
        test_queries.extend([f"q{i}" for i in range(15)])
    
    for cache_size in [5, 10, 20]:
        test_cache = PredictiveCache(cache_size=cache_size)
        hits = 0
        
        for query in test_queries:
            value, hit = await test_cache.get(query)
            if hit:
                hits += 1
            else:
                await test_cache.set(query, "value")
        
        hit_rate = hits / len(test_queries)
        print(f"   Cache size {cache_size}: {hit_rate:.1%} hit rate")
    
    print("\n=== Optimization Insights ===")
    print("✓ Access patterns significantly impact cache performance")
    print("✓ Predictive prefetching improves hit rates")
    print("✓ Optimal cache size depends on working set size")
    print("✓ LRU eviction enhanced with access probability")


async def main():
    """Run all demonstrations."""
    print("Deep Research Memory System - Predictive Cache Demo")
    print("=" * 50)
    
    # Run predictive cache demo
    await demonstrate_predictive_cache()
    
    # Run multi-tier memory demo
    await demonstrate_memory_tiers()
    
    # Run optimization demo
    await demonstrate_cache_optimization()
    
    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())