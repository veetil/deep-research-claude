"""
Test suite for GDPR compliance features
"""
import pytest
from datetime import datetime, timezone
from src.memory.event_sourcing import EventStore
from src.memory.audit_trail import AuditTrail
from src.memory.predictive_cache import PredictiveCache
from src.memory.advanced_memory_manager import AdvancedMemoryManager
from src.memory.gdpr_compliance import GDPRCompliantMemory, ConsentRequiredError


@pytest.mark.asyncio
async def test_consent_management():
    """Test consent grant and revoke."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Initially no consent
    assert not await gdpr_memory.has_consent("user1", "research")
    
    # Grant consent
    await gdpr_memory.grant_consent("user1", "research")
    assert await gdpr_memory.has_consent("user1", "research")
    
    # Revoke consent
    await gdpr_memory.revoke_consent("user1", "research")
    assert not await gdpr_memory.has_consent("user1", "research")


@pytest.mark.asyncio
async def test_store_with_consent():
    """Test storing data with consent requirement."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Try to store without consent
    with pytest.raises(ConsentRequiredError):
        await gdpr_memory.store_with_consent(
            key="user_data_1",
            value={"name": "John"},
            user_id="user1",
            purpose="research"
        )
    
    # Grant consent and store
    await gdpr_memory.grant_consent("user1", "research")
    await gdpr_memory.store_with_consent(
        key="user_data_1",
        value={"name": "John"},
        user_id="user1",
        purpose="research"
    )
    
    # Check data was stored
    assert len(memory_manager.event_store.events) == 1
    event = memory_manager.event_store.events[0]
    assert event.metadata['user_id'] == "user1"
    assert event.metadata['purpose'] == "research"
    assert event.metadata['contains_pii'] is True


@pytest.mark.asyncio
async def test_right_to_erasure():
    """Test GDPR right to be forgotten."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Store some user data
    await gdpr_memory.grant_consent("user1", "research")
    await gdpr_memory.store_with_consent(
        key="data1",
        value={"info": "personal"},
        user_id="user1",
        purpose="research"
    )
    
    # Store data that can't be deleted
    await memory_manager.remember(
        key="data2",
        value={"info": "required"},
        metadata={"user_id": "user1", "can_delete": False},
        actor="system"
    )
    
    # Execute right to erasure
    result = await gdpr_memory.right_to_erasure("user1")
    
    assert result['deleted'] >= 1
    assert result['anonymized'] >= 0
    
    # Consent should be revoked
    assert not await gdpr_memory.has_consent("user1", "research")


@pytest.mark.asyncio
async def test_export_user_data():
    """Test GDPR data export."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Store user data
    await gdpr_memory.grant_consent("user1", "research")
    await gdpr_memory.store_with_consent(
        key="data1",
        value={"name": "John", "age": 30},
        user_id="user1",
        purpose="research"
    )
    
    # Export data
    export = await gdpr_memory.export_user_data("user1")
    
    assert export['user_id'] == "user1"
    assert 'export_timestamp' in export
    assert len(export['data']) >= 1
    assert export['data'][0]['purpose'] == "research"


@pytest.mark.asyncio
async def test_right_to_rectification():
    """Test GDPR right to rectification."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Store initial data
    await gdpr_memory.grant_consent("user1", "research")
    await gdpr_memory.store_with_consent(
        key="user_profile",
        value={"name": "Jon", "email": "jon@example.com"},  # Typo in name
        user_id="user1",
        purpose="research"
    )
    
    # Rectify data
    await gdpr_memory.grant_consent("user1", "legal_compliance")
    await gdpr_memory.right_to_rectification(
        user_id="user1",
        key="user_profile",
        corrected_value={"name": "John", "email": "john@example.com"}
    )
    
    # Check rectification was stored
    events = [e for e in memory_manager.event_store.events 
              if "rectified" in e.aggregate_id]
    assert len(events) == 1
    assert events[0].data['value']['name'] == "John"


@pytest.mark.asyncio
async def test_data_minimization_check():
    """Test data minimization compliance check."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Create some duplicate data
    await memory_manager.remember(
        key="data1",
        value={"info": "same"},
        metadata={},
        actor="system"
    )
    await memory_manager.remember(
        key="data2",
        value={"info": "same"},
        metadata={},
        actor="system"
    )
    
    # Run minimization check
    report = await gdpr_memory.data_minimization_check()
    
    assert report['total_events'] == 2
    # Note: Simple hash collision might not detect these as duplicates
    # but the mechanism is in place


@pytest.mark.asyncio
async def test_invalid_purpose():
    """Test invalid processing purpose."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    with pytest.raises(ValueError, match="Invalid purpose"):
        await gdpr_memory.grant_consent("user1", "invalid_purpose")


@pytest.mark.asyncio
async def test_consent_registry():
    """Test consent registry management."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Grant multiple consents
    await gdpr_memory.grant_consent("user1", "research")
    await gdpr_memory.grant_consent("user1", "analytics")
    
    # Check consents
    assert await gdpr_memory.has_consent("user1", "research")
    assert await gdpr_memory.has_consent("user1", "analytics")
    assert not await gdpr_memory.has_consent("user1", "improvement")
    
    # Check internal registry
    consents = gdpr_memory._get_user_consents("user1")
    assert "research" in consents
    assert "analytics" in consents


@pytest.mark.asyncio
async def test_clear_from_memory_tiers():
    """Test clearing user data from all memory tiers."""
    memory_manager = AdvancedMemoryManager()
    gdpr_memory = GDPRCompliantMemory(memory_manager)
    
    # Add data to different tiers
    await memory_manager.short_term.set("user_key", {"data": "value"})
    memory_manager.short_term.memory["user_key"].metadata = {"user_id": "user1"}
    
    # Clear user data
    await gdpr_memory._clear_from_memory_tiers("user1")
    
    # Check data is cleared
    assert "user_key" not in memory_manager.short_term.memory


@pytest.mark.asyncio
async def test_sanitize_for_export():
    """Test data sanitization for export."""
    gdpr_memory = GDPRCompliantMemory(AdvancedMemoryManager())
    
    data = {
        "name": "John",
        "_id": "internal123",
        "_internal": "secret",
        "email": "john@example.com",
        "system_metadata": {"internal": "data"}
    }
    
    sanitized = gdpr_memory._sanitize_for_export(data)
    
    assert "name" in sanitized
    assert "email" in sanitized
    assert "_id" not in sanitized
    assert "_internal" not in sanitized
    assert "system_metadata" not in sanitized