"""
Research Agent - Specialized in gathering information from various sources
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

from src.agents.base import BaseAgent, AgentCapability, AgentMessage, AgentStatus


class ResearchAgent(BaseAgent):
    """Agent specialized in research and information gathering"""
    
    def __init__(self, agent_type: str = "research", capabilities: List[AgentCapability] = None, **kwargs):
        if capabilities is None:
            capabilities = [
                AgentCapability.WEB_SEARCH,
                AgentCapability.ACADEMIC_SEARCH,
                AgentCapability.DATA_COLLECTION,
                AgentCapability.MULTILINGUAL
            ]
        super().__init__(agent_type=agent_type, capabilities=capabilities)
        
        # Research-specific attributes
        self.research_tasks: List[Dict[str, Any]] = []
        self.sources_consulted: List[Dict[str, Any]] = []
        self.findings: List[Dict[str, Any]] = []
        self.search_depth = 3  # How many levels deep to search
        self.max_sources = 20  # Maximum sources to consult
        
    async def on_initialize(self):
        """Initialize research agent"""
        # Load research configurations if any
        if self.context and 'research_config' in self.context.metadata:
            config = self.context.metadata['research_config']
            self.search_depth = config.get('search_depth', self.search_depth)
            self.max_sources = config.get('max_sources', self.max_sources)
    
    async def on_terminate(self):
        """Clean up research agent"""
        # Save any pending findings
        if self.findings:
            await self._save_findings()
    
    async def on_pause(self):
        """Pause research activities"""
        # Save current state
        await self._save_state()
    
    async def on_resume(self):
        """Resume research activities"""
        # Restore state and continue
        await self._restore_state()
    
    async def on_health_check(self) -> bool:
        """Check if research agent is healthy"""
        # Check if we're making progress
        if self.research_tasks:
            # Check if stuck on same task for too long
            current_task = self.research_tasks[0]
            if 'started_at' in current_task:
                elapsed = (datetime.now(timezone.utc) - current_task['started_at']).total_seconds()
                if elapsed > 300:  # 5 minutes
                    return False
        return True
    
    async def on_error(self, error: Exception, message: Optional[AgentMessage] = None):
        """Handle errors during research"""
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if message:
            error_context["related_message"] = message.id
            error_context["message_type"] = message.message_type
        
        # Log error to findings
        self.findings.append({
            "type": "error",
            "context": error_context
        })
        
        # Notify orchestrator of error
        await self.send_message(
            target_agent_id="orchestrator",
            message_type="agent_error",
            payload=error_context
        )
    
    async def get_custom_metrics(self) -> Dict[str, Any]:
        """Get research-specific metrics"""
        return {
            "total_tasks": len(self.research_tasks),
            "completed_tasks": len([t for t in self.research_tasks if t.get('completed', False)]),
            "sources_consulted": len(self.sources_consulted),
            "findings_count": len(self.findings),
            "average_task_time": self._calculate_average_task_time()
        }
    
    async def process_message(self, message: AgentMessage):
        """Process incoming research requests"""
        if message.message_type == "research_request":
            await self._handle_research_request(message)
        elif message.message_type == "refine_search":
            await self._handle_refine_search(message)
        elif message.message_type == "get_findings":
            await self._handle_get_findings(message)
        elif message.message_type == "prioritize_sources":
            await self._handle_prioritize_sources(message)
        else:
            # Unknown message type
            await self.on_error(
                ValueError(f"Unknown message type: {message.message_type}"),
                message
            )
    
    async def _handle_research_request(self, message: AgentMessage):
        """Handle a new research request"""
        query = message.payload.get('query', '')
        parameters = message.payload.get('parameters', {})
        
        # Create research task
        task = {
            "id": f"task_{len(self.research_tasks)}",
            "query": query,
            "parameters": parameters,
            "started_at": datetime.now(timezone.utc),
            "completed": False,
            "findings": []
        }
        
        self.research_tasks.append(task)
        
        # Start research
        await self._conduct_research(task)
        
        # Send initial findings
        if message.requires_response:
            await self.send_message(
                target_agent_id=message.source_agent_id,
                message_type="research_findings",
                payload={
                    "task_id": task["id"],
                    "preliminary_findings": task["findings"][:5],  # First 5 findings
                    "status": "in_progress"
                }
            )
    
    async def _conduct_research(self, task: Dict[str, Any]):
        """Conduct research for a task"""
        query = task['query']
        parameters = task['parameters']
        
        # Determine search strategies based on query
        strategies = self._determine_search_strategies(query, parameters)
        
        # Execute searches in parallel
        search_tasks = []
        for strategy in strategies:
            search_tasks.append(self._execute_search_strategy(strategy, query))
        
        # Gather results
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                await self.on_error(result)
            else:
                await self._process_search_results(task, result)
        
        # Mark task as completed
        task['completed'] = True
        task['completed_at'] = datetime.now(timezone.utc)
        
        # Synthesize findings
        synthesized = await self._synthesize_findings(task)
        
        # Broadcast completion
        await self.broadcast_message(
            message_type="research_completed",
            payload={
                "task_id": task["id"],
                "query": query,
                "findings_count": len(task["findings"]),
                "synthesis": synthesized
            }
        )
    
    def _determine_search_strategies(self, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine appropriate search strategies for the query"""
        strategies = []
        
        # Always include web search
        strategies.append({
            "type": "web_search",
            "engines": ["google", "bing", "duckduckgo"],
            "depth": parameters.get('depth', self.search_depth)
        })
        
        # Add academic search if query seems academic
        if any(term in query.lower() for term in ['research', 'study', 'paper', 'journal', 'academic']):
            strategies.append({
                "type": "academic_search",
                "databases": ["google_scholar", "arxiv", "pubmed"],
                "filters": parameters.get('academic_filters', {})
            })
        
        # Add news search if query is time-sensitive
        if any(term in query.lower() for term in ['latest', 'recent', 'news', 'current', 'today']):
            strategies.append({
                "type": "news_search",
                "sources": ["google_news", "reuters", "ap"],
                "time_range": parameters.get('time_range', '7d')
            })
        
        # Add data search if query involves statistics
        if any(term in query.lower() for term in ['statistics', 'data', 'numbers', 'percentage', 'growth']):
            strategies.append({
                "type": "data_search",
                "sources": ["statista", "world_bank", "government_data"],
                "data_type": parameters.get('data_type', 'all')
            })
        
        return strategies
    
    async def _execute_search_strategy(self, strategy: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Execute a specific search strategy"""
        # This is a placeholder - in real implementation, this would call actual search APIs
        
        strategy_type = strategy['type']
        
        if strategy_type == "web_search":
            return await self._web_search(query, strategy)
        elif strategy_type == "academic_search":
            return await self._academic_search(query, strategy)
        elif strategy_type == "news_search":
            return await self._news_search(query, strategy)
        elif strategy_type == "data_search":
            return await self._data_search(query, strategy)
        else:
            return {"error": f"Unknown strategy type: {strategy_type}"}
    
    async def _web_search(self, query: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search"""
        # Placeholder implementation
        results = {
            "strategy": "web_search",
            "query": query,
            "sources": []
        }
        
        # Simulate search results
        for i in range(min(5, self.max_sources)):
            results["sources"].append({
                "title": f"Web Result {i+1} for: {query}",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a snippet about {query}...",
                "relevance_score": 0.9 - (i * 0.1)
            })
        
        return results
    
    async def _academic_search(self, query: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Perform academic search"""
        # Placeholder implementation
        results = {
            "strategy": "academic_search",
            "query": query,
            "sources": []
        }
        
        # Simulate academic results
        for i in range(min(3, self.max_sources)):
            results["sources"].append({
                "title": f"Academic Paper: {query} Study {i+1}",
                "authors": ["Author A", "Author B"],
                "journal": "Journal of Advanced Research",
                "year": 2023 - i,
                "doi": f"10.1234/jar.2023.{i+1}",
                "abstract": f"This paper examines {query} in detail...",
                "citations": 50 - (i * 10)
            })
        
        return results
    
    async def _news_search(self, query: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Perform news search"""
        # Placeholder implementation
        results = {
            "strategy": "news_search",
            "query": query,
            "sources": []
        }
        
        # Simulate news results
        for i in range(min(4, self.max_sources)):
            results["sources"].append({
                "title": f"Breaking: {query} News Update",
                "source": ["Reuters", "AP", "BBC", "CNN"][i],
                "published": datetime.now(timezone.utc).isoformat(),
                "url": f"https://news.example.com/article{i+1}",
                "summary": f"Latest developments regarding {query}..."
            })
        
        return results
    
    async def _data_search(self, query: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Perform data/statistics search"""
        # Placeholder implementation
        results = {
            "strategy": "data_search",
            "query": query,
            "sources": []
        }
        
        # Simulate data results
        results["sources"].append({
            "title": f"Statistical Data: {query}",
            "source": "World Data Bank",
            "data_points": {
                "2020": 100,
                "2021": 110,
                "2022": 125,
                "2023": 140
            },
            "unit": "millions",
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
        
        return results
    
    async def _process_search_results(self, task: Dict[str, Any], results: Dict[str, Any]):
        """Process and store search results"""
        strategy = results.get('strategy', 'unknown')
        sources = results.get('sources', [])
        
        for source in sources:
            # Create finding
            finding = {
                "id": f"finding_{len(self.findings)}",
                "task_id": task["id"],
                "strategy": strategy,
                "source": source,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "relevance": source.get('relevance_score', 0.5)
            }
            
            # Extract key information based on source type
            if strategy == "academic_search":
                finding["key_points"] = await self._extract_academic_insights(source)
            elif strategy == "data_search":
                finding["key_points"] = await self._extract_data_insights(source)
            else:
                finding["key_points"] = await self._extract_general_insights(source)
            
            # Add to findings
            self.findings.append(finding)
            task["findings"].append(finding["id"])
            
            # Track source
            self.sources_consulted.append({
                "url": source.get('url', ''),
                "title": source.get('title', ''),
                "consulted_at": datetime.now(timezone.utc).isoformat()
            })
    
    async def _synthesize_findings(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize findings into coherent insights"""
        task_findings = [
            f for f in self.findings 
            if f.get('task_id') == task['id']
        ]
        
        synthesis = {
            "query": task['query'],
            "total_sources": len(task_findings),
            "key_insights": [],
            "consensus_points": [],
            "conflicting_points": [],
            "data_summary": {},
            "confidence_level": 0.0
        }
        
        # Extract key insights
        for finding in task_findings:
            synthesis["key_insights"].extend(finding.get('key_points', []))
        
        # Calculate confidence based on source agreement
        if task_findings:
            avg_relevance = sum(f.get('relevance', 0) for f in task_findings) / len(task_findings)
            synthesis["confidence_level"] = avg_relevance
        
        return synthesis
    
    async def _extract_academic_insights(self, source: Dict[str, Any]) -> List[str]:
        """Extract insights from academic sources"""
        insights = []
        
        if 'abstract' in source:
            # In real implementation, would use NLP to extract key points
            insights.append(f"Study findings: {source['abstract'][:100]}...")
        
        if 'citations' in source and source['citations'] > 30:
            insights.append(f"Highly cited work with {source['citations']} citations")
        
        return insights
    
    async def _extract_data_insights(self, source: Dict[str, Any]) -> List[str]:
        """Extract insights from data sources"""
        insights = []
        
        if 'data_points' in source:
            # Calculate trends
            values = list(source['data_points'].values())
            if len(values) > 1:
                trend = "increasing" if values[-1] > values[0] else "decreasing"
                insights.append(f"Data shows {trend} trend")
        
        return insights
    
    async def _extract_general_insights(self, source: Dict[str, Any]) -> List[str]:
        """Extract insights from general sources"""
        insights = []
        
        if 'snippet' in source:
            insights.append(source['snippet'])
        elif 'summary' in source:
            insights.append(source['summary'])
        
        return insights
    
    def _calculate_average_task_time(self) -> float:
        """Calculate average time to complete tasks"""
        completed_tasks = [
            t for t in self.research_tasks 
            if t.get('completed', False) and 'completed_at' in t
        ]
        
        if not completed_tasks:
            return 0.0
        
        total_time = 0.0
        for task in completed_tasks:
            duration = (task['completed_at'] - task['started_at']).total_seconds()
            total_time += duration
        
        return total_time / len(completed_tasks)
    
    async def _save_state(self):
        """Save current state for persistence"""
        state = {
            "research_tasks": self.research_tasks,
            "sources_consulted": self.sources_consulted,
            "findings": self.findings
        }
        
        # In real implementation, would save to persistent storage
        # For now, just store in context
        if self.context:
            self.context.shared_memory['research_state'] = state
    
    async def _restore_state(self):
        """Restore saved state"""
        if self.context and 'research_state' in self.context.shared_memory:
            state = self.context.shared_memory['research_state']
            self.research_tasks = state.get('research_tasks', [])
            self.sources_consulted = state.get('sources_consulted', [])
            self.findings = state.get('findings', [])
    
    async def _save_findings(self):
        """Save findings to persistent storage"""
        # In real implementation, would save to database
        # For now, broadcast findings
        await self.broadcast_message(
            message_type="findings_available",
            payload={
                "agent_id": self.id,
                "findings_count": len(self.findings),
                "sources_count": len(self.sources_consulted)
            }
        )
    
    async def _handle_refine_search(self, message: AgentMessage):
        """Handle request to refine search parameters"""
        task_id = message.payload.get('task_id')
        refinements = message.payload.get('refinements', {})
        
        # Find task
        task = next((t for t in self.research_tasks if t['id'] == task_id), None)
        if not task:
            await self.send_message(
                target_agent_id=message.source_agent_id,
                message_type="error",
                payload={"error": f"Task {task_id} not found"}
            )
            return
        
        # Apply refinements
        task['parameters'].update(refinements)
        
        # Re-run research with refined parameters
        await self._conduct_research(task)
    
    async def _handle_get_findings(self, message: AgentMessage):
        """Handle request to get current findings"""
        task_id = message.payload.get('task_id')
        
        if task_id:
            # Get findings for specific task
            task_findings = [
                f for f in self.findings 
                if f.get('task_id') == task_id
            ]
        else:
            # Get all findings
            task_findings = self.findings
        
        await self.send_message(
            target_agent_id=message.source_agent_id,
            message_type="findings_response",
            payload={
                "findings": task_findings,
                "total_count": len(task_findings)
            }
        )
    
    async def _handle_prioritize_sources(self, message: AgentMessage):
        """Handle request to prioritize certain sources"""
        priorities = message.payload.get('priorities', {})
        
        # Update source priorities
        # In real implementation, would affect search strategy selection
        if self.context:
            self.context.metadata['source_priorities'] = priorities