"""
Memory system for deep research
"""
from .event_sourcing import Event, EventType, EventStore, AggregateState
from .audit_trail import AuditTrail
from .predictive_cache import PredictiveCache, AccessPatternPredictor
from .advanced_memory_manager import AdvancedMemoryManager
from .gdpr_compliance import GDPRCompliantMemory, ConsentRequiredError

__all__ = [
    'Event',
    'EventType', 
    'EventStore',
    'AggregateState',
    'AuditTrail',
    'PredictiveCache',
    'AccessPatternPredictor',
    'AdvancedMemoryManager',
    'GDPRCompliantMemory',
    'ConsentRequiredError'
]