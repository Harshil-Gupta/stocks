"""
Portfolio Import Utility

Handles importing holdings from a configurable directory.
All CSV files in the directory are imported.

Usage:
    # Auto-detect from config (HOLDINGS_DIR env var)
    python -m data.import_portfolio
    
    # Force use specific directory
    python -m data.import_portfolio C:/path/to/holdings/

The directory should contain CSV files with holdings data.
Each CSV will be imported and merged into the portfolio.
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


def get_holdings_dir() -> str:
    """Get holdings directory from config."""
    return config.holdings_dir


def get_all_holdings_files() -> List[str]:
    """Get all CSV files from the holdings directory."""
    holdings_dir = get_holdings_dir()
    
    if not os.path.exists(holdings_dir):
        raise FileNotFoundError(f"Holdings directory not found: {holdings_dir}")
    
    csv_files = []
    for f in os.listdir(holdings_dir):
        if f.endswith('.csv'):
            csv_files.append(os.path.join(holdings_dir, f))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {holdings_dir}")
    
    return sorted(csv_files)


def import_holdings(csv_dir: Optional[str] = None, output_dir: str = "data") -> Dict[str, Any]:
    """
    Import holdings from all CSV files in the configured directory.
    
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
    
    # Determine which directory to use
    if csv_dir is None:
        csv_dir = get_holdings_dir()
        print(f"Using holdings directory: {csv_dir}")
    
    csv_files = []
    
    if os.path.isfile(csv_dir):
        # Single file provided
        csv_files = [csv_dir]
    elif os.path.isdir(csv_dir):
        # Directory provided - get all CSV files
        for f in os.listdir(csv_dir):
            if f.endswith('.csv'):
                csv_files.append(os.path.join(csv_dir, f))
        csv_files = sorted(csv_files)
    else:
        raise FileNotFoundError(f"Holdings path not found: {csv_dir}")
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {csv_dir}")
    
    print(f"Found {len(csv_files)} CSV file(s)")
    
    portfolio = []
    trades = []
    
    # Track symbols to avoid duplicates (use latest value)
    symbol_data = {}
    
    for csv_path in csv_files:
        print(f"  Processing: {os.path.basename(csv_path)}")
        
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
                    
                    # Store (will use latest if duplicate)
                    symbol_data[symbol] = {
                        "Symbol": symbol,
                        "Qty": int(qty_val),
                        "Entry": avg_cost_val,
                        "LTP": ltp_val,
                        "P&L": pnl,
                        "P&L%": net_chg
                    }
                    
                except (ValueError, KeyError) as e:
                    print(f"    Warning: Skipping row for {symbol}: {e}")
                    continue
    
    # Convert to list
    for symbol, data in symbol_data.items():
        portfolio.append(data)
        
        # Generate trade record
        trades.append({
            "Time": datetime.now().strftime("%Y-%m-%d 09:15:00"),
            "Symbol": data["Symbol"],
            "Action": "BUY",
            "Qty": data["Qty"],
            "Price": data["Entry"]
        })
    
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
        "source_dir": csv_dir,
        "files_processed": len(csv_files)
    }


def check_holdings_exists() -> bool:
    """Check if holdings directory exists and contains CSV files."""
    holdings_dir = get_holdings_dir()
    
    if not os.path.exists(holdings_dir):
        return False
    
    # Check for any CSV files
    for f in os.listdir(holdings_dir):
        if f.endswith('.csv'):
            return True
    
    return False


def get_holdings_symbols() -> List[str]:
    """Get list of symbols from holdings."""
    holdings_dir = get_holdings_dir()
    
    if not os.path.exists(holdings_dir):
        return []
    
    symbols = set()
    
    for f in os.listdir(holdings_dir):
        if f.endswith('.csv'):
            csv_path = os.path.join(holdings_dir, f)
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    symbol = row.get('Instrument', '').strip()
                    if symbol:
                        symbols.add(symbol)
    
    return sorted(list(symbols))


def main():
    csv_dir = None
    
    # If path provided as argument, use it
    if len(sys.argv) >= 2:
        csv_dir = sys.argv[1]
    
    print(f"Importing holdings...")
    result = import_holdings(csv_dir)
    
    print(f"\nImported from: {result['source_dir']}")
    print(f"  Files processed: {result['files_processed']}")
    print(f"  - {len(result['portfolio'])} positions")
    print(f"  - {len(result['trades'])} trades")


if __name__ == "__main__":
    main()
