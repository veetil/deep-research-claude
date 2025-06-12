"""
Financial analysis and risk assessment specialized agents
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from src.agents.enhanced_base import EnhancedBaseAgent, Task, AgentResult


class FinancialAnalysisAgent(EnhancedBaseAgent):
    """Specialized agent for financial analysis and market research"""
    
    QUALITY_THRESHOLD = 0.93
    REQUIRES_APPROVAL = True
    MAX_TOKENS = 8000
    SPECIALIZATION = "financial"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.financial_sources = [
            "bloomberg.com", "reuters.com", "wsj.com", "ft.com",
            "sec.gov", "federalreserve.gov", "yahoo.finance",
            "morningstar.com", "seekingalpha.com"
        ]
        self.analysis_components = {
            'fundamental': ['revenue', 'earnings', 'cash flow', 'debt', 'equity'],
            'technical': ['price', 'volume', 'moving average', 'rsi', 'macd'],
            'macro': ['gdp', 'inflation', 'interest rates', 'unemployment'],
            'risk': ['volatility', 'beta', 'var', 'sharpe ratio']
        }
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        analysis_type = task.metadata.get('analysis_type', 'comprehensive')
        time_horizon = task.metadata.get('time_horizon', 'medium-term')
        
        return f"""
        Role: Financial Analysis Specialist
        
        Task: {task.query}
        
        IMPORTANT DISCLAIMER: This is financial analysis only, NOT investment advice.
        Consult a licensed financial advisor for investment decisions.
        
        Analysis Type: {analysis_type}
        Time Horizon: {time_horizon}
        
        Requirements:
        1. Use authoritative financial data sources
        2. Include quantitative metrics and ratios
        3. Provide both fundamental and technical analysis
        4. Assess market conditions and trends
        5. Identify risks and opportunities
        6. Compare to industry benchmarks
        7. Note any data limitations
        
        Financial Context:
        {context.get('financial_context', 'No previous context')}
        
        Quality Standards:
        - Data Sources: Official filings > Financial databases > News
        - Metrics: Include standard financial ratios
        - Timeframe: Specify all data dates
        - Assumptions: Clearly state all assumptions
        - Risks: Comprehensive risk assessment
        
        Required Sections:
        1. Executive Summary
        2. Financial Performance Analysis
           - Revenue and growth trends
           - Profitability metrics
           - Cash flow analysis
           - Balance sheet strength
        3. Market Analysis
           - Industry comparison
           - Competitive positioning
           - Market trends
        4. Valuation Analysis
           - Multiple approaches (DCF, comparables, etc.)
           - Key assumptions
        5. Risk Assessment
           - Market risks
           - Company-specific risks
           - Regulatory risks
        6. Outlook and Scenarios
           - Base case
           - Bull/Bear scenarios
        7. Data Sources and Limitations
        
        DISCLAIMER: For informational purposes only. Not investment advice.
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate financial analysis quality"""
        scores = []
        
        # Check data source quality (35% weight)
        if result.sources:
            official_sources = sum(1 for s in result.sources
                                 if any(domain in s.get('url', '').lower()
                                       for domain in ['sec.gov', '10-k', '10-q', 'annual report']))
            source_score = min(official_sources / max(len(result.sources) * 0.3, 1), 1.0)
            scores.append(('sources', source_score, 0.35))
        else:
            scores.append(('sources', 0.0, 0.35))
        
        # Check quantitative analysis (30% weight)
        quant_terms = ['revenue', 'margin', 'ratio', 'growth', 'return', 'cash flow']
        quant_count = sum(1 for term in quant_terms if term in result.content.lower())
        quant_score = min(quant_count / len(quant_terms), 1.0)
        scores.append(('quantitative', quant_score, 0.3))
        
        # Check risk assessment (20% weight)
        risk_terms = ['risk', 'volatility', 'uncertainty', 'exposure', 'hedge']
        risk_count = sum(1 for term in risk_terms if term in result.content.lower())
        risk_score = min(risk_count / 3, 1.0)  # Expect at least 3 risk mentions
        scores.append(('risk', risk_score, 0.2))
        
        # Check disclaimer presence (10% weight)
        has_disclaimer = 'not investment advice' in result.content.lower() or \
                        'disclaimer' in result.content.lower()
        scores.append(('disclaimer', 1.0 if has_disclaimer else 0.0, 0.1))
        
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
        """Execute with financial-specific monitoring"""
        # Mock implementation
        return AgentResult(
            success=True,
            content="""
            # Financial Analysis: Apple Inc. (AAPL)
            
            ## Executive Summary
            Apple demonstrates strong financial performance with robust margins...
            
            ## Financial Performance Analysis
            
            ### Revenue Analysis
            - FY2023 Revenue: $383.3B (-2.8% YoY)
            - Services Revenue: $85.2B (+9.1% YoY)
            - Gross Margin: 44.1% (stable)
            
            ### Profitability Metrics
            - Operating Margin: 29.8%
            - Net Margin: 25.3%
            - ROE: 171.9%
            - ROIC: 56.1%
            
            ## Risk Assessment
            - Concentration risk in iPhone sales (52% of revenue)
            - Regulatory scrutiny in EU and US
            - Supply chain dependencies
            
            ## DISCLAIMER
            This analysis is for informational purposes only and not investment advice.
            
            ## Data Sources
            - Apple 10-K Filing (2023)
            - Company earnings reports
            """,
            sources=[
                {
                    "name": "Apple 10-K 2023",
                    "url": "https://www.sec.gov/Archives/edgar/data/320193/10-K",
                    "metadata": {
                        "source_type": "official_filing",
                        "date": "2023-11-03"
                    }
                }
            ],
            tokens_used=700
        )


class RiskAssessmentAgent(EnhancedBaseAgent):
    """Agent specialized in financial risk assessment and modeling"""
    
    QUALITY_THRESHOLD = 0.91
    REQUIRES_APPROVAL = True
    SPECIALIZATION = "risk_assessment"
    
    async def build_quality_prompt(self, task: Task, context: Dict) -> str:
        risk_type = task.metadata.get('risk_type', 'comprehensive')
        entity_type = task.metadata.get('entity_type', 'corporate')
        
        return f"""
        Role: Financial Risk Assessment Specialist
        
        Task: {task.query}
        
        Risk Type: {risk_type}
        Entity Type: {entity_type}
        
        Assessment Framework:
        1. Identify and categorize risks
        2. Quantify risk exposure where possible
        3. Assess probability and impact
        4. Evaluate existing controls
        5. Recommend mitigation strategies
        6. Stress test scenarios
        7. Monitor key risk indicators
        
        Risk Categories:
        - Market Risk (price, interest rate, FX)
        - Credit Risk (counterparty, concentration)
        - Operational Risk (process, systems, people)
        - Liquidity Risk (funding, market liquidity)
        - Regulatory/Compliance Risk
        - Strategic Risk (competition, technology)
        - Reputational Risk
        
        Output Format:
        1. Risk Summary Dashboard
        2. Detailed Risk Register
           - Risk description
           - Likelihood (1-5)
           - Impact (1-5)
           - Risk score
           - Controls
           - Mitigation actions
        3. Risk Heat Map
        4. Scenario Analysis
        5. Key Risk Indicators (KRIs)
        6. Recommendations
        
        DISCLAIMER: Risk assessment only. Consult professionals for decisions.
        """
    
    async def evaluate_quality(self, result: AgentResult) -> float:
        """Evaluate risk assessment quality"""
        quality = 0.0
        
        # Check risk categorization (35%)
        risk_categories = ['market', 'credit', 'operational', 'liquidity', 'regulatory']
        found_categories = sum(1 for cat in risk_categories if cat in result.content.lower())
        quality += 0.35 * (found_categories / len(risk_categories))
        
        # Check quantification (30%)
        quant_indicators = ['probability', 'impact', 'score', 'exposure', 'var']
        found_quant = sum(1 for ind in quant_indicators if ind in result.content.lower())
        quality += 0.3 * min(found_quant / 3, 1.0)
        
        # Check mitigation strategies (25%)
        if 'mitigation' in result.content.lower() or 'control' in result.content.lower():
            quality += 0.25
        
        # Success factor (10%)
        if result.success:
            quality += 0.1
        
        return min(quality, 1.0)