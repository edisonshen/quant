"""Plotly charts: candlesticks with S/R lines, pin bars, and signal markers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from quant.core.types import AnalysisResult, Direction, Signal, SRType


def create_chart(
    df: pd.DataFrame,
    result: AnalysisResult,
    signals: list[Signal] | None = None,
    output_path: Path | None = None,
) -> go.Figure:
    """Create an interactive plotly chart with analysis overlays.

    Layers:
    1. Candlestick chart
    2. Horizontal S/R lines (solid = strong, dashed = weak)
    3. Diagonal trendlines
    4. Pin bar markers
    5. Signal entry/SL/TP markers
    """
    fig = go.Figure()

    timestamps = df["timestamp"]

    # 1. Candlesticks
    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        )
    )

    # 2. Horizontal S/R lines
    for level in result.sr_levels:
        if level.sr_type != SRType.HORIZONTAL:
            continue
        color = "#2196F3" if level.role.value == "support" else "#FF5722"
        dash = "solid" if level.strength >= 0.6 else "dash"
        fig.add_hline(
            y=level.price,
            line_dash=dash,
            line_color=color,
            line_width=1,
            opacity=min(level.strength + 0.3, 1.0),
            annotation_text=f"{'S' if level.role.value == 'support' else 'R'} {level.price:.2f} ({level.touches}t)",
            annotation_position="right",
            annotation_font_size=9,
            annotation_font_color=color,
        )

    # 3. Diagonal trendlines
    for level in result.sr_levels:
        if level.sr_type != SRType.DIAGONAL:
            continue
        color = "#4CAF50" if level.role.value == "support" else "#E91E63"
        # Draw from first_seen to end of chart
        start_idx = max(0, level.anchor_index - 50)
        end_idx = len(df) - 1
        if start_idx >= len(df) or end_idx < 0:
            continue

        x_vals = [timestamps.iloc[start_idx], timestamps.iloc[end_idx]]
        y_vals = [level.price_at(start_idx), level.price_at(end_idx)]

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines",
                line=dict(color=color, width=1, dash="dot"),
                name=f"Trend {'S' if level.role.value == 'support' else 'R'}",
                showlegend=False,
            )
        )

    # 4. Pin bar markers
    for pb in result.pin_bars:
        marker_color = "#00E676" if pb.direction == Direction.LONG else "#FF1744"
        y_pos = pb.candle.low * 0.999 if pb.direction == Direction.LONG else pb.candle.high * 1.001
        fig.add_trace(
            go.Scatter(
                x=[pb.candle.timestamp],
                y=[y_pos],
                mode="markers",
                marker=dict(
                    symbol="triangle-up" if pb.direction == Direction.LONG else "triangle-down",
                    size=12,
                    color=marker_color,
                ),
                name=f"Pin Bar {'Bull' if pb.direction == Direction.LONG else 'Bear'}",
                showlegend=False,
                hovertext=f"Wick ratio: {pb.wick_ratio:.1f}x | SR dist: {pb.sr_distance_pct:.3%}",
            )
        )

    # 5. Signal markers
    if signals:
        for sig in signals:
            color = "#00E676" if sig.direction == Direction.LONG else "#FF1744"
            # Entry
            fig.add_trace(
                go.Scatter(
                    x=[sig.timestamp],
                    y=[sig.entry_price],
                    mode="markers+text",
                    marker=dict(symbol="diamond", size=10, color=color),
                    text=[f"{sig.direction.value} {sig.confidence:.0%}"],
                    textposition="top center",
                    textfont=dict(size=9, color=color),
                    name=f"Signal {sig.direction.value}",
                    showlegend=False,
                )
            )
            # SL line
            fig.add_shape(
                type="line",
                x0=sig.timestamp,
                x1=sig.timestamp,
                y0=sig.entry_price,
                y1=sig.stop_loss,
                line=dict(color="red", width=1, dash="dot"),
            )
            # TP line
            fig.add_shape(
                type="line",
                x0=sig.timestamp,
                x1=sig.timestamp,
                y0=sig.entry_price,
                y1=sig.take_profit,
                line=dict(color="green", width=1, dash="dot"),
            )

    # Layout
    fig.update_layout(
        title=f"{result.symbol} {result.timeframe.value} — S/R + Pin Bars",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=700,
        margin=dict(l=60, r=20, t=50, b=40),
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))

    return fig
