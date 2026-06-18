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
        'exit_signals': []
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
