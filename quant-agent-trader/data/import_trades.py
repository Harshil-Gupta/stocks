"""
Trade History Import Utility

Usage:
    # Auto-detect from config (TRADES_CSV_PATH env var)
    python -m data.import_trades
    
    # Or specify custom path
    python -m data.import_trades "C:/custom/path/trades.csv"
    
This will generate data/trades.json from your broker trade history export.
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


def get_trades_path() -> str:
    """Get trades CSV path from config."""
    return config.trades_csv_path


def import_trades(csv_path: Optional[str] = None, output_dir: str = "data") -> Dict[str, Any]:
    """
    Import trade history from broker CSV export.
    
    Expected columns (Zerodha/Upstox format):
    - Order Date / Date
    - Trade Date
    - Symbol / Instrument
    - Transaction Type / Trade Type (BUY/SELL)
    - Quantity / Qty.
    - Price / Average Price
    - Order Type
    - Product (CNC/MIS/NRML)
    """
    
    # Use provided path or get from config
    if csv_path is None:
        csv_path = get_trades_path()
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Trades CSV not found: {csv_path}")
    
    trades = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Try different column names for different broker formats
            symbol = (row.get('Symbol') or 
                     row.get('Instrument') or 
                     row.get('Trading Symbol') or 
                     '').strip()
            
            trade_date = (row.get('Trade Date') or 
                         row.get('Order Date') or 
                         row.get('Date') or 
                         '').strip()
            
            action = (row.get('Transaction Type') or 
                     row.get('Trade Type') or 
                     row.get('Type') or 
                     '').strip().upper()
            
            qty = (row.get('Quantity') or 
                  row.get('Qty.') or 
                  row.get('Qty') or 
                  '').strip()
            
            price = (row.get('Price') or 
                    row.get('Average Price') or 
                    row.get('Avg. Price') or 
                    row.get('Trade Price') or 
                    '').strip()
            
            # Skip empty rows
            if not symbol or not qty:
                continue
            
            # Normalize action
            if 'BUY' in action:
                action = 'BUY'
            elif 'SELL' in action:
                action = 'SELL'
            else:
                continue  # Skip unknown types
            
            try:
                qty_val = float(qty.replace(',', ''))
                price_val = float(price.replace(',', ''))
                
                # Parse date - try multiple formats
                trade_time = trade_date
                if trade_date:
                    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%d-%b-%Y']:
                        try:
                            dt = datetime.strptime(trade_date, fmt)
                            trade_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            continue
                
                trades.append({
                    "Time": trade_time,
                    "Symbol": symbol,
                    "Action": action,
                    "Qty": int(qty_val),
                    "Price": price_val
                })
                
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row for {symbol}: {e}")
                continue
    
    # Sort by date descending (newest first)
    trades.sort(key=lambda x: x['Time'], reverse=True)
    
    # Write trades.json
    trades_path = os.path.join(output_dir, "trades.json")
    with open(trades_path, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"Created: {trades_path}")
    
    return {
        "trades": trades
    }


def check_trades_exists() -> bool:
    """Check if trades CSV exists at configured path."""
    return os.path.exists(get_trades_path())


def main():
    csv_path = None
    
    # If path provided as argument, use it
    if len(sys.argv) >= 2:
        csv_path = sys.argv[1]
    else:
        # Use config path
        csv_path = get_trades_path()
        print(f"Using trades path from config: {csv_path}")
    
    print(f"Importing trades from: {csv_path}")
    result = import_trades(csv_path)
    
    print(f"\nImported:")
    print(f"  - {len(result['trades'])} trades")


if __name__ == "__main__":
    main()
