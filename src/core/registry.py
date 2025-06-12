"""
Agent Registry for managing agent lifecycle and discovery
"""
from typing import Dict, List, Optional, Set, Type
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

from src.agents.base import BaseAgent, AgentCapability, AgentStatus


@dataclass
class AgentRegistration:
    """Registration information for an agent"""
    agent: BaseAgent
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, any] = field(default_factory=dict)


class AgentRegistry:
    """Registry for managing agents in the system"""
    
    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._lock = threading.RLock()
        self._capability_index: Dict[AgentCapability, Set[str]] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._parent_index: Dict[str, Set[str]] = {}  # parent_id -> set of child_ids
        self._agent_factories: Dict[str, Type[BaseAgent]] = {}
        
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]):
        """Register an agent type with its factory class"""
        with self._lock:
            self._agent_factories[agent_type] = agent_class
    
    def create_agent(self, agent_type: str, capabilities: List[AgentCapability], **kwargs) -> BaseAgent:
        """Create a new agent instance"""
        if agent_type not in self._agent_factories:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self._agent_factories[agent_type]
        agent = agent_class(agent_type=agent_type, capabilities=capabilities, **kwargs)
        return agent
    
    def register(self, agent: BaseAgent, metadata: Optional[Dict[str, any]] = None):
        """Register an agent in the registry"""
        with self._lock:
            if agent.id in self._agents:
                raise ValueError(f"Agent {agent.id} already registered")
            
            # Create registration
            registration = AgentRegistration(
                agent=agent,
                metadata=metadata or {}
            )
            self._agents[agent.id] = registration
            
            # Update indices
            self._update_indices_on_register(agent)
    
    def unregister(self, agent_id: str):
        """Unregister an agent from the registry"""
        with self._lock:
            if agent_id not in self._agents:
                return
            
            registration = self._agents[agent_id]
            agent = registration.agent
            
            # Update indices
            self._update_indices_on_unregister(agent)
            
            # Remove registration
            del self._agents[agent_id]
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        with self._lock:
            registration = self._agents.get(agent_id)
            if registration:
                registration.last_seen = datetime.now(timezone.utc)
                return registration.agent
            return None
    
    def exists(self, agent_id: str) -> bool:
        """Check if an agent exists"""
        with self._lock:
            return agent_id in self._agents
    
    def list_all(self) -> List[BaseAgent]:
        """List all registered agents"""
        with self._lock:
            return [reg.agent for reg in self._agents.values()]
    
    def list_by_type(self, agent_type: str) -> List[BaseAgent]:
        """List agents by type"""
        with self._lock:
            agent_ids = self._type_index.get(agent_type, set())
            return [self._agents[aid].agent for aid in agent_ids if aid in self._agents]
    
    def list_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """List agents by capability"""
        with self._lock:
            agent_ids = self._capability_index.get(capability, set())
            return [self._agents[aid].agent for aid in agent_ids if aid in self._agents]
    
    def list_by_status(self, status: AgentStatus) -> List[BaseAgent]:
        """List agents by status"""
        with self._lock:
            return [
                reg.agent for reg in self._agents.values()
                if reg.agent.status == status
            ]
    
    def find_agents(self, agent_type: Optional[str] = None,
                   capabilities: Optional[List[AgentCapability]] = None,
                   status: Optional[AgentStatus] = None) -> List[BaseAgent]:
        """Find agents matching criteria"""
        with self._lock:
            agents = list(self._agents.values())
            
            # Filter by type
            if agent_type:
                agents = [
                    reg for reg in agents
                    if reg.agent.agent_type == agent_type
                ]
            
            # Filter by capabilities
            if capabilities:
                agents = [
                    reg for reg in agents
                    if all(cap in reg.agent.capabilities for cap in capabilities)
                ]
            
            # Filter by status
            if status:
                agents = [
                    reg for reg in agents
                    if reg.agent.status == status
                ]
            
            return [reg.agent for reg in agents]
    
    def get_children(self, parent_id: str) -> List[BaseAgent]:
        """Get all children of a parent agent"""
        with self._lock:
            child_ids = self._parent_index.get(parent_id, set())
            return [self._agents[cid].agent for cid in child_ids if cid in self._agents]
    
    def get_parent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get parent of an agent"""
        with self._lock:
            registration = self._agents.get(agent_id)
            if registration and registration.agent.parent_id:
                return self.get(registration.agent.parent_id)
            return None
    
    def get_ancestry(self, agent_id: str) -> List[BaseAgent]:
        """Get all ancestors of an agent (parent, grandparent, etc.)"""
        ancestors = []
        current_id = agent_id
        
        with self._lock:
            while current_id:
                parent = self.get_parent(current_id)
                if parent:
                    ancestors.append(parent)
                    current_id = parent.id
                else:
                    break
        
        return ancestors
    
    def get_descendants(self, agent_id: str) -> List[BaseAgent]:
        """Get all descendants of an agent (children, grandchildren, etc.)"""
        descendants = []
        to_process = [agent_id]
        
        with self._lock:
            while to_process:
                current_id = to_process.pop(0)
                children = self.get_children(current_id)
                descendants.extend(children)
                to_process.extend([child.id for child in children])
        
        return descendants
    
    def update_metadata(self, agent_id: str, metadata: Dict[str, any]):
        """Update agent metadata"""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].metadata.update(metadata)
    
    def get_metadata(self, agent_id: str) -> Optional[Dict[str, any]]:
        """Get agent metadata"""
        with self._lock:
            registration = self._agents.get(agent_id)
            return registration.metadata if registration else None
    
    def get_statistics(self) -> Dict[str, any]:
        """Get registry statistics"""
        with self._lock:
            status_counts = {}
            type_counts = {}
            capability_counts = {}
            
            for registration in self._agents.values():
                agent = registration.agent
                
                # Count by status
                status = agent.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count by type
                agent_type = agent.agent_type
                type_counts[agent_type] = type_counts.get(agent_type, 0) + 1
                
                # Count by capability
                for capability in agent.capabilities:
                    cap_name = capability.value
                    capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1
            
            return {
                "total_agents": len(self._agents),
                "by_status": status_counts,
                "by_type": type_counts,
                "by_capability": capability_counts,
                "total_parent_child_relationships": sum(
                    len(children) for children in self._parent_index.values()
                )
            }
    
    def _update_indices_on_register(self, agent: BaseAgent):
        """Update internal indices when registering an agent"""
        # Type index
        if agent.agent_type not in self._type_index:
            self._type_index[agent.agent_type] = set()
        self._type_index[agent.agent_type].add(agent.id)
        
        # Capability index
        for capability in agent.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = set()
            self._capability_index[capability].add(agent.id)
        
        # Parent index
        if agent.parent_id:
            if agent.parent_id not in self._parent_index:
                self._parent_index[agent.parent_id] = set()
            self._parent_index[agent.parent_id].add(agent.id)
    
    def _update_indices_on_unregister(self, agent: BaseAgent):
        """Update internal indices when unregistering an agent"""
        # Type index
        if agent.agent_type in self._type_index:
            self._type_index[agent.agent_type].discard(agent.id)
            if not self._type_index[agent.agent_type]:
                del self._type_index[agent.agent_type]
        
        # Capability index
        for capability in agent.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability].discard(agent.id)
                if not self._capability_index[capability]:
                    del self._capability_index[capability]
        
        # Parent index
        if agent.parent_id and agent.parent_id in self._parent_index:
            self._parent_index[agent.parent_id].discard(agent.id)
            if not self._parent_index[agent.parent_id]:
                del self._parent_index[agent.parent_id]


class AgentDiscoveryService:
    """Service for discovering agents based on various criteria"""
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
    
    def find_best_agent_for_task(self, required_capabilities: List[AgentCapability],
                                preferred_type: Optional[str] = None) -> Optional[BaseAgent]:
        """Find the best available agent for a task"""
        # Find agents with required capabilities
        candidates = self.registry.find_agents(
            agent_type=preferred_type,
            capabilities=required_capabilities,
            status=AgentStatus.READY
        )
        
        if not candidates:
            # Try without type preference
            candidates = self.registry.find_agents(
                capabilities=required_capabilities,
                status=AgentStatus.READY
            )
        
        if not candidates:
            return None
        
        # Score candidates
        scored_candidates = []
        for agent in candidates:
            score = self._score_agent(agent, required_capabilities)
            scored_candidates.append((score, agent))
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        return scored_candidates[0][1] if scored_candidates else None
    
    def _score_agent(self, agent: BaseAgent, required_capabilities: List[AgentCapability]) -> float:
        """Score an agent based on various factors"""
        score = 0.0
        
        # Base score for having required capabilities
        score += 10.0
        
        # Bonus for additional capabilities
        extra_capabilities = set(agent.capabilities) - set(required_capabilities)
        score += len(extra_capabilities) * 0.5
        
        # Penalty for busy agents (if we had load metrics)
        # score -= agent.current_load * 2.0
        
        # Bonus for specialized agents
        if len(agent.capabilities) <= len(required_capabilities) + 2:
            score += 2.0  # Specialist bonus
        
        return score