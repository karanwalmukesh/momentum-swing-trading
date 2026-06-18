import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import time
import os
from state_engine import StateEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchEngine:
    def __init__(self, state_engine: StateEngine, csv_path: str = "NSE_Sector_Master.csv"):
        self.state_engine = state_engine
        self.csv_path = csv_path
        self.target_universe = self._load_universe_from_csv()
        self.friction_coefficient = 0.003
        self.max_positions = 10
        self.max_per_sector = 3
        self.initial_capital = 500000
        self.entry_allocation_pct = 0.10
        self.min_volume_threshold = 50000
        self.holding_period_velocity = 15
        self.velocity_threshold = 5.0
        self.hard_stop_loss = -5.0
        self.trailing_activation = 15.0
        self.atr_multiplier = 2.5
        self.throttle_delay = 0.5
        
    def _load_universe_from_csv(self) -> List[Dict]:
        """Load and validate stock universe from CSV file with dynamic .NS transformation."""
        try:
            if not os.path.exists(self.csv_path):
                logger.error(f"CSV file not found: {self.csv_path}")
                return []
            
            df = pd.read_csv(self.csv_path)
            required_columns = ['Symbol', 'Company Name', 'NSE Macro Sector', 'NSE Sector', 'NSE Industry', 'Heatmap Sector']
            
            # Validate required columns
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return []
            
            universe = []
            for _, row in df.iterrows():
                symbol = str(row['Symbol']).strip()
                if symbol and not pd.isna(symbol):
                    # Append .NS for Yahoo Finance
                    ticker = f"{symbol}.NS"
                    universe.append({
                        'symbol': symbol,
                        'ticker': ticker,
                        'company_name': row['Company Name'],
                        'macro_sector': row['NSE Macro Sector'],
                        'nse_sector': row['NSE Sector'],
                        'nse_industry': row['NSE Industry'],
                        'heatmap_sector': row['Heatmap Sector']
                    })
            
            logger.info(f"Loaded {len(universe)} stocks from {self.csv_path}")
            return universe
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return []
    
    def _check_liquidity_floor(self, ticker: str) -> bool:
        """Check if ticker meets minimum 20-day average volume requirement."""
        try:
            data = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if len(data) < 20:
                return False
            
            avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1]
            meets_threshold = avg_volume >= self.min_volume_threshold
            
            if not meets_threshold:
                logger.info(f"❌ {ticker} failed liquidity check: Avg Volume = {avg_volume:,.0f} < {self.min_volume_threshold:,}")
            else:
                logger.info(f"✅ {ticker} passed liquidity check: Avg Volume = {avg_volume:,.0f}")
            
            return meets_threshold
            
        except Exception as e:
            logger.warning(f"Could not check liquidity for {ticker}: {e}")
            return False
    
    def _get_liquid_universe(self) -> List[Dict]:
        """Filter universe for stocks meeting liquidity requirements."""
        liquid_stocks = []
        total_stocks = len(self.target_universe)
        
        for idx, stock in enumerate(self.target_universe, 1):
            ticker = stock['ticker']
            logger.info(f"Checking liquidity {idx}/{total_stocks}: {ticker}")
            
            if self._check_liquidity_floor(ticker):
                liquid_stocks.append(stock)
            
            # Throttle delay to prevent rate limiting
            time.sleep(self.throttle_delay)
        
        logger.info(f"✅ {len(liquid_stocks)}/{total_stocks} stocks passed liquidity filter")
        return liquid_stocks
    
    def check_nifty_regime(self) -> bool:
        """Check if Nifty 50 is above its 20-day SMA."""
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
        """Get current EOD prices for tickers with throttling."""
        prices = {}
        try:
            # Process in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i+batch_size]
                data = yf.download(batch, period="1d", interval="1d", progress=False)
                
                if not data.empty and 'Close' in data.columns:
                    for ticker in batch:
                        if ticker in data['Close'].columns and not pd.isna(data['Close'][ticker].iloc[-1]):
                            prices[ticker] = float(data['Close'][ticker].iloc[-1])
                        else:
                            logger.warning(f"No price data available for {ticker}")
                
                # Throttle between batches
                time.sleep(self.throttle_delay)
            
            return prices
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}
    
    def calculate_technical_indicators(self, ticker: str, period: str = "3mo") -> Dict:
        """Calculate technical indicators with throttling."""
        try:
            time.sleep(self.throttle_delay)
            data = yf.download(ticker, period=period, interval="1d", progress=False)
            if len(data) < 20:
                return {}
            
            # Calculate moving averages
            data['SMA20'] = data['Close'].rolling(window=20).mean()
            data['SMA50'] = data['Close'].rolling(window=50).mean()
            
            # Calculate ATR
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            # Calculate 15-day velocity
            velocity_15d = (data['Close'].iloc[-1] / data['Close'].iloc[-15] - 1) * 100 if len(data) >= 15 else 0
            
            # Check for breakout
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
    
    def scan_exit_signals(self) -> List[Dict]:
        """Scan active positions for exit triggers."""
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
            
            # Update highest recorded close
            if current_price > highest_close:
                highest_close = current_price
                self.state_engine.update_position(ticker, {
                    'highest_recorded_close': highest_close,
                    'holding_days': holding_days
                })
            else:
                self.state_engine.update_position(ticker, {'holding_days': holding_days})
            
            # Calculate P&L
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_amount = (current_price - entry_price) * position['quantity']
            
            # Get ATR for trailing stop
            indicators = self.calculate_technical_indicators(ticker, period="1mo")
            atr = indicators.get('atr', 0) if indicators else 0
            
            exit_reason = None
            
            # 1. Hard Stop Check (-5%)
            if pnl_pct <= self.hard_stop_loss:
                exit_reason = f'Hard Stop Hit ({pnl_pct:.2f}%)'
            
            # 2. Breakeven Stop (transaction-adjusted)
            elif pnl_pct >= 0.5 and pnl_pct <= 1.0:
                breakeven_price = entry_price * (1 + self.friction_coefficient)
                if current_price <= breakeven_price:
                    exit_reason = f'Breakeven Stop Hit (Friction-adjusted)'
            
            # 3. Velocity Exit (15-day < 5%)
            elif holding_days >= self.holding_period_velocity:
                if indicators and indicators['velocity_15d'] < self.velocity_threshold:
                    exit_reason = f'Velocity Exit (15-day gain: {indicators["velocity_15d"]:.2f}%)'
            
            # 4. Trailing Stop (>=15% profit)
            elif pnl_pct >= self.trailing_activation and atr > 0:
                trailing_stop = highest_close - (self.atr_multiplier * atr)
                if current_price <= trailing_stop:
                    exit_reason = f'Trailing Stop Hit (Stop: {trailing_stop:.2f})'
            
            if exit_reason:
                exit_signal = {
                    'ticker': ticker,
                    'heatmap_sector': position.get('heatmap_sector', 'Unknown'),
                    'action': 'SELL',
                    'price': current_price,
                    'quantity': position['quantity'],
                    'reason': exit_reason,
                    'entry_date': position['entry_date'],
                    'entry_price': entry_price,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'holding_days': holding_days,
                    'position_data': position,
                    'status': 'PENDING'
                }
                exit_signals.append(exit_signal)
                # Log to system signals
                self.state_engine.add_system_signal(exit_signal)
        
        return exit_signals
    
    def scan_entry_signals(self) -> List[Dict]:
        """Scan for new entry signals based on breakout criteria."""
        if not self.check_nifty_regime():
            logger.info("Nifty regime not favorable for entries")
            return []
        
        active_positions = self.state_engine.get_active_positions()
        if len(active_positions) >= self.max_positions:
            logger.info(f"Max positions reached: {len(active_positions)}/{self.max_positions}")
            return []
        
        # Get liquid universe
        liquid_universe = self._get_liquid_universe()
        if not liquid_universe:
            logger.warning("No liquid stocks found in universe")
            return []
        
        # Get sector counts
        sector_counts = self.state_engine.get_sector_count()
        available_slots = self.max_positions - len(active_positions)
        
        entry_signals = []
        current_equity = self.state_engine.get_total_equity()
        allocation_per_position = min(current_equity * self.entry_allocation_pct, 50000)
        
        active_tickers = [pos['ticker'] for pos in active_positions]
        
        for stock in liquid_universe:
            ticker = stock['ticker']
            heatmap_sector = stock['heatmap_sector']
            
            # Skip if already held
            if ticker in active_tickers:
                continue
            
            # Check sector limit
            if sector_counts.get(heatmap_sector, 0) >= self.max_per_sector:
                continue
            
            # Calculate indicators
            indicators = self.calculate_technical_indicators(ticker)
            if not indicators or not indicators.get('breakout', False):
                continue
            
            current_price = indicators['current_price']
            quantity = int(allocation_per_position / current_price)
            allocated_capital = quantity * current_price
            
            # Check cash availability
            if allocated_capital > self.state_engine.get_available_cash():
                continue
            
            entry_signal = {
                'ticker': ticker,
                'symbol': stock['symbol'],
                'heatmap_sector': heatmap_sector,
                'company_name': stock['company_name'],
                'action': 'BUY',
                'price': current_price,
                'quantity': quantity,
                'allocated_capital': allocated_capital,
                'reason': 'New Breakout Setup',
                'sma20': indicators['sma20'],
                'sma50': indicators['sma50'],
                'status': 'PENDING'
            }
            
            entry_signals.append(entry_signal)
            # Log to system signals
            self.state_engine.add_system_signal(entry_signal)
            
            if len(entry_signals) >= available_slots:
                break
        
        return entry_signals
    
    def scan_with_statistics(self) -> Dict[str, Any]:
        """Complete scan with detailed statistics."""
        stats = {
            'total_scanned': 0,
            'nifty_regime': False,
            'active_positions': 0,
            'sector_limits_hit': 0,
            'breakout_found': 0,
            'technical_fail': 0,
            'already_held': 0,
            'cash_insufficient': 0,
            'liquidity_fail': 0,
            'entry_signals': [],
            'exit_signals': [],
            'total_equity': self.state_engine.get_total_equity()
        }
        
        # Check Nifty regime
        stats['nifty_regime'] = self.check_nifty_regime()
        if not stats['nifty_regime']:
            logger.info("❌ Nifty regime not favorable - skipping scan")
            return stats
        
        active_positions = self.state_engine.get_active_positions()
        stats['active_positions'] = len(active_positions)
        
        if len(active_positions) >= self.max_positions:
            logger.info(f"❌ Max positions reached: {len(active_positions)}/{self.max_positions}")
            return stats
        
        # Get liquid universe
        liquid_universe = self._get_liquid_universe()
        if not liquid_universe:
            return stats
        
        sector_counts = self.state_engine.get_sector_count()
        active_tickers = [pos['ticker'] for pos in active_positions]
        available_slots = self.max_positions - len(active_positions)
        current_equity = self.state_engine.get_total_equity()
        allocation_per_position = min(current_equity * self.entry_allocation_pct, 50000)
        
        stats['available_slots'] = available_slots
        stats['total_scanned'] = len(liquid_universe)
        
        # Scan each liquid stock
        for stock in liquid_universe:
            ticker = stock['ticker']
            heatmap_sector = stock['heatmap_sector']
            
            # Check if already held
            if ticker in active_tickers:
                stats['already_held'] += 1
                continue
            
            # Check sector limit
            if sector_counts.get(heatmap_sector, 0) >= self.max_per_sector:
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
                'symbol': stock['symbol'],
                'heatmap_sector': heatmap_sector,
                'company_name': stock['company_name'],
                'action': 'BUY',
                'price': current_price,
                'quantity': quantity,
                'allocated_capital': allocated_capital,
                'reason': 'New Breakout Setup',
                'sma20': indicators['sma20'],
                'sma50': indicators['sma50'],
                'status': 'PENDING'
            }
            
            stats['entry_signals'].append(entry_signal)
            self.state_engine.add_system_signal(entry_signal)
            
            if len(stats['entry_signals']) >= available_slots:
                break
        
        # Scan for exit signals
        stats['exit_signals'] = self.scan_exit_signals()
        
        return stats
