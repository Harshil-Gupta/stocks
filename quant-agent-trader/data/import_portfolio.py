"""
Portfolio Import Utility

Handles both static holdings CSV and daily holdings with format YYYY-MM-DD.csv

Usage:
    # Auto-detect latest daily holdings or fall back to static
    python -m data.import_portfolio
    
    # Force use specific file
    python -m data.import_portfolio C:/path/to/holdings.csv
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PortfolioConfig

config = PortfolioConfig()


def get_holdings_path() -> str:
    """Get holdings CSV path from config."""
    return config.holdings_csv_path


def get_latest_daily_holdings() -> Optional[str]:
    """
    Find the latest daily holdings file in data/daily_holdings/.
    Looks for files matching YYYY-MM-DD.csv format.
    """
    daily_dir = config.daily_holdings_dir
    
    if not os.path.exists(daily_dir):
        return None
    
    csv_files = []
    for f in os.listdir(daily_dir):
        if f.endswith('.csv'):
            # Check if it matches YYYY-MM-DD.csv format
            try:
                date_str = f.replace('.csv', '')
                datetime.strptime(date_str, '%Y-%m-%d')
                csv_files.append((f, date_str))
            except ValueError:
                continue
    
    if not csv_files:
        return None
    
    # Sort by date descending (newest first)
    csv_files.sort(key=lambda x: x[1], reverse=True)
    latest_file = csv_files[0][0]
    
    return os.path.join(daily_dir, latest_file)


def import_holdings(csv_path: Optional[str] = None, output_dir: str = "data") -> Dict[str, Any]:
    """
    Import holdings from broker CSV export.
    
    Expected columns:
    - Instrument (Symbol)
    - Qty. (Quantity)
    - Avg. cost (Entry price)
    - LTP (Current price)
    - Invested
    - Cur. val (Current value)
    - P&L
    - Net chg. (Net change %)
    - Day chg. (Day change %)
    """
    
    # Determine which file to use
    if csv_path is None:
        # Try daily holdings first
        daily_path = get_latest_daily_holdings()
        if daily_path:
            csv_path = daily_path
            print(f"Using daily holdings: {csv_path}")
        else:
            csv_path = get_holdings_path()
            print(f"Using static holdings: {csv_path}")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Holdings CSV not found: {csv_path}")
    
    portfolio = []
    trades = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            symbol = row.get('Instrument', '').strip()
            qty = row.get('Qty.', '').strip()
            avg_cost = row.get('Avg. cost', '').strip()
            ltp = row.get('LTP', '').strip()
            pnl = row.get('P&L', '').strip()
            net_chg = row.get('Net chg.', '').strip()
            
            # Skip empty rows
            if not symbol or not qty or qty == '0':
                continue
            
            try:
                qty_val = float(qty.replace(',', ''))
                avg_cost_val = float(avg_cost.replace(',', ''))
                ltp_val = float(ltp.replace(',', ''))
                
                # Format P&L string
                pnl_val = 0.0
                if pnl:
                    pnl_val = float(pnl.replace(',', ''))
                
                pnl_str = f"Rs.{abs(pnl_val):,.0f}" if pnl_val >= 0 else f"Rs.-{abs(pnl_val):,.0f}"
                pnl_pct_str = f"+{net_chg}%" if net_chg.startswith('-') == False else f"{net_chg}%"
                
                # Add to portfolio
                portfolio.append({
                    "Symbol": symbol,
                    "Qty": int(qty_val),
                    "Entry": avg_cost_val,
                    "LTP": ltp_val,
                    "P&L": pnl_str,
                    "P&L%": pnl_pct_str
                })
                
                # Generate a trade record (entry)
                trades.append({
                    "Time": datetime.now().strftime("%Y-%m-%d 09:15:00"),
                    "Symbol": symbol,
                    "Action": "BUY",
                    "Qty": int(qty_val),
                    "Price": avg_cost_val
                })
                
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row for {symbol}: {e}")
                continue
    
    # Write portfolio.json
    portfolio_path = os.path.join(output_dir, "portfolio.json")
    with open(portfolio_path, 'w') as f:
        json.dump(portfolio, f, indent=2)
    print(f"Created: {portfolio_path}")
    
    # Write trades.json
    trades_path = os.path.join(output_dir, "trades.json")
    with open(trades_path, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"Created: {trades_path}")
    
    return {
        "portfolio": portfolio,
        "trades": trades,
        "source": csv_path
    }


def check_holdings_exists() -> bool:
    """Check if holdings CSV exists at configured path or in daily directory."""
    # Check daily holdings first
    if get_latest_daily_holdings():
        return True
    
    # Fall back to static holdings
    return os.path.exists(get_holdings_path())


def get_holdings_symbols() -> List[str]:
    """Get list of symbols from current holdings."""
    csv_path = get_latest_daily_holdings() or get_holdings_path()
    
    if not os.path.exists(csv_path):
        return []
    
    symbols = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row.get('Instrument', '').strip()
            if symbol:
                symbols.append(symbol)
    
    return symbols


def main():
    csv_path = None
    
    # If path provided as argument, use it
    if len(sys.argv) >= 2:
        csv_path = sys.argv[1]
    
    print(f"Importing holdings...")
    result = import_holdings(csv_path)
    
    print(f"\nImported from: {result['source']}")
    print(f"  - {len(result['portfolio'])} positions")
    print(f"  - {len(result['trades'])} trades")


if __name__ == "__main__":
    main()
