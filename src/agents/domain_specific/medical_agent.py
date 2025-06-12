"""
Medical and healthcare specialized agents
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from src.agents.enhanced_base import EnhancedBaseAgent, Task, AgentResult


class MedicalResearchAgent(EnhancedBaseAgent):
    """Specialized agent for medical and healthcare research"""
    
    QUALITY_THRESHOLD = 0.95  # Higher threshold for medical information
    REQUIRES_APPROVAL = True  # Medical advice should be reviewed
    MAX_TOKENS = 8000
    SPECIALIZATION = "medical"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medical_sources = [
            "pubmed", "cochrane", "clinicaltrials.gov",
            "who.int", "cdc.gov", "nejm.org", "lancet.com",
            "bmj.com", "nature.com/medicine", "sciencedirect.com"
        ]
        self.peer_review_threshold = 0.8
        self.evidence_hierarchy = {
            'systematic_review': 1.0,
            'meta_analysis': 0.95,
            'rct': 0.9,
            'cohort_study': 0.7,
            'case_control': 0.6,
            'case_series': 0.4,
            'case_report': 0.3,
            'expert_opinion': 0.2
        }
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Medical Research Specialist
        
        Task: {task.query}
        
        IMPORTANT: This is for research purposes only. Not medical advice.
        
        Requirements:
        1. Prioritize peer-reviewed sources (>80% of citations)
        2. Include latest clinical guidelines
        3. Verify drug interactions and contraindications
        4. Follow medical ethics and patient privacy
        5. Use proper medical terminology with lay explanations
        6. Include evidence levels for all claims
        7. Note any limitations or uncertainties
        
        Medical Context:
        {context.get('medical_context', 'No previous medical context')}
        
        Quality Standards:
        - Evidence Level: Prefer Level 1 evidence (systematic reviews, RCTs)
        - Recency: Prioritize studies from last 5 years
        - Sample Size: Note study populations
        - Conflicts of Interest: Disclose any noted
        - Clinical Relevance: Focus on practical applications
        
        Required Sections:
        1. Executive Summary (for healthcare providers)
        2. Clinical Evidence Summary
           - Key findings with evidence levels
           - Study quality assessment
           - Population characteristics
        3. Clinical Guidelines (if applicable)
        4. Safety Considerations
           - Contraindications
           - Drug interactions
           - Adverse effects
        5. Patient-Friendly Summary
        6. Limitations and Uncertainties
        7. References (AMA citation style)
        
        DISCLAIMER: Include clear disclaimer that this is research information only.
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate medical research quality with strict criteria"""
        scores = []
        
        # Check peer review ratio (40% weight)
        if result.sources:
            peer_reviewed = sum(1 for s in result.sources 
                              if s.get('metadata', {}).get('peer_reviewed', False))
            peer_review_score = peer_reviewed / len(result.sources)
            scores.append(('peer_review', peer_review_score, 0.4))
        else:
            scores.append(('peer_review', 0.0, 0.4))
        
        # Check evidence levels (30% weight)
        if result.sources:
            evidence_scores_list = []
            for source in result.sources:
                evidence_level = source.get('metadata', {}).get('evidence_level', 'expert_opinion')
                evidence_scores_list.append(
                    self.evidence_hierarchy.get(evidence_level, 0.2)
                )
            evidence_score = sum(evidence_scores_list) / len(evidence_scores_list)
            scores.append(('evidence', evidence_score, 0.3))
        else:
            scores.append(('evidence', 0.0, 0.3))
        
        # Check recency (15% weight)
        if result.sources:
            current_year = datetime.now(timezone.utc).year
            recency_scores = []
            for source in result.sources:
                year = source.get('metadata', {}).get('year', 0)
                if year >= current_year - 2:
                    recency_scores.append(1.0)
                elif year >= current_year - 5:
                    recency_scores.append(0.7)
                else:
                    recency_scores.append(0.3)
            recency_score = sum(recency_scores) / len(recency_scores)
            scores.append(('recency', recency_score, 0.15))
        else:
            scores.append(('recency', 0.0, 0.15))
        
        # Check for required sections (10% weight)
        content_lower = result.content.lower()
        required_sections = [
            'clinical evidence',
            'safety',
            'disclaimer',
            'references'
        ]
        section_count = sum(1 for section in required_sections if section in content_lower)
        section_score = section_count / len(required_sections)
        scores.append(('sections', section_score, 0.1))
        
        # Success factor (5% weight)
        scores.append(('success', 1.0 if result.success else 0.0, 0.05))
        
        # Calculate weighted score
        total_score = sum(score * weight for _, score, weight in scores)
        
        # Store detailed scoring in metadata
        result.metadata['quality_breakdown'] = {
            name: score for name, score, _ in scores
        }
        
        return min(total_score, 1.0)
    
    async def execute_with_monitoring(self, prompt: str) -> AgentResult:
        """Execute with medical-specific monitoring"""
        # In production, this would call the actual CLI
        # For now, return a mock result
        return AgentResult(
            success=True,
            content="""
            # Clinical Research Summary: Type 2 Diabetes Management
            
            ## Executive Summary
            Recent systematic reviews show HbA1c targets should be individualized...
            
            ## Clinical Evidence Summary
            - Meta-analysis (2023, n=10,000): Intensive control reduces complications
            - RCT (2024, n=500): SGLT2 inhibitors show cardiovascular benefits
            
            ## Safety Considerations
            - Hypoglycemia risk with intensive control
            - Monitor renal function with SGLT2 inhibitors
            
            ## DISCLAIMER
            This information is for research purposes only and not medical advice.
            
            ## References
            1. Smith et al. Diabetes Care. 2023;46(5):1234-45.
            """,
            sources=[
                {
                    "name": "Diabetes Care Meta-analysis",
                    "url": "https://diabetesjournals.org/care/article/46/5/1234",
                    "metadata": {
                        "peer_reviewed": True,
                        "evidence_level": "meta_analysis",
                        "year": 2023
                    }
                }
            ],
            tokens_used=500
        )


class ClinicalTrialAgent(EnhancedBaseAgent):
    """Agent specialized in clinical trial research and analysis"""
    
    QUALITY_THRESHOLD = 0.92
    REQUIRES_APPROVAL = True
    SPECIALIZATION = "clinical_trials"
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        return f"""
        Role: Clinical Trial Research Specialist
        
        Task: {task.query}
        
        Focus Areas:
        1. Search ClinicalTrials.gov and international registries
        2. Analyze trial design and methodology
        3. Evaluate inclusion/exclusion criteria
        4. Assess statistical power and endpoints
        5. Review safety monitoring plans
        
        Trial Context: {context.get('trial_context', 'No context')}
        
        Required Analysis:
        - Trial phase and status
        - Study design (RCT, observational, etc.)
        - Primary and secondary endpoints
        - Sample size and power calculations
        - Inclusion/exclusion criteria
        - Safety monitoring
        - Ethical considerations
        - Results (if available)
        
        Output Format:
        1. Trial Overview
        2. Methodology Assessment
        3. Population Characteristics
        4. Results Summary (if available)
        5. Limitations
        6. Clinical Implications
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate clinical trial research quality"""
        quality = 0.0
        
        # Check for trial registry sources (40%)
        if result.sources:
            registry_sources = sum(1 for s in result.sources
                                 if 'clinicaltrials.gov' in s.get('url', '').lower()
                                 or 'registry' in s.get('name', '').lower())
            quality += 0.4 * min(registry_sources / len(result.sources), 1.0)
        
        # Check methodology assessment (30%)
        if 'methodology' in result.content.lower() or 'study design' in result.content.lower():
            quality += 0.3
        
        # Check for critical appraisal (20%)
        if any(term in result.content.lower() for term in ['limitation', 'bias', 'power']):
            quality += 0.2
        
        # Success factor (10%)
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)