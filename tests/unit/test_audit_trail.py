"""
Test suite for audit trail system
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.memory.event_sourcing import EventStore, Event, EventType
from src.memory.audit_trail import AuditTrail


@pytest.mark.asyncio
async def test_audit_trail_log_access():
    """Test logging access to resources."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Log a read access
    await audit_trail.log_access(
        resource_id="doc-123",
        accessor="user-1",
        action="read",
        result="success",
        metadata={"ip": "192.168.1.1"}
    )
    
    # Check event was logged
    assert len(event_store.events) == 1
    event = event_store.events[0]
    assert event.type == EventType.MEMORY_READ
    assert event.actor == "user-1"
    assert event.data['action'] == "read"
    assert event.data['result'] == "success"
    assert event.metadata['ip'] == "192.168.1.1"


@pytest.mark.asyncio
async def test_audit_trail_access_history():
    """Test retrieving access history."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Log multiple accesses
    base_time = datetime.now(timezone.utc)
    for i in range(5):
        await audit_trail.log_access(
            resource_id="doc-456",
            accessor=f"user-{i}",
            action="read",
            result="success"
        )
    
    # Get full history
    history = await audit_trail.get_access_history("doc-456")
    assert len(history) == 5
    
    # Get history with time range
    mid_time = base_time + timedelta(minutes=1)
    recent_history = await audit_trail.get_access_history(
        "doc-456",
        start_time=mid_time
    )
    assert len(recent_history) < 5


@pytest.mark.asyncio
async def test_retention_policy():
    """Test GDPR retention policy application."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Create old events
    old_time = datetime.now(timezone.utc) - timedelta(days=100)
    
    # System log (90 day retention)
    old_event = Event(
        id="evt-old-1",
        timestamp=old_time,
        type=EventType.MEMORY_READ,
        aggregate_id="system-log",
        data={"action": "read"},
        actor="system",
        metadata={"data_type": "system_logs"}
    )
    await event_store.append(old_event)
    
    # Recent event
    recent_event = Event(
        id="evt-recent-1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_WRITE,
        aggregate_id="recent-data",
        data={"action": "write"},
        actor="user",
        metadata={"data_type": "system_logs"}
    )
    await event_store.append(recent_event)
    
    # Apply retention policy
    await audit_trail.apply_retention_policy()
    
    # Old event should be deleted
    assert len(event_store.events) == 1
    assert event_store.events[0].id == "evt-recent-1"


@pytest.mark.asyncio
async def test_anonymize_pii():
    """Test PII anonymization."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Create event with PII
    pii_event = Event(
        id="evt-pii",
        timestamp=datetime.now(timezone.utc) - timedelta(days=400),
        type=EventType.MEMORY_WRITE,
        aggregate_id="user-data",
        data={
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "other": "non-pii"
        },
        actor="user-123",
        metadata={"contains_pii": True, "data_type": "gdpr_personal_data"}
    )
    await event_store.append(pii_event)
    
    # Apply retention policy (should anonymize, not delete)
    await audit_trail.apply_retention_policy()
    
    # Event should still exist but be anonymized
    assert len(event_store.events) == 1
    anonymized = event_store.events[0]
    
    # Check PII is hashed
    assert anonymized.data['name'] != "John Doe"
    assert len(anonymized.data['name']) == 16  # Hash length
    assert anonymized.data['email'] != "john@example.com"
    assert anonymized.data['other'] == "non-pii"  # Non-PII unchanged
    assert anonymized.actor != "user-123"


@pytest.mark.asyncio
async def test_event_id_generation():
    """Test unique event ID generation."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Generate multiple IDs
    ids = set()
    for _ in range(100):
        event_id = audit_trail.generate_event_id()
        assert event_id.startswith("evt-")
        ids.add(event_id)
    
    # All IDs should be unique
    assert len(ids) == 100


@pytest.mark.asyncio
async def test_hash_identifier():
    """Test identifier hashing."""
    audit_trail = AuditTrail(EventStore())
    
    # Same input should produce same hash
    hash1 = audit_trail.hash_identifier("test@example.com")
    hash2 = audit_trail.hash_identifier("test@example.com")
    assert hash1 == hash2
    assert len(hash1) == 16
    
    # Different inputs should produce different hashes
    hash3 = audit_trail.hash_identifier("other@example.com")
    assert hash3 != hash1


@pytest.mark.asyncio
async def test_retention_policies():
    """Test different retention policies."""
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Check default policies
    assert audit_trail.retention_policies['gdpr_personal_data'] == timedelta(days=365)
    assert audit_trail.retention_policies['system_logs'] == timedelta(days=90)
    assert audit_trail.retention_policies['research_data'] == timedelta(days=1825)


@pytest.mark.asyncio
async def test_anonymize_data():
    """Test data anonymization function."""
    audit_trail = AuditTrail(EventStore())
    
    # Test data with PII
    data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "555-5678",
        "address": "123 Main St",
        "ssn": "123-45-6789",
        "non_pii": "some data",
        "age": 30
    }
    
    anonymized = audit_trail.anonymize_data(data)
    
    # Check PII fields are hashed
    for field in ['name', 'email', 'phone', 'address', 'ssn']:
        assert anonymized[field] != data[field]
        assert len(anonymized[field]) == 16
    
    # Non-PII fields unchanged
    assert anonymized['non_pii'] == "some data"
    assert anonymized['age'] == 30