from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from typing import Dict, Any

class VolatilityRegimeAgent(BaseAgent):
    def __init__(self, config=None, metadata=None):
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Volatility regime classification and exposure adjustment",
                required_features=["volatility_20", "atr", "volatility_percentile"],
                tags=["risk", "volatility", "regime"]
            )
        super().__init__(
            agent_name="volatility_regime_agent",
            agent_category=AgentCategory.RISK,
            metadata=metadata,
            config=config
        )
        
        self._normal_volatility = 1.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        volatility_20 = features.get("volatility_20", 0.0)
        atr = features.get("atr", 0.0)
        volatility_percentile = features.get("volatility_percentile", 50.0)
        
        signal = "hold"
        confidence = 50.0
        numerical_score = 0.0
        reasoning = ""
        supporting_data = {}
        
        if volatility_20 > 0:
            volatility_ratio = volatility_20 / self._normal_volatility
        else:
            volatility_ratio = 1.0
        
        base_confidence = min(90.0, 50.0 + abs(volatility_ratio - 1) * 20)
        
        if volatility_ratio > 3.0:
            signal = "sell"
            confidence = min(95.0, base_confidence + 10)
            numerical_score = -1.0
            reasoning = (
                f"Extreme volatility regime detected ({volatility_ratio:.1f}x normal). "
                f"Volatility: {volatility_20:.4f}, ATR: {atr:.4f}, "
                f"Percentile: {volatility_percentile:.1f}. Consider reducing exposure."
            )
            supporting_data = {
                "volatility_20": volatility_20,
                "atr": atr,
                "volatility_percentile": volatility_percentile,
                "volatility_ratio": volatility_ratio,
                "regime": "extreme",
                "exposure_recommendation": "reduce"
            }
        elif volatility_ratio > 2.0:
            signal = "sell"
            confidence = min(85.0, base_confidence)
            numerical_score = -0.6
            reasoning = (
                f"High volatility regime detected ({volatility_ratio:.1f}x normal). "
                f"Volatility: {volatility_20:.4f}, ATR: {atr:.4f}, "
                f"Percentile: {volatility_percentile:.1f}. Consider reducing exposure."
            )
            supporting_data = {
                "volatility_20": volatility_20,
                "atr": atr,
                "volatility_percentile": volatility_percentile,
                "volatility_ratio": volatility_ratio,
                "regime": "high",
                "exposure_recommendation": "reduce"
            }
        elif volatility_ratio < 0.5:
            signal = "buy"
            confidence = min(85.0, base_confidence)
            numerical_score = 0.6
            reasoning = (
                f"Low volatility regime detected ({volatility_ratio:.1f}x normal). "
                f"Volatility: {volatility_20:.4f}, ATR: {atr:.4f}, "
                f"Percentile: {volatility_percentile:.1f}. Consider increasing exposure."
            )
            supporting_data = {
                "volatility_20": volatility_20,
                "atr": atr,
                "volatility_percentile": volatility_percentile,
                "volatility_ratio": volatility_ratio,
                "regime": "low",
                "exposure_recommendation": "increase"
            }
        else:
            signal = "hold"
            confidence = 60.0
            numerical_score = 0.0
            reasoning = (
                f"Normal volatility regime ({volatility_ratio:.1f}x normal). "
                f"Volatility: {volatility_20:.4f}, ATR: {atr:.4f}, "
                f"Percentile: {volatility_percentile:.1f}. Full exposure allowed."
            )
            supporting_data = {
                "volatility_20": volatility_20,
                "atr": atr,
                "volatility_percentile": volatility_percentile,
                "volatility_ratio": volatility_ratio,
                "regime": "normal",
                "exposure_recommendation": "full"
            }
        
        return AgentSignal(
            agent_name=self._agent_name,
            agent_category=self._agent_category.value,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data=supporting_data
        )
