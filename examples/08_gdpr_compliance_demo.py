#!/usr/bin/env python3
"""
GDPR Compliance and Data Privacy Demo

This example demonstrates:
1. Consent management
2. Right to erasure (forget)
3. Data portability
4. Data minimization
5. Audit trail for compliance
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory.advanced_memory_manager import AdvancedMemoryManager
from src.memory.gdpr_compliance import GDPRCompliantMemory, ConsentRequiredError


async def demonstrate_consent_management():
    """Demonstrate GDPR consent management."""
    print("=== GDPR Consent Management Demo ===\n")
    
    # Initialize GDPR-compliant memory
    manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(manager)
    
    user_id = "user-12345"
    
    # 1. Attempt to store without consent
    print("1. Attempting to store data without consent...")
    try:
        await gdpr_memory.store_with_consent(
            key="profile_001",
            value={"name": "Alice Johnson", "interests": ["AI", "Privacy"]},
            user_id=user_id,
            purpose="research"
        )
    except ConsentRequiredError as e:
        print(f"   ❌ Blocked: {e}")
    
    # 2. Grant consent
    print("\n2. User grants consent for research...")
    await gdpr_memory.grant_consent(user_id, "research")
    print("   ✓ Consent granted for 'research' purpose")
    
    # 3. Store with consent
    print("\n3. Storing data with valid consent...")
    await gdpr_memory.store_with_consent(
        key="profile_001",
        value={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "interests": ["AI", "Privacy"],
            "research_participation": True
        },
        user_id=user_id,
        purpose="research"
    )
    print("   ✓ Personal data stored with consent tracking")
    
    # 4. Multiple purpose consent
    print("\n4. Managing multiple purposes...")
    purposes = ["analytics", "personalization"]
    
    for purpose in purposes:
        await gdpr_memory.grant_consent(user_id, purpose)
        print(f"   ✓ Consent granted for '{purpose}'")
    
    # Show active consents
    print("\n   Active consents:")
    consents = gdpr_memory._get_user_consents(user_id)
    for purpose, timestamp in consents.items():
        print(f"     - {purpose}: granted at {timestamp}")
    
    # 5. Revoke consent
    print("\n5. User revokes consent for analytics...")
    await gdpr_memory.revoke_consent(user_id, "analytics")
    print("   ✓ Consent revoked")
    
    # Verify revocation
    has_analytics = await gdpr_memory.has_consent(user_id, "analytics")
    has_research = await gdpr_memory.has_consent(user_id, "research")
    print(f"   Analytics consent: {has_analytics}")
    print(f"   Research consent: {has_research}")
    
    return gdpr_memory, user_id


async def demonstrate_data_rights():
    """Demonstrate GDPR data subject rights."""
    print("\n\n=== GDPR Data Subject Rights Demo ===\n")
    
    # Initialize
    manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(manager)
    
    # Create test users
    users = [
        {
            "id": "user-001",
            "data": {
                "name": "Bob Smith",
                "email": "bob@example.com",
                "age": 30,
                "country": "Germany"
            }
        },
        {
            "id": "user-002",
            "data": {
                "name": "Carol Davis",
                "email": "carol@example.com",
                "age": 25,
                "country": "France"
            }
        }
    ]
    
    # Store user data
    print("1. Storing user data with consent...")
    for user in users:
        await gdpr_memory.grant_consent(user["id"], "research")
        await gdpr_memory.store_with_consent(
            key=f"profile_{user['id']}",
            value=user["data"],
            user_id=user["id"],
            purpose="research"
        )
        
        # Add some activity data
        await gdpr_memory.store_with_consent(
            key=f"activity_{user['id']}_001",
            value={"last_login": "2024-01-12", "actions": ["view", "edit"]},
            user_id=user["id"],
            purpose="research"
        )
    
    print("   ✓ User data stored for 2 users")
    
    # 2. Right to Access (Data Export)
    print("\n2. Right to Access - Data Export:")
    
    export_data = await gdpr_memory.export_user_data("user-001")
    
    print(f"   User ID: {export_data['user_id']}")
    print(f"   Export timestamp: {export_data['export_timestamp']}")
    print(f"   Number of records: {len(export_data['data'])}")
    print("\n   Exported data samples:")
    
    for record in export_data['data'][:2]:
        print(f"     - Type: {record['type']}")
        print(f"       Purpose: {record['purpose']}")
        print(f"       Data: {json.dumps(record['data'], indent=8)}")
    
    # 3. Right to Rectification
    print("\n3. Right to Rectification - Correct Data:")
    
    # Grant compliance consent
    await gdpr_memory.grant_consent("user-001", "legal_compliance")
    
    # Correct the email
    await gdpr_memory.right_to_rectification(
        user_id="user-001",
        key="profile_user-001",
        corrected_value={
            "name": "Bob Smith",
            "email": "bob.smith@newexample.com",  # Corrected
            "age": 30,
            "country": "Germany"
        }
    )
    print("   ✓ Email address corrected")
    print("   ✓ Correction logged with timestamp")
    
    # 4. Right to Erasure
    print("\n4. Right to Erasure - Delete User Data:")
    
    # Show data before erasure
    stats_before = manager.get_stats()
    print(f"   Events before erasure: {stats_before['event_count']}")
    
    # Execute erasure
    result = await gdpr_memory.right_to_erasure("user-002")
    
    print(f"   ✓ Deleted: {result['deleted']} records")
    print(f"   ✓ Anonymized: {result['anonymized']} records")
    
    # Verify erasure
    stats_after = manager.get_stats()
    print(f"   Events after erasure: {stats_after['event_count']}")
    
    # Consent should be revoked
    has_consent = await gdpr_memory.has_consent("user-002", "research")
    print(f"   User consent after erasure: {has_consent}")
    
    # 5. Data Minimization Check
    print("\n5. Data Minimization Compliance Check:")
    
    report = await gdpr_memory.data_minimization_check()
    
    print(f"   Total events: {report['total_events']}")
    print(f"   Redundant data: {len(report['redundant_data'])} items")
    print(f"   Excessive retention: {len(report['excessive_retention'])} items")
    
    return gdpr_memory


async def demonstrate_privacy_by_design():
    """Demonstrate privacy by design principles."""
    print("\n\n=== Privacy by Design Demo ===\n")
    
    manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(manager)
    
    # 1. Data classification
    print("1. Automatic Data Classification:")
    
    data_examples = [
        {
            "type": "personal",
            "data": {"ssn": "123-45-6789", "name": "Test User"},
            "classification": "gdpr_personal_data"
        },
        {
            "type": "system",
            "data": {"log_level": "INFO", "timestamp": "2024-01-12"},
            "classification": "system_logs"
        },
        {
            "type": "research",
            "data": {"experiment_id": "QC-2024-001", "results": [1.23, 4.56]},
            "classification": "research_data"
        }
    ]
    
    for example in data_examples:
        retention_days = manager.audit_trail.retention_policies[example["classification"]].days
        print(f"\n   {example['type'].capitalize()} Data:")
        print(f"     Classification: {example['classification']}")
        print(f"     Retention: {retention_days} days")
        print(f"     Auto-deletion: {'Yes' if retention_days < 365 else 'After retention period'}")
    
    # 2. Anonymization demonstration
    print("\n2. Automatic Anonymization:")
    
    sensitive_data = {
        "user_id": "12345",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-0123",
        "address": "123 Main St, City",
        "purchase_amount": 99.99,
        "product_id": "PROD-001"
    }
    
    print("\n   Original data:")
    for key, value in list(sensitive_data.items())[:5]:
        print(f"     {key}: {value}")
    
    # Anonymize
    anonymized = manager.audit_trail.anonymize_data(sensitive_data)
    
    print("\n   After anonymization:")
    for key, value in list(anonymized.items())[:5]:
        if key in ['name', 'email', 'phone', 'address']:
            print(f"     {key}: {value} [ANONYMIZED]")
        else:
            print(f"     {key}: {value}")
    
    # 3. Consent-based access control
    print("\n3. Consent-Based Access Control:")
    
    user_id = "demo-user"
    
    # Define access scenarios
    scenarios = [
        ("Store for research", "research", True),
        ("Store for marketing", "marketing", False),  # No consent
        ("Store for legal compliance", "legal_compliance", True)
    ]
    
    for scenario, purpose, should_grant in scenarios:
        print(f"\n   Scenario: {scenario}")
        
        if should_grant and purpose in gdpr_memory.processing_purposes:
            await gdpr_memory.grant_consent(user_id, purpose)
            print(f"     ✓ Consent granted for '{purpose}'")
        
        try:
            await gdpr_memory.store_with_consent(
                key=f"test_{purpose}",
                value={"data": "test"},
                user_id=user_id,
                purpose=purpose
            )
            print("     ✓ Data stored successfully")
        except ConsentRequiredError:
            print("     ❌ Blocked: No consent for this purpose")
    
    # 4. Audit trail for compliance
    print("\n4. Comprehensive Audit Trail:")
    
    # Get access history
    history = await manager.get_memory_timeline("profile_user-001")
    
    print(f"   Total audit events: {len(history)}")
    if history:
        print("\n   Recent audit entries:")
        for event in history[-3:]:
            print(f"     - {event.timestamp.strftime('%H:%M:%S')}: "
                  f"{event.type.value} by {event.actor}")
    
    print("\n=== Privacy Protection Features ===")
    print("✓ Consent required before processing")
    print("✓ Automatic data classification")
    print("✓ Time-based retention policies")
    print("✓ Built-in anonymization")
    print("✓ Complete audit trail")
    print("✓ Granular access control")


async def main():
    """Run all demonstrations."""
    print("Deep Research Memory System - GDPR Compliance Demo")
    print("=" * 50)
    
    # Run consent management demo
    gdpr_memory, user_id = await demonstrate_consent_management()
    
    # Run data rights demo
    await demonstrate_data_rights()
    
    # Run privacy by design demo
    await demonstrate_privacy_by_design()
    
    print("\n✅ GDPR Compliance Demo completed successfully!")
    print("\n📋 Summary:")
    print("   - Consent management enforced")
    print("   - Data subject rights implemented")
    print("   - Privacy by design principles applied")
    print("   - Full compliance audit trail maintained")


if __name__ == "__main__":
    asyncio.run(main())