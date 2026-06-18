import os
import sys
import logging
from datetime import datetime
from state_engine import StateEngine
from match_engine import MatchEngine
from notification import NotificationManager
from dashboard import DashboardGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("MOMENTUM SWING TRADING SYSTEM - FULL UNIVERSE SCAN")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("=" * 70)
    
    try:
        # Initialize components
        logger.info("Initializing State Engine...")
        state_engine = StateEngine()
        
        logger.info("Initializing Match Engine with CSV universe...")
        match_engine = MatchEngine(state_engine)
        
        logger.info("Initializing Notification Manager...")
        notification = NotificationManager()
        
        logger.info("Initializing Dashboard Generator...")
        dashboard = DashboardGenerator()
        
        # Process signals with statistics
        logger.info("\n📊 SCANNING FULL MARKET...")
        logger.info("-" * 70)
        
        scan_results = match_engine.scan_with_statistics()
        
        # Display detailed scan statistics
        logger.info("\n📈 SCAN STATISTICS:")
        logger.info(f"   📌 Total Stocks Scanned:     {scan_results['total_scanned']}")
        logger.info(f"   📌 Nifty Regime:             {'✅ ABOVE' if scan_results['nifty_regime'] else '❌ BELOW'} 20-day SMA")
        logger.info(f"   📌 Active Positions:          {scan_results['active_positions']}/{match_engine.max_positions}")
        logger.info(f"   📌 Available Slots:           {scan_results.get('available_slots', 0)}")
        logger.info(f"   📌 Already Held:             {scan_results['already_held']}")
        logger.info(f"   📌 Sector Limits Hit:        {scan_results['sector_limits_hit']}")
        logger.info(f"   📌 Technical Failures:       {scan_results['technical_fail']}")
        logger.info(f"   📌 Breakouts Found:          {scan_results['breakout_found']}")
        logger.info(f"   📌 Cash Insufficient:        {scan_results['cash_insufficient']}")
        logger.info(f"   📌 Entry Signals Generated:  {len(scan_results['entry_signals'])}")
        logger.info(f"   📌 Exit Signals Generated:   {len(scan_results['exit_signals'])}")
        
        logger.info("-" * 70)
        
        # Execute entries and exits
        entry_signals = scan_results['entry_signals']
        exit_signals = scan_results['exit_signals']
        
        # Process exits first (to free up capital for new entries)
        for signal in exit_signals:
            logger.info(f"📤 EXIT SIGNAL: {signal['ticker']} - {signal['reason']}")
        
        # Process entries
        for signal in entry_signals:
            logger.info(f"📥 ENTRY SIGNAL: {signal['symbol']} - {signal['reason']}")
        
        # Save state
        state_engine.save_state()
        
        # Send notifications
        logger.info(f"\n📧 Sending notifications: {len(entry_signals)} entries, {len(exit_signals)} exits")
        notification.send_alert(entry_signals, exit_signals, scan_results)
        
        # Generate dashboard
        logger.info("\n📊 Generating dashboard...")
        dashboard.generate_dashboard()
        
        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ EXECUTION COMPLETE")
        logger.info(f"   💰 Total Equity:     ₹{state_engine.get_total_equity():,.2f}")
        logger.info(f"   💵 Available Cash:   ₹{state_engine.get_available_cash():,.2f}")
        logger.info(f"   📊 Active Positions: {len(state_engine.get_active_positions())}")
        logger.info(f"   📈 Total Trades:     {len(state_engine.get_historical_trades())}")
        logger.info(f"   📋 Total Signals:    {len(state_engine.get_system_signals())}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
