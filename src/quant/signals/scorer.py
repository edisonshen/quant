"""Confidence scoring for trade signals — weighted sub-scores."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.core.config import ScorerConfig
from quant.core.types import Direction, PinBar


def score_setup(
    pin_bar: PinBar,
    df: pd.DataFrame,
    bias: Direction | None,
    config: ScorerConfig | None = None,
) -> float:
    """Compute a confidence score (0.0 - 1.0) for a pin bar setup.

    Sub-scores:
    - S/R strength: how strong is the nearby S/R level
    - Wick ratio: larger wick → stronger rejection
    - Volume spike: volume at pin bar vs average
    - Trend alignment: pin bar direction matches bias
    - Multi-TF confluence: placeholder (always 0.5 for now, needs multi-TF data)
    """
    if config is None:
        config = ScorerConfig()

    sr_strength = _sr_strength_score(pin_bar)
    wick_score = _wick_ratio_score(pin_bar)
    volume_score = _volume_spike_score(pin_bar, df)
    trend_score = _trend_alignment_score(pin_bar, bias)
    confluence_score = 0.5  # placeholder until multi-TF is wired

    total = (
        config.weight_sr_strength * sr_strength
        + config.weight_wick_ratio * wick_score
        + config.weight_volume_spike * volume_score
        + config.weight_trend_alignment * trend_score
        + config.weight_multi_tf_confluence * confluence_score
    )

    return float(np.clip(total, 0.0, 1.0))


def _sr_strength_score(pin_bar: PinBar) -> float:
    if pin_bar.nearest_sr is None:
        return 0.0
    return pin_bar.nearest_sr.strength


def _wick_ratio_score(pin_bar: PinBar) -> float:
    """Higher wick ratio → stronger rejection → higher score. Cap at ratio=5."""
    return float(np.clip(pin_bar.wick_ratio / 5.0, 0.0, 1.0))


def _volume_spike_score(pin_bar: PinBar, df: pd.DataFrame) -> float:
    """Pin bar volume relative to average."""
    if "volume" not in df.columns or df["volume"].sum() == 0:
        return 0.5
    avg_vol = df["volume"].mean()
    if avg_vol == 0:
        return 0.5
    ratio = pin_bar.candle.volume / avg_vol
    return float(np.clip(ratio / 2.0, 0.0, 1.0))  # 2x avg volume = 1.0


def _trend_alignment_score(pin_bar: PinBar, bias: Direction | None) -> float:
    """Counter-trend at S/R is the strategy, but alignment with higher TF bias is a plus."""
    if bias is None:
        return 0.5
    # Pin bar direction matching bias = good (counter-trend reversal aligning with bigger picture)
    if pin_bar.direction == bias:
        return 0.8
    return 0.3
