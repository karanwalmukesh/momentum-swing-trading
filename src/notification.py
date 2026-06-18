import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_RECIPIENT")
        
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            logger.warning("Email credentials not fully configured. Email alerts will be logged only.")
    
    def generate_html_summary(self, entry_signals: List[Dict], exit_signals: List[Dict]) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
                h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
                .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th {{ background: #1a1a2e; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .buy {{ color: #2ecc71; font-weight: bold; }}
                .sell {{ color: #e74c3c; font-weight: bold; }}
                .reason {{ font-style: italic; color: #7f8c8d; }}
                .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 12px; color: #95a5a6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Momentum Swing Trading Signals</h1>
                <p><strong>Generated:</strong> {timestamp}</p>
        """
        
        if entry_signals:
            html += """
            <div class="section">
                <h2>🔵 ENTRY SIGNALS ({0})</h2>
                <table>
                    <tr>
                        <th>Ticker</th>
                        <th>Sector</th>
                        <th>Action</th>
                        <th>Price</th>
                        <th>Quantity</th>
                        <th>Allocation</th>
                        <th>Reason</th>
                    </tr>
            """.format(len(entry_signals))
            
            for signal in entry_signals:
                html += f"""
                    <tr>
                        <td><strong>{signal['ticker']}</strong></td>
                        <td>{signal['sector']}</td>
                        <td class="buy">BUY</td>
                        <td>₹{signal['price']:.2f}</td>
                        <td>{signal['quantity']}</td>
                        <td>₹{signal['allocated_capital']:,.2f}</td>
                        <td class="reason">{signal['reason']}</td>
                    </tr>
                """
            
            html += "</table></div>"
        
        if exit_signals:
            html += """
            <div class="section">
                <h2>🔴 EXIT SIGNALS ({0})</h2>
                <table>
                    <tr>
                        <th>Ticker</th>
                        <th>Sector</th>
                        <th>Action</th>
                        <th>Price</th>
                        <th>Quantity</th>
                        <th>P&L</th>
                        <th>Hold Days</th>
                        <th>Reason</th>
                    </tr>
            """.format(len(exit_signals))
            
            for signal in exit_signals:
                pnl_color = "#2ecc71" if signal['pnl_amount'] >= 0 else "#e74c3c"
                html += f"""
                    <tr>
                        <td><strong>{signal['ticker']}</strong></td>
                        <td>{signal['sector']}</td>
                        <td class="sell">SELL</td>
                        <td>₹{signal['price']:.2f}</td>
                        <td>{signal['quantity']}</td>
                        <td style="color:{pnl_color};font-weight:bold;">
                            ₹{signal['pnl_amount']:,.2f} ({signal['pnl_pct']:.2f}%)
                        </td>
                        <td>{signal['holding_days']}</td>
                        <td class="reason">{signal['reason']}</td>
                    </tr>
                """
            
            html += "</table></div>"
        
        if not entry_signals and not exit_signals:
            html += """
            <div class="section">
                <h2>⏸️ No New Signals</h2>
                <p>No entry or exit signals generated in this scan.</p>
            </div>
            """
        
        html += """
                <div class="footer">
                    <p>This is an automated notification from your Momentum Swing Trading System.</p>
                    <p>Please execute trades manually as per the instructions above.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_alert(self, entry_signals: List[Dict], exit_signals: List[Dict]) -> bool:
        if not self.sender_email or not self.sender_password:
            logger.info("Email credentials not configured. Logging signals instead.")
            self._log_signals(entry_signals, exit_signals)
            return False
        
        try:
            html_content = self.generate_html_summary(entry_signals, exit_signals)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚀 Trading Signals - {timestamp}"
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {self.recipient_email} with {len(entry_signals)} entries and {len(exit_signals)} exits")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            self._log_signals(entry_signals, exit_signals)
            return False
    
    def _log_signals(self, entry_signals: List[Dict], exit_signals: List[Dict]) -> None:
        logger.info("=" * 50)
        logger.info("TRADING SIGNALS (Email disabled)")
        logger.info("=" * 50)
        
        if entry_signals:
            logger.info(f"\nENTRY SIGNALS ({len(entry_signals)}):")
            for signal in entry_signals:
                logger.info(f"  BUY {signal['ticker']} @ ₹{signal['price']:.2f} x {signal['quantity']} | {signal['reason']}")
        
        if exit_signals:
            logger.info(f"\nEXIT SIGNALS ({len(exit_signals)}):")
            for signal in exit_signals:
                logger.info(f"  SELL {signal['ticker']} @ ₹{signal['price']:.2f} | P&L: {signal['pnl_pct']:.2f}% | {signal['reason']}")
        
        if not entry_signals and not exit_signals:
            logger.info("\nNo new signals generated.")
        
        logger.info("=" * 50)
