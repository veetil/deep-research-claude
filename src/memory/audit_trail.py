"""
Audit trail system with GDPR compliance
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import hashlib
from .event_sourcing import EventStore, Event, EventType


class AuditTrail:
    """
    Comprehensive audit trail system with retention policies and compliance features.
    """
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.retention_policies = {
            'gdpr_personal_data': timedelta(days=365),  # 1 year
            'system_logs': timedelta(days=90),  # 90 days
            'research_data': timedelta(days=1825),  # 5 years
        }
    
    async def log_access(self, resource_id: str, accessor: str, 
                        action: str, result: str, metadata: Optional[Dict] = None):
        """
        Log an access attempt to a resource.
        
        Args:
            resource_id: The resource being accessed
            accessor: Who is accessing the resource
            action: The action being performed
            result: The result of the action
            metadata: Additional metadata
        """
        event = Event(
            id=self.generate_event_id(),
            timestamp=datetime.now(timezone.utc),
            type=EventType.MEMORY_READ if action == "read" else EventType.MEMORY_WRITE,
            aggregate_id=resource_id,
            data={
                'action': action,
                'result': result,
                'accessor': accessor
            },
            actor=accessor,
            metadata=metadata or {}
        )
        
        await self.event_store.append(event)
    
    async def get_access_history(self, resource_id: str, 
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None) -> List[Event]:
        """
        Get access history for a resource.
        
        Args:
            resource_id: The resource to get history for
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of access events
        """
        events = self.event_store.event_streams.get(resource_id, [])
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events
    
    async def apply_retention_policy(self):
        """Apply GDPR-compliant retention policies."""
        current_time = datetime.now(timezone.utc)
        
        # Create a copy of events to iterate over
        events_to_check = self.event_store.events.copy()
        
        for event in events_to_check:
            # Determine retention period
            data_type = event.metadata.get('data_type', 'system_logs')
            retention_period = self.retention_policies.get(data_type, timedelta(days=90))
            
            # Check if event should be deleted
            if current_time - event.timestamp > retention_period:
                await self.anonymize_or_delete(event)
    
    async def anonymize_or_delete(self, event: Event):
        """Anonymize personal data or delete event based on requirements."""
        if event.metadata.get('contains_pii', False):
            # Anonymize instead of delete
            event.data = self.anonymize_data(event.data)
            event.actor = self.hash_identifier(event.actor)
        else:
            # Safe to delete
            if event in self.event_store.events:
                self.event_store.events.remove(event)
            
            # Also remove from event streams
            aggregate_id = event.aggregate_id
            if aggregate_id in self.event_store.event_streams:
                if event in self.event_store.event_streams[aggregate_id]:
                    self.event_store.event_streams[aggregate_id].remove(event)
    
    def anonymize_data(self, data: Dict) -> Dict:
        """Remove or hash PII from data."""
        anonymized = data.copy()
        pii_fields = ['name', 'email', 'phone', 'address', 'ssn']
        
        for field in pii_fields:
            if field in anonymized:
                anonymized[field] = self.hash_identifier(str(anonymized[field]))
        
        return anonymized
    
    def hash_identifier(self, identifier: str) -> str:
        """Create consistent hash for anonymization."""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = datetime.now(timezone.utc).timestamp()
        return f"evt-{int(timestamp * 1000000)}"