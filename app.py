"""
app.py — Premium EGX Intelligence Dashboard
===========================================
A high-end, glassmorphic trading interface for the Egyptian Market.
"""

import logging
from datetime import date, datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import config
import database

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EGX Intelligence Hub",
    page_icon="🔮",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# PREMIUM DESIGN SYSTEM (CSS)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700&display=swap');

    /* Global Overlay */
    .stApp {
        background: radial-gradient(circle at top right, #1e1e3f, #0a0a12);
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 10, 20, 0.8) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Premium Header */
    .glow-header {
        background: linear-gradient(90deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 0 10px rgba(129, 140, 248, 0.3));
    }

    /* Insight Cards (Glassmorphism) */
    .insight-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .insight-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(129, 140, 248, 0.4);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }

    .stock-badge {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        color: white;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    .price-main {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 10px 0;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-top: 15px;
    }

    .sub-metric {
        background: rgba(0, 0, 0, 0.2);
        padding: 8px;
        border-radius: 10px;
        text-align: center;
    }

    .label-tiny { color: #94a3b8; font-size: 0.7rem; text-transform: uppercase; }
    .val-med { color: #e2e8f0; font-size: 0.95rem; font-weight: 600; }
    .val-green { color: #10b981; }
    .val-red { color: #ef4444; }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0a0a12; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:#818cf8; font-family:Outfit;'>COMMAND CENTER</h2>", unsafe_allow_html=True)
    st.image("https://img.icons8.com/isometric/512/financial-analytics.png", width=150)
    
    selected_date = st.date_input("TARGET DATE", value=date.today(), max_value=date.today())
    selected_date_str = selected_date.isoformat()
    
    st.markdown("---")
    st.markdown("### 🧬 BIOMETRICS")
    st.info(f"RSI FLOOR: {config.RSI_OVERSOLD}\n\nVOL GAIN: {config.VOLUME_SPIKE_MULTIPLIER}x")
    
    st.markdown("---")
    st.caption("EGX INTELLIGENCE SYSTEM v2.0")

# ─────────────────────────────────────────────────────────────
# TOP BAR / HERO
# ─────────────────────────────────────────────────────────────
st.markdown('<h1 class="glow-header">INTELLIGENCE HUB</h1>', unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:#94a3b8;'>Live Sync: {datetime.now().strftime('%H:%M')} CLT · Data Archive: {selected_date_str}</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CORE LOGIC: DATA FETCH
# ─────────────────────────────────────────────────────────────
database.init_db()
picks = database.get_latest_picks(selected_date_str)
market_df = database.get_all_prices_for_date(selected_date_str)

# ─────────────────────────────────────────────────────────────
# HIGH-CONVICTION PICKS
# ─────────────────────────────────────────────────────────────
st.markdown("<h3 style='font-family:Outfit; color:#f8fafc; margin-bottom:20px;'>⚡ HIGH-CONVICTION SIGNALS</h3>", unsafe_allow_html=True)

if picks:
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(picks):
            pick = picks[i]
            with col:
                st.markdown(f"""
                <div class="insight-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="stock-badge">{pick.get('name', 'N/A')}</span>
                        <span style="color:#818cf8; font-weight:700;">#{pick.get('rank', '0')}</span>
                    </div>
                    <div class="price-main">{pick.get('entry_price', 0):.2f} <small style="font-size:0.5em; color:#94a3b8;">EGP</small></div>
                    
                    <div class="metric-grid">
                        <div class="sub-metric">
                            <div class="label-tiny">Target (5%)</div>
                            <div class="val-med val-green">{pick.get('target_price', 0):.2f}</div>
                        </div>
                        <div class="sub-metric">
                            <div class="label-tiny">Stop (3%)</div>
                            <div class="val-med val-red">{pick.get('stop_loss', 0):.2f}</div>
                        </div>
                        <div class="sub-metric">
                            <div class="label-tiny">RSI</div>
                            <div class="val-med">{pick.get('rsi', 0):.1f}</div>
                        </div>
                        <div class="sub-metric">
                            <div class="label-tiny">Vol Gain</div>
                            <div class="val-med">{pick.get('volume_spike', 1.0):.1f}x</div>
                        </div>
                    </div>
                    
                    <div style="margin-top:20px; padding:8px; background:rgba(129, 140, 248, 0.1); border-radius:8px; text-align:center; color:#818cf8; font-size:0.8rem; font-weight:600;">
                        {pick.get('signal_type', 'ANALYZING').upper()}
                    </div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.warning("NO SIGNALS DETECTED IN THE CURRENT DATA STREAM.")

# ─────────────────────────────────────────────────────────────
# CHARTING & MARKET DATA
# ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown("<h3 style='font-family:Outfit; color:#f8fafc;'>📈 TRAJECTORY ANALYSIS</h3>", unsafe_allow_html=True)
    if picks:
        selected_stock = st.selectbox("FOCUS ASSET", [p.get("name") for p in picks])
        history = database.get_historical_prices(selected_stock, days=60)
        
        if not history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=history["date"], y=history["Last"],
                line=dict(color='#818cf8', width=3),
                fill='tozeroy', fillcolor='rgba(129, 140, 248, 0.05)',
                name="Close"
            ))
            
            # Trendlines
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=20, b=0),
                height=350,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("WAITING FOR SIGNAL DATA...")

with right_col:
    st.markdown("<h3 style='font-family:Outfit; color:#f8fafc;'>📊 MARKET FLOW</h3>", unsafe_allow_html=True)
    if not market_df.empty:
        # Simple stats
        avg_v = f"{market_df['Change_Pct'].mean():.2f}%"
        st.metric("AVG MARKET DELTA", avg_v)
        
        # Mini Table
        st.dataframe(
            market_df[["Name", "Last", "Change_Pct"]].head(10),
            use_container_width=True,
            hide_index=True
        )

# ─────────────────────────────────────────────────────────────
# HISTORICAL AUDIT
# ─────────────────────────────────────────────────────────────
st.markdown("<br><h3 style='font-family:Outfit; color:#f8fafc;'>📜 PERFORMANCE LOG</h3>", unsafe_allow_html=True)
hist_picks = database.get_picks_history(days=30)
if not hist_picks.empty:
    st.dataframe(hist_picks, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<p style='text-align:center; color:#475569; font-size:0.75rem;'>EGX INTELLIGENCE SYSTEM · QUANT-DRIVEN REVENUE GENERATION · NO ADVICE IMPLIED</p>", unsafe_allow_html=True)
