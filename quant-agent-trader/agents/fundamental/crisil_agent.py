"""
CRISIL Analysis Agent - Company analysis from CRISIL

This agent integrates CRISIL's in-depth company analysis including:
- CRISIL ratings and outlook
- Industry outlook and positioning
- Business risk assessment
- Financial risk assessment
- Management quality scoring

Note: CRISIL analysis is typically available through their website and may require
subscription for full access. This agent uses publicly available data and simulated
metrics where actual data is unavailable.
"""

from typing import Dict, Any, Optional, List
import logging

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


logger = logging.getLogger(__name__)


class CRISILAnalysisAgent(BaseAgent):
    """
    CRISIL Analysis Agent for fundamental research.
    
    Analyzes company fundamentals based on CRISIL's rating methodology:
    - Company rating (AAA to D)
    - Industry outlook (Positive/Negative/Stable)
    - Business risk profile
    - Financial risk profile
    - Management quality assessment
    """
    
    # CRISIL Rating to numeric score mapping
    RATING_SCORES = {
        "AAA": 100, "AA+": 90, "AA": 85, "AA-": 80,
        "A+": 75, "A": 70, "A-": 65,
        "BBB+": 60, "BBB": 55, "BBB-": 50,
        "BB+": 45, "BB": 40, "BB-": 35,
        "B+": 30, "B": 25, "B-": 20,
        "CCC+": 15, "CCC": 12, "CCC-": 10,
        "CC": 7, "C": 5, "D": 2
    }
    
    # Industry outlook scores
    OUTLOOK_SCORES = {
        "positive": 80,
        "stable": 50,
        "negative": 20
    }
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the CRISIL Analysis agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="CRISIL in-depth company analysis for fundamental research",
                required_features=[
                    "crisil_rating",
                    "crisil_outlook",
                    "industry_outlook",
                    "business_risk",
                    "financial_risk",
                    "management_score"
                ],
                author="Quant Team",
                tags=["crisil", "fundamental", "rating", "research"]
            )
        
        super().__init__(
            agent_name="crisil_analysis_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
    
    def _parse_rating(self, rating: str) -> float:
        """Convert CRISIL rating to numeric score."""
        if not rating:
            return 50.0
        
        rating = rating.upper().strip()
        return self.RATING_SCORES.get(rating, 50.0)
    
    def _parse_outlook(self, outlook: str) -> float:
        """Convert outlook to numeric score."""
        if not outlook:
            return 50.0
        
        outlook = outlook.lower().strip()
        return self.OUTLOOK_SCORES.get(outlook, 50.0)
    
    def _analyze_rating(
        self,
        rating: str
    ) -> tuple:
        """Analyze CRISIL rating."""
        score = self._parse_rating(rating)
        
        if score >= 80:
            return "bullish", 85.0, f"CRISIL rating {rating} indicates highest credit quality"
        elif score >= 60:
            return "bullish", 70.0, f"CRISIL rating {rating} indicates strong credit quality"
        elif score >= 50:
            return "neutral", 55.0, f"CRISIL rating {rating} indicates adequate credit quality"
        elif score >= 30:
            return "bearish", 40.0, f"CRISIL rating {rating} indicates speculative quality"
        else:
            return "bearish", 25.0, f"CRISIL rating {rating} indicates high risk"
    
    def _analyze_outlook(
        self,
        outlook: str
    ) -> tuple:
        """Analyze company outlook."""
        score = self._parse_outlook(outlook)
        
        if score >= 70:
            return "bullish", 75.0, f"Positive outlook suggests strong future performance"
        elif score >= 40:
            return "neutral", 50.0, f"Stable outlook indicates consistent performance expected"
        else:
            return "bearish", 35.0, f"Negative outlook suggests challenges ahead"
    
    def _analyze_industry_outlook(
        self,
        industry_outlook: str
    ) -> tuple:
        """Analyze industry outlook."""
        score = self._parse_outlook(industry_outlook)
        
        if score >= 70:
            return "bullish", 75.0, f"Industry outlook positive - favorable sector conditions"
        elif score >= 40:
            return "neutral", 50.0, f"Industry outlook stable - steady sector performance"
        else:
            return "bearish", 35.0, f"Industry outlook negative - challenging sector dynamics"
    
    def _analyze_business_risk(
        self,
        business_risk: str
    ) -> tuple:
        """Analyze business risk profile."""
        risk_lower = (business_risk or "").lower()
        
        if "low" in risk_lower:
            return "bullish", 80.0, "Low business risk - strong market position"
        elif "moderate" in risk_lower:
            return "neutral", 55.0, "Moderate business risk - acceptable business profile"
        elif "high" in risk_lower:
            return "bearish", 30.0, "High business risk - elevated operational challenges"
        else:
            return "neutral", 50.0, "Business risk profile unclear"
    
    def _analyze_financial_risk(
        self,
        financial_risk: str
    ) -> tuple:
        """Analyze financial risk profile."""
        risk_lower = (financial_risk or "").lower()
        
        if "low" in risk_lower:
            return "bullish", 80.0, "Low financial risk - strong balance sheet"
        elif "moderate" in risk_lower:
            return "neutral", 55.0, "Moderate financial risk - adequate financial flexibility"
        elif "high" in risk_lower:
            return "bearish", 30.0, "High financial risk - elevated leverage concerns"
        else:
            return "neutral", 50.0, "Financial risk profile unclear"
    
    def _analyze_management(
        self,
        management_score: float
    ) -> tuple:
        """Analyze management quality score (0-100)."""
        if management_score >= 80:
            return "bullish", 80.0, "Excellent management quality - experienced and proven team"
        elif management_score >= 60:
            return "bullish", 65.0, "Good management quality - capable leadership"
        elif management_score >= 40:
            return "neutral", 50.0, "Average management quality - satisfactory oversight"
        else:
            return "bearish", 35.0, "Below average management - potential execution risks"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute CRISIL-based trading signal.
        
        Args:
            features: Dictionary containing CRISIL analysis data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            rating = features.get("crisil_rating", "")
            outlook = features.get("crisil_outlook", "stable")
            industry_outlook = features.get("industry_outlook", "stable")
            business_risk = features.get("business_risk", "moderate")
            financial_risk = features.get("financial_risk", "moderate")
            management_score = features.get("management_score", 50.0)
            
            # Additional CRISIL metrics
            rating_watch = features.get("rating_watch", "")
            corporate_governance = features.get("corporate_governance_score", 50.0)
            
            # Analyze each component
            rating_signal, rating_conf, rating_reason = self._analyze_rating(rating)
            outlook_signal, outlook_conf, outlook_reason = self._analyze_outlook(outlook)
            industry_signal, industry_conf, industry_reason = self._analyze_industry_outlook(industry_outlook)
            business_signal, business_conf, business_reason = self._analyze_business_risk(business_risk)
            financial_signal, financial_conf, financial_reason = self._analyze_financial_risk(financial_risk)
            mgmt_signal, mgmt_conf, mgmt_reason = self._analyze_management(management_score)
            
            # Collect all signals
            signals = [
                (rating_signal, rating_conf, rating_reason),
                (outlook_signal, outlook_conf, outlook_reason),
                (industry_signal, industry_conf, industry_reason),
                (business_signal, business_conf, business_reason),
                (financial_signal, financial_conf, financial_reason),
                (mgmt_signal, mgmt_conf, mgmt_reason)
            ]
            
            bullish_count = sum(1 for s, c, _ in signals if s == "bullish" and c > 0)
            bearish_count = sum(1 for s, c, _ in signals if s == "bearish" and c > 0)
            total_confidence = sum(c for _, c, _ in signals if c > 0)
            
            active_signals = sum(1 for _, c, _ in signals if c > 0)
            avg_confidence = total_confidence / active_signals if active_signals > 0 else 50.0
            
            # Determine final signal
            if bullish_count > bearish_count + 1:
                final_signal = "buy"
                final_score = 0.3
                confidence = min(90.0, avg_confidence + 10)
            elif bearish_count > bullish_count + 1:
                final_signal = "sell"
                final_score = -0.3
                confidence = min(90.0, avg_confidence + 10)
            elif bullish_count > bearish_count:
                final_signal = "buy"
                final_score = 0.15
                confidence = avg_confidence
            elif bearish_count > bullish_count:
                final_signal = "sell"
                final_score = -0.15
                confidence = avg_confidence
            else:
                final_signal = "hold"
                final_score = 0.0
                confidence = avg_confidence
            
            # Generate comprehensive reasoning
            reasoning_parts = [
                f"CRISIL Rating: {rating or 'N/A'} - {rating_reason}",
                f"Outlook: {outlook or 'N/A'} - {outlook_reason}",
                f"Industry: {industry_outlook or 'N/A'} - {industry_reason}",
                f"Business Risk: {business_risk or 'N/A'} - {business_reason}",
                f"Financial Risk: {financial_risk or 'N/A'} - {financial_reason}",
                f"Management: Score {management_score:.0f}/100 - {mgmt_reason}"
            ]
            
            if rating_watch:
                reasoning_parts.append(f"Rating Watch: {rating_watch}")
            
            final_reason = " | ".join(reasoning_parts)
            
            supporting_data = {
                "crisil_rating": rating,
                "crisil_rating_score": self._parse_rating(rating),
                "crisil_outlook": outlook,
                "industry_outlook": industry_outlook,
                "business_risk": business_risk,
                "financial_risk": financial_risk,
                "management_score": management_score,
                "rating_watch": rating_watch,
                "corporate_governance_score": corporate_governance,
                "bullish_signals": bullish_count,
                "bearish_signals": bearish_count,
                "avg_component_confidence": avg_confidence
            }
            
            return AgentSignal(
                agent_name=self.agent_name,
                agent_category=self.agent_category.value,
                signal=final_signal,
                confidence=confidence,
                numerical_score=final_score,
                reasoning=final_reason,
                supporting_data=supporting_data
            )
            
        except Exception as e:
            return self._create_error_signal(f"CRISIL analysis failed: {str(e)}")


class CRISILDataEngine:
    """
    Engine to fetch CRISIL analysis data for companies.
    
    Provides:
    - CRISIL ratings
    - Industry outlook
    - Business/Financial risk assessments
    - Management quality scores
    
    Note: This uses publicly available data and simulated metrics
    where actual CRISIL data requires subscription.
    """
    
    # Common CRISIL ratings for Indian stocks (simulated data - in production, use API)
    MOCK_RATINGS = {
        "RELIANCE": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "TCS": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "HDFCBANK": {"rating": "AAA", "outlook": "positive", "business_risk": "low", "financial_risk": "low"},
        "INFY": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "ICICIBANK": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "moderate"},
        "SBIN": {"rating": "AA+", "outlook": "positive", "business_risk": "low", "financial_risk": "moderate"},
        "KOTAKBANK": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "HINDUNILVR": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "LT": {"rating": "AAA", "outlook": "stable", "business_risk": "low", "financial_risk": "low"},
        "BAJFINANCE": {"rating": "AA+", "outlook": "positive", "business_risk": "low", "financial_risk": "moderate"},
    }
    
    # Industry outlook mapping
    INDUSTRY_OUTLOOK = {
        "IT": "positive",
        "PHARMA": "positive",
        "FINANCE": "positive",
        "CONSUMER": "stable",
        "INFRA": "positive",
        "METALS": "negative",
        "ENERGY": "stable",
        "AUTOMOBILE": "stable",
    }
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def _detect_industry(self, symbol: str) -> str:
        """Detect industry from symbol (simplified)."""
        it_stocks = ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"]
        finance_stocks = ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "BAJFINANCE", "AXISBANK"]
        pharma_stocks = ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB"]
        consumer_stocks = ["HINDUNILVR", "ASIANPAINT", "TITAN", "MARUTI"]
        
        if symbol in it_stocks:
            return "IT"
        elif symbol in finance_stocks:
            return "FINANCE"
        elif symbol in pharma_stocks:
            return "PHARMA"
        elif symbol in consumer_stocks:
            return "CONSUMER"
        return "OTHER"
    
    async def get_crisil_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get CRISIL analysis for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with CRISIL analysis data
        """
        symbol_upper = symbol.upper()
        
        # Check cache
        if symbol_upper in self.cache:
            return self.cache[symbol_upper]
        
        # Get mock data or generate simulated data
        if symbol_upper in self.MOCK_RATINGS:
            data = self.MOCK_RATINGS[symbol_upper].copy()
        else:
            # Generate simulated data for unknown symbols
            import random
            ratings = ["AAA", "AA+", "AA", "A+", "A", "BBB+", "BBB"]
            outlooks = ["positive", "stable", "negative"]
            risks = ["low", "moderate", "high"]
            
            data = {
                "rating": ratings[random.randint(0, len(ratings)-1)],
                "outlook": outlooks[random.randint(0, len(outlooks)-1)],
                "business_risk": risks[random.randint(0, len(risks)-1)],
                "financial_risk": risks[random.randint(0, len(risks)-1)]
            }
        
        # Add derived fields
        data["symbol"] = symbol_upper
        data["industry"] = self._detect_industry(symbol_upper)
        data["industry_outlook"] = self.INDUSTRY_OUTLOOK.get(data["industry"], "stable")
        
        # Generate management score based on rating
        rating_score = CRISILAnalysisAgent.RATING_SCORES.get(data["rating"], 50)
        import random
        data["management_score"] = min(100, rating_score + random.uniform(-10, 10))
        
        # Add corporate governance score
        data["corporate_governance_score"] = min(100, rating_score + random.uniform(-5, 5))
        
        # Cache the result
        self.cache[symbol_upper] = data
        
        return data
    
    async def get_batch_analysis(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get CRISIL analysis for multiple symbols."""
        import asyncio
        tasks = [self.get_crisil_analysis(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: (result if not isinstance(result, Exception) else {"error": str(result)})
            for symbol, result in zip(symbols, results)
        }


# Global instance
crisil_engine = CRISILDataEngine()
