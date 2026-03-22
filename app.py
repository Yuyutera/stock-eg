"""
app.py — Premium EGX Intelligence Dashboard
=============================================
Professional trading terminal dashboard built with Streamlit.
Inspired by Bloomberg/Refinitiv — clean, dark, data-dense.
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
    page_icon="📈",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# GLOBAL STYLES — Bloomberg/Refinitiv professional aesthetic
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Base ─────────────────────────────────── */
    .stApp {
        background-color: #0a0e17;
        font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #e2e8f0;
    }
    [data-testid="stSidebar"] {
        background-color: #0d1117 !important;
        border-right: 1px solid #1f2937;
    }

    /* ── Typography ───────────────────────────── */
    h1, h2, h3, h4 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 600 !important;
        color: #f1f5f9 !important;
    }
    .page-title {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #f8fafc;
        text-align: center;
        text-shadow: 0 0 30px rgba(59, 130, 246, 0.3);
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    }
    .page-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 0.85rem;
        margin-bottom: 24px;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* ── Card system ──────────────────────────── */
    .card {
        background: #111827;
        border: 1px solid #1f2937;
        border-top: 2px solid #3b82f6;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .card-warn {
        border-top-color: #f59e0b;
    }
    .card-danger {
        border-top-color: #ef4444;
    }
    .card-success {
        border-top-color: #10b981;
    }

    /* ── Ticker badge ─────────────────────────── */
    .ticker-badge {
        display: inline-block;
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.4);
        color: #93c5fd;
        padding: 3px 10px;
        border-radius: 3px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* ── Price display ────────────────────────── */
    .price-display {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: #f8fafc;
        margin: 8px 0;
    }

    /* ── Metric grid ──────────────────────────── */
    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 12px;
    }
    .metric-cell {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid #1f2937;
        border-radius: 4px;
        padding: 8px;
        text-align: center;
    }
    .metric-label {
        color: #64748b;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.05rem;
        color: #e2e8f0;
        font-weight: 500;
    }
    .val-green { color: #10b981; }
    .val-red { color: #ef4444; }
    .val-blue { color: #3b82f6; }
    .val-amber { color: #f59e0b; }

    /* ── Signal strength bar ──────────────────── */
    .strength-bar-container {
        background: #1e293b;
        border-radius: 3px;
        height: 6px;
        width: 100%;
        margin-top: 6px;
    }
    .strength-bar {
        height: 6px;
        border-radius: 3px;
        transition: width 0.3s ease;
    }

    /* ── Signal reason ────────────────────────── */
    .signal-reason {
        color: #64748b;
        font-size: 0.7rem;
        font-family: 'IBM Plex Mono', monospace;
        margin-top: 6px;
        line-height: 1.4;
    }

    /* ── Market banner ────────────────────────── */
    .market-banner {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 12px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
    }
    .market-banner-warn {
        border-color: #ef4444;
        background: rgba(239, 68, 68, 0.08);
    }

    /* ── Stat card (performance) ──────────────── */
    .stat-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 16px;
        text-align: center;
    }
    .stat-label {
        color: #64748b;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .stat-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.8rem;
        font-weight: 600;
    }

    /* ── Badge (gainers / losers) ─────────────── */
    .count-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .badge-green {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-red {
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* ── Table styling ────────────────────────── */
    .outcome-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.85rem;
    }
    .outcome-table th {
        background: #1e293b;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.5px;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid #334155;
    }
    .outcome-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #1f2937;
        color: #cbd5e1;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
    }
    .outcome-table tr:hover {
        background: rgba(59, 130, 246, 0.05);
    }
    .outcome-hit-target { color: #10b981; font-weight: 600; }
    .outcome-hit-stop { color: #ef4444; font-weight: 600; }
    .outcome-pending { color: #f59e0b; }
    .outcome-expired { color: #64748b; }

    /* ── Section header ───────────────────────── */
    .section-header {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #f1f5f9;
        margin: 28px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #1f2937;
    }

    /* ── Sidebar ──────────────────────────────── */
    .sidebar-title {
        color: #3b82f6;
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.5px;
    }

    /* ── Footer ───────────────────────────────── */
    .footer {
        text-align: center;
        color: #475569;
        font-size: 0.7rem;
        padding: 20px 0;
        font-family: 'IBM Plex Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def _strength_color(score: float) -> str:
    """Return CSS color based on confidence score."""
    if score >= 70:
        return "#10b981"
    elif score >= 40:
        return "#f59e0b"
    else:
        return "#ef4444"


def _outcome_css_class(outcome: str) -> str:
    """Return CSS class for outcome display."""
    mapping = {
        "HIT_TARGET": "outcome-hit-target",
        "HIT_STOP": "outcome-hit-stop",
        "PENDING": "outcome-pending",
        "EXPIRED": "outcome-expired",
    }
    return mapping.get(outcome, "outcome-pending")


def _format_pnl(entry: float, exit_price: float) -> str:
    """Calculate and format P&L percentage."""
    if entry <= 0:
        return "—"
    pnl = ((exit_price - entry) / entry) * 100
    sign = "+" if pnl > 0 else ""
    return f"{sign}{pnl:.1f}%"


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">COMMAND CENTER</div>', unsafe_allow_html=True)
    st.markdown("")
    selected_date = st.date_input(
        "Target Date", value=date.today(), max_value=date.today()
    )
    selected_date_str = selected_date.isoformat()
    st.markdown("---")
    st.markdown("**Parameters**")
    st.info(
        f"RSI Threshold: {config.RSI_OVERSOLD}\n\n"
        f"Volume Spike: {config.VOLUME_SPIKE_MULTIPLIER}×\n\n"
        f"Min Volume: {config.MIN_DAILY_VOLUME:,.0f}\n\n"
        f"Max Hold: {config.MAX_HOLDING_DAYS} days"
    )
    st.caption("EGX Intelligence System v3.0")


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">EGX Intelligence Hub</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-subtitle">'
    f'{datetime.now().strftime("%H:%M")} · {selected_date_str}'
    f'</div>',
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────
database.init_db()
picks = database.get_latest_picks(selected_date_str)
market_df = database.get_all_prices_for_date(selected_date_str)


# ─────────────────────────────────────────────────────────────
# HISTORY PROGRESS BAR (data accumulation phase)
# ─────────────────────────────────────────────────────────────
MIN_HISTORY = config.MIN_HISTORY_DAYS
history_days = database.get_available_history_days()

if history_days < MIN_HISTORY:
    remaining = MIN_HISTORY - history_days
    progress = history_days / MIN_HISTORY
    st.warning(
        f"📊 **Data accumulation in progress** — "
        f"{history_days}/{MIN_HISTORY} trading days collected. "
        f"Signals will activate in **{remaining}** more trading days."
    )
    st.progress(progress)


# ─────────────────────────────────────────────────────────────
# EGX 30 MARKET CONTEXT BANNER
# ─────────────────────────────────────────────────────────────
if not market_df.empty and "Change_Pct" in market_df.columns:
    total_stocks = len(market_df)
    gainers = int((market_df["Change_Pct"] > 0).sum())
    losers = int((market_df["Change_Pct"] < 0).sum())
    unchanged = total_stocks - gainers - losers
    decline_ratio = losers / total_stocks if total_stocks > 0 else 0
    avg_change = market_df["Change_Pct"].mean()
    market_direction = "▲" if avg_change >= 0 else "▼"
    dir_color = "#10b981" if avg_change >= 0 else "#ef4444"

    is_broad_weakness = decline_ratio > 0.6
    banner_class = "market-banner market-banner-warn" if is_broad_weakness else "market-banner"

    warning_html = ""
    if is_broad_weakness:
        warning_html = (
            '<span style="color:#ef4444; font-weight:600;">'
            '⚠ Broad market weakness — treat signals with extra caution'
            '</span>'
        )

    st.markdown(
        f'<div class="{banner_class}">'
        f'<span>Market <span style="color:{dir_color}; font-weight:600;">'
        f'{market_direction} {avg_change:+.2f}%</span></span>'
        f'<span>'
        f'<span class="count-badge badge-green">📈 {gainers}</span> '
        f'<span class="count-badge badge-red" style="margin-left:8px;">📉 {losers}</span> '
        f'<span style="color:#64748b; margin-left:8px;">Flat: {unchanged}</span>'
        f'</span>'
        f'{warning_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# HIGH-CONVICTION SIGNALS
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">⚡ High-Conviction Signals</div>', unsafe_allow_html=True)

if picks:
    cols = st.columns(min(len(picks), 3))
    for i, col in enumerate(cols):
        if i < len(picks):
            pick = picks[i]
            with col:
                name = pick.get("name", "N/A")
                entry = pick.get("entry_price", 0) or 0
                target = pick.get("target_price", 0) or 0
                stop = pick.get("stop_loss", 0) or 0
                rsi = pick.get("rsi", 0) or 0
                vol_spike = pick.get("volume_spike", 1.0) or 1.0
                confidence = pick.get("confidence_score", 0) or 0
                signal_reason = pick.get("signal_reason", "")

                # Confidence bar color
                conf_color = _strength_color(confidence)

                card_html = f"""<div class="card">
<div class="ticker-badge">{name}</div>
<div class="signal-reason">{signal_reason}</div>
<div class="price-display">{entry:.2f} <span style="color:#64748b; font-size:0.9rem;">EGP</span></div>
<div style="margin-top:4px;">
    <div class="metric-label">Signal Strength</div>
    <div style="display:flex; align-items:center; gap:8px;">
        <div class="strength-bar-container" style="flex:1;">
            <div class="strength-bar" style="width:{min(confidence, 100):.0f}%; background:{conf_color};"></div>
        </div>
        <span style="color:{conf_color}; font-family:'IBM Plex Mono',monospace; font-size:0.8rem; font-weight:600;">{confidence:.0f}%</span>
    </div>
</div>
<div class="metric-grid">
    <div class="metric-cell">
        <div class="metric-label">Target</div>
        <div class="metric-value val-green">{target:.2f}</div>
    </div>
    <div class="metric-cell">
        <div class="metric-label">Stop Loss</div>
        <div class="metric-value val-red">{stop:.2f}</div>
    </div>
    <div class="metric-cell">
        <div class="metric-label">RSI</div>
        <div class="metric-value">{rsi:.1f}</div>
    </div>
    <div class="metric-cell">
        <div class="metric-label">Vol Spike</div>
        <div class="metric-value">{vol_spike:.1f}×</div>
    </div>
</div>
</div>"""
                st.markdown(card_html, unsafe_allow_html=True)
else:
    st.info("No signals detected for this date.")


# ─────────────────────────────────────────────────────────────
# LIVE PICK TRACKER
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📍 Live Pick Tracker</div>', unsafe_allow_html=True)

# Bug fix 1: Date-aware pick tracker.
# If selected date is today, show pending picks.
# If it's a past date, show all picks from that date.
is_today = selected_date == date.today()
if is_today:
    all_picks_for_tracker = database.get_pending_picks()
else:
    all_picks_for_tracker = database.get_latest_picks(selected_date_str)

if all_picks_for_tracker:
    for idx, pick in enumerate(all_picks_for_tracker):
        name = pick.get("name", "Unknown")
        entry = pick.get("entry_price", 0) or 0
        target = pick.get("target_price", 0)
        stop = pick.get("stop_loss", 0)
        pick_date = pick.get("date", selected_date_str)

        journey = database.get_pick_price_journey(name, pick_date)
        if not journey or entry == 0:
            continue

        latest_price = journey[-1]["price"] if journey[-1]["price"] else entry
        latest_pnl = ((latest_price - entry) / entry) * 100
        pnl_color = "#10b981" if latest_pnl >= 0 else "#ef4444"
        pnl_sign = "+" if latest_pnl >= 0 else ""

        # Header for each pick
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px;">'
            f'<span class="ticker-badge">{name}</span>'
            f'<span style="font-family:\'IBM Plex Mono\',monospace; color:{pnl_color}; '
            f'font-weight:600; font-size:1.1rem;">{pnl_sign}{latest_pnl:.1f}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if len(journey) > 1:
            dates = [d["date"] for d in journey]
            prices = [d["price"] for d in journey]
            fig_spark = go.Figure()
            fig_spark.add_trace(go.Scatter(
                x=dates, y=prices, mode="lines+markers",
                line=dict(color=pnl_color, width=2.5),
                marker=dict(size=6, color=pnl_color, line=dict(width=1.5, color="#0a0e17")),
                fill="none",
                hovertemplate="<b>%{x}</b><br>Price: %{y:.2f} EGP<extra></extra>",
            ))
            for val, color, dash, label in [
                (entry, "#3b82f6", "dot", f"Entry: {entry:.2f}"),
                (target, "#10b981", "dot", f"Target: {target:.2f}"),
                (stop, "#ef4444", "dot", f"Stop: {stop:.2f}"),
            ]:
                fig_spark.add_hline(
                    y=val, line_dash=dash, line_color=color,
                    annotation_text=label, annotation_font_color=color,
                    annotation_font_size=10,
                )
            # Current price annotation
            if prices:
                fig_spark.add_annotation(
                    x=dates[-1], y=prices[-1],
                    text=f" {prices[-1]:.2f}",
                    showarrow=False,
                    font=dict(size=11, color=pnl_color, family="IBM Plex Mono"),
                    xanchor="left",
                )
            # Tight Y-axis bounds from actual data + reference lines
            all_values = [p for p in prices if p is not None] + [entry, target, stop]
            y_min = min(all_values) * 0.98
            y_max = max(all_values) * 1.02
            fig_spark.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=180,
                showlegend=False,
                margin=dict(l=0, r=60, t=10, b=0),
                yaxis=dict(
                    showgrid=True, gridcolor="rgba(31,41,55,0.5)",
                    range=[y_min, y_max],
                    tickformat=".2f",
                    tickfont=dict(size=10, family="IBM Plex Mono"),
                ),
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(size=10, family="IBM Plex Mono"),
                ),
            )
            # Bug fix 2: unique key with enumerate index
            st.plotly_chart(
                fig_spark, use_container_width=True,
                key=f"spark_{name}_{pick_date}_{idx}"
            )
else:
    st.info("No pending picks to track.")


# ─────────────────────────────────────────────────────────────
# TWO-COLUMN LAYOUT: TRAJECTORY + MARKET FLOW
# ─────────────────────────────────────────────────────────────
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown('<div class="section-header">📈 Trajectory Analysis</div>', unsafe_allow_html=True)
    if picks:
        selected_stock = st.selectbox(
            "Focus Asset",
            [p.get("name") for p in picks],
            label_visibility="collapsed",
        )
        active_pick = next((p for p in picks if p.get("name") == selected_stock), None)
        history = database.get_historical_prices(selected_stock, days=60)

        if active_pick:
            entry = active_pick.get("entry_price", 0)
            target = active_pick.get("target_price", 0)
            stop = active_pick.get("stop_loss", 0)

            if not history.empty and len(history) >= 5:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history["date"], y=history["Last"],
                    mode="lines+markers",
                    line=dict(color="#3b82f6", width=2.5),
                    marker=dict(size=4, color="#3b82f6", line=dict(width=1, color="#0a0e17")),
                    fill="none",
                    hovertemplate="<b>%{x}</b><br>Price: %{y:.2f} EGP<extra></extra>",
                ))
                for val, color, label in [
                    (entry, "#3b82f6", f"Entry: {entry:.2f}"),
                    (target, "#10b981", f"Target: {target:.2f}"),
                    (stop, "#ef4444", f"Stop: {stop:.2f}"),
                ]:
                    fig.add_hline(
                        y=val, line_dash="dash", line_color=color,
                        annotation_text=label, annotation_font_color=color,
                        annotation_font_size=10,
                    )
                # Tight Y-axis bounds from actual data + reference lines
                all_values = list(history["Last"].dropna()) + [entry, target, stop]
                y_min = min(all_values) * 0.98
                y_max = max(all_values) * 1.02
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=360,
                    margin=dict(l=0, r=60, t=20, b=0),
                    xaxis=dict(
                        showgrid=False,
                        tickfont=dict(size=10, family="IBM Plex Mono"),
                    ),
                    yaxis=dict(
                        showgrid=True, gridcolor="rgba(31,41,55,0.5)",
                        range=[y_min, y_max],
                        tickformat=".2f",
                        tickfont=dict(size=10, family="IBM Plex Mono"),
                    ),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough price history for trajectory chart.")
    else:
        st.info("Select a date with signals to view trajectory.")

with right_col:
    st.markdown('<div class="section-header">📊 Market Flow</div>', unsafe_allow_html=True)
    if not market_df.empty and "Change_Pct" in market_df.columns:
        # Bug fix 3: Replace AVG MARKET DELTA with gainers/losers badges
        gainers_count = int((market_df["Change_Pct"] > 0).sum())
        losers_count = int((market_df["Change_Pct"] < 0).sum())

        st.markdown(
            f'<div style="display:flex; gap:12px; margin-bottom:16px;">'
            f'<span class="count-badge badge-green" style="flex:1; text-align:center;">📈 Gainers: {gainers_count}</span>'
            f'<span class="count-badge badge-red" style="flex:1; text-align:center;">📉 Losers: {losers_count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Top and bottom movers bar chart
        top_movers = market_df.nlargest(5, "Change_Pct")
        bottom_movers = market_df.nsmallest(5, "Change_Pct")
        movers = pd.concat([top_movers, bottom_movers]).sort_values("Change_Pct", ascending=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=movers["Name"], x=movers["Change_Pct"],
            orientation="h",
            marker_color=[
                "#10b981" if v > 0 else "#ef4444" for v in movers["Change_Pct"]
            ],
            text=[f"{v:+.1f}%" for v in movers["Change_Pct"]],
            textposition="outside",
            textfont=dict(size=11, family="IBM Plex Mono"),
        ))
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=0, r=40, t=10, b=0),
            xaxis=dict(visible=False),
            yaxis=dict(tickfont=dict(size=10, family="IBM Plex Mono")),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No market data for this date.")


# ─────────────────────────────────────────────────────────────
# PERFORMANCE TRACKER
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏆 Performance Tracker</div>', unsafe_allow_html=True)

stats = database.get_performance_stats()
p1, p2, p3, p4, p5 = st.columns(5)

wr = stats["win_rate"]
wr_color = "#10b981" if wr >= 50 else "#ef4444"

p1.markdown(
    f'<div class="stat-card">'
    f'<div class="stat-label">Win Rate</div>'
    f'<div class="stat-value" style="color:{wr_color};">{wr:.0f}%</div>'
    f'</div>',
    unsafe_allow_html=True,
)
p2.markdown(
    f'<div class="stat-card">'
    f'<div class="stat-label">Total Picks</div>'
    f'<div class="stat-value" style="color:#e2e8f0;">{stats["total"]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
p3.markdown(
    f'<div class="stat-card">'
    f'<div class="stat-label">Wins</div>'
    f'<div class="stat-value val-green">{stats["wins"]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
p4.markdown(
    f'<div class="stat-card">'
    f'<div class="stat-label">Losses</div>'
    f'<div class="stat-value val-red">{stats["losses"]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
p5.markdown(
    f'<div class="stat-card">'
    f'<div class="stat-label">Pending</div>'
    f'<div class="stat-value" style="color:#f59e0b;">{stats["pending"]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# RECENT OUTCOMES TABLE
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Recent Outcomes</div>', unsafe_allow_html=True)

recent_outcomes = database.get_recent_outcomes(limit=15)
if recent_outcomes:
    cumulative_pnl = 0.0
    table_rows = ""
    for r in recent_outcomes:
        entry_p = r.get("entry_price", 0) or 0
        out_p = r.get("outcome_price", 0) or 0
        name = r.get("name", "Unknown")
        outcome = r.get("outcome", "PENDING")
        pick_date = r.get("date", "")
        confidence = r.get("confidence_score", 0) or 0

        # Calculate P&L
        if outcome in ("HIT_TARGET", "HIT_STOP") and entry_p > 0 and out_p > 0:
            pnl = ((out_p - entry_p) / entry_p) * 100
            cumulative_pnl += pnl
            pnl_class = "val-green" if pnl > 0 else "val-red"
            pnl_str = f'<span class="{pnl_class}">{pnl:+.1f}%</span>'
            exit_str = f"{out_p:.2f}"
        elif outcome == "EXPIRED" and entry_p > 0 and out_p > 0:
            pnl = ((out_p - entry_p) / entry_p) * 100
            cumulative_pnl += pnl
            pnl_class = "val-green" if pnl > 0 else "val-red"
            pnl_str = f'<span class="{pnl_class}">{pnl:+.1f}%</span>'
            exit_str = f"{out_p:.2f}"
        else:
            pnl_str = '<span style="color:#64748b;">—</span>'
            exit_str = "—"

        outcome_class = _outcome_css_class(outcome)
        conf_color = _strength_color(confidence)

        table_rows += f"""<tr>
            <td style="font-weight:500;">{name}</td>
            <td>{pick_date}</td>
            <td><span style="color:{conf_color};">{confidence:.0f}%</span></td>
            <td>{entry_p:.2f}</td>
            <td>{exit_str}</td>
            <td>{pnl_str}</td>
            <td><span class="{outcome_class}">{outcome}</span></td>
        </tr>"""

    cum_pnl_color = "#10b981" if cumulative_pnl >= 0 else "#ef4444"
    cum_pnl_sign = "+" if cumulative_pnl > 0 else ""

    st.markdown(
        f"""<table class="outcome-table">
        <thead>
            <tr>
                <th>Stock</th>
                <th>Date</th>
                <th>Strength</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>P&L</th>
                <th>Outcome</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
            <tr style="border-top:2px solid #334155;">
                <td colspan="5" style="text-align:right; font-weight:600; color:#94a3b8;">
                    Cumulative P&L
                </td>
                <td colspan="2" style="font-weight:700; font-size:1rem; color:{cum_pnl_color};">
                    {cum_pnl_sign}{cumulative_pnl:.1f}%
                </td>
            </tr>
        </tbody>
        </table>""",
        unsafe_allow_html=True,
    )
else:
    st.info("No outcomes recorded yet.")


# ─────────────────────────────────────────────────────────────
# HISTORICAL PICKS (raw data table)
# ─────────────────────────────────────────────────────────────
hist_picks = database.get_picks_history(days=30)
if not hist_picks.empty:
    st.markdown('<div class="section-header">📂 Pick History (30 Days)</div>', unsafe_allow_html=True)
    st.dataframe(hist_picks, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="footer">EGX INTELLIGENCE SYSTEM v3.0 · FOR INFORMATIONAL PURPOSES ONLY · NO INVESTMENT ADVICE IMPLIED</div>',
    unsafe_allow_html=True,
)
