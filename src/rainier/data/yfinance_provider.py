"""Fetch OHLCV data from yfinance and save to CSV + database."""

from __future__ import annotations

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


def fetch_symbol(
    symbol: str,
    timeframes: list[Timeframe],
    data_dir: Path,
) -> dict[Timeframe, int]:
    """Fetch data for a symbol across timeframes, merge with existing CSVs.

    Returns dict of {timeframe: total_rows} after merge.
    """
    ticker = SYMBOL_TO_TICKER.get(symbol)
    if not ticker:
        raise ValueError(f"Unknown symbol {symbol}. Known: {list(SYMBOL_TO_TICKER)}")

    data_dir.mkdir(parents=True, exist_ok=True)
    results: dict[Timeframe, int] = {}

    for tf in timeframes:
        yf_interval, yf_period = TF_TO_YF[tf]
        raw = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval)

        if raw.empty:
            continue

        df = _normalize(raw)

        # Resample 1h → 4h if needed
        if tf == Timeframe.H4:
            df = _resample_4h(df)

        # Merge with existing CSV
        csv_path = data_dir / f"{symbol}_{tf.value}.csv"
        df = _merge_with_existing(df, csv_path)

        # Save to CSV
        df.to_csv(csv_path, index=False)

        # Save to database
        _persist_to_db(df, symbol, tf)

        results[tf] = len(df)

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


def _persist_to_db(df: pd.DataFrame, symbol: str, tf: Timeframe) -> None:
    """Upsert candle data into the CandleRecord table."""
    try:
        from sqlalchemy import select

        from rainier.core.database import get_session
        from rainier.core.models import CandleRecord

        with get_session() as db:
            for _, row in df.iterrows():
                ts = row["timestamp"].to_pydatetime().replace(tzinfo=None)
                existing = db.execute(
                    select(CandleRecord).where(
                        CandleRecord.symbol == symbol,
                        CandleRecord.timeframe == tf.value,
                        CandleRecord.timestamp == ts,
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = float(row["volume"])
                else:
                    db.add(CandleRecord(
                        symbol=symbol,
                        timeframe=tf.value,
                        timestamp=ts,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    ))

        log.info("db_persisted", symbol=symbol, timeframe=tf.value, rows=len(df))
    except Exception as exc:
        log.warning("db_persist_skipped", symbol=symbol, reason=str(exc))


def _merge_with_existing(new_df: pd.DataFrame, csv_path: Path) -> pd.DataFrame:
    """Merge new data with existing CSV, dedup on timestamp."""
    if csv_path.exists():
        existing = pd.read_csv(csv_path)
        existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="timestamp", keep="last")
        combined = combined.sort_values("timestamp").reset_index(drop=True)
        return combined
    return new_df
