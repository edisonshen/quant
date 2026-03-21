"""Pin bar detection + S/R proximity matching."""

from __future__ import annotations

import pandas as pd

from quant.core.config import PinBarConfig
from quant.core.types import Candle, Direction, PinBar, SRLevel, Timeframe


def detect_pin_bars(
    df: pd.DataFrame,
    sr_levels: list[SRLevel],
    config: PinBarConfig | None = None,
    symbol: str = "",
    timeframe: Timeframe = Timeframe.H1,
) -> list[PinBar]:
    """Detect pin bars and match them to nearby S/R levels.

    Pin bar criteria:
    1. Dominant wick / body ratio > min_wick_body_ratio (default 2:1)
    2. Body < max_body_pct of total range (default 30%)
    3. Dominant wick extends beyond preceding N candles' high/low
    4. Must be within sr_proximity_pct of an S/R level
    """
    if config is None:
        config = PinBarConfig()

    pin_bars: list[PinBar] = []
    lookback = config.wick_exceed_lookback

    for i in range(lookback, len(df)):
        row = df.iloc[i]
        candle = Candle(
            timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
            symbol=symbol,
            timeframe=timeframe,
        )

        if candle.range == 0:
            continue

        # Check body size
        if candle.body_size / candle.range > config.max_body_pct:
            continue

        # Determine dominant wick
        upper = candle.upper_wick
        lower = candle.lower_wick

        body = candle.body_size if candle.body_size > 0 else candle.range * 0.01  # avoid div/0

        is_bearish_pin = upper > lower and upper / body >= config.min_wick_body_ratio
        is_bullish_pin = lower > upper and lower / body >= config.min_wick_body_ratio

        if not is_bearish_pin and not is_bullish_pin:
            continue

        direction = Direction.LONG if is_bullish_pin else Direction.SHORT
        wick_ratio = (lower / body) if is_bullish_pin else (upper / body)

        # Wick must exceed preceding candles
        preceding = df.iloc[i - lookback : i]
        if is_bearish_pin:
            if candle.high <= preceding["high"].max():
                continue
        else:
            if candle.low >= preceding["low"].min():
                continue

        # Find nearest S/R level
        nearest_sr, distance_pct = _find_nearest_sr(candle, i, sr_levels, config)
        if nearest_sr is None:
            continue  # no S/R nearby — not a valid setup

        pin_bars.append(
            PinBar(
                candle=candle,
                index=i,
                direction=direction,
                wick_ratio=wick_ratio,
                nearest_sr=nearest_sr,
                sr_distance_pct=distance_pct,
            )
        )

    return pin_bars


def _find_nearest_sr(
    candle: Candle,
    bar_index: int,
    sr_levels: list[SRLevel],
    config: PinBarConfig,
) -> tuple[SRLevel | None, float]:
    """Find the nearest S/R level within proximity threshold.

    Returns (level, distance_as_pct_of_price) or (None, 0.0).
    """
    if not sr_levels or candle.close == 0:
        return None, 0.0

    best_level: SRLevel | None = None
    best_distance = float("inf")

    # Use the wick tip as the reference point
    for level in sr_levels:
        level_price = level.price_at(bar_index)

        # Distance from the wick tip to the S/R level
        if candle.lower_wick > candle.upper_wick:
            # Bullish pin — lower wick tip near support
            dist = abs(candle.low - level_price)
        else:
            # Bearish pin — upper wick tip near resistance
            dist = abs(candle.high - level_price)

        distance_pct = dist / candle.close

        if distance_pct <= config.sr_proximity_pct and dist < best_distance:
            best_distance = dist
            best_level = level
            best_distance_pct = distance_pct

    if best_level is None:
        return None, 0.0

    return best_level, best_distance_pct
