import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Momentum Swing Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
    </style>
""", unsafe_allow_html=True)

def load_state():
    """Load portfolio state from JSON file."""
    try:
        with open("data/portfolio_state.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Portfolio state file not found. Please run the trading system first.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading state: {e}")
        return None

def save_state(state):
    """Save portfolio state to JSON file."""
    try:
        with open("data/portfolio_state.json", 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        st.error(f"❌ Error saving state: {e}")
        return False

def calculate_metrics(state):
    """Calculate portfolio metrics."""
    active = state.get('active_positions', [])
    historical = state.get('historical_trades', [])
    
    metrics = {
        'total_equity': state.get('total_equity', 0),
        'available_cash': state.get('available_cash', 0),
        'active_count': len(active),
        'max_positions': 10,
        'historical_count': len(historical),
        'total_pnl': 0,
        'win_rate': 0,
        'avg_win': 0,
        'avg_loss': 0
    }
    
    if historical:
        total_pnl = sum(trade.get('pnl_amount', 0) for trade in historical)
        metrics['total_pnl'] = total_pnl
        
        winning_trades = [t for t in historical if t.get('pnl_amount', 0) > 0]
        losing_trades = [t for t in historical if t.get('pnl_amount', 0) < 0]
        
        metrics['win_rate'] = (len(winning_trades) / len(historical)) * 100 if historical else 0
        
        if winning_trades:
            metrics['avg_win'] = np.mean([t.get('pnl_pct', 0) for t in winning_trades])
        if losing_trades:
            metrics['avg_loss'] = np.mean([t.get('pnl_pct', 0) for t in losing_trades])
    
    return metrics

def main():
    st.title("📈 Momentum Swing Trading Dashboard")
    st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    # Load state
    state = load_state()
    if not state:
        return
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ System Controls")
        if st.button("🔄 Refresh Data"):
            st.rerun()
        
        st.divider()
        st.metric("📊 Total Equity", f"₹{state.get('total_equity', 0):,.2f}")
        st.metric("💵 Available Cash", f"₹{state.get('available_cash', 0):,.2f}")
        
        active_count = len(state.get('active_positions', []))
        st.metric("📌 Active Positions", f"{active_count} / 10")
        
        if st.button("🔄 Update Dashboard"):
            st.rerun()
    
    # Metrics Row
    metrics = calculate_metrics(state)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("💰 Total Equity", f"₹{metrics['total_equity']:,.2f}")
    with col2:
        st.metric("💵 Available Cash", f"₹{metrics['available_cash']:,.2f}")
    with col3:
        st.metric("📊 Active Positions", f"{metrics['active_count']} / {metrics['max_positions']}")
    with col4:
        st.metric("📈 Win Rate", f"{metrics['win_rate']:.1f}%")
    with col5:
        st.metric("💹 Total P&L", f"₹{metrics['total_pnl']:,.2f}")
    
    # Risk Inspector - Sector Pie Chart
    st.subheader("🎯 Risk Inspector: Sector Allocations")
    
    active_positions = state.get('active_positions', [])
    if active_positions:
        sector_counts = {}
        for pos in active_positions:
            sector = pos.get('heatmap_sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        df_sectors = pd.DataFrame({
            'Sector': list(sector_counts.keys()),
            'Count': list(sector_counts.values())
        })
        
        # Create pie chart
        fig = px.pie(df_sectors, values='Count', names='Sector', 
                     title='Active Positions by Sector',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        
        fig.add_annotation(
            text=f"Max 3 per sector",
            xref="paper", yref="paper",
            x=0.5, y=-0.1,
            showarrow=False,
            font=dict(size=12, color="gray")
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Warning for sectors at limit
        for sector, count in sector_counts.items():
            if count >= 3:
                st.warning(f"⚠️ **{sector}** has {count} positions (at maximum limit!)")
    else:
        st.info("No active positions to display")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Today's Scanned Signals", "📊 Active Positions Matrix", "📈 Edge Asymmetry Analytics"])
    
    # Tab 1: Today's Scanned Signals
    with tab1:
        st.subheader("📋 Today's Scanned Signals")
        
        system_signals = state.get('system_signals_log', [])
        pending_signals = [s for s in system_signals if s.get('status') == 'PENDING']
        
        if pending_signals:
            # Display entries and exits separately
            entries = [s for s in pending_signals if s.get('action') == 'BUY']
            exits = [s for s in pending_signals if s.get('action') == 'SELL']
            
            if entries:
                st.write("**🔵 Entry Signals (Pending Execution)**")
                df_entries = pd.DataFrame(entries)
                display_cols = ['symbol', 'company_name', 'heatmap_sector', 'price', 'quantity', 'allocated_capital', 'reason']
                if all(col in df_entries.columns for col in display_cols):
                    st.dataframe(df_entries[display_cols], use_container_width=True)
            
            if exits:
                st.write("**🔴 Exit Signals (Pending Execution)**")
                df_exits = pd.DataFrame(exits)
                display_cols = ['ticker', 'heatmap_sector', 'price', 'quantity', 'reason', 'pnl_pct', 'pnl_amount']
                if all(col in df_exits.columns for col in display_cols):
                    st.dataframe(df_exits[display_cols], use_container_width=True)
            
            if not entries and not exits:
                st.info("No pending signals")
        else:
            st.info("No pending signals to display")
    
    # Tab 2: Active Positions Matrix
    with tab2:
        st.subheader("📊 Active Positions Matrix")
        
        active_positions = state.get('active_positions', [])
        
        if active_positions:
            # Display active positions
            df_active = pd.DataFrame(active_positions)
            st.dataframe(df_active, use_container_width=True)
            
            # Interactive execution controls
            st.divider()
            st.write("**🛠️ Manual Execution Controls**")
            st.caption("Use these controls to manually execute or skip signals")
            
            # Get pending signals
            system_signals = state.get('system_signals_log', [])
            pending_signals = [s for s in system_signals if s.get('status') == 'PENDING']
            
            if pending_signals:
                # Select signal to execute
                signal_options = [f"{s.get('symbol', s.get('ticker'))} - {s.get('action')} @ ₹{s.get('price', 0):.2f}" 
                                 for s in pending_signals]
                selected_idx = st.selectbox("Select Signal to Execute", range(len(pending_signals)), 
                                            format_func=lambda x: signal_options[x])
                
                selected_signal = pending_signals[selected_idx]
                
                # Show signal details
                with st.expander("Signal Details"):
                    st.json(selected_signal)
                
                # Execution controls
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Execute Signal"):
                        # Here you would call the execute_signal method
                        st.success(f"Signal executed: {selected_signal.get('ticker')}")
                        # Update state would happen here
                
                with col2:
                    if st.button("⏭️ Skip Signal"):
                        st.info(f"Signal skipped: {selected_signal.get('ticker')}")
            else:
                st.info("No pending signals to execute")
        else:
            st.info("No active positions")
    
    # Tab 3: Edge Asymmetry Analytics
    with tab3:
        st.subheader("📈 Edge Asymmetry Analytics")
        
        historical = state.get('historical_trades', [])
        
        if historical:
            # Calculate metrics
            winning_trades = [t for t in historical if t.get('pnl_amount', 0) > 0]
            losing_trades = [t for t in historical if t.get('pnl_amount', 0) < 0]
            
            avg_win = np.mean([t.get('pnl_pct', 0) for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t.get('pnl_pct', 0) for t in losing_trades]) if losing_trades else 0
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Win Rate", f"{metrics['win_rate']:.1f}%")
            with col2:
                st.metric("📈 Avg Win %", f"{avg_win:.2f}%")
            with col3:
                st.metric("📉 Avg Loss %", f"{avg_loss:.2f}%")
            
            # Profit Factor
            total_win = sum([t.get('pnl_amount', 0) for t in winning_trades]) if winning_trades else 0
            total_loss = abs(sum([t.get('pnl_amount', 0) for t in losing_trades])) if losing_trades else 1
            
            profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
            st.metric("💰 Profit Factor", f"{profit_factor:.2f}")
            
            # Create P&L distribution chart
            if historical:
                df_historical = pd.DataFrame(historical)
                fig = px.histogram(df_historical, x='pnl_pct', nbins=20,
                                  title='P&L Distribution of Closed Trades',
                                  labels={'pnl_pct': 'P&L %'})
                fig.add_vline(x=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
                
                # Cumulative P&L
                df_historical['cumulative_pnl'] = df_historical['pnl_amount'].cumsum()
                fig2 = px.line(df_historical, x='exit_date', y='cumulative_pnl',
                              title='Cumulative P&L Over Time',
                              labels={'exit_date': 'Exit Date', 'cumulative_pnl': 'Cumulative P&L (₹)'})
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No historical trades yet. Edge analytics will appear after trades are closed.")

if __name__ == "__main__":
    main()
