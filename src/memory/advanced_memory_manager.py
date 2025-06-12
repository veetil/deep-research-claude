"""
Advanced memory manager integrating event sourcing, audit trail, and predictive cache
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import asyncio

from .event_sourcing import EventStore, Event, EventType
from .audit_trail import AuditTrail
from .predictive_cache import PredictiveCache


@dataclass
class MemoryItem:
    """Represents a memory item with metadata."""
    key: str
    value: Any
    timestamp: datetime
    metadata: Dict[str, Any]
    relevance_score: float = 1.0


class ShortTermMemory:
    """Short-term memory implementation."""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.memory: Dict[str, MemoryItem] = {}
        self._access_order: List[str] = []
    
    async def set(self, key: str, value: Any) -> None:
        """Store in short-term memory."""
        if key in self.memory:
            # Update existing
            self.memory[key].value = value
            self.memory[key].timestamp = datetime.now(timezone.utc)
        else:
            # Add new
            if len(self.memory) >= self.capacity:
                # Evict oldest
                oldest_key = self._access_order.pop(0)
                del self.memory[oldest_key]
            
            self.memory[key] = MemoryItem(
                key=key,
                value=value,
                timestamp=datetime.now(timezone.utc),
                metadata={}
            )
            self._access_order.append(key)
    
    async def search(self, query: str) -> List[MemoryItem]:
        """Search short-term memory."""
        results = []
        query_lower = query.lower()
        
        for key, item in self.memory.items():
            if query_lower in key.lower() or query_lower in str(item.value).lower():
                results.append(item)
        
        return sorted(results, key=lambda x: x.timestamp, reverse=True)


class LongTermVectorMemory:
    """Long-term memory with vector embeddings."""
    
    def __init__(self):
        self.storage: Dict[str, MemoryItem] = {}
        self.embeddings: Dict[str, List[float]] = {}
    
    async def store(self, key: str, value: Any, embedding: List[float], 
                   metadata: Dict[str, Any]) -> None:
        """Store in long-term memory with embedding."""
        self.storage[key] = MemoryItem(
            key=key,
            value=value,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
        self.embeddings[key] = embedding
    
    async def search(self, query_embedding: List[float], k: int = 10) -> List[MemoryItem]:
        """Vector similarity search."""
        if not self.embeddings:
            return []
        
        # Calculate similarities (simple cosine similarity)
        similarities = []
        for key, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((key, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        results = []
        for key, score in similarities[:k]:
            if key in self.storage:
                item = self.storage[key]
                item.relevance_score = score
                results.append(item)
        
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class SharedRedisMemory:
    """Shared memory implementation (simulated)."""
    
    def __init__(self):
        self.shared_storage: Dict[str, MemoryItem] = {}
    
    async def search(self, query: str) -> List[MemoryItem]:
        """Search shared memory."""
        results = []
        query_lower = query.lower()
        
        for key, item in self.shared_storage.items():
            if query_lower in key.lower() or query_lower in str(item.value).lower():
                results.append(item)
        
        return results


class AdvancedMemoryManager:
    """
    Advanced memory manager with event sourcing, audit trail, and multi-tier storage.
    """
    
    def __init__(self):
        self.event_store = EventStore()
        self.audit_trail = AuditTrail(self.event_store)
        self.predictive_cache = PredictiveCache()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermVectorMemory()
        self.shared = SharedRedisMemory()
        
    async def remember(self, key: str, value: Any, metadata: Dict[str, Any], 
                      actor: str) -> None:
        """Store memory with full audit trail."""
        # Create event
        event = Event(
            id=self.audit_trail.generate_event_id(),
            timestamp=datetime.now(timezone.utc),
            type=EventType.MEMORY_WRITE,
            aggregate_id=key,
            data={'key': key, 'value': value},
            actor=actor,
            metadata=metadata
        )
        
        # Store in event store
        await self.event_store.append(event)
        
        # Update caches
        await self.predictive_cache.set(key, value)
        await self.short_term.set(key, value)
        
        # Store in long-term with vector embedding
        if metadata.get('store_long_term', True):
            embedding = await self.generate_embedding(value)
            await self.long_term.store(key, value, embedding, metadata)
    
    async def recall(self, query: str, actor: str, 
                    context: Optional[Dict] = None) -> List[MemoryItem]:
        """Retrieve memories with multi-tier search."""
        # Log access attempt
        await self.audit_trail.log_access(
            resource_id=f"query_{query}",
            accessor=actor,
            action="read",
            result="pending"
        )
        
        # Check predictive cache first
        cached_result, hit = await self.predictive_cache.get(query)
        if hit:
            return cached_result if isinstance(cached_result, list) else [cached_result]
        
        # Multi-tier search
        results = []
        
        # Short-term search
        short_term_results = await self.short_term.search(query)
        results.extend(short_term_results)
        
        # Long-term vector search
        if len(results) < 10:
            query_embedding = await self.generate_embedding(query)
            long_term_results = await self.long_term.search(
                query_embedding, 
                k=10 - len(results)
            )
            results.extend(long_term_results)
        
        # Shared memory search
        if context and context.get('include_shared', True):
            shared_results = await self.shared.search(query)
            results.extend(shared_results)
        
        # Cache results
        await self.predictive_cache.set(query, results)
        
        # Log successful access
        await self.audit_trail.log_access(
            resource_id=f"query_{query}",
            accessor=actor,
            action="read",
            result="success",
            metadata={'result_count': len(results)}
        )
        
        return results
    
    async def get_memory_timeline(self, key: str, 
                                 start_time: Optional[datetime] = None) -> List[Event]:
        """Get complete timeline of memory changes."""
        return await self.audit_trail.get_access_history(key, start_time)
    
    async def time_travel(self, key: str, timestamp: datetime) -> Optional[Any]:
        """Get memory state at specific point in time."""
        state = await self.event_store.get_state_at(key, timestamp)
        return state.current_value
    
    async def generate_embedding(self, text: Any) -> List[float]:
        """
        Generate embedding for text (placeholder).
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # In production, use actual embedding model
        text_str = str(text)
        # Simple hash-based embedding for testing
        import hashlib
        hash_obj = hashlib.md5(text_str.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            if i + 4 <= len(hash_bytes):
                value = int.from_bytes(hash_bytes[i:i+4], 'big') / (2**32)
                embedding.append(value)
        
        # Pad to fixed size
        while len(embedding) < 32:
            embedding.append(0.0)
        
        return embedding[:32]
    
    async def apply_retention_policy(self) -> None:
        """Apply retention policies to all memories."""
        await self.audit_trail.apply_retention_policy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            'event_count': len(self.event_store.events),
            'aggregate_count': len(self.event_store.event_streams),
            'cache_stats': self.predictive_cache.get_cache_stats(),
            'short_term_size': len(self.short_term.memory),
            'long_term_size': len(self.long_term.storage),
            'shared_size': len(self.shared.shared_storage)
        }