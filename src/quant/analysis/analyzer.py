"""Orchestrator: runs all detectors and produces an AnalysisResult."""

from __future__ import annotations

import pandas as pd

from quant.core.config import AnalysisConfig
from quant.core.types import AnalysisResult, Timeframe

from .bias import determine_bias
from .inside_bar import detect_inside_bars
from .pinbar import detect_pin_bars
from .pivots import compute_atr, detect_pivots
from .sr_diagonal import detect_diagonal_sr
from .sr_horizontal import detect_horizontal_sr


def analyze(
    df: pd.DataFrame,
    symbol: str,
    timeframe: Timeframe,
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    """Run the full analysis pipeline on OHLCV data.

    Pipeline:
    1. Detect pivots (swing highs/lows)
    2. Compute ATR
    3. Detect horizontal S/R from pivot clusters
    4. Detect diagonal S/R (trendlines) from swing-point pairs
    5. Detect pin bars near S/R levels
    6. Detect inside bars (range compression)
    7. Determine directional bias
    """
    if config is None:
        config = AnalysisConfig()

    result = AnalysisResult(symbol=symbol, timeframe=timeframe)

    if len(df) < 2:
        return result

    # 1. Pivots
    pivots = detect_pivots(df, config.pivot)
    result.pivots = pivots

    # 2. ATR
    atr = compute_atr(df)

    # 3. Horizontal S/R
    h_levels = detect_horizontal_sr(pivots, df, atr, config.sr_horizontal)

    # 4. Diagonal S/R
    d_levels = detect_diagonal_sr(pivots, df, atr, config.sr_diagonal)

    result.sr_levels = h_levels + d_levels

    # 5. Pin bars
    result.pin_bars = detect_pin_bars(df, result.sr_levels, config.pin_bar, symbol, timeframe)

    # 6. Inside bars
    result.inside_bars = detect_inside_bars(df, config.inside_bar, symbol, timeframe)

    # 7. Bias
    result.bias = determine_bias(df, pivots)

    return result
