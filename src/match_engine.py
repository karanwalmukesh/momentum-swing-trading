import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from state_engine import StateEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchEngine:
    def __init__(self, state_engine: StateEngine):
        self.state_engine = state_engine
        self.target_universe = self._get_target_universe()
        self.friction_coefficient = 0.003
        self.max_positions = 10
        self.max_per_sector = 3
        self.initial_capital = 500000
        self.entry_allocation_pct = 0.10
        
    def _get_target_universe(self) -> List[Dict]:
        return [
            {"ticker": "RELIANCE.NS", "sector": "Energy"},
            {"ticker": "TCS.NS", "sector": "Technology"},
            {"ticker": "HDFCBANK.NS", "sector": "Financial"},
            {"ticker": "INFY.NS", "sector": "Technology"},
            {"ticker": "ICICIBANK.NS", "sector": "Financial"},
            {"ticker": "HINDUNILVR.NS", "sector": "Consumer"},
            {"ticker": "SBIN.NS", "sector": "Financial"},
            {"ticker": "BHARTIARTL.NS", "sector": "Telecom"},
            {"ticker": "ITC.NS", "sector": "Consumer"},
            {"ticker": "LT.NS", "sector": "Construction"},
            {"ticker": "KOTAKBANK.NS", "sector": "Financial"},
            {"ticker": "BAJFINANCE.NS", "sector": "Financial"},
            {"ticker": "WIPRO.NS", "sector": "Technology"},
            {"ticker": "ASIANPAINT.NS", "sector": "Consumer"},
            {"ticker": "HCLTECH.NS", "sector": "Technology"},
            {"ticker": "SUNPHARMA.NS", "sector": "Healthcare"},
            {"ticker": "MARUTI.NS", "sector": "Automotive"},
            {"ticker": "ULTRACEMCO.NS", "sector": "Construction"},
            {"ticker": "TITAN.NS", "sector": "Consumer"},
            {"ticker": "TATAMOTORS.NS", "sector": "Automotive"},
            {"ticker": "POWERGRID.NS", "sector": "Energy"},
            {"ticker": "NTPC.NS", "sector": "Energy"},
            {"ticker": "M&M.NS", "sector": "Automotive"},
            {"ticker": "NESTLEIND.NS", "sector": "Consumer"},
            {"ticker": "ADANIPORTS.NS", "sector": "Infrastructure"},
            {"ticker": "HDFC.NS", "sector": "Financial"},
            {"ticker": "JSWSTEEL.NS", "sector": "Metals"},
            {"ticker": "TECHM.NS", "sector": "Technology"},
            {"ticker": "ONGC.NS", "sector": "Energy"},
            {"ticker": "GRASIM.NS", "sector": "Construction"},
            {"ticker": "HDFCLIFE.NS", "sector": "Financial"},
            {"ticker": "BRITANNIA.NS", "sector": "Consumer"},
            {"ticker": "UPL.NS", "sector": "Chemicals"},
            {"ticker": "EICHERMOT.NS", "sector": "Automotive"},
            {"ticker": "TATASTEEL.NS", "sector": "Metals"},
            {"ticker": "BAJAJFINSV.NS", "sector": "Financial"},
            {"ticker": "COALINDIA.NS", "sector": "Energy"},
            {"ticker": "BPCL.NS", "sector": "Energy"},
            {"ticker": "IOC.NS", "sector": "Energy"},
            {"ticker": "SBILIFE.NS", "sector": "Financial"},
            {"ticker": "HINDALCO.NS", "sector": "Metals"},
            {"ticker": "SHREECEM.NS", "sector": "Construction"},
            {"ticker": "DRREDDY.NS", "sector": "Healthcare"},
            {"ticker": "CIPLA.NS", "sector": "Healthcare"},
            {"ticker": "DIVISLAB.NS", "sector": "Healthcare"},
            {"ticker": "APOLLOHOSP.NS", "sector": "Healthcare"},
            {"ticker": "HEROMOTOCO.NS", "sector": "Automotive"},
            {"ticker": "BAJAJ-AUTO.NS", "sector": "Automotive"},
            {"ticker": "ADANIENT.NS", "sector": "Infrastructure"},
            {"ticker": "INDUSINDBK.NS", "sector": "Financial"}
        ]
    
    def check_nifty_regime(self) -> bool:
        try:
            nifty = yf.download("^NSEI", period="1mo", interval="1d", progress=False)
            if len(nifty) < 20:
                logger.warning("Insufficient Nifty data for 20-day SMA calculation")
                return False
            
            nifty['SMA20'] = nifty['Close'].rolling(window=20).mean()
            current_close = nifty['Close'].iloc[-1]
            current_sma = nifty['SMA20'].iloc[-1]
            
            is_above = current_close > current_sma
            logger.info(f"Nifty Regime: Close={current_close:.2f}, SMA20={current_sma:.2f}, Above={is_above}")
            return is_above
        except Exception as e:
            logger.error(f"Error checking Nifty regime: {e}")
            return False
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        prices = {}
        try:
            data = yf.download(tickers, period="1d", interval="1d", progress=False)
            if not data.empty and 'Close' in data.columns:
                for ticker in tickers:
                    if ticker in data['Close'].columns and not pd.isna(data['Close'][ticker].iloc[-1]):
                        prices[ticker] = float(data['Close'][ticker].iloc[-1])
                    else:
                        logger.warning(f"No price data available for {ticker}")
            return prices
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}
    
    def calculate_technical_indicators(self, ticker: str, period: str = "3mo") -> Dict:
        try:
            data = yf.download(ticker, period=period, interval="1d", progress=False)
            if len(data) < 20:
                return {}
            
            data['SMA20'] = data['Close'].rolling(window=20).mean()
            data['SMA50'] = data['Close'].rolling(window=50).mean()
            
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            velocity_15d = (data['Close'].iloc[-1] / data['Close'].iloc[-15] - 1) * 100 if len(data) >= 15 else 0
            
            current_close = data['Close'].iloc[-1]
            current_sma20 = data['SMA20'].iloc[-1]
            current_sma50 = data['SMA50'].iloc[-1]
            
            breakout = current_close > current_sma20 and current_sma20 > current_sma50
            
            return {
                'current_price': current_close,
                'sma20': current_sma20,
                'sma50': current_sma50,
                'atr': atr,
                'velocity_15d': velocity_15d,
                'breakout': breakout,
                'highest_close': data['Close'].max()
            }
        except Exception as e:
            logger.error(f"Error calculating indicators for {ticker}: {e}")
            return {}
    
    def scan_entry_signals(self) -> List[Dict]:
        if not self.check_nifty_regime():
            logger.info("Nifty regime not favorable for entries")
            return []
        
        active_positions = self.state_engine.get_active_positions()
        if len(active_positions) >= self.max_positions:
            logger.info(f"Max positions reached: {len(active_positions)}/{self.max_positions}")
            return []
        
        sector_counts = self.state_engine.get_sector_count()
        available_slots = self.max_positions - len(active_positions)
        
        entry_signals = []
        current_equity = self.state_engine.get_total_equity()
        allocation_per_position = current_equity * self.entry_allocation_pct
        
        active_tickers = [pos['ticker'] for pos in active_positions]
        
        for stock in self.target_universe:
            ticker = stock['ticker']
            sector = stock['sector']
            
            if ticker in active_tickers:
                continue
            
            if sector_counts.get(sector, 0) >= self.max_per_sector:
                continue
            
            indicators = self.calculate_technical_indicators(ticker)
            if not indicators or not indicators.get('breakout', False):
                continue
            
            current_price = indicators['current_price']
            quantity = int(allocation_per_position / current_price)
            allocated_capital = quantity * current_price
            
            if allocated_capital > self.state_engine.get_available_cash():
                continue
            
            entry_signal = {
                'ticker': ticker,
                'sector': sector,
                'action': 'BUY',
                'price': current_price,
                'quantity': quantity,
                'allocated_capital': allocated_capital,
                'reason': 'New Breakout Setup',
                'sma20': indicators['sma20'],
                'sma50': indicators['sma50']
            }
            
            entry_signals.append(entry_signal)
            
            if len(entry_signals) >= available_slots:
                break
        
        return entry_signals
    
    def scan_exit_signals(self) -> List[Dict]:
        exit_signals = []
        active_positions = self.state_engine.get_active_positions()
        
        if not active_positions:
            return exit_signals
        
        tickers = [pos['ticker'] for pos in active_positions]
        current_prices = self.get_current_prices(tickers)
        
        for position in active_positions:
            ticker = position['ticker']
            current_price = current_prices.get(ticker)
            
            if not current_price:
                continue
            
            entry_price = position['entry_price']
            highest_close = position.get('highest_recorded_close', entry_price)
            holding_days = position.get('holding_days', 0) + 1
            
            if current_price > highest_close:
                highest_close = current_price
                self.state_engine.update_position(ticker, {
                    'highest_recorded_close': highest_close,
                    'holding_days': holding_days
                })
            else:
                self.state_engine.update_position(ticker, {'holding_days': holding_days})
            
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_amount = (current_price - entry_price) * position['quantity']
            
            indicators = self.calculate_technical_indicators(ticker, period="1mo")
            atr = indicators.get('atr', 0) if indicators else 0
            
            exit_reason = None
            
            if pnl_pct <= -5.0:
                exit_reason = 'Hard Stop Hit (-5%)'
            elif pnl_pct >= 0.5 and pnl_pct <= 1.0:
                if current_price <= entry_price * (1 + self.friction_coefficient):
                    exit_reason = 'Breakeven Stop Hit'
            elif holding_days >= 15:
                if indicators and indicators['velocity_15d'] < 5.0:
                    exit_reason = f'Velocity Exit (15-day gain: {indicators["velocity_15d"]:.2f}%)'
            elif pnl_pct >= 15.0 and atr > 0:
                trailing_stop = highest_close - (2.5 * atr)
                if current_price <= trailing_stop:
                    exit_reason = f'Trailing Stop Hit (Stop: {trailing_stop:.2f})'
            
            if exit_reason:
                exit_signal = {
                    'ticker': ticker,
                    'sector': position['sector'],
                    'action': 'SELL',
                    'price': current_price,
                    'quantity': position['quantity'],
                    'reason': exit_reason,
                    'entry_date': position['entry_date'],
                    'entry_price': entry_price,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'holding_days': holding_days,
                    'position_data': position
                }
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def scan_with_statistics(self) -> Dict[str, Any]:
        """Scan for signals with detailed statistics."""
        stats = {
            'total_scanned': 0,
            'nifty_regime': False,
            'active_positions': 0,
            'sector_limits_hit': 0,
            'breakout_found': 0,
            'technical_fail': 0,
            'already_held': 0,
            'cash_insufficient': 0,
            'entry_signals': [],
            'exit_signals': [],
            'total_equity': self.state_engine.get_total_equity()
        }
        
        # Check Nifty regime first
        stats['nifty_regime'] = self.check_nifty_regime()
        if not stats['nifty_regime']:
            logger.info("❌ Nifty regime not favorable - skipping scan")
            return stats
        
        active_positions = self.state_engine.get_active_positions()
        stats['active_positions'] = len(active_positions)
        
        if len(active_positions) >= self.max_positions:
            logger.info(f"❌ Max positions reached: {len(active_positions)}/{self.max_positions}")
            return stats
        
        # Get sector counts
        sector_counts = self.state_engine.get_sector_count()
        active_tickers = [pos['ticker'] for pos in active_positions]
        available_slots = self.max_positions - len(active_positions)
        current_equity = self.state_engine.get_total_equity()
        allocation_per_position = current_equity * self.entry_allocation_pct
        
        stats['available_slots'] = available_slots
        
        # Scan each stock
        for stock in self.target_universe:
            ticker = stock['ticker']
            sector = stock['sector']
            stats['total_scanned'] += 1
            
            # Check if already held
            if ticker in active_tickers:
                stats['already_held'] += 1
                continue
            
            # Check sector limit
            if sector_counts.get(sector, 0) >= self.max_per_sector:
                stats['sector_limits_hit'] += 1
                continue
            
            # Calculate indicators
            indicators = self.calculate_technical_indicators(ticker)
            if not indicators:
                stats['technical_fail'] += 1
                continue
            
            # Check breakout
            if not indicators.get('breakout', False):
                stats['technical_fail'] += 1
                continue
            
            stats['breakout_found'] += 1
            
            # Check cash availability
            current_price = indicators['current_price']
            quantity = int(allocation_per_position / current_price)
            allocated_capital = quantity * current_price
            
            if allocated_capital > self.state_engine.get_available_cash():
                stats['cash_insufficient'] += 1
                continue
            
            # Create entry signal
            entry_signal = {
                'ticker': ticker,
                'sector': sector,
                'action': 'BUY',
                'price': current_price,
                'quantity': quantity,
                'allocated_capital': allocated_capital,
                'reason': 'New Breakout Setup',
                'sma20': indicators['sma20'],
                'sma50': indicators['sma50']
            }
            
            stats['entry_signals'].append(entry_signal)
            
            if len(stats['entry_signals']) >= available_slots:
                break
        
        # Scan for exit signals
        stats['exit_signals'] = self.scan_exit_signals()
        
        return stats
    
    def process_signals(self) -> Dict[str, List[Dict]]:
        entry_signals = self.scan_entry_signals()
        exit_signals = self.scan_exit_signals()
        
        for signal in exit_signals:
            self.execute_exit(signal)
        
        for signal in entry_signals:
            self.execute_entry(signal)
        
        self.state_engine.save_state()
        
        return {
            'entry_signals': entry_signals,
            'exit_signals': exit_signals
        }
    
    def execute_entry(self, signal: Dict) -> bool:
        try:
            ticker = signal['ticker']
            quantity = signal['quantity']
            price = signal['price']
            allocated_capital = signal['allocated_capital']
            sector = signal['sector']
            
            if allocated_capital > self.state_engine.get_available_cash():
                logger.warning(f"Insufficient cash for {ticker}: {allocated_capital} > {self.state_engine.get_available_cash()}")
                return False
            
            position = {
                'ticker': ticker,
                'sector': sector,
                'entry_date': datetime.now().isoformat(),
                'entry_price': price,
                'allocated_capital': allocated_capital,
                'quantity': quantity,
                'highest_recorded_close': price,
                'holding_days': 0
            }
            
            self.state_engine.update_cash(allocated_capital, operation="debit")
            self.state_engine.add_position(position)
            
            logger.info(f"Executed BUY: {ticker} @ {price:.2f} x {quantity} = ₹{allocated_capital:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing entry for {signal.get('ticker')}: {e}")
            return False
    
    def execute_exit(self, signal: Dict) -> bool:
        try:
            ticker = signal['ticker']
            price = signal['price']
            quantity = signal['quantity']
            pnl_amount = signal['pnl_amount']
            pnl_pct = signal['pnl_pct']
            position = signal['position_data']
            
            removed = self.state_engine.remove_position(ticker)
            if not removed:
                logger.warning(f"Position {ticker} not found in active positions")
                return False
            
            sale_proceeds = price * quantity
            self.state_engine.update_cash(sale_proceeds, operation="credit")
            
            historical_trade = {
                'ticker': ticker,
                'sector': position.get('sector'),
                'entry_date': position['entry_date'],
                'exit_date': datetime.now().isoformat(),
                'entry_price': position['entry_price'],
                'exit_price': price,
                'quantity': quantity,
                'pnl_amount': pnl_amount,
                'pnl_pct': pnl_pct,
                'holding_days': signal['holding_days'],
                'exit_reason': signal['reason']
            }
            
            self.state_engine.add_historical_trade(historical_trade)
            
            logger.info(f"Executed SELL: {ticker} @ {price:.2f} x {quantity} | P&L: ₹{pnl_amount:,.2f} ({pnl_pct:.2f}%)")
            return True
            
        except Exception as e:
            logger.error(f"Error executing exit for {signal.get('ticker')}: {e}")
            return False
