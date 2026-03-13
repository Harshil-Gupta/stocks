"""
Run analysis on all holdings and save signals for dashboard.

Usage:
    python -m data.run_holdings_analysis
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import PortfolioConfig
from data.import_portfolio import get_holdings_symbols, get_holdings_dir


async def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """Run analysis on a single symbol."""
    from main import QuantTradingSystem
    
    system = QuantTradingSystem()
    try:
        result = await system.analyze_stock(symbol)
        return {
            "symbol": symbol,
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "success": False,
            "error": str(e)
        }
    finally:
        system.shutdown()


def save_holdings_signals(signals_data: List[Dict], output_path: str = "data/holdings_signals.json"):
    """Save signals for all holdings."""
    with open(output_path, 'w') as f:
        json.dump(signals_data, f, indent=2)
    print(f"Saved: {output_path}")


def save_market_regime(regime: str, output_path: str = "data/market_regime.json"):
    """Save current market regime."""
    data = {
        "regime": regime,
        "timestamp": datetime.now().isoformat()
    }
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {output_path}")


async def main():
    print("="*60)
    print("Running analysis on all holdings...")
    print("="*60)
    
    # Get holdings symbols
    symbols = get_holdings_symbols()
    
    if not symbols:
        print("No holdings found!")
        sys.exit(1)
    
    print(f"\nFound {len(symbols)} holdings: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print()
    
    results = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Analyzing {symbol}...", end=" ")
        
        result = await analyze_symbol(symbol)
        
        if result["success"]:
            agg = result["result"].get("aggregated_signal", {})
            decision = agg.get("decision", "UNKNOWN")
            confidence = agg.get("confidence", 0)
            score = agg.get("score", 0)
            
            print(f"{decision} ({confidence:.1f}%)")
            
            results.append({
                "symbol": symbol,
                "decision": decision,
                "confidence": confidence,
                "score": score,
                "supporting_agents": len(agg.get("supporting_agents", [])),
                "conflicting_agents": len(agg.get("conflicting_agents", [])),
                "regime": agg.get("regime", "unknown")
            })
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")
            results.append({
                "symbol": symbol,
                "decision": "ERROR",
                "confidence": 0,
                "score": 0,
                "error": result.get("error", "Unknown error")
            })
    
    # Save signals
    save_holdings_signals(results)
    
    # Get market regime from first successful result
    successful_results = [r for r in results if r.get("decision") not in ["ERROR", "UNKNOWN"]]
    if successful_results:
        # Determine overall regime (most common)
        regimes = [r.get("regime", "normal") for r in successful_results]
        regime = max(set(regimes), key=regimes.count)
        save_market_regime(regime)
    
    # Summary
    buy_count = sum(1 for r in results if r.get("decision") == "BUY")
    sell_count = sum(1 for r in results if r.get("decision") == "SELL")
    hold_count = sum(1 for r in results if r.get("decision") == "HOLD")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total holdings analyzed: {len(results)}")
    print(f"  BUY:  {buy_count}")
    print(f"  HOLD: {hold_count}")
    print(f"  SELL: {sell_count}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
