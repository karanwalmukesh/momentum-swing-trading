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
        self.throttle_delay = 0.3
        self.batch_size = 20
        self.batch_pause = 2.0
        
    def _load_universe_from_csv(self) -> List[Dict]:
        """Load complete universe from CSV file."""
        try:
            if not os.path.exists(self.csv_path):
                logger.warning(f"CSV file not found: {self.csv_path}. Creating sample NSE 50 universe.")
                sample_data = {
                    'Symbol': ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 
                              'SBIN', 'BHARTIARTL', 'ITC', 'LT', 'KOTAKBANK', 'BAJFINANCE',
                              'WIPRO', 'ASIANPAINT', 'HCLTECH', 'SUNPHARMA', 'MARUTI', 'ULTRACEMCO',
                              'TITAN', 'TATAMOTORS', 'NTPC', 'POWERGRID', 'M&M', 'NESTLEIND',
                              'ADANIPORTS', 'HDFC', 'JSWSTEEL', 'TECHM', 'ONGC', 'GRASIM'],
                    'Company Name': ['Reliance Industries', 'Tata Consultancy', 'HDFC Bank', 
                                    'Infosys', 'ICICI Bank', 'Hindustan Unilever',
                                    'SBI', 'Bharti Airtel', 'ITC', 'Larsen', 'Kotak Bank', 
                                    'Bajaj Finance', 'Wipro', 'Asian Paints', 'HCL Tech',
                                    'Sun Pharma', 'Maruti Suzuki', 'UltraTech Cement',
                                    'Titan', 'Tata Motors', 'NTPC', 'Power Grid', 'M&M', 
                                    'Nestle', 'Adani Ports', 'HDFC', 'JSW Steel', 'Tech Mahindra',
                                    'ONGC', 'Grasim'],
                    'NSE Macro Sector': ['Energy', 'Technology', 'Financial', 'Technology', 
                                        'Financial', 'Consumer', 'Financial', 'Telecom',
                                        'Consumer', 'Construction', 'Financial', 'Financial',
                                        'Technology', 'Consumer', 'Technology', 'Healthcare',
                                        'Automotive', 'Construction', 'Consumer', 'Automotive',
                                        'Energy', 'Energy', 'Automotive', 'Consumer',
                                        'Infrastructure', 'Financial', 'Metals', 'Technology',
                                        'Energy', 'Construction'],
                    'NSE Sector': ['Oil & Gas', 'IT', 'Banking', 'IT', 'Banking', 'FMCG',
                                  'Banking', 'Telecom', 'FMCG', 'Engineering', 'Banking', 
                                  'Finance', 'IT', 'Paints', 'IT', 'Pharma', 'Auto',
                                  'Cement', 'Jewellery', 'Auto', 'Power', 'Power', 'Auto',
                                  'Food', 'Ports', 'Housing', 'Steel', 'IT', 'Oil & Gas',
                                  'Cement'],
                    'NSE Industry': ['Energy', 'Technology', 'Banking', 'Technology',
                                    'Banking', 'Consumer Goods', 'Banking', 'Telecom',
                                    'Consumer Goods', 'Construction', 'Banking', 'Finance',
                                    'Technology', 'Consumer Goods', 'Technology', 'Pharma',
                                    'Automotive', 'Cement', 'Consumer Goods', 'Automotive',
                                    'Power', 'Power', 'Automotive', 'Food', 'Infrastructure',
                                    'Housing', 'Steel', 'Technology', 'Energy', 'Cement'],
                    'Heatmap Sector': ['Energy', 'Technology', 'Financial', 'Technology',
                                      'Financial', 'Consumer', 'Financial', 'Telecom',
                                      'Consumer', 'Construction', 'Financial', 'Financial',
                                      'Technology', 'Consumer', 'Technology', 'Healthcare',
                                      'Automotive', 'Construction', 'Consumer', 'Automotive',
                                      'Energy', 'Energy', 'Automotive', 'Consumer',
                                      'Infrastructure', 'Financial', 'Metals', 'Technology',
                                      'Energy', 'Construction']
                }
                df = pd.DataFrame(sample_data)
                df.to_csv(self.csv_path, index=False)
                logger.info(f"Created sample CSV with {len(df)} stocks at {self.csv_path}")
                return self._load_universe_from_csv()
            
            df = pd.read_csv(self.csv_path)
            required_columns = ['Symbol', 'Company Name', 'NSE Macro Sector', 'NSE Sector', 'NSE Industry', 'Heatmap Sector']
            
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return []
            
            universe = []
            total_rows = len(df)
            logger.info(f"Loading {total_rows} stocks from CSV...")
            
            for idx, row in df.iterrows():
                symbol = str(row['Symbol']).strip()
                if symbol and not pd.isna(symbol):
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
                
                # Show progress for large files
                if (idx + 1) % 100 == 0:
                    logger.info(f"  Loaded {idx + 1}/{total_rows} stocks...")
            
            logger.info(f"✅ Loaded {len(universe)} stocks from {self.csv_path}")
            return universe
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return []
    
    def _safe_download(self, ticker: str, period: str = "1mo", retries: int = 2) -> Optional[pd.DataFrame]:
        """Safe download with retries for rate limiting."""
        for attempt in range(retries):
            try:
                data = yf.download(ticker, period=period, interval="1d", progress=False)
                return data
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Download failed for {ticker}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"Download failed for {ticker} after {retries} attempts: {e}")
                    return None
        return None
    
    def _check_liquidity_floor(self, ticker: str) -> bool:
        """Check if ticker meets minimum 20-day average volume requirement."""
        try:
            data = self._safe_download(ticker, period="1mo")
            if data is None or len(data) < 20:
                return False
            
            if 'Volume' not in data.columns:
                return False
            
            volume_series = data['Volume'].rolling(window=20).mean()
            if volume_series.empty:
                return False
            
            try:
                last_val = volume_series.iloc[-1]
                if pd.isna(last_val) or last_val is None:
                    return False
                avg_volume = float(last_val)
            except (ValueError, TypeError, IndexError):
                return False
            
            meets_threshold = avg_volume >= self.min_volume_threshold
            if meets_threshold:
                logger.info(f"✅ {ticker} passed liquidity check: Avg Volume = {avg_volume:,.0f}")
            
            return meets_threshold
            
        except Exception as e:
            logger.warning(f"Could not check liquidity for {ticker}: {e}")
            return False
    
    def _get_liquid_universe(self) -> List[Dict]:
        """Scan ALL stocks in universe with batch processing."""
        liquid_stocks = []
        total_stocks = len(self.target_universe)
        
        if total_stocks == 0:
            logger.warning("No stocks to scan")
            return []
        
        logger.info(f"🔄 Starting full universe scan of {total_stocks} stocks...")
        logger.info(f"⏱️ Estimated time: ~{total_stocks * 0.4 / 60:.1f} minutes")
        
        # Process in batches
        total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_stocks)
            batch = self.target_universe[start_idx:end_idx]
            
            logger.info(f"📦 Batch {batch_num + 1}/{total_batches} (stocks {start_idx + 1}-{end_idx})")
            
            for idx, stock in enumerate(batch, start=start_idx + 1):
                ticker = stock['ticker']
                
                # Show progress every 10 stocks
                if idx % 10 == 0:
                    logger.info(f"  Progress: {idx}/{total_stocks} ({idx/total_stocks*100:.1f}%)")
                
                try:
                    if self._check_liquidity_floor(ticker):
                        liquid_stocks.append(stock)
                except Exception as e:
                    logger.warning(f"Error checking {ticker}: {e}")
                
                # Throttle between individual requests
                time.sleep(self.throttle_delay)
            
            # Longer pause between batches to avoid rate limiting
            if batch_num < total_batches - 1:
                logger.info(f"⏳ Pausing {self.batch_pause}s between batches...")
                time.sleep(self.batch_pause)
        
        logger.info(f"✅ {len(liquid_stocks)}/{total_stocks} stocks passed liquidity filter")
        logger.info(f"📊 Liquidity pass rate: {len(liquid_stocks)/total_stocks*100:.1f}%")
        return liquid_stocks
    
    def check_nifty_regime(self) -> bool:
        """Check if Nifty 50 is above its 20-day SMA."""
        try:
            data = self._safe_download("^NSEI", period="2mo")
            if data is None or len(data) < 20:
                logger.warning("Insufficient Nifty data for 20-day SMA calculation")
                return True
            
            if 'Close' not in data.columns:
                logger.warning("No Close data for Nifty")
                return True
            
            sma = data['Close'].rolling(window=20).mean()
            
            try:
                current_close = float(data['Close'].iloc[-1])
                current_sma = float(sma.iloc[-1])
                is_above = current_close > current_sma
                logger.info(f"Nifty Regime: Close={current_close:.2f}, SMA20={current_sma:.2f}, Above={is_above}")
                return is_above
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Error extracting Nifty values: {e}")
                return True
                
        except Exception as e:
            logger.error(f"Error checking Nifty regime: {e}")
            return True
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Get current EOD prices for tickers with batch processing."""
        prices = {}
        try:
            total_tickers = len(tickers)
            logger.info(f"Fetching prices for {total_tickers} tickers...")
            
            # Process in small batches
            price_batch = 5
            for i in range(0, total_tickers, price_batch):
                batch = tickers[i:i+price_batch]
                logger.info(f"  Price batch {i//price_batch + 1}/{(total_tickers + price_batch - 1)//price_batch}")
                
                for ticker in batch:
                    try:
                        data = self._safe_download(ticker, period="1d")
                        if data is not None and 'Close' in data.columns and len(data) > 0:
                            val = data['Close'].iloc[-1]
                            if not pd.isna(val):
                                prices[ticker] = float(val)
                    except Exception as e:
                        logger.warning(f"Error getting price for {ticker}: {e}")
                    
                    time.sleep(self.throttle_delay)
                
                # Pause between batches
                if i + price_batch < total_tickers:
                    time.sleep(self.batch_pause)
            
            return prices
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}
    
    def calculate_technical_indicators(self, ticker: str, period: str = "3mo") -> Dict:
        """Calculate technical indicators for a ticker."""
        try:
            data = self._safe_download(ticker, period=period)
            if data is None or len(data) < 20:
                return {}
            
            required_cols = ['Close', 'High', 'Low']
            if not all(col in data.columns for col in required_cols):
                return {}
            
            # Calculate moving averages
            sma20 = data['Close'].rolling(window=20).mean()
            sma50 = data['Close'].rolling(window=50).mean()
            
            # Calculate ATR
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr_series = true_range.rolling(14).mean()
            
            try:
                current_close = float(data['Close'].iloc[-1])
                current_sma20 = float(sma20.iloc[-1])
                current_sma50 = float(sma50.iloc[-1])
                
                if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
                    atr = float(atr_series.iloc[-1])
                else:
                    atr = 0.0
                
                # Calculate 15-day velocity
                if len(data) >= 15:
                    close_today = float(data['Close'].iloc[-1])
                    close_15d_ago = float(data['Close'].iloc[-15])
                    velocity_15d = float((close_today / close_15d_ago - 1) * 100)
                else:
                    velocity_15d = 0.0
                
                # Check for breakout
                breakout = current_close > current_sma20 and current_sma20 > current_sma50
                
                return {
                    'current_price': current_close,
                    'sma20': current_sma20,
                    'sma50': current_sma50,
                    'atr': atr,
                    'velocity_15d': velocity_15d,
                    'breakout': breakout,
                    'highest_close': float(data['Close'].max())
                }
            except (ValueError, TypeError, IndexError):
                return {}
                
        except Exception as e:
            logger.warning(f"Error calculating indicators for {ticker}: {e}")
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
            
            # 1. Hard Stop Check (-5%)
            if pnl_pct <= self.hard_stop_loss:
                exit_reason = f'Hard Stop Hit ({pnl_pct:.2f}%)'
            
            # 2. Breakeven Stop (transaction-adjusted)
            elif pnl_pct >= 0.5 and pnl_pct <= 1.0:
                breakeven_price = entry_price * (1 + self.friction_coefficient)
                if current_price <= breakeven_price:
                    exit_reason = 'Breakeven Stop Hit (Friction-adjusted)'
            
            # 3. Velocity Exit (15-day < 5%)
            elif holding_days >= self.holding_period_velocity:
                if indicators and indicators.get('velocity_15d', 0) < self.velocity_threshold:
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
                self.state_engine.add_system_signal(exit_signal)
        
        return exit_signals
    
    def scan_entry_signals(self) -> List[Dict]:
        """Scan for new entry signals across ALL liquid stocks."""
        if not self.check_nifty_regime():
            logger.info("Nifty regime not favorable for entries")
            return []
        
        active_positions = self.state_engine.get_active_positions()
        if len(active_positions) >= self.max_positions:
            logger.info(f"Max positions reached: {len(active_positions)}/{self.max_positions}")
            return []
        
        # Get ALL liquid stocks
        liquid_universe = self._get_liquid_universe()
        if not liquid_universe:
            logger.warning("No liquid stocks found in universe")
            return []
        
        sector_counts = self.state_engine.get_sector_count()
        available_slots = self.max_positions - len(active_positions)
        
        entry_signals = []
        current_equity = self.state_engine.get_total_equity()
        allocation_per_position = min(current_equity * self.entry_allocation_pct, 50000)
        
        active_tickers = [pos['ticker'] for pos in active_positions]
        
        logger.info(f"🔍 Scanning {len(liquid_universe)} liquid stocks for breakouts...")
        breakout_count = 0
        
        for idx, stock in enumerate(liquid_universe, 1):
            ticker = stock['ticker']
            heatmap_sector = stock['heatmap_sector']
            
            # Show progress every 10 stocks
            if idx % 10 == 0:
                logger.info(f"  Scan progress: {idx}/{len(liquid_universe)} ({idx/len(liquid_universe)*100:.1f}%)")
            
            # Skip if already held
            if ticker in active_tickers:
                continue
            
            # Check sector limit
            if sector_counts.get(heatmap_sector, 0) >= self.max_per_sector:
                continue
            
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(ticker)
            if not indicators:
                continue
            
            # Check for breakout
            if not indicators.get('breakout', False):
                continue
            
            breakout_count += 1
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
            self.state_engine.add_system_signal(entry_signal)
            
            if len(entry_signals) >= available_slots:
                break
        
        logger.info(f"📊 Breakouts found: {breakout_count}, Signals generated: {len(entry_signals)}")
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
        
        # Get ALL liquid stocks
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
        
        # Scan ALL liquid stocks
        for idx, stock in enumerate(liquid_universe, 1):
            ticker = stock['ticker']
            heatmap_sector = stock['heatmap_sector']
            
            # Show progress
            if idx % 20 == 0:
                logger.info(f"  Scan progress: {idx}/{len(liquid_universe)} ({idx/len(liquid_universe)*100:.1f}%)")
            
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
        
        # Final summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 FULL SCAN COMPLETE")
        logger.info(f"   Total stocks scanned: {stats['total_scanned']}")
        logger.info(f"   Breakouts found: {stats['breakout_found']}")
        logger.info(f"   Entry signals: {len(stats['entry_signals'])}")
        logger.info(f"   Exit signals: {len(stats['exit_signals'])}")
        logger.info("=" * 50)
        
        return stats
