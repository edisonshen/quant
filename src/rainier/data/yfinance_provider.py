"""YFinance data provider — fetches OHLCV from Yahoo Finance."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog
import yfinance as yf

from rainier.core.types import Timeframe

log = structlog.get_logger()

# Map our symbols to yfinance tickers
SYMBOL_TO_TICKER: dict[str, str] = {
    "NQ": "NQ=F",
    "MNQ": "MNQ=F",
    "ES": "ES=F",
    "MES": "MES=F",
    "GC": "GC=F",
}

# Map our timeframes to yfinance intervals + sensible periods
TF_TO_YF: dict[Timeframe, tuple[str, str]] = {
    Timeframe.M5: ("5m", "60d"),
    Timeframe.H1: ("1h", "730d"),
    Timeframe.H4: ("1h", "730d"),  # yfinance has no 4h; we resample from 1h
    Timeframe.D1: ("1d", "max"),
}


class YFinanceProvider:
    """DataProvider implementation backed by yfinance."""

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch candles from yfinance, return normalized DataFrame."""
        ticker = SYMBOL_TO_TICKER.get(symbol, symbol)
        if timeframe not in TF_TO_YF:
            raise ValueError(f"Unsupported timeframe {timeframe} for yfinance")

        yf_interval, yf_period = TF_TO_YF[timeframe]
        raw = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval)

        if raw.empty:
            log.warning("yfinance_no_data", symbol=symbol, timeframe=timeframe.value)
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = _normalize(raw)

        # Resample 1h → 4h if needed
        if timeframe == Timeframe.H4:
            df = _resample_4h(df)

        # Filter date range
        if start:
            df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

        return df.reset_index(drop=True)


def fetch_symbol(
    symbol: str,
    timeframes: list[Timeframe],
    data_dir: Path,
) -> dict[Timeframe, int]:
    """Fetch data for a symbol across timeframes, merge with existing CSVs.

    Returns dict of {timeframe: total_rows} after merge.
    Backward-compatible wrapper around YFinanceProvider.
    """
    from rainier.data.persistence import save_candles

    provider = YFinanceProvider()
    results: dict[Timeframe, int] = {}

    for tf in timeframes:
        df = provider.get_candles(symbol, tf)
        if df.empty:
            continue
        results[tf] = save_candles(df, symbol, tf, data_dir)

    return results


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert yfinance DataFrame to our standard format."""
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "timestamp"
    df = df.reset_index()
    # yfinance index name is 'Datetime' for intraday, 'Date' for daily
    df = df.rename(columns={"Datetime": "timestamp", "Date": "timestamp"})
    # Keep timezone info in the CSV for proper merging
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    """Resample 1h data to 4h bars."""
    df = df.set_index("timestamp")
    resampled = df.resample("4h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()
    return resampled.reset_index()
