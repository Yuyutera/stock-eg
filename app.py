"""
app.py — Streamlit Web Dashboard for the EGX Intelligence System
=================================================================
A clean, dark-themed dashboard that displays:
    1. Today's Top 3 Picks (signal cards)
    2. Full EGX stocks table with RSI & Volume
    3. Interactive price charts

RUN:
    streamlit run app.py

WHY Streamlit?
    It converts a plain Python script into an interactive web app
    with zero frontend code. Perfect for data-heavy dashboards.
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
# PAGE CONFIG & STYLING
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.STREAMLIT_PAGE_TITLE,
    page_icon=config.STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS for a premium dark look.
st.markdown("""
<style>
    /* ── Global ─────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e0e0e0;
    }

    /* ── Signal Cards ───────────────────────────── */
    .pick-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .pick-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(99,102,241,0.2);
    }
    .pick-card h3 {
        color: #818cf8;
        margin: 0 0 12px 0;
        font-size: 1.3em;
    }
    .pick-card .metric {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #1e293b;
    }
    .pick-card .metric:last-child { border-bottom: none; }
    .pick-card .label { color: #94a3b8; font-size: 0.9em; }
    .pick-card .value { color: #f1f5f9; font-weight: 600; }
    .pick-card .target { color: #34d399; }
    .pick-card .stop   { color: #f87171; }

    /* ── Section Headers ────────────────────────── */
    .section-header {
        color: #818cf8;
        font-size: 1.6em;
        font-weight: 700;
        margin-top: 32px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #334155;
    }

    /* ── Sidebar ────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #0f172a;
    }

    /* ── Metrics override ───────────────────────── */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        color: #818cf8;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/stock-market.png", width=64)
    st.title("EGX Intelligence")
    st.caption("Egyptian Stock Exchange Analyzer")
    st.markdown("---")

    # Date selector — lets you review past reports.
    selected_date = st.date_input(
        "📅 Report Date",
        value=date.today(),
        max_value=date.today(),
    )
    selected_date_str = selected_date.isoformat()

    st.markdown("---")
    st.markdown("### ⚙️ Thresholds")
    st.markdown(f"- RSI Oversold: **< {config.RSI_OVERSOLD}**")
    st.markdown(f"- Volume Spike: **≥ {config.VOLUME_SPIKE_MULTIPLIER}×**")
    st.markdown(f"- Target: **+{config.TARGET_PCT*100:.0f}%**")
    st.markdown(f"- Stop-Loss: **-{config.STOP_LOSS_PCT*100:.0f}%**")

    st.markdown("---")
    st.markdown(
        "⚠️ *This is NOT financial advice. "
        "Always do your own research.*"
    )


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='text-align:center; color:#818cf8;'>"
    f"📈 EGX Intelligence Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='text-align:center; color:#94a3b8; font-size:1.1em;'>"
    f"Report for {selected_date_str} · "
    f"Generated at {datetime.now().strftime('%H:%M CLT')}</p>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# INITIALIZE DATABASE
# ─────────────────────────────────────────────────────────────
try:
    database.init_db()
except Exception as e:
    st.error(f"Database initialization error: {e}")

# ─────────────────────────────────────────────────────────────
# TOP 3 PICKS
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏆 Top 3 Picks</div>', unsafe_allow_html=True)

picks = database.get_latest_picks(selected_date_str)

if picks:
    cols = st.columns(len(picks))
    for col, pick in zip(cols, picks):
        with col:
            signal_color = "#34d399" if pick.get("signal_type") == "Strong Signal" else "#fbbf24"
            st.markdown(f"""
            <div class="pick-card">
                <h3>#{pick.get('rank', '-')} {pick.get('name', 'N/A')}</h3>
                <div class="metric">
                    <span class="label">💰 Entry</span>
                    <span class="value">{pick.get('entry_price', 0):.2f} EGP</span>
                </div>
                <div class="metric">
                    <span class="label">🎯 Target</span>
                    <span class="value target">{pick.get('target_price', 0):.2f} EGP</span>
                </div>
                <div class="metric">
                    <span class="label">🛑 Stop-Loss</span>
                    <span class="value stop">{pick.get('stop_loss', 0):.2f} EGP</span>
                </div>
                <div class="metric">
                    <span class="label">📊 RSI</span>
                    <span class="value">{pick.get('rsi', 0):.1f}</span>
                </div>
                <div class="metric">
                    <span class="label">📈 Volume Spike</span>
                    <span class="value">{pick.get('volume_spike', 1.0):.1f}×</span>
                </div>
                <div style="margin-top:12px; text-align:center;">
                    <span style="background:{signal_color}; color:#000;
                           padding:4px 12px; border-radius:20px; font-weight:600;
                           font-size:0.85em;">
                        {pick.get('signal_type', 'Signal')}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info(
        "🔍 No picks available for this date. "
        "Run `python core_engine.py` to generate today's report."
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# MARKET OVERVIEW (Full Table)
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 EGX Market Overview</div>', unsafe_allow_html=True)

market_df = database.get_all_prices_for_date(selected_date_str)

if not market_df.empty:
    # Summary metrics row.
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Stocks", len(market_df))
    gainers  = len(market_df[market_df["Change_Pct"] > 0]) if "Change_Pct" in market_df else 0
    losers   = len(market_df[market_df["Change_Pct"] < 0]) if "Change_Pct" in market_df else 0
    m2.metric("📈 Gainers", gainers)
    m3.metric("📉 Losers", losers)
    avg_change = market_df["Change_Pct"].mean() if "Change_Pct" in market_df else 0
    m4.metric("Avg Change", f"{avg_change:+.2f}%")

    # Display the table with highlighting.
    st.dataframe(
        market_df.style.format({
            "Last":       "{:.2f}",
            "High":       "{:.2f}",
            "Low":        "{:.2f}",
            "Change_Pct": "{:+.2f}%",
            "Volume":     "{:,.0f}",
        }).applymap(
            lambda v: "color: #34d399" if isinstance(v, (int, float)) and v > 0
            else ("color: #f87171" if isinstance(v, (int, float)) and v < 0 else ""),
            subset=["Change_Pct"] if "Change_Pct" in market_df.columns else [],
        ),
        use_container_width=True,
        height=400,
    )
else:
    st.info("No market data available for this date.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# PRICE CHART (for Top Picks)
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Price Charts</div>', unsafe_allow_html=True)

if picks:
    # Let the user choose which pick to chart.
    pick_names = [p.get("name", "Unknown") for p in picks]
    selected_stock = st.selectbox("Select a stock to chart", pick_names)

    if selected_stock:
        history = database.get_historical_prices(selected_stock, days=60)

        if not history.empty:
            fig = go.Figure()

            # Candlestick-style line chart.
            fig.add_trace(go.Scatter(
                x=history["date"],
                y=history["Last"],
                mode="lines+markers",
                name="Price",
                line=dict(color="#818cf8", width=2),
                marker=dict(size=4),
            ))

            # High / Low band.
            fig.add_trace(go.Scatter(
                x=history["date"],
                y=history["High"],
                mode="lines",
                name="High",
                line=dict(color="#34d399", width=1, dash="dot"),
                opacity=0.5,
            ))
            fig.add_trace(go.Scatter(
                x=history["date"],
                y=history["Low"],
                mode="lines",
                name="Low",
                line=dict(color="#f87171", width=1, dash="dot"),
                opacity=0.5,
                fill="tonexty",
                fillcolor="rgba(248,113,113,0.05)",
            ))

            # Entry / Target / Stop-Loss lines from the pick.
            active_pick = next(
                (p for p in picks if p.get("name") == selected_stock), None
            )
            if active_pick:
                for level, color, label in [
                    ("entry_price",  "#818cf8", "Entry"),
                    ("target_price", "#34d399", "Target"),
                    ("stop_loss",    "#f87171", "Stop-Loss"),
                ]:
                    fig.add_hline(
                        y=active_pick.get(level, 0),
                        line_dash="dash",
                        line_color=color,
                        annotation_text=f"{label}: {active_pick.get(level, 0):.2f}",
                        annotation_font_color=color,
                    )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
                xaxis_title="Date",
                yaxis_title="Price (EGP)",
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                f"No historical data for {selected_stock} yet. "
                f"Data accumulates as the scraper runs daily."
            )
else:
    st.info("Generate picks first to see price charts.")

# ─────────────────────────────────────────────────────────────
# PICKS HISTORY
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">📜 Picks History</div>', unsafe_allow_html=True)

history_df = database.get_picks_history(days=30)
if not history_df.empty:
    st.dataframe(
        history_df.style.format({
            "entry_price":  "{:.2f}",
            "target_price": "{:.2f}",
            "stop_loss":    "{:.2f}",
            "rsi":          "{:.1f}",
            "volume_spike": "{:.1f}×",
        }),
        use_container_width=True,
        height=300,
    )
else:
    st.info("No historical picks yet. Run the engine daily to build history.")

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:0.85em;'>"
    "⚠️ Disclaimer: This tool is for educational purposes only. "
    "It does not constitute financial advice. Always consult a licensed "
    "financial advisor before making investment decisions.</p>",
    unsafe_allow_html=True,
)
