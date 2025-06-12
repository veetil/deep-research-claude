"""
GDPR compliance features for memory system
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .advanced_memory_manager import AdvancedMemoryManager


class ConsentRequiredError(Exception):
    """Raised when consent is required but not provided."""
    pass


class GDPRCompliantMemory:
    """
    GDPR-compliant memory system with consent management and data rights.
    """
    
    def __init__(self, memory_manager: AdvancedMemoryManager):
        self.memory = memory_manager
        self.consent_registry: Dict[str, Dict[str, datetime]] = {}
        self.processing_purposes = [
            'research',
            'analytics',
            'improvement',
            'personalization',
            'legal_compliance'
        ]
        
    async def grant_consent(self, user_id: str, purpose: str) -> None:
        """
        Grant consent for data processing.
        
        Args:
            user_id: The user granting consent
            purpose: The purpose for which consent is granted
        """
        if purpose not in self.processing_purposes:
            raise ValueError(f"Invalid purpose: {purpose}")
        
        if user_id not in self.consent_registry:
            self.consent_registry[user_id] = {}
        
        self.consent_registry[user_id][purpose] = datetime.now(timezone.utc)
    
    async def revoke_consent(self, user_id: str, purpose: str) -> None:
        """
        Revoke consent for data processing.
        
        Args:
            user_id: The user revoking consent
            purpose: The purpose for which consent is revoked
        """
        if user_id in self.consent_registry:
            self.consent_registry[user_id].pop(purpose, None)
    
    async def has_consent(self, user_id: str, purpose: str) -> bool:
        """
        Check if user has given consent for purpose.
        
        Args:
            user_id: The user to check
            purpose: The purpose to check
            
        Returns:
            True if consent is granted
        """
        return (user_id in self.consent_registry and 
                purpose in self.consent_registry[user_id])
        
    async def store_with_consent(self, key: str, value: Any, 
                                user_id: str, purpose: str) -> None:
        """Store data only with explicit consent."""
        if not await self.has_consent(user_id, purpose):
            raise ConsentRequiredError(f"No consent for {purpose}")
        
        metadata = {
            'user_id': user_id,
            'purpose': purpose,
            'consent_timestamp': self.consent_registry[user_id][purpose].isoformat(),
            'contains_pii': True,
            'data_type': 'gdpr_personal_data'
        }
        
        await self.memory.remember(key, value, metadata, f"gdpr_system_{user_id}")
    
    async def right_to_erasure(self, user_id: str) -> Dict[str, int]:
        """Implement GDPR right to be forgotten."""
        deleted_count = 0
        anonymized_count = 0
        
        # Find all user data
        user_events = []
        for event in self.memory.event_store.events:
            if event.metadata.get('user_id') == user_id:
                user_events.append(event)
        
        # Process each event
        for event in user_events:
            if event.metadata.get('can_delete', True):
                # Delete completely
                if event in self.memory.event_store.events:
                    self.memory.event_store.events.remove(event)
                deleted_count += 1
            else:
                # Anonymize if deletion not possible
                await self.memory.audit_trail.anonymize_or_delete(event)
                anonymized_count += 1
        
        # Clear from all memory tiers
        await self._clear_from_memory_tiers(user_id)
        
        # Revoke all consents
        self.consent_registry.pop(user_id, None)
        
        return {
            'deleted': deleted_count,
            'anonymized': anonymized_count
        }
    
    async def right_to_access(self, user_id: str) -> Dict[str, Any]:
        """GDPR right to access personal data."""
        return await self.export_user_data(user_id)
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """GDPR right to data portability."""
        user_data = {
            'user_id': user_id,
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'consents': self._get_user_consents(user_id),
            'data': []
        }
        
        # Collect all user data
        for event in self.memory.event_store.events:
            if event.metadata.get('user_id') == user_id:
                user_data['data'].append({
                    'timestamp': event.timestamp.isoformat(),
                    'type': event.type.value,
                    'data': self._sanitize_for_export(event.data),
                    'purpose': event.metadata.get('purpose', 'unknown')
                })
        
        return user_data
    
    async def right_to_rectification(self, user_id: str, key: str, 
                                    corrected_value: Any) -> None:
        """GDPR right to correct inaccurate data."""
        # Check consent
        has_any_consent = False
        for purpose in ['legal_compliance', 'rectification']:
            if await self.has_consent(user_id, purpose):
                has_any_consent = True
                break
        
        if not has_any_consent:
            raise ConsentRequiredError("Consent required for rectification")
        
        # Store correction as new event
        metadata = {
            'user_id': user_id,
            'rectification': True,
            'original_key': key,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await self.memory.remember(
            f"{key}_rectified",
            corrected_value,
            metadata,
            f"gdpr_rectification_{user_id}"
        )
    
    async def data_minimization_check(self) -> Dict[str, Any]:
        """
        Check for data minimization compliance.
        
        Returns:
            Report on data that may violate minimization principle
        """
        report = {
            'total_events': len(self.memory.event_store.events),
            'redundant_data': [],
            'excessive_retention': [],
            'unnecessary_fields': []
        }
        
        # Check for redundant data
        seen_data = {}
        for event in self.memory.event_store.events:
            data_hash = hash(str(event.data))
            if data_hash in seen_data:
                report['redundant_data'].append({
                    'event_id': event.id,
                    'duplicate_of': seen_data[data_hash]
                })
            else:
                seen_data[data_hash] = event.id
        
        # Check retention periods
        current_time = datetime.now(timezone.utc)
        for event in self.memory.event_store.events:
            data_type = event.metadata.get('data_type', 'unknown')
            retention_period = self.memory.audit_trail.retention_policies.get(
                data_type, 
                self.memory.audit_trail.retention_policies['system_logs']
            )
            
            if current_time - event.timestamp > retention_period:
                report['excessive_retention'].append({
                    'event_id': event.id,
                    'age_days': (current_time - event.timestamp).days,
                    'retention_days': retention_period.days
                })
        
        return report
    
    def _get_user_consents(self, user_id: str) -> Dict[str, str]:
        """Get user's current consents."""
        if user_id not in self.consent_registry:
            return {}
        
        return {
            purpose: timestamp.isoformat()
            for purpose, timestamp in self.consent_registry[user_id].items()
        }
    
    def _sanitize_for_export(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data for export."""
        # Remove internal fields
        sanitized = data.copy()
        internal_fields = ['_id', '_internal', 'system_metadata']
        
        for field in internal_fields:
            sanitized.pop(field, None)
        
        return sanitized
    
    async def _clear_from_memory_tiers(self, user_id: str) -> None:
        """Clear user data from all memory tiers."""
        # Clear from short-term memory
        keys_to_remove = []
        for key, item in self.memory.short_term.memory.items():
            if item.metadata.get('user_id') == user_id:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory.short_term.memory[key]
            if key in self.memory.short_term._access_order:
                self.memory.short_term._access_order.remove(key)
        
        # Clear from long-term memory
        keys_to_remove = []
        for key, item in self.memory.long_term.storage.items():
            if item.metadata.get('user_id') == user_id:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory.long_term.storage[key]
            self.memory.long_term.embeddings.pop(key, None)
        
        # Clear from cache
        cache_keys_to_remove = []
        for key in self.memory.predictive_cache.cache:
            if f"user_{user_id}" in key:
                cache_keys_to_remove.append(key)
        
        for key in cache_keys_to_remove:
            del self.memory.predictive_cache.cache[key]