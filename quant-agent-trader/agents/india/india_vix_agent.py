from typing import Dict, Any
import logging

from signals.signal_schema import AgentSignal, AgentCategory
from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig


logger = logging.getLogger(__name__)


class IndiaVIXAgent(BaseAgent):
    """
    India VIX Analysis Agent.
    
    Analyzes India VIX (Volatility Index) to gauge market fear/uncertainty
    and generate trading signals based on volatility regime.
    """
    
    def __init__(self, config: AgentConfig = None):
        super().__init__(
            agent_name="india_vix_agent",
            agent_category=AgentCategory.RISK,
            metadata=AgentMetadata(
                version="1.0.0",
                description="India VIX volatility analysis agent",
                required_features=["india_vix", "india_vix_history"],
                tags=["volatility", "india", "risk", "vix"]
            ),
            config=config
        )
        self.vix_buy_threshold = 15.0
        self.vix_sell_threshold = 25.0
        self.extreme_high = 30.0
    
    def _calculate_vix_regime(self, vix_value: float) -> str:
        """Determine volatility regime based on VIX value."""
        if vix_value < self.vix_buy_threshold:
            return "low"
        elif vix_value < self.vix_sell_threshold:
            return "normal"
        elif vix_value < self.extreme_high:
            return "elevated"
        else:
            return "extreme"
    
    def _calculate_vix_signal(
        self,
        vix_value: float,
        vix_change: float,
        regime: str
    ) -> tuple[str, float, str]:
        """
        Generate signal based on VIX analysis.
        
        Returns:
            Tuple of (signal, confidence, reasoning)
        """
        confidence = 50.0
        reasoning = ""
        signal = "hold"
        
        if regime == "low":
            if vix_change < -2:
                signal = "buy"
                confidence = 75.0
                reasoning = (
                    f"VIX at {vix_value:.2f} (low volatility regime) with "
                    f"sharp decline of {vix_change:.2f}. Low fear suggests "
                    f"bullish market conditions."
                )
            elif vix_change < 0:
                signal = "hold"
                confidence = 60.0
                reasoning = (
                    f"VIX at {vix_value:.2f} indicates low volatility. "
                    f"Market may continue current trend."
                )
            else:
                signal = "hold"
                confidence = 55.0
                reasoning = f"VIX at {vix_value:.2f} (low), but rising."
        
        elif regime == "normal":
            if vix_change > 3:
                signal = "sell"
                confidence = 70.0
                reasoning = (
                    f"VIX rising sharply (+{vix_change:.2f}) from {vix_value:.2f}. "
                    f"Increasing volatility often precedes market corrections."
                )
            elif vix_change > 1:
                signal = "hold"
                confidence = 60.0
                reasoning = (
                    f"VIX at {vix_value:.2f} showing elevated readings. "
                    f"Monitor for further increases."
                )
            else:
                signal = "hold"
                confidence = 55.0
                reasoning = f"VIX at {vix_value:.2f} in normal range."
        
        elif regime == "elevated":
            if vix_change > 5:
                signal = "sell"
                confidence = 85.0
                reasoning = (
                    f"VIX spike to {vix_value:.2f} with +{vix_change:.2f} change. "
                    f"High volatility environment - defensive positioning advised."
                )
            elif vix_change > 2:
                signal = "sell"
                confidence = 75.0
                reasoning = (
                    f"VIX at {vix_value:.2f} (elevated) and rising. "
                    f"Market uncertainty increasing."
                )
            else:
                signal = "hold"
                confidence = 65.0
                reasoning = (
                    f"VIX at {vix_value:.2f} indicates elevated volatility. "
                    f"Caution warranted."
                )
        
        elif regime == "extreme":
            signal = "sell"
            confidence = 90.0
            reasoning = (
                f"VIX at {vix_value:.2f} (extreme). "
                f"High fear in market - expect panic selling or potential bottom."
            )
        
        return signal, confidence, reasoning
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """Compute India VIX based trading signal."""
        
        vix_value = features.get("india_vix")
        
        if vix_value is None:
            return self._create_error_signal("India VIX data not available")
        
        vix_history = features.get("india_vix_history", [])
        
        if len(vix_history) > 0:
            vix_change = vix_value - vix_history[-1]
        else:
            vix_change = 0.0
        
        if len(vix_history) >= 5:
            vix_ma5 = sum(vix_history[-5:]) / 5
            vix_trend = "rising" if vix_value > vix_ma5 else "falling"
        else:
            vix_trend = "stable"
        
        regime = self._calculate_vix_regime(vix_value)
        
        signal_type, confidence, reasoning = self._calculate_vix_signal(
            vix_value, vix_change, regime
        )
        
        numerical_score = 0.0
        if signal_type == "buy":
            numerical_score = -0.5
        elif signal_type == "sell":
            numerical_score = 0.5
        else:
            numerical_score = 0.0
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category.value,
            signal=signal_type,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={
                "india_vix": vix_value,
                "vix_change": vix_change,
                "vix_regime": regime,
                "vix_trend": vix_trend,
                "vix_history_length": len(vix_history)
            }
        )
