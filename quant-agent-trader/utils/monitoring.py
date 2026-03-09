"""
Monitoring & Alerts - Real-time monitoring and notifications.

Usage:
    monitor = Monitor()
    
    # Add alert
    monitor.alert("Trade executed", level="info")
    
    # Check thresholds
    monitor.check_drawdown(0.15)
    monitor.check_pnl(-5000)
    
    # Send to Slack
    monitor.send_slack("Trade completed")
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert."""
    level: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


class AlertHandler:
    """Base class for alert handlers."""
    
    def send(self, alert: Alert) -> None:
        raise NotImplementedError


class ConsoleHandler(AlertHandler):
    """Log alerts to console."""
    
    def send(self, alert: Alert) -> None:
        level_str = alert.level.upper()
        print(f"[{alert.timestamp}] [{level_str}] {alert.message}")


class FileHandler(AlertHandler):
    """Log alerts to file."""
    
    def __init__(self, filepath: str = "alerts.log"):
        self.filepath = filepath
    
    def send(self, alert: Alert) -> None:
        with open(self.filepath, "a") as f:
            f.write(f"[{alert.timestamp.isoformat()}] [{alert.level.upper()}] {alert.message}\n")


class SlackHandler(AlertHandler):
    """Send alerts to Slack."""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
    
    def send(self, alert: Alert) -> None:
        if not self.webhook_url:
            return
        
        try:
            import requests
            
            payload = {
                "text": f"[{alert.level.upper()}] {alert.message}",
                "context": alert.context
            }
            
            requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to send Slack alert: {e}")


class TelegramHandler(AlertHandler):
    """Send alerts to Telegram."""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
    
    def send(self, alert: Alert) -> None:
        if not self.bot_token or not self.chat_id:
            return
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": f"[{alert.level.upper()}] {alert.message}"
            }
            
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to send Telegram alert: {e}")


class EmailHandler(AlertHandler):
    """Send alerts via email."""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        from_addr: str = None,
        to_addrs: List[str] = None
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs or []
    
    def send(self, alert: Alert) -> None:
        if not self.smtp_server or not self.to_addrs:
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(f"[{alert.level.upper()}] {alert.message}")
            msg["Subject"] = f"Quant Trader Alert: {alert.level.upper()}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
        except Exception as e:
            logger.warning(f"Failed to send email alert: {e}")


class Monitor:
    """
    Real-time monitoring and alerting system.
    
    Usage:
        monitor = Monitor()
        monitor.add_handler(ConsoleHandler())
        
        monitor.alert("Trade executed", level="info")
    """
    
    def __init__(self):
        self.handlers: List[AlertHandler] = []
        self.alert_history: List[Alert] = []
        
        self.handlers.append(ConsoleHandler())
        self.handlers.append(FileHandler())
    
    def add_handler(self, handler: AlertHandler) -> None:
        """Add an alert handler."""
        self.handlers.append(handler)
    
    def alert(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict] = None
    ) -> None:
        """
        Send an alert.
        
        Args:
            message: Alert message
            level: Alert level (debug, info, warning, error, critical)
            context: Additional context
        """
        alert = Alert(
            level=level,
            message=message,
            context=context or {}
        )
        
        self.alert_history.append(alert)
        
        for handler in self.handlers:
            try:
                handler.send(alert)
            except Exception as e:
                logger.error(f"Handler failed: {e}")
    
    def info(self, message: str, **kwargs) -> None:
        self.alert(message, "info", kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self.alert(message, "warning", kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self.alert(message, "error", kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        self.alert(message, "critical", kwargs)
    
    def check_drawdown(self, drawdown: float, threshold: float = 0.10) -> None:
        """Check drawdown threshold."""
        if drawdown > threshold:
            self.alert(
                f"Drawdown {drawdown:.1%} exceeds threshold {threshold:.1%}",
                level="warning",
                drawdown=drawdown,
                threshold=threshold
            )
    
    def check_pnl(self, pnl: float, loss_threshold: float = -5000) -> None:
        """Check P&L threshold."""
        if pnl < loss_threshold:
            self.alert(
                f"P&L ${pnl:.0f} exceeds loss threshold ${loss_threshold:.0f}",
                level="error",
                pnl=pnl,
                threshold=loss_threshold
            )
    
    def check_signal(self, symbol: str, signal: str, confidence: float) -> None:
        """Log signal generation."""
        self.alert(
            f"Signal: {signal.upper()} {symbol} (confidence: {confidence:.0f}%)",
            level="info",
            symbol=symbol,
            signal=signal,
            confidence=confidence
        )
    
    def check_trade(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float,
        pnl: float = None
    ) -> None:
        """Log trade execution."""
        msg = f"Trade: {direction.upper()} {quantity} {symbol} @ {price:.2f}"
        
        if pnl is not None:
            msg += f" | P&L: {pnl:.2f}"
        
        self.alert(
            msg,
            level="info",
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            price=price,
            pnl=pnl
        )
    
    def check_data_quality(self, symbol: str, issues: int) -> None:
        """Check data quality issues."""
        if issues > 0:
            self.alert(
                f"Data quality issues for {symbol}: {issues} issues found",
                level="warning",
                symbol=symbol,
                issues=issues
            )
    
    def check_model_performance(self, accuracy: float, threshold: float = 0.55) -> None:
        """Check model performance."""
        if accuracy < threshold:
            self.alert(
                f"Model accuracy {accuracy:.1%} below threshold {threshold:.1%}",
                level="warning",
                accuracy=accuracy,
                threshold=threshold
            )
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get recent alerts."""
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        
        return alerts[-limit:]
    
    def clear_history(self) -> None:
        """Clear alert history."""
        self.alert_history.clear()


class TradingMonitor:
    """
    Specialized monitor for trading systems.
    """
    
    def __init__(self):
        self.monitor = Monitor()
        self.trade_count = 0
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
    
    def on_trade(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float,
        pnl: float = None
    ) -> None:
        """Called when a trade is executed."""
        self.trade_count += 1
        self.daily_pnl += pnl if pnl else 0
        
        self.monitor.check_trade(symbol, direction, quantity, price, pnl)
    
    def on_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float
    ) -> None:
        """Called when a signal is generated."""
        self.monitor.check_signal(symbol, signal, confidence)
    
    def on_data_issue(self, symbol: str, issues: int) -> None:
        """Called when data quality issues are detected."""
        self.monitor.check_data_quality(symbol, issues)
    
    def on_periodic_check(self, metrics: Dict[str, float]) -> None:
        """Called for periodic health checks."""
        if "drawdown" in metrics:
            self.monitor.check_drawdown(metrics["drawdown"])
        
        if "pnl" in metrics:
            self.monitor.check_pnl(metrics["pnl"])
        
        if "model_accuracy" in metrics:
            self.monitor.check_model_performance(metrics["model_accuracy"])


_global_monitor = None


def get_monitor() -> Monitor:
    """Get global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = Monitor()
    return _global_monitor
