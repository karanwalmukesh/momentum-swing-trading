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
        return {
            "available_cash": 500000.0,
            "active_positions": [],
            "historical_trades": [],
            "total_equity": 500000.0,
            "last_update": datetime.now().isoformat()
        }
    
    def save_state(self) -> None:
        self.state["last_update"] = datetime.now().isoformat()
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"State saved successfully to {self.state_file_path}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    def get_available_cash(self) -> float:
        return self.state["available_cash"]
    
    def update_cash(self, amount: float, operation: str = "debit") -> None:
        if operation == "debit":
            if amount > self.state["available_cash"]:
                raise ValueError(f"Insufficient cash: {self.state['available_cash']} < {amount}")
            self.state["available_cash"] -= amount
        elif operation == "credit":
            self.state["available_cash"] += amount
        else:
            raise ValueError("Operation must be 'debit' or 'credit'")
    
    def get_active_positions(self) -> List[Dict]:
        return self.state["active_positions"]
    
    def add_position(self, position: Dict) -> None:
        self.state["active_positions"].append(position)
        self.update_total_equity()
    
    def remove_position(self, ticker: str) -> Optional[Dict]:
        for i, pos in enumerate(self.state["active_positions"]):
            if pos["ticker"] == ticker:
                removed = self.state["active_positions"].pop(i)
                self.update_total_equity()
                return removed
        return None
    
    def update_position(self, ticker: str, updates: Dict) -> bool:
        for pos in self.state["active_positions"]:
            if pos["ticker"] == ticker:
                pos.update(updates)
                self.update_total_equity()
                return True
        return False
    
    def add_historical_trade(self, trade: Dict) -> None:
        self.state["historical_trades"].append(trade)
    
    def update_total_equity(self) -> float:
        total_equity = self.state["available_cash"]
        for pos in self.state["active_positions"]:
            total_equity += pos.get("allocated_capital", 0)
        self.state["total_equity"] = total_equity
        return total_equity
    
    def get_total_equity(self) -> float:
        return self.state["total_equity"]
    
    def get_sector_count(self) -> Dict[str, int]:
        sector_counts = {}
        for pos in self.state["active_positions"]:
            sector = pos.get("sector", "Unknown")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        return sector_counts
    
    def get_holding_days(self, entry_date: str) -> int:
        entry = datetime.fromisoformat(entry_date).date()
        today = date.today()
        return (today - entry).days

    def get_historical_trades(self) -> List[Dict]:
        return self.state["historical_trades"]
