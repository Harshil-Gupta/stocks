from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from typing import Dict, Any

class TailRiskAgent(BaseAgent):
    def __init__(self, config=None, metadata=None):
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Tail risk analysis using drawdowns and VaR metrics",
                required_features=["max_drawdown_30d", "max_drawdown_90d", "var_95", "cvar_95"],
                tags=["risk", "tail", "drawdown", "var"]
            )
        super().__init__(
            agent_name="tail_risk_agent",
            agent_category=AgentCategory.RISK,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        max_dd_30d = features.get("max_drawdown_30d", 0.0)
        max_dd_90d = features.get("max_drawdown_90d", 0.0)
        var_95 = features.get("var_95", 0.0)
        cvar_95 = features.get("cvar_95", 0.0)
        
        signal = "hold"
        confidence = 50.0
        numerical_score = 0.0
        reasoning = ""
        supporting_data = {}
        
        drawdown_severity = max(max_dd_30d, max_dd_90d)
        
        extreme_var = abs(var_95) > 0.10
        high_var = abs(var_95) > 0.05
        
        if drawdown_severity > 0.15 or (extreme_var and drawdown_severity > 0.10):
            signal = "sell"
            confidence = min(95.0, 70.0 + abs(drawdown_severity) * 100)
            numerical_score = -1.0
            reasoning = (
                f"High tail risk detected. 30d drawdown: {max_dd_30d:.2%}, "
                f"90d drawdown: {max_dd_90d:.2%}. VaR(95%): {var_95:.2%}, "
                f"CVaR(95%): {cvar_95:.2%}. Recent drawdown exceeds 15% with extreme VaR."
            )
            supporting_data = {
                "max_drawdown_30d": max_dd_30d,
                "max_drawdown_90d": max_dd_90d,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "drawdown_severity": drawdown_severity,
                "risk_level": "high",
                "pattern_consistency": "extreme"
            }
        elif drawdown_severity > 0.05 or high_var:
            signal = "sell"
            confidence = min(80.0, 55.0 + abs(drawdown_severity) * 200)
            numerical_score = -0.5
            reasoning = (
                f"Medium tail risk detected. 30d drawdown: {max_dd_30d:.2%}, "
                f"90d drawdown: {max_dd_90d:.2%}. VaR(95%): {var_95:.2%}, "
                f"CVaR(95%): {cvar_95:.2%}. Drawdown in 5-15% range with elevated VaR."
            )
            supporting_data = {
                "max_drawdown_30d": max_dd_30d,
                "max_drawdown_90d": max_dd_90d,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "drawdown_severity": drawdown_severity,
                "risk_level": "medium",
                "pattern_consistency": "elevated"
            }
        else:
            signal = "buy"
            confidence = min(85.0, 60.0 + (0.05 - drawdown_severity) * 200)
            numerical_score = 0.5
            reasoning = (
                f"Low tail risk detected. 30d drawdown: {max_dd_30d:.2%}, "
                f"90d drawdown: {max_dd_90d:.2%}. VaR(95%): {var_95:.2%}, "
                f"CVaR(95%): {cvar_95:.2%}. Minimal drawdown with low VaR."
            )
            supporting_data = {
                "max_drawdown_30d": max_dd_30d,
                "max_drawdown_90d": max_dd_90d,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "drawdown_severity": drawdown_severity,
                "risk_level": "low",
                "pattern_consistency": "stable"
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
