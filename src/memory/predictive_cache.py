"""
Predictive cache with ML-based access pattern prediction
"""
import numpy as np
from collections import defaultdict, Counter
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio


class PredictiveCache:
    """
    Cache with predictive prefetching based on access patterns.
    """
    
    def __init__(self, cache_size: int = 10000):
        self.cache_size = cache_size
        self.access_history = defaultdict(list)
        self.cache = {}
        self.prediction_model = AccessPatternPredictor()
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache with predictive prefetching.
        
        Args:
            key: The cache key
            
        Returns:
            Tuple of (value, hit/miss)
        """
        async with self._lock:
            # Record access
            self.access_history[key].append(datetime.now(timezone.utc))
            
            if key in self.cache:
                # Cache hit
                self.cache[key]['hits'] += 1
                self.cache[key]['last_access'] = datetime.now(timezone.utc)
                return self.cache[key]['value'], True
            
            # Cache miss - predict if should pre-fetch related
            related_keys = await self.predict_related_keys(key)
            asyncio.create_task(self.prefetch_related(related_keys))
            
            return None, False
    
    async def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with eviction if needed.
        
        Args:
            key: The cache key
            value: The value to cache
        """
        async with self._lock:
            if len(self.cache) >= self.cache_size:
                # Evict based on prediction
                await self.predictive_evict()
            
            self.cache[key] = {
                'value': value,
                'hits': 0,
                'last_access': datetime.now(timezone.utc),
                'created': datetime.now(timezone.utc)
            }
    
    async def predict_related_keys(self, key: str) -> List[str]:
        """Predict which keys are likely to be accessed next."""
        # Get access patterns
        patterns = self.analyze_access_patterns()
        
        # Use ML model to predict
        predictions = await self.prediction_model.predict_next_access(
            current_key=key,
            patterns=patterns,
            history=self.access_history
        )
        
        return predictions[:5]  # Top 5 predictions
    
    async def prefetch_related(self, keys: List[str]) -> None:
        """Prefetch predicted keys in background."""
        for key in keys:
            if key not in self.cache:
                # Simulate fetching from long-term storage
                value = await self.fetch_from_storage(key)
                if value:
                    await self.set(key, value)
    
    async def fetch_from_storage(self, key: str) -> Optional[Any]:
        """
        Simulate fetching from storage (placeholder).
        
        Args:
            key: The key to fetch
            
        Returns:
            The value if found
        """
        # This would connect to actual storage in production
        await asyncio.sleep(0.01)  # Simulate I/O
        return None
    
    async def predictive_evict(self) -> None:
        """Evict items least likely to be accessed."""
        # Calculate access probability for each item
        access_probs = {}
        
        for key, metadata in self.cache.items():
            # Features for prediction
            features = {
                'hits': metadata['hits'],
                'age': (datetime.now(timezone.utc) - metadata['created']).seconds,
                'recency': (datetime.now(timezone.utc) - metadata['last_access']).seconds,
                'access_frequency': len(self.access_history.get(key, [])),
            }
            
            # Predict future access probability
            prob = await self.prediction_model.predict_access_probability(features)
            access_probs[key] = prob
        
        # Evict items with lowest probability
        sorted_keys = sorted(access_probs.keys(), key=lambda k: access_probs[k])
        evict_count = len(self.cache) - int(self.cache_size * 0.9)  # Keep 90% full
        
        for key in sorted_keys[:evict_count]:
            del self.cache[key]
    
    def analyze_access_patterns(self) -> Dict[str, Any]:
        """
        Analyze access patterns for prediction.
        
        Returns:
            Pattern analysis results
        """
        total_accesses = sum(len(history) for history in self.access_history.values())
        unique_keys = len(self.access_history)
        
        # Calculate access frequencies
        access_counts = {key: len(history) for key, history in self.access_history.items()}
        
        return {
            'total_accesses': total_accesses,
            'unique_keys': unique_keys,
            'access_counts': access_counts,
            'avg_accesses_per_key': total_accesses / unique_keys if unique_keys > 0 else 0
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        total_hits = sum(item['hits'] for item in self.cache.values())
        total_accesses = sum(len(history) for history in self.access_history.values())
        
        return {
            'size': len(self.cache),
            'capacity': self.cache_size,
            'utilization': len(self.cache) / self.cache_size,
            'total_hits': total_hits,
            'total_accesses': total_accesses,
            'hit_rate': total_hits / total_accesses if total_accesses > 0 else 0
        }


class AccessPatternPredictor:
    """ML model for predicting cache access patterns."""
    
    def __init__(self):
        self.sequence_length = 10
        self.embedding_dim = 32
        
    async def predict_next_access(self, current_key: str, patterns: Dict, 
                                 history: Dict[str, List]) -> List[str]:
        """
        Predict next likely accesses based on patterns.
        
        Args:
            current_key: Current accessed key
            patterns: Access patterns
            history: Access history
            
        Returns:
            List of predicted keys
        """
        # Analyze sequential patterns
        sequences = self.extract_sequences(history)
        
        # Find similar sequences
        similar = self.find_similar_sequences(current_key, sequences)
        
        # Predict next keys
        predictions = []
        for seq in similar:
            if current_key in seq:
                idx = seq.index(current_key)
                if idx < len(seq) - 1:
                    predictions.append(seq[idx + 1])
        
        # Rank by frequency
        prediction_counts = Counter(predictions)
        
        return [key for key, _ in prediction_counts.most_common()]
    
    async def predict_access_probability(self, features: Dict[str, float]) -> float:
        """
        Predict probability of future access.
        
        Args:
            features: Features describing the cache entry
            
        Returns:
            Probability of future access (0-1)
        """
        # Simple heuristic model (in production, use proper ML)
        hits_weight = 0.4
        recency_weight = 0.3
        frequency_weight = 0.3
        
        # Normalize features
        max_recency = 3600  # 1 hour
        recency_score = max(0, 1 - features['recency'] / max_recency)
        
        # Calculate score
        score = (
            hits_weight * min(features['hits'] / 10, 1) +
            recency_weight * recency_score +
            frequency_weight * min(features['access_frequency'] / 20, 1)
        )
        
        return min(max(score, 0), 1)
    
    def extract_sequences(self, history: Dict[str, List]) -> List[List[str]]:
        """Extract access sequences from history."""
        # Combine all accesses with timestamps
        all_accesses = []
        for key, timestamps in history.items():
            for ts in timestamps:
                all_accesses.append((ts, key))
        
        # Sort by timestamp
        all_accesses.sort(key=lambda x: x[0])
        
        # Create sequences
        sequences = []
        for i in range(len(all_accesses) - self.sequence_length + 1):
            if i + self.sequence_length <= len(all_accesses):
                seq = [access[1] for access in all_accesses[i:i + self.sequence_length]]
                sequences.append(seq)
        
        return sequences
    
    def find_similar_sequences(self, key: str, sequences: List[List[str]]) -> List[List[str]]:
        """
        Find sequences containing the key.
        
        Args:
            key: The key to find
            sequences: List of sequences
            
        Returns:
            Similar sequences
        """
        return [seq for seq in sequences if key in seq]