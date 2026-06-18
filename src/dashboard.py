import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardGenerator:
    def __init__(self, state_file_path: str = "data/portfolio_state.json"):
        self.state_file_path = state_file_path
        self.output_file = "README.md"
    
    def load_state(self) -> Dict[str, Any]:
        try:
            with open(self.state_file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state for dashboard: {e}")
            return {}
    
    def calculate_metrics(self, state: Dict) -> Dict:
        metrics = {
            'total_equity': state.get('total_equity', 0),
            'available_cash': state.get('available_cash', 0),
            'active_positions': len(state.get('active_positions', [])),
            'historical_trades': len(state.get('historical_trades', [])),
            'drawdown': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
        
        historical = state.get('historical_trades', [])
        if historical:
            total_pnl = sum(trade.get('pnl_amount', 0) for trade in historical)
            metrics['total_pnl'] = total_pnl
            
            winning_trades = [t for t in historical if t.get('pnl_amount', 0) > 0]
            metrics['win_rate'] = (len(winning_trades) / len(historical)) * 100 if historical else 0
            
            cumulative_pnl = 0
            max_pnl = 0
            max_drawdown = 0
            for trade in historical:
                cumulative_pnl += trade.get('pnl_amount', 0)
                if cumulative_pnl > max_pnl:
                    max_pnl = cumulative_pnl
                drawdown = max_pnl - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            metrics['drawdown'] = max_drawdown
        
        return metrics
    
    def generate_markdown(self) -> str:
        state = self.load_state()
        if not state:
            return "# Portfolio Dashboard\n\nNo data available."
        
        metrics = self.calculate_metrics(state)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        
        markdown = f"""# 📈 Momentum Swing Trading Dashboard

**Last Updated:** {timestamp}

---

## 📊 Portfolio Summary

| Metric | Value |
|--------|-------|
| **Total Equity** | ₹{metrics['total_equity']:,.2f} |
| **Available Cash** | ₹{metrics['available_cash']:,.2f} |
| **Active Positions** | {metrics['active_positions']} / 10 |
| **Total Trades** | {metrics['historical_trades']} |
| **Total P&L** | ₹{metrics['total_pnl']:,.2f} |
| **Win Rate** | {metrics['win_rate']:.1f}% |
| **Max Drawdown** | ₹{metrics['drawdown']:,.2f} |

---

## 🟢 Active Positions ({metrics['active_positions']})

"""
        
        active = state.get('active_positions', [])
        if active:
            markdown += "| Ticker | Sector | Entry Date | Entry Price | Allocated | Quantity | Days Held |\n"
            markdown += "|--------|--------|------------|-------------|-----------|----------|-----------|\n"
            
            for pos in active:
                entry_date = pos.get('entry_date', '')[:10]
                holding_days = pos.get('holding_days', 0)
                markdown += f"| {pos['ticker']} | {pos['sector']} | {entry_date} | ₹{pos['entry_price']:.2f} | ₹{pos['allocated_capital']:,.2f} | {pos['quantity']} | {holding_days} |\n"
        else:
            markdown += "No active positions.\n"
        
        markdown += f"""

---

## 📜 Recent Trades ({metrics['historical_trades']})

"""
        
        historical = state.get('historical_trades', [])
        if historical:
            recent_trades = historical[-10:]
            markdown += "| Ticker | Entry Date | Exit Date | Entry | Exit | P&L | P&L % | Hold Days | Reason |\n"
            markdown += "|--------|------------|-----------|-------|------|-----|-------|-----------|--------|\n"
            
            for trade in reversed(recent_trades):
                pnl = trade.get('pnl_amount', 0)
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                entry_date = trade.get('entry_date', '')[:10]
                exit_date = trade.get('exit_date', '')[:10]
                markdown += f"| {trade['ticker']} | {entry_date} | {exit_date} | ₹{trade['entry_price']:.2f} | ₹{trade['exit_price']:.2f} | {pnl_color}₹{pnl:,.2f} | {trade['pnl_pct']:.2f}% | {trade['holding_days']} | {trade['exit_reason']} |\n"
        else:
            markdown += "No historical trades yet.\n"
        
        markdown += """

---

## ⚙️ System Parameters

- **Initial Capital:** ₹500,000
- **Max Positions:** 10
- **Max Per Sector:** 3
- **Allocation:** 10% per position
- **Entry Filter:** Nifty 50 > 20-day SMA
- **Exit Rules:** Hard Stop (-5%), Breakeven, Velocity (15-day <5%), Trailing (2.5x ATR)
- **Friction:** 0.3% round-trip

---

*Automated dashboard generated by Momentum Swing Trading System*
"""
        
        return markdown
    
    def generate_dashboard(self) -> bool:
        try:
            markdown = self.generate_markdown()
            with open(self.output_file, 'w') as f:
                f.write(markdown)
            logger.info(f"Dashboard generated: {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return False
    
    def generate_json_dashboard(self) -> Dict:
        state = self.load_state()
        metrics = self.calculate_metrics(state)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'active_positions': state.get('active_positions', []),
            'recent_trades': state.get('historical_trades', [])[-10:]
        }
