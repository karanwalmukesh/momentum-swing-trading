import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StateEngine:
    def __init__(self, state_file_path: str = "data/portfolio_state.json"):
        self.state_file_path = state_file_path
        self.state = self._initialize_state()
        
    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize or load existing state from JSON file."""
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded existing state from {self.state_file_path}")
                return state
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Error loading state file: {e}. Creating new state.")
                return self._create_default_state()
        else:
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            return self._create_default_state()
    
    def _create_default_state(self) -> Dict[str, Any]:
        """Create default initial state."""
        return {
            "available_cash": 500000.0,
            "total_equity": 500000.0,
            "active_positions": [],
            "historical_trades": [],
            "system_signals_log": [],
            "user_execution_log": [],
            "last_update": datetime.now().isoformat()
        }
    
    def save_state(self) -> None:
        """Persist current state to JSON file."""
        self.state["last_update"] = datetime.now().isoformat()
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"State saved successfully to {self.state_file_path}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    def get_available_cash(self) -> float:
        """Get current available cash balance."""
        return self.state["available_cash"]
    
    def update_cash(self, amount: float, operation: str = "debit") -> None:
        """Update cash balance (debit for purchases, credit for sales)."""
        if operation == "debit":
            if amount > self.state["available_cash"]:
                raise ValueError(f"Insufficient cash: {self.state['available_cash']} < {amount}")
            self.state["available_cash"] -= amount
        elif operation == "credit":
            self.state["available_cash"] += amount
        else:
            raise ValueError("Operation must be 'debit' or 'credit'")
        self.update_total_equity()
    
    def get_active_positions(self) -> List[Dict]:
        """Get list of active positions."""
        return self.state["active_positions"]
    
    def add_position(self, position: Dict) -> None:
        """Add a new position to active positions."""
        self.state["active_positions"].append(position)
        self.update_total_equity()
    
    def remove_position(self, ticker: str) -> Optional[Dict]:
        """Remove a position and return it for historical tracking."""
        for i, pos in enumerate(self.state["active_positions"]):
            if pos["ticker"] == ticker:
                removed = self.state["active_positions"].pop(i)
                self.update_total_equity()
                return removed
        return None
    
    def update_position(self, ticker: str, updates: Dict) -> bool:
        """Update specific fields of an active position."""
        for pos in self.state["active_positions"]:
            if pos["ticker"] == ticker:
                pos.update(updates)
                self.update_total_equity()
                return True
        return False
    
    def add_historical_trade(self, trade: Dict) -> None:
        """Add a closed trade to historical trades."""
        self.state["historical_trades"].append(trade)
    
    def add_system_signal(self, signal: Dict) -> None:
        """Log a system-generated signal."""
        signal["timestamp"] = datetime.now().isoformat()
        self.state["system_signals_log"].append(signal)
    
    def add_user_execution(self, execution: Dict) -> None:
        """Log a user-executed trade."""
        execution["timestamp"] = datetime.now().isoformat()
        self.state["user_execution_log"].append(execution)
    
    def update_total_equity(self) -> float:
        """Calculate and update total equity."""
        total_equity = self.state["available_cash"]
        for pos in self.state["active_positions"]:
            current_value = pos.get("current_value", pos.get("allocated_capital", 0))
            total_equity += current_value
        self.state["total_equity"] = total_equity
        return total_equity
    
    def get_total_equity(self) -> float:
        """Get current total equity."""
        return self.state["total_equity"]
    
    def get_sector_count(self) -> Dict[str, int]:
        """Get count of active positions per sector."""
        sector_counts = {}
        for pos in self.state["active_positions"]:
            sector = pos.get("heatmap_sector", "Unknown")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        return sector_counts
    
    def get_holding_days(self, entry_date: str) -> int:
        """Calculate holding days from entry date."""
        entry = datetime.fromisoformat(entry_date).date()
        today = date.today()
        return (today - entry).days
    
    def get_historical_trades(self) -> List[Dict]:
        """Get all historical trades."""
        return self.state["historical_trades"]
    
    def get_system_signals(self) -> List[Dict]:
        """Get all system signals."""
        return self.state["system_signals_log"]
    
    def get_user_executions(self) -> List[Dict]:
        """Get all user executions."""
        return self.state["user_execution_log"]
    
    def execute_signal(self, ticker: str, action: str, executed_price: float, 
                      shares: int, sector: str, signal_reason: str) -> bool:
        """
        Manually execute or skip a signal via operator intervention.
        Shifts cash balances and moves positions into historical_trades dynamically.
        """
        try:
            # Find the signal in system_signals_log
            signal_found = False
            for signal in self.state["system_signals_log"]:
                if (signal.get("ticker") == ticker and 
                    signal.get("action") == action and 
                    signal.get("status") == "PENDING"):
                    signal_found = True
                    signal["status"] = "EXECUTED"
                    signal["executed_price"] = executed_price
                    signal["executed_shares"] = shares
                    signal["executed_at"] = datetime.now().isoformat()
                    break
            
            if not signal_found:
                logger.warning(f"No pending signal found for {ticker} with action {action}")
                return False
            
            if action.upper() == "BUY":
                # Execute buy
                allocated_capital = executed_price * shares
                if allocated_capital > self.get_available_cash():
                    logger.error(f"Insufficient cash for {ticker}: {allocated_capital} > {self.get_available_cash()}")
                    return False
                
                position = {
                    "ticker": ticker,
                    "heatmap_sector": sector,
                    "entry_date": datetime.now().isoformat(),
                    "entry_price": executed_price,
                    "allocated_capital": allocated_capital,
                    "quantity": shares,
                    "highest_recorded_close": executed_price,
                    "holding_days": 0,
                    "current_value": allocated_capital
                }
                
                self.update_cash(allocated_capital, operation="debit")
                self.add_position(position)
                
                # Log user execution
                self.add_user_execution({
                    "ticker": ticker,
                    "action": "BUY",
                    "price": executed_price,
                    "shares": shares,
                    "sector": sector,
                    "reason": signal_reason
                })
                
                logger.info(f"USER EXECUTED BUY: {ticker} @ {executed_price:.2f} x {shares} = ₹{allocated_capital:,.2f}")
                return True
                
            elif action.upper() == "SELL":
                # Find and remove active position
                position = self.remove_position(ticker)
                if not position:
                    logger.warning(f"Position {ticker} not found in active positions")
                    return False
                
                # Calculate P&L
                pnl_amount = (executed_price - position["entry_price"]) * shares
                pnl_pct = ((executed_price - position["entry_price"]) / position["entry_price"]) * 100
                
                # Credit cash
                sale_proceeds = executed_price * shares
                self.update_cash(sale_proceeds, operation="credit")
                
                # Create historical trade
                historical_trade = {
                    "ticker": ticker,
                    "sector": sector,
                    "entry_date": position["entry_date"],
                    "exit_date": datetime.now().isoformat(),
                    "entry_price": position["entry_price"],
                    "exit_price": executed_price,
                    "quantity": shares,
                    "pnl_amount": pnl_amount,
                    "pnl_pct": pnl_pct,
                    "holding_days": position.get("holding_days", 0),
                    "exit_reason": signal_reason
                }
                self.add_historical_trade(historical_trade)
                
                # Log user execution
                self.add_user_execution({
                    "ticker": ticker,
                    "action": "SELL",
                    "price": executed_price,
                    "shares": shares,
                    "sector": sector,
                    "reason": signal_reason,
                    "pnl_amount": pnl_amount,
                    "pnl_pct": pnl_pct
                })
                
                logger.info(f"USER EXECUTED SELL: {ticker} @ {executed_price:.2f} x {shares} | P&L: ₹{pnl_amount:,.2f} ({pnl_pct:.2f}%)")
                return True
            
            else:
                logger.error(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal for {ticker}: {e}")
            return False
    
    def skip_signal(self, ticker: str, action: str) -> bool:
        """Mark a signal as skipped without execution."""
        for signal in self.state["system_signals_log"]:
            if (signal.get("ticker") == ticker and 
                signal.get("action") == action and 
                signal.get("status") == "PENDING"):
                signal["status"] = "SKIPPED"
                signal["skipped_at"] = datetime.now().isoformat()
                self.save_state()
                return True
        return False
