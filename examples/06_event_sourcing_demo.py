#!/usr/bin/env python3
"""
Event Sourcing and Time Travel Demo

This example demonstrates:
1. Event sourcing for complete audit trail
2. Time travel to any point in history
3. Event replay and state reconstruction
4. Audit logging with retention policies
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory.event_sourcing import EventStore, Event, EventType
from src.memory.audit_trail import AuditTrail


async def demonstrate_event_sourcing():
    """Demonstrate event sourcing capabilities."""
    print("=== Event Sourcing Demo ===\n")
    
    # Initialize event store and audit trail
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # 1. Create a series of events
    print("1. Creating research document with multiple edits...")
    
    # Initial creation
    await audit_trail.log_access(
        resource_id="doc-research-001",
        accessor="researcher-alice",
        action="create",
        result="success",
        metadata={
            "title": "Quantum Computing Research",
            "version": "1.0",
            "data_type": "research_data"
        }
    )
    
    # First edit
    await asyncio.sleep(0.1)
    edit1_time = datetime.now(timezone.utc)
    
    await event_store.append(Event(
        id="evt-edit-1",
        timestamp=edit1_time,
        type=EventType.MEMORY_UPDATE,
        aggregate_id="doc-research-001",
        data={
            "action": "edit",
            "value": {
                "content": "Initial findings on quantum entanglement...",
                "version": "1.1"
            }
        },
        actor="researcher-alice",
        metadata={"section": "introduction"}
    ))
    
    # Second edit by different user
    await asyncio.sleep(0.1)
    edit2_time = datetime.now(timezone.utc)
    
    await event_store.append(Event(
        id="evt-edit-2",
        timestamp=edit2_time,
        type=EventType.MEMORY_UPDATE,
        aggregate_id="doc-research-001",
        data={
            "action": "edit",
            "value": {
                "content": "Added experimental results...",
                "version": "1.2"
            }
        },
        actor="researcher-bob",
        metadata={"section": "results"}
    ))
    
    # 2. View complete history
    print("\n2. Complete audit history:")
    history = await audit_trail.get_access_history("doc-research-001")
    
    for i, event in enumerate(history):
        print(f"   [{i+1}] {event.timestamp.strftime('%H:%M:%S')} - "
              f"{event.actor} performed {event.data.get('action', 'unknown')}")
    
    # 3. Time travel demonstration
    print("\n3. Time travel to different versions:")
    
    # Current state
    current_state = await event_store.replay_events("doc-research-001")
    print(f"   Current version: {current_state.current_value.get('version', 'Unknown')}")
    print(f"   Total events: {len(current_state.events)}")
    
    # Travel to first edit
    past_state = await event_store.get_state_at("doc-research-001", edit1_time)
    print(f"\n   State at first edit: Version {past_state.current_value.get('version', 'Unknown')}")
    print(f"   Events at that time: {len(past_state.events)}")
    
    # 4. Event statistics by actor
    print("\n4. Activity by researcher:")
    alice_events = event_store.get_events_by_actor("researcher-alice")
    bob_events = event_store.get_events_by_actor("researcher-bob")
    
    print(f"   Alice: {len(alice_events)} actions")
    print(f"   Bob: {len(bob_events)} actions")
    
    # 5. Demonstrate event types
    print("\n5. Creating various event types...")
    
    # Cache events
    await event_store.append(Event(
        id="evt-cache-1",
        timestamp=datetime.now(timezone.utc),
        type=EventType.CACHE_MISS,
        aggregate_id="cache-quantum",
        data={"query": "quantum entanglement", "latency_ms": 150},
        actor="cache-system"
    ))
    
    await event_store.append(Event(
        id="evt-cache-2",
        timestamp=datetime.now(timezone.utc),
        type=EventType.CACHE_HIT,
        aggregate_id="cache-quantum",
        data={"query": "quantum entanglement", "latency_ms": 2},
        actor="cache-system"
    ))
    
    # Get cache performance
    cache_events = event_store.get_events_by_type(EventType.CACHE_HIT, limit=10)
    print(f"   Recent cache hits: {len(cache_events)}")
    
    # 6. Demonstrate PII handling
    print("\n6. GDPR-compliant data handling...")
    
    # Create event with PII
    pii_event = Event(
        id="evt-user-data",
        timestamp=datetime.now(timezone.utc) - timedelta(days=400),  # Old data
        type=EventType.MEMORY_WRITE,
        aggregate_id="user-profile-123",
        data={
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"theme": "dark"}
        },
        actor="user-123",
        metadata={
            "contains_pii": True,
            "data_type": "gdpr_personal_data",
            "purpose": "personalization"
        }
    )
    await event_store.append(pii_event)
    
    print("   Created user data with PII markers")
    print("   Retention policy: 365 days for personal data")
    print("   Data will be anonymized after retention period")
    
    # 7. Event replay for debugging
    print("\n7. Event replay for debugging:")
    
    # Subscribe to events
    events_received = []
    
    async def debug_handler(event):
        events_received.append(f"{event.type.value}: {event.aggregate_id}")
    
    event_store.subscribe("doc-research-001", debug_handler)
    
    # Replay by adding new event
    await event_store.append(Event(
        id="evt-debug",
        timestamp=datetime.now(timezone.utc),
        type=EventType.MEMORY_READ,
        aggregate_id="doc-research-001",
        data={"purpose": "debugging"},
        actor="system-debugger"
    ))
    
    print(f"   Replayed {len(events_received)} events to subscribers")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total events in store: {len(event_store.events)}")
    print(f"Unique aggregates: {len(event_store.event_streams)}")
    print(f"Event types used: {len(set(e.type for e in event_store.events))}")
    
    return event_store


async def demonstrate_audit_compliance():
    """Demonstrate audit trail compliance features."""
    print("\n\n=== Audit Trail Compliance Demo ===\n")
    
    event_store = EventStore()
    audit_trail = AuditTrail(event_store)
    
    # Create events with different retention requirements
    print("1. Creating events with different retention policies...")
    
    # System logs (90 day retention)
    for i in range(3):
        await audit_trail.log_access(
            resource_id=f"system-log-{i}",
            accessor="system",
            action="log",
            result="success",
            metadata={"data_type": "system_logs", "level": "info"}
        )
    
    # Research data (5 year retention)
    await audit_trail.log_access(
        resource_id="research-quantum-2024",
        accessor="lab-team",
        action="create",
        result="success",
        metadata={
            "data_type": "research_data",
            "project": "quantum-computing",
            "funding": "NSF-2024-QC"
        }
    )
    
    print("   Created system logs (90-day retention)")
    print("   Created research data (5-year retention)")
    
    # Show retention policies
    print("\n2. Active retention policies:")
    for data_type, retention in audit_trail.retention_policies.items():
        print(f"   {data_type}: {retention.days} days")
    
    # Demonstrate anonymization
    print("\n3. Data anonymization example:")
    
    # Original data
    test_data = {
        "name": "Jane Smith",
        "email": "jane@research.org",
        "phone": "555-0123",
        "research_id": "RES-2024-001",
        "findings": "Quantum entanglement observed"
    }
    
    print("   Original data:")
    for key, value in test_data.items():
        print(f"     {key}: {value}")
    
    # Anonymize
    anonymized = audit_trail.anonymize_data(test_data)
    
    print("\n   Anonymized data:")
    for key, value in anonymized.items():
        if key in ['name', 'email', 'phone']:
            print(f"     {key}: {value} (hashed)")
        else:
            print(f"     {key}: {value}")
    
    print("\n=== Compliance Features ===")
    print("✓ Complete audit trail of all operations")
    print("✓ Configurable retention policies by data type")
    print("✓ Automatic PII anonymization")
    print("✓ Time-based data lifecycle management")
    print("✓ Immutable event log for compliance")


async def main():
    """Run all demonstrations."""
    print("Deep Research Memory System - Event Sourcing Demo")
    print("=" * 50)
    
    # Run event sourcing demo
    await demonstrate_event_sourcing()
    
    # Run compliance demo
    await demonstrate_audit_compliance()
    
    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())