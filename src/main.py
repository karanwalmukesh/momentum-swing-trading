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
    logger.info("=" * 60)
    logger.info("MOMENTUM SWING TRADING SYSTEM - LIVE EXECUTION")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("=" * 60)
    
    try:
        logger.info("Initializing State Engine...")
        state_engine = StateEngine()
        
        logger.info("Initializing Match Engine...")
        match_engine = MatchEngine(state_engine)
        
        logger.info("Initializing Notification Manager...")
        notification = NotificationManager()
        
        logger.info("Initializing Dashboard Generator...")
        dashboard = DashboardGenerator()
        
        logger.info("Processing signals...")
        signals = match_engine.process_signals()
        entry_signals = signals['entry_signals']
        exit_signals = signals['exit_signals']
        
        logger.info(f"Sending notifications: {len(entry_signals)} entries, {len(exit_signals)} exits")
        notification.send_alert(entry_signals, exit_signals)
        
        logger.info("Generating dashboard...")
        dashboard.generate_dashboard()
        
        logger.info("=" * 60)
        logger.info("EXECUTION SUMMARY")
        logger.info(f"  Entry Signals: {len(entry_signals)}")
        logger.info(f"  Exit Signals: {len(exit_signals)}")
        logger.info(f"  Total Equity: ₹{state_engine.get_total_equity():,.2f}")
        logger.info(f"  Available Cash: ₹{state_engine.get_available_cash():,.2f}")
        logger.info(f"  Active Positions: {len(state_engine.get_active_positions())}")
        logger.info("=" * 60)
        logger.info("SYSTEM EXECUTION COMPLETE")
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
