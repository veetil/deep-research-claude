"""
Legal research and analysis specialized agents
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from src.agents.enhanced_base import EnhancedBaseAgent, Task, AgentResult


class LegalResearchAgent(EnhancedBaseAgent):
    """Specialized agent for legal research and analysis"""
    
    QUALITY_THRESHOLD = 0.92
    REQUIRES_APPROVAL = True
    MAX_TOKENS = 8000
    SPECIALIZATION = "legal"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.legal_sources = [
            "westlaw", "lexisnexis", "justia.com", "law.cornell.edu",
            "supremecourt.gov", "uscourts.gov", "findlaw.com",
            "scholar.google.com", "ssrn.com"
        ]
        self.authority_hierarchy = {
            'constitution': 1.0,
            'statute': 0.9,
            'regulation': 0.85,
            'supreme_court': 0.95,
            'circuit_court': 0.8,
            'district_court': 0.7,
            'state_supreme': 0.75,
            'state_appellate': 0.65,
            'administrative': 0.6,
            'secondary': 0.4
        }
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        jurisdiction = task.metadata.get('jurisdiction', 'United States Federal')
        area_of_law = task.metadata.get('area_of_law', 'General')
        
        return f"""
        Role: Legal Research Specialist
        
        Task: {task.query}
        
        IMPORTANT DISCLAIMER: This is legal research only, NOT legal advice.
        Consult a licensed attorney for legal advice.
        
        Requirements:
        1. Cite primary sources (statutes, regulations, case law)
        2. Include jurisdictional considerations
        3. Note any recent legal developments or changes
        4. Provide balanced analysis of different interpretations
        5. Include relevant precedents with proper citations
        6. Identify any circuit splits or conflicting authorities
        7. Use proper legal citation format (Bluebook)
        
        Jurisdiction: {jurisdiction}
        Area of Law: {area_of_law}
        
        Legal Context:
        {context.get('legal_context', 'No previous legal context')}
        
        Quality Standards:
        - Authority: Primary > Secondary > Tertiary sources
        - Recency: Note if law has changed recently
        - Jurisdiction: Clearly identify applicable jurisdiction
        - Precedent: Include binding and persuasive precedents
        - Citation: Proper Bluebook format
        
        Required Sections:
        1. Legal Issue Summary
        2. Applicable Law
           - Statutes and Regulations
           - Key Cases (with holdings)
           - Circuit/Jurisdiction variations
        3. Legal Analysis
           - Elements/Requirements
           - Arguments for each position
           - Precedential value
        4. Recent Developments
        5. Practical Implications
        6. Procedural Considerations
        7. References (Bluebook format)
        
        DISCLAIMER: Legal information only. Not legal advice.
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate legal research quality"""
        scores = []
        
        # Check primary source usage (40% weight)
        if result.sources:
            primary_sources = sum(1 for s in result.sources
                                if any(auth in s.get('metadata', {}).get('authority_type', '').lower()
                                     for auth in ['statute', 'regulation', 'case', 'constitution']))
            primary_ratio = primary_sources / len(result.sources)
            scores.append(('primary_sources', primary_ratio, 0.4))
        else:
            scores.append(('primary_sources', 0.0, 0.4))
        
        # Check authority levels (25% weight)
        if result.sources:
            auth_scores = []
            for source in result.sources:
                auth_type = source.get('metadata', {}).get('authority_type', 'secondary')
                auth_scores.append(self.authority_hierarchy.get(auth_type, 0.4))
            authority_score = sum(auth_scores) / len(auth_scores)
            scores.append(('authority', authority_score, 0.25))
        else:
            scores.append(('authority', 0.0, 0.25))
        
        # Check citation format (15% weight)
        content_lower = result.content.lower()
        citation_indicators = ['v.', 'f.3d', 'f.2d', 'u.s.', 'f. supp']
        citation_count = sum(1 for indicator in citation_indicators if indicator in content_lower)
        citation_score = min(citation_count / 3, 1.0)  # Expect at least 3 proper citations
        scores.append(('citations', citation_score, 0.15))
        
        # Check required sections (15% weight)
        required_sections = ['applicable law', 'analysis', 'disclaimer', 'references']
        section_count = sum(1 for section in required_sections if section in content_lower)
        section_score = section_count / len(required_sections)
        scores.append(('sections', section_score, 0.15))
        
        # Success factor (5% weight)
        scores.append(('success', 1.0 if result.success else 0.0, 0.05))
        
        # Calculate weighted score
        total_score = sum(score * weight for _, score, weight in scores)
        
        # Store breakdown
        result.metadata['quality_breakdown'] = {
            name: score for name, score, _ in scores
        }
        
        return min(total_score, 1.0)
    
    async def execute_with_monitoring(self, prompt: str) -> AgentResult:
        """Execute with legal-specific monitoring"""
        # Mock implementation
        return AgentResult(
            success=True,
            content="""
            # Legal Research: Employment Discrimination Claims
            
            ## Legal Issue Summary
            Analysis of Title VII employment discrimination claims...
            
            ## Applicable Law
            
            ### Federal Statutes
            - Title VII of the Civil Rights Act, 42 U.S.C. § 2000e et seq.
            - Americans with Disabilities Act, 42 U.S.C. § 12101 et seq.
            
            ### Key Cases
            - McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)
              Holding: Established burden-shifting framework...
            
            ## Legal Analysis
            To establish a prima facie case of discrimination...
            
            ## DISCLAIMER
            This is legal information only and not legal advice.
            
            ## References
            1. 42 U.S.C. § 2000e-2(a)(1)
            2. McDonnell Douglas Corp. v. Green, 411 U.S. 792, 802 (1973)
            """,
            sources=[
                {
                    "name": "McDonnell Douglas Corp. v. Green",
                    "url": "https://supreme.justia.com/cases/federal/us/411/792/",
                    "metadata": {
                        "authority_type": "supreme_court",
                        "year": 1973,
                        "citation": "411 U.S. 792"
                    }
                }
            ],
            tokens_used=600
        )


class ContractAnalysisAgent(EnhancedBaseAgent):
    """Agent specialized in contract analysis and review"""
    
    QUALITY_THRESHOLD = 0.90
    REQUIRES_APPROVAL = True
    SPECIALIZATION = "contracts"
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        contract_type = task.metadata.get('contract_type', 'General')
        jurisdiction = task.metadata.get('jurisdiction', 'United States')
        
        return f"""
        Role: Contract Analysis Specialist
        
        Task: {task.query}
        
        Contract Type: {contract_type}
        Governing Law: {jurisdiction}
        
        Analysis Requirements:
        1. Identify key terms and definitions
        2. Analyze rights and obligations of each party
        3. Review termination and breach provisions
        4. Assess risk allocation and liability
        5. Check for unusual or problematic clauses
        6. Verify compliance with applicable law
        7. Suggest potential negotiation points
        
        Focus Areas:
        - Payment terms and conditions
        - Deliverables and milestones
        - Intellectual property rights
        - Confidentiality provisions
        - Warranties and representations
        - Indemnification clauses
        - Dispute resolution mechanisms
        - Force majeure provisions
        
        Output Format:
        1. Executive Summary
        2. Key Terms Analysis
        3. Rights and Obligations Matrix
        4. Risk Assessment
        5. Compliance Review
        6. Negotiation Recommendations
        7. Red Flags and Concerns
        
        DISCLAIMER: Contract review only. Consult an attorney for legal advice.
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate contract analysis quality"""
        quality = 0.0
        
        # Check comprehensive analysis (40%)
        analysis_terms = ['obligations', 'rights', 'termination', 'liability', 'risk']
        found_terms = sum(1 for term in analysis_terms if term in result.content.lower())
        quality += 0.4 * (found_terms / len(analysis_terms))
        
        # Check for risk assessment (30%)
        if 'risk' in result.content.lower() and 'assessment' in result.content.lower():
            quality += 0.3
        
        # Check for practical recommendations (20%)
        if 'recommend' in result.content.lower() or 'suggest' in result.content.lower():
            quality += 0.2
        
        # Success factor (10%)
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)