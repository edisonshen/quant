"""
TQQQ Strategy — All Combos (2-50) × 3 MA Types → Top 20 HTML Report

Tests every entry/exit period from 2 to 50 across EMA/SMA, EMA/EMA, SMA/SMA.
Total combos: 49×49×3 = 7,203. Outputs top 20 by Calmar ratio.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path

INITIAL_CAPITAL = 100_000
CASH_YIELD = 0.045
MIN_PERIOD = 2
MAX_PERIOD = 50
TOP_N = 20

REPORT_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORT_DIR / "tqqq_top20_all_combos.html"
CSV_PATH = REPORT_DIR / "tqqq_all_combos_raw.csv"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def fetch_data(years: int = 10) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=years * 365)

    qqq = yf.download("QQQ", start=start, end=end, auto_adjust=True)
    tqqq = yf.download("TQQQ", start=start, end=end, auto_adjust=True)

    if isinstance(qqq.columns, pd.MultiIndex):
        qqq.columns = qqq.columns.get_level_values(0)
    if isinstance(tqqq.columns, pd.MultiIndex):
        tqqq.columns = tqqq.columns.get_level_values(0)

    df = pd.DataFrame(index=qqq.index)
    df["qqq_close"] = qqq["Close"]
    df["tqqq_close"] = tqqq["Close"]
    df = df.dropna()
    df["tqqq_return"] = df["tqqq_close"].pct_change().fillna(0)
    df["qqq_return"] = df["qqq_close"].pct_change().fillna(0)
    return df


def precompute_mas(df: pd.DataFrame) -> dict:
    """Precompute all EMAs and SMAs for periods 2-50 to avoid redundant calculation."""
    mas = {}
    close = df["qqq_close"]
    for p in range(MIN_PERIOD, MAX_PERIOD + 1):
        mas[("ewm", p)] = close.ewm(span=p, adjust=False).mean()
        mas[("rolling", p)] = close.rolling(window=p).mean()
    return mas


def run_backtest(
    df: pd.DataFrame,
    entry_ma: pd.Series,
    exit_ma: pd.Series,
    entry_period: int,
    exit_period: int,
    entry_type: str,
    exit_type: str,
    strategy_name: str,
) -> dict:
    data = df.copy()
    data["entry_ma"] = entry_ma
    data["exit_ma"] = exit_ma

    entry_prefix = "EMA" if entry_type == "ewm" else "SMA"
    exit_prefix = "EMA" if exit_type == "ewm" else "SMA"

    warmup = max(entry_period, exit_period) + 5
    data = data.dropna()
    data = data.iloc[warmup:].copy()

    # Vectorized position tracking
    close = data["qqq_close"].values
    entry_vals = data["entry_ma"].values
    exit_vals = data["exit_ma"].values

    position = 0
    positions = np.empty(len(data), dtype=np.int8)
    for i in range(len(data)):
        if position == 0 and close[i] >= entry_vals[i]:
            position = 1
        elif position == 1 and close[i] < exit_vals[i]:
            position = 0
        positions[i] = position

    data["position"] = positions
    shifted = np.roll(positions, 1)
    shifted[0] = 0
    data["pos_shifted"] = shifted

    daily_cash = (1 + CASH_YIELD) ** (1 / 252) - 1
    tqqq_ret = data["tqqq_return"].values
    pos = data["pos_shifted"].values
    strat_return = np.where(pos == 1, tqqq_ret, daily_cash)
    data["strat_return"] = strat_return
    data["equity"] = INITIAL_CAPITAL * np.cumprod(1 + strat_return)

    final = data["equity"].iloc[-1]
    years = len(data) / 252
    cagr = (final / INITIAL_CAPITAL) ** (1 / years) - 1

    peak = np.maximum.accumulate(data["equity"].values)
    dd = (data["equity"].values - peak) / peak
    max_dd = dd.min()

    std = strat_return.std()
    sharpe = strat_return.mean() / std * np.sqrt(252) if std > 0 else 0

    neg_returns = strat_return[strat_return < 0]
    downside = neg_returns.std() if len(neg_returns) > 0 else 0
    sortino = strat_return.mean() / downside * np.sqrt(252) if downside > 0 else 0

    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    time_in_market = pos.mean()

    trade_changes = np.diff(pos, prepend=0)
    entries_mask = trade_changes == 1
    exits_mask = trade_changes == -1
    num_trades = entries_mask.sum()

    entry_idx = np.where(entries_mask)[0]
    exit_idx = np.where(exits_mask)[0]
    equity_vals = data["equity"].values

    trade_returns = []
    ei_ptr = 0
    for xi in exit_idx:
        while ei_ptr < len(entry_idx) and entry_idx[ei_ptr] >= xi:
            ei_ptr += 1
        if ei_ptr > 0:
            ei = entry_idx[ei_ptr - 1]
            if xi > ei:
                trade_returns.append(equity_vals[xi] / equity_vals[ei] - 1)

    trade_wr = np.mean([r > 0 for r in trade_returns]) if trade_returns else 0

    data["year"] = data.index.year
    yearly = data.groupby("year")["strat_return"].apply(lambda x: (1 + x).prod() - 1)

    # Per-year Calmar: yearly_return / abs(yearly_max_drawdown)
    yearly_calmar = {}
    for year, grp in data.groupby("year"):
        yr_eq = grp["equity"]
        yr_return = yearly[year]
        yr_peak = yr_eq.cummax()
        yr_dd = ((yr_eq - yr_peak) / yr_peak).min()
        yearly_calmar[year] = yr_return / abs(yr_dd) if yr_dd != 0 else (10.0 if yr_return > 0 else 0.0)

    # --- Stability Score (composite) ---
    # See docs/stability_score.md for full rationale
    #
    # 1. Consistency: std of rolling 12-month Sharpe (lower = more consistent)
    rolling_ret = pd.Series(strat_return, index=data.index)
    rolling_sharpe = (
        rolling_ret.rolling(252).mean() / rolling_ret.rolling(252).std()
    ) * np.sqrt(252)
    rolling_sharpe = rolling_sharpe.dropna()
    rolling_sharpe_std = rolling_sharpe.std() if len(rolling_sharpe) > 0 else 10.0
    consistency = 1.0 / (1.0 + rolling_sharpe_std)

    # 2. Win frequency: % of months with positive return
    monthly_ret = rolling_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    pct_months_positive = (monthly_ret > 0).mean() if len(monthly_ret) > 0 else 0.0

    # 3. Pain avoidance: Ulcer Index = sqrt(mean(drawdown%^2))
    dd_pct = pd.Series(dd, index=data.index) * 100  # dd is already negative
    ulcer_index = np.sqrt((dd_pct ** 2).mean())
    pain_avoidance = 1.0 / (1.0 + ulcer_index)

    # Composite: 0.5 consistency + 0.3 win frequency + 0.2 pain avoidance
    stability_score = 0.5 * consistency + 0.3 * pct_months_positive + 0.2 * pain_avoidance

    label = f"{entry_prefix}{entry_period}/{exit_prefix}{exit_period}"

    return {
        "label": label,
        "strategy": strategy_name,
        "entry_period": entry_period,
        "exit_period": exit_period,
        "cagr": cagr,
        "total_return": final / INITIAL_CAPITAL - 1,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "num_trades": num_trades,
        "trade_wr": trade_wr,
        "time_in_market": time_in_market,
        "final_equity": final,
        "equity_series": data[["equity"]].copy(),
        "drawdown_series": pd.Series(dd, index=data.index),
        "yearly": yearly.to_dict(),
        "yearly_calmar": yearly_calmar,
        "stability_score": stability_score,
        "consistency": consistency,
        "rolling_sharpe_std": rolling_sharpe_std,
        "pct_months_positive": pct_months_positive,
        "ulcer_index": ulcer_index,
        "pain_avoidance": pain_avoidance,
    }


def compute_benchmark(df: pd.DataFrame, col: str, label: str) -> dict:
    data = df.copy()
    data["bh_return"] = data[col].pct_change().fillna(0)
    data["equity"] = INITIAL_CAPITAL * (1 + data["bh_return"]).cumprod()

    final = data["equity"].iloc[-1]
    years = len(data) / 252
    cagr = (final / INITIAL_CAPITAL) ** (1 / years) - 1

    peak = data["equity"].cummax()
    dd = (data["equity"] - peak) / peak
    max_dd = dd.min()

    std = data["bh_return"].std()
    sharpe = data["bh_return"].mean() / std * np.sqrt(252) if std > 0 else 0

    downside = data["bh_return"][data["bh_return"] < 0].std()
    sortino = data["bh_return"].mean() / downside * np.sqrt(252) if downside > 0 else 0

    calmar = cagr / abs(max_dd) if max_dd != 0 else 0

    data["year"] = data.index.year
    yearly = data.groupby("year")["bh_return"].apply(lambda x: (1 + x).prod() - 1)

    return {
        "label": label,
        "cagr": cagr,
        "total_return": final / INITIAL_CAPITAL - 1,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "num_trades": 1,
        "trade_wr": 1.0 if final > INITIAL_CAPITAL else 0.0,
        "time_in_market": 1.0,
        "final_equity": final,
        "equity_series": data[["equity"]].copy(),
        "drawdown_series": dd.copy(),
        "yearly": yearly.to_dict(),
    }


def _weekly(series: pd.Series) -> pd.Series:
    return series.resample("W").last().dropna()


def build_html(top_results: list, benchmarks: list, total_combos: int) -> str:
    def fmt_pct(v):
        color = "#4caf50" if v >= 0 else "#ef5350"
        return f'<span style="color:{color}">{v:.1%}</span>'

    def fmt_num(v):
        color = "#4caf50" if v >= 0 else "#ef5350"
        return f'<span style="color:{color}">{v:.2f}</span>'

    def fmt_dollar(v):
        color = "#4caf50" if v >= INITIAL_CAPITAL else "#ef5350"
        return f'<span style="color:{color}">${v:,.0f}</span>'

    # --- Summary table ---
    rows = ""
    for b in benchmarks:
        rows += f"""<tr style="background:#2a2a3e; font-weight:bold;">
            <td>—</td><td>{b['label']}</td><td>{fmt_pct(b['cagr'])}</td>
            <td>{fmt_pct(b['max_dd'])}</td>
            <td>{fmt_num(b['sharpe'])}</td>
            <td>{fmt_num(b['calmar'])}</td>
            <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>
            <td>{b['num_trades']}</td>
            <td>{fmt_pct(b['time_in_market'])}</td>
            <td>{fmt_dollar(b['final_equity'])}</td></tr>"""

    rows += '<tr style="height:4px;background:#555;"><td colspan="14"></td></tr>'

    strat_colors = {"EMA/SMA": "#ff9800", "EMA/EMA": "#2196f3", "SMA/SMA": "#4caf50"}
    for i, r in enumerate(top_results, 1):
        strat = r.get("strategy", "EMA/SMA")
        sc = strat_colors.get(strat, "#888")
        # Color composite rank score
        rs = r['rank_score']
        if rs >= 0.65:
            rs_color = "#4caf50"
        elif rs >= 0.50:
            rs_color = "#ffc107"
        else:
            rs_color = "#ef5350"
        # Color stability score
        ss = r['stability_score']
        if ss >= 0.55:
            ss_color = "#4caf50"
        elif ss >= 0.40:
            ss_color = "#ffc107"
        else:
            ss_color = "#ef5350"
        rows += f"""<tr>
            <td>{i}</td>
            <td><span style="color:{sc}">{strat}</span> {r['label']}</td>
            <td>{fmt_pct(r['cagr'])}</td>
            <td>{fmt_pct(r['max_dd'])}</td><td>{fmt_num(r['sharpe'])}</td>
            <td>{fmt_num(r['calmar'])}</td>
            <td><span style="color:{rs_color};font-weight:bold">{r['rank_score']:.3f}</span></td>
            <td><span style="color:{ss_color}">{r['stability_score']:.3f}</span></td>
            <td>{r['consistency']:.2f}</td>
            <td>{r['pct_months_positive']:.1%}</td>
            <td>{r['ulcer_index']:.1f}</td>
            <td>{r['num_trades']}</td>
            <td>{fmt_pct(r['time_in_market'])}</td>
            <td>{fmt_dollar(r['final_equity'])}</td></tr>"""

    summary_html = f"""
    <h2 id="summary">Top {TOP_N} Strategies — Composite Ranked</h2>
    <p>Tested {total_combos:,} combinations (periods {MIN_PERIOD}-{MAX_PERIOD} × 3 MA types).<br>
    <strong>Rank Score</strong> = 0.4 × Stability + 0.3 × CAGR percentile + 0.3 × (1 - |MaxDD| percentile)<br>
    <strong>Stability</strong> = 0.5 × Rolling Sharpe consistency + 0.3 × % months positive + 0.2 × (1/Ulcer Index)<br>
    See <code>docs/stability_score.md</code> for full methodology.</p>
    <table>
        <thead><tr>
            <th>#</th><th>Combo</th><th>CAGR</th><th>Max DD</th>
            <th>Sharpe</th><th>Calmar</th>
            <th style="color:#ffc107">Rank Score</th><th>Stability</th>
            <th>Consistency</th><th>Months +</th><th>Ulcer Idx</th>
            <th># Trades</th><th>In Market</th><th>Final Equity</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""

    # --- Equity curves (top 5 + benchmarks) ---
    fig_eq = go.Figure()
    colors = [
        "#ff9800", "#2196f3", "#4caf50", "#e91e63", "#9c27b0",
        "#00bcd4", "#ffc107", "#8bc34a", "#ff5722", "#673ab7",
        "#f44336", "#03a9f4", "#cddc39", "#ff4081", "#7c4dff",
        "#18ffff", "#ffab40", "#b2ff59", "#ff6e40", "#e040fb",
    ]
    for i, r in enumerate(top_results):
        eq = _weekly(r["equity_series"]["equity"])
        fig_eq.add_trace(go.Scatter(
            x=eq.index, y=eq.values, name=r["label"],
            line=dict(color=colors[i % len(colors)], width=2 if i < 5 else 1),
            opacity=1.0 if i < 5 else 0.6,
        ))
    for b in benchmarks:
        eq = _weekly(b["equity_series"]["equity"])
        dash = "dash" if "TQQQ" in b["label"] else "dot"
        fig_eq.add_trace(go.Scatter(
            x=eq.index, y=eq.values, name=b["label"],
            line=dict(color="#888", width=1.5, dash=dash),
        ))
    fig_eq.update_layout(
        title=f"Equity Curves: Top {TOP_N} by Calmar + Benchmarks",
        yaxis_title="Equity ($)", yaxis_type="log", height=600,
        template="plotly_dark", paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        legend=dict(x=0.01, y=0.99), hovermode="x unified",
    )
    equity_html = f"""
    <h2 id="equity">Equity Curves</h2>
    <div>{fig_eq.to_html(full_html=False, include_plotlyjs=False)}</div>"""

    # --- Yearly Calmar heatmap (new section) ---
    yc_labels = [r["label"] for r in top_results]
    yc_years = sorted(set(y for r in top_results for y in r["yearly_calmar"].keys()))
    yc_z = []
    yc_text = []
    for r in top_results:
        row = []
        text_row = []
        for year in yc_years:
            val = r["yearly_calmar"].get(year, None)
            if val is not None:
                row.append(round(val, 2))
                text_row.append(f"{val:.2f}")
            else:
                row.append(None)
                text_row.append("")
        yc_z.append(row)
        yc_text.append(text_row)

    fig_yc = go.Figure(data=go.Heatmap(
        z=yc_z,
        x=[str(y) for y in yc_years],
        y=yc_labels,
        text=yc_text,
        texttemplate="%{text}",
        textfont={"size": 11},
        colorscale=[
            [0, "#d32f2f"], [0.3, "#ef5350"], [0.5, "#ffffff"],
            [0.7, "#66bb6a"], [1.0, "#1b5e20"],
        ],
        zmid=0,
        colorbar=dict(title="Calmar"),
    ))
    fig_yc.update_layout(
        title="Yearly Calmar Ratio by Strategy (consistency check)",
        height=max(500, len(yc_labels) * 35 + 100),
        template="plotly_dark", paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=140),
    )
    yearly_calmar_html = f"""
    <h2 id="yr-calmar">Yearly Calmar Heatmap</h2>
    <p>Per-year Calmar = year return / abs(year max drawdown). Green = strong risk-adjusted year, red = poor. Look for rows with consistently green cells.</p>
    <div>{fig_yc.to_html(full_html=False, include_plotlyjs=False)}</div>"""

    # --- Yearly returns heatmap ---
    all_items = benchmarks + top_results
    all_years = sorted(set(y for item in all_items for y in item["yearly"].keys()))
    labels = [item["label"] for item in all_items]
    z_data = []
    text_data = []
    for item in all_items:
        row = []
        text_row = []
        for year in all_years:
            val = item["yearly"].get(year, None)
            if val is not None:
                row.append(round(val * 100, 1))
                text_row.append(f"{val:.1%}")
            else:
                row.append(None)
                text_row.append("")
        z_data.append(row)
        text_data.append(text_row)

    fig_hm = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[str(y) for y in all_years],
        y=labels,
        text=text_data,
        texttemplate="%{text}",
        textfont={"size": 11},
        colorscale=[
            [0, "#d32f2f"], [0.35, "#ef5350"], [0.5, "#ffffff"],
            [0.65, "#66bb6a"], [1.0, "#1b5e20"],
        ],
        zmid=0,
        colorbar=dict(title="Return %", ticksuffix="%"),
    ))
    fig_hm.update_layout(
        title="Yearly Returns by Strategy",
        height=max(500, len(labels) * 35 + 100),
        template="plotly_dark", paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=140),
    )
    heatmap_html = f"""
    <h2 id="heatmap">Yearly Returns Heatmap</h2>
    <div>{fig_hm.to_html(full_html=False, include_plotlyjs=False)}</div>"""

    # --- Drawdown chart (top 5 + TQQQ B&H) ---
    fig_dd = go.Figure()
    for i, r in enumerate(top_results[:5]):
        dd = _weekly(r["drawdown_series"]) * 100
        fig_dd.add_trace(go.Scatter(
            x=dd.index, y=dd.values, name=r["label"],
            line=dict(color=colors[i], width=1.5),
            fill="tozeroy",
            fillcolor=f"rgba({int(colors[i][1:3],16)},{int(colors[i][3:5],16)},{int(colors[i][5:7],16)},0.1)",
        ))
    tqqq_bh = [b for b in benchmarks if "TQQQ" in b["label"]][0]
    dd = _weekly(tqqq_bh["drawdown_series"]) * 100
    fig_dd.add_trace(go.Scatter(
        x=dd.index, y=dd.values, name="TQQQ B&H",
        line=dict(color="#ef5350", width=1.5, dash="dash"),
        fill="tozeroy", fillcolor="rgba(239,83,80,0.05)",
    ))
    fig_dd.update_layout(
        title="Drawdowns: Top 5 vs TQQQ Buy & Hold",
        yaxis_title="Drawdown (%)", height=400,
        template="plotly_dark", paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        legend=dict(x=0.01, y=-0.15, orientation="h"), hovermode="x unified",
    )
    drawdown_html = f"""
    <h2 id="drawdown">Drawdowns</h2>
    <div>{fig_dd.to_html(full_html=False, include_plotlyjs=False)}</div>"""

    # --- Strategy type distribution ---
    strat_counts = {}
    for r in top_results:
        s = r["strategy"]
        strat_counts[s] = strat_counts.get(s, 0) + 1
    dist_text = " | ".join(
        f'<span style="color:{strat_colors.get(s, "#888")}">{s}: {c}</span>'
        for s, c in sorted(strat_counts.items(), key=lambda x: -x[1])
    )

    # --- Comparison table (top 10 strategies + TQQQ/QQQ B&H benchmarks) ---
    all_years = sorted(set(y for c in top_results for y in c["yearly"].keys()))
    tqqq_bm = [b for b in benchmarks if "TQQQ" in b["label"]][0]
    qqq_bm = [b for b in benchmarks if "QQQ" in b["label"]][0]
    comp_items = top_results[:10]

    header = (
        '<tr><th>Metric</th>'
        + '<th style="background:#2a2a3e">TQQQ B&H</th>'
        + '<th style="background:#2a2a3e">QQQ B&H</th>'
        + "".join(f"<th>{c['label']}</th>" for c in comp_items)
        + "</tr>"
    )

    metrics = [
        ("CAGR", "cagr", True), ("Total Return", "total_return", True),
        ("Max Drawdown", "max_dd", True), ("Sharpe", "sharpe", False),
        ("Sortino", "sortino", False), ("Calmar", "calmar", False),
        ("Rank Score", "rank_score", False),
        ("Stability", "stability_score", False),
        ("Consistency", "consistency", False),
        ("% Months +", "pct_months_positive", True),
        ("Ulcer Index", "ulcer_index", False),
        ("# Trades", "num_trades", False), ("Win Rate", "trade_wr", True),
        ("Time in Market", "time_in_market", True), ("Final Equity", "final_equity", False),
    ]

    def _fmt_cell(key, val, is_pct):
        if key == "final_equity":
            return f"<td>${val:,.0f}</td>"
        elif key == "num_trades":
            return f"<td>{val}</td>"
        elif is_pct:
            color = "#4caf50" if val >= 0 else "#ef5350"
            return f'<td style="color:{color}">{val:.1%}</td>'
        else:
            color = "#4caf50" if val >= 0 else "#ef5350"
            return f'<td style="color:{color}">{val:.2f}</td>'

    comp_rows = ""
    for name, key, is_pct in metrics:
        comp_rows += f"<tr><td><strong>{name}</strong></td>"
        # Benchmark columns (some keys don't exist on benchmarks)
        for bm in [tqqq_bm, qqq_bm]:
            if key in bm:
                val = bm[key]
                if key == "final_equity":
                    comp_rows += f'<td style="background:#1e1e30">${val:,.0f}</td>'
                elif key == "num_trades":
                    comp_rows += f'<td style="background:#1e1e30">{val}</td>'
                elif is_pct:
                    color = "#4caf50" if val >= 0 else "#ef5350"
                    comp_rows += f'<td style="color:{color};background:#1e1e30">{val:.1%}</td>'
                else:
                    color = "#4caf50" if val >= 0 else "#ef5350"
                    comp_rows += f'<td style="color:{color};background:#1e1e30">{val:.2f}</td>'
            else:
                comp_rows += '<td style="background:#1e1e30">—</td>'
        # Strategy columns
        for c in comp_items:
            comp_rows += _fmt_cell(key, c[key], is_pct)
        comp_rows += "</tr>"

    # Yearly rows with benchmark comparison
    for year in all_years:
        comp_rows += f"<tr><td><em>{year}</em></td>"
        for bm in [tqqq_bm, qqq_bm]:
            val = bm["yearly"].get(year, 0)
            color = "#4caf50" if val >= 0 else "#ef5350"
            comp_rows += f'<td style="color:{color};background:#1e1e30">{val:.1%}</td>'
        for c in comp_items:
            val = c["yearly"].get(year, 0)
            color = "#4caf50" if val >= 0 else "#ef5350"
            comp_rows += f'<td style="color:{color}">{val:.1%}</td>'
        comp_rows += "</tr>"

    comparison_html = f"""
    <h2 id="comparison">Top 10 — Year-by-Year Comparison vs Benchmarks</h2>
    <p>TQQQ B&H and QQQ B&H columns show what buy-and-hold would have returned each year for reference.</p>
    <table>
        <thead>{header}</thead>
        <tbody>{comp_rows}</tbody>
    </table>"""

    # --- Period heatmap (entry vs exit, colored by best calmar) ---
    # Build a grid: for each (entry, exit) pick the best calmar across strategy types
    period_grid = {}
    for r in top_results:
        key = (r["entry_period"], r["exit_period"])
        if key not in period_grid or r["calmar"] > period_grid[key]["calmar"]:
            period_grid[key] = r

    # --- Assemble ---
    nav = ' | '.join(
        f'<a href="#{id}">{label}</a>' for id, label in [
            ("summary", "Summary"), ("equity", "Equity"),
            ("yr-calmar", "Yr Calmar"), ("heatmap", "Yearly Returns"),
            ("drawdown", "Drawdowns"), ("comparison", "Comparison"),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TQQQ Strategy — Top {TOP_N} from All Combos (2-50)</title>
    <script src="{PLOTLY_CDN}"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: #0d0d1a; color: #e0e0e0;
            padding: 20px; max-width: 1400px; margin: 0 auto;
        }}
        h1 {{ text-align: center; color: #ff9800; margin: 20px 0; font-size: 2em; }}
        h2 {{ color: #64b5f6; border-bottom: 2px solid #333; padding-bottom: 8px; margin: 40px 0 16px 0; }}
        nav {{
            text-align: center; padding: 12px; background: #1a1a2e;
            border-radius: 8px; margin-bottom: 20px; position: sticky; top: 0; z-index: 100;
        }}
        nav a {{ color: #64b5f6; text-decoration: none; padding: 4px 10px; }}
        nav a:hover {{ color: #ff9800; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
        th, td {{ padding: 6px 10px; text-align: right; border-bottom: 1px solid #333; }}
        th {{ background: #1a1a2e; color: #ff9800; position: sticky; top: 52px; cursor: pointer; user-select: none; }}
        th:hover {{ color: #fff; background: #2a2a4e; }}
        th.sort-asc::after {{ content: " ▲"; font-size: 10px; }}
        th.sort-desc::after {{ content: " ▼"; font-size: 10px; }}
        td:first-child, th:first-child {{ text-align: left; }}
        tr:hover {{ background: #1a1a2e; }}
        p {{ color: #999; margin: 8px 0; font-size: 14px; }}
        .meta {{ text-align: center; color: #666; font-size: 12px; margin-top: 40px; }}
        .dist {{ text-align: center; font-size: 14px; margin: 10px 0; }}
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        document.querySelectorAll('table').forEach(function(table) {{
            var headers = table.querySelectorAll('th');
            headers.forEach(function(th, colIdx) {{
                th.addEventListener('click', function() {{
                    var tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    var rows = Array.from(tbody.querySelectorAll('tr'));

                    // Separate pinned rows (benchmarks/separators) from sortable rows
                    var pinned = [];
                    var sortable = [];
                    rows.forEach(function(row) {{
                        var style = row.getAttribute('style') || '';
                        if (style.indexOf('background:#2a2a3e') !== -1 || style.indexOf('background:#555') !== -1) {{
                            pinned.push(row);
                        }} else {{
                            sortable.push(row);
                        }}
                    }});

                    if (sortable.length === 0) return;

                    // Determine sort direction
                    var isAsc = th.classList.contains('sort-asc');
                    headers.forEach(function(h) {{ h.classList.remove('sort-asc', 'sort-desc'); }});

                    sortable.sort(function(a, b) {{
                        var cellA = a.cells[colIdx];
                        var cellB = b.cells[colIdx];
                        if (!cellA || !cellB) return 0;
                        var txtA = cellA.textContent.replace(/[$,%,—]/g, '').trim();
                        var txtB = cellB.textContent.replace(/[$,%,—]/g, '').trim();
                        var numA = parseFloat(txtA);
                        var numB = parseFloat(txtB);
                        if (isNaN(numA) || isNaN(numB)) {{
                            return isAsc ? txtB.localeCompare(txtA) : txtA.localeCompare(txtB);
                        }}
                        return isAsc ? numA - numB : numB - numA;
                    }});

                    th.classList.add(isAsc ? 'sort-desc' : 'sort-asc');

                    // Re-append: pinned first, then sorted
                    pinned.forEach(function(row) {{ tbody.appendChild(row); }});
                    sortable.forEach(function(row) {{ tbody.appendChild(row); }});
                }});
            }});
        }});
    }});
    </script>
</head>
<body>
    <h1>TQQQ Strategy — Top {TOP_N} from {total_combos:,} Combos</h1>
    <p style="text-align:center; color:#aaa;">
        Entry: Buy TQQQ when QQQ Close &ge; MA(entry) | Exit: Sell when QQQ Close &lt; MA(exit)<br>
        All periods {MIN_PERIOD}-{MAX_PERIOD} &times; 3 MA types (EMA/SMA, EMA/EMA, SMA/SMA)<br>
        Cash yield: {CASH_YIELD:.1%} | Starting capital: ${INITIAL_CAPITAL:,} | 10-year backtest
    </p>
    <p class="dist">Strategy distribution in top {TOP_N}: {dist_text}</p>
    <nav>{nav}</nav>

    {summary_html}
    {equity_html}
    {yearly_calmar_html}
    {heatmap_html}
    {drawdown_html}
    {comparison_html}

    <p class="meta">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PT |
    Plotly 2.35.2 (CDN) | Data: yfinance</p>
</body>
</html>"""


def main():
    print("Fetching QQQ and TQQQ data (10 years)...")
    df = fetch_data(years=10)
    print(f"Got {len(df)} trading days ({df.index[0].date()} to {df.index[-1].date()})")

    print("Computing benchmarks...")
    tqqq_bh = compute_benchmark(df, "tqqq_close", "TQQQ Buy & Hold")
    qqq_bh = compute_benchmark(df, "qqq_close", "QQQ Buy & Hold")
    benchmarks = [tqqq_bh, qqq_bh]

    print("Precomputing all MAs (2-50)...")
    mas = precompute_mas(df)

    strategy_types = [
        ("EMA/SMA", "ewm", "rolling"),
        ("EMA/EMA", "ewm", "ewm"),
        ("SMA/SMA", "rolling", "rolling"),
    ]

    periods = list(range(MIN_PERIOD, MAX_PERIOD + 1))
    combos = list(product(periods, periods))
    total = len(combos) * len(strategy_types)
    print(f"Running {total:,} backtests ({len(strategy_types)} strategies × {len(combos):,} combos)...")

    results = []
    done = 0
    for strat_name, entry_type, exit_type in strategy_types:
        for entry_p, exit_p in combos:
            entry_ma = mas[(entry_type, entry_p)]
            exit_ma = mas[(exit_type, exit_p)]
            r = run_backtest(df, entry_ma, exit_ma, entry_p, exit_p, entry_type, exit_type, strat_name)
            results.append(r)
            done += 1
            if done % 1000 == 0:
                print(f"  {done:,}/{total:,} done...")

    print(f"All {total:,} backtests complete.")

    # --- Compute Rank Score (composite: stability + returns + drawdown) ---
    # Rank Score = 0.4 × stability + 0.3 × CAGR_percentile + 0.3 × (1 - |MaxDD|_percentile)
    # This finds strategies that are stable AND have high returns AND low drawdowns
    print("Computing rank scores...")
    viable = [r for r in results if r["calmar"] > 0]
    cagrs = np.array([r["cagr"] for r in viable])
    max_dds = np.array([abs(r["max_dd"]) for r in viable])

    # Percentile rank (0 to 1) using numpy argsort
    def percentile_rank(arr):
        order = arr.argsort().argsort()  # rank (0-based)
        return (order + 1) / len(arr)

    cagr_pct = percentile_rank(cagrs)
    dd_pct = 1.0 - percentile_rank(max_dds)  # invert: lower DD = higher score

    for i, r in enumerate(viable):
        r["rank_score"] = (
            0.4 * r["stability_score"]
            + 0.3 * cagr_pct[i]
            + 0.3 * dd_pct[i]
        )

    # Also set rank_score for non-viable (negative calmar) results for CSV
    for r in results:
        if "rank_score" not in r:
            r["rank_score"] = 0.0

    # --- Export ALL results to CSV ---
    print("Exporting all results to CSV...")
    all_years = sorted(set(y for r in results for y in r["yearly"].keys()))
    csv_rows = []
    for r in results:
        row = {
            "strategy": r["strategy"],
            "label": r["label"],
            "entry_period": r["entry_period"],
            "exit_period": r["exit_period"],
            "cagr": round(r["cagr"], 6),
            "total_return": round(r["total_return"], 6),
            "max_dd": round(r["max_dd"], 6),
            "sharpe": round(r["sharpe"], 4),
            "sortino": round(r["sortino"], 4),
            "calmar": round(r["calmar"], 4),
            "rank_score": round(r["rank_score"], 4),
            "stability_score": round(r["stability_score"], 4),
            "consistency": round(r["consistency"], 4),
            "rolling_sharpe_std": round(r["rolling_sharpe_std"], 4),
            "pct_months_positive": round(r["pct_months_positive"], 4),
            "ulcer_index": round(r["ulcer_index"], 4),
            "pain_avoidance": round(r["pain_avoidance"], 4),
            "num_trades": r["num_trades"],
            "trade_wr": round(r["trade_wr"], 4),
            "time_in_market": round(r["time_in_market"], 4),
            "final_equity": round(r["final_equity"], 2),
        }
        # Yearly returns
        for year in all_years:
            row[f"return_{year}"] = round(r["yearly"].get(year, 0), 6)
        # Yearly calmar
        for year in all_years:
            row[f"calmar_{year}"] = round(r["yearly_calmar"].get(year, 0), 4)
        csv_rows.append(row)

    csv_df = pd.DataFrame(csv_rows)
    csv_df = csv_df.sort_values("rank_score", ascending=False).reset_index(drop=True)
    csv_df.index += 1  # 1-based rank
    csv_df.index.name = "rank"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_df.to_csv(CSV_PATH)
    print(f"  All {len(csv_df):,} combos → {CSV_PATH.name} ({CSV_PATH.stat().st_size / 1024:.0f} KB)")

    # --- Top N for HTML ---
    print("Ranking by Rank Score (stability + returns + drawdown)...")
    top = sorted(viable, key=lambda x: x["rank_score"], reverse=True)[:TOP_N]
    print(f"\nTop {TOP_N} by Rank Score:")
    for i, r in enumerate(top, 1):
        print(
            f"  {i:>2}. {r['strategy']:>7} {r['label']:<14} "
            f"Rank={r['rank_score']:.3f}  Stability={r['stability_score']:.3f}  "
            f"CAGR={r['cagr']:.1%}  MaxDD={r['max_dd']:.1%}  "
            f"Months+={r['pct_months_positive']:.0%}  Ulcer={r['ulcer_index']:.1f}"
        )

    print("\nBuilding HTML report (top 20 only)...")
    html = build_html(top, benchmarks, total)

    REPORT_PATH.write_text(html)
    size_kb = REPORT_PATH.stat().st_size / 1024
    print(f"  Top {TOP_N} → {REPORT_PATH.name} ({size_kb:.0f} KB)")
    print(f"\nDone. Reports in: {REPORT_DIR.resolve()}")


if __name__ == "__main__":
    main()
