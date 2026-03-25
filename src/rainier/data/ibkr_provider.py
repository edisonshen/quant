"""IBKR data provider — fetches OHLCV via TWS/Gateway using ib_insync."""

from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime

import pandas as pd
import structlog

from rainier.core.config import IBKRConfig, get_settings, load_watchlist
from rainier.core.types import Timeframe

log = structlog.get_logger()

# Map Rainier timeframes to IBKR barSizeSetting
TF_TO_IB_BAR_SIZE: dict[Timeframe, str] = {
    Timeframe.M5: "5 mins",
    Timeframe.H1: "1 hour",
    Timeframe.H4: "4 hours",
    Timeframe.D1: "1 day",
}

# Map Rainier timeframes to IBKR durationStr (how far back to fetch)
TF_TO_IB_DURATION: dict[Timeframe, str] = {
    Timeframe.M5: "20 D",
    Timeframe.H1: "365 D",
    Timeframe.H4: "365 D",
    Timeframe.D1: "10 Y",
}

EMPTY_DF = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


class _RateLimiter:
    """Simple sliding-window rate limiter for IBKR historical data requests."""

    def __init__(self, max_requests: int = 55, window_seconds: int = 600):
        self._timestamps: deque[float] = deque()
        self._max = max_requests
        self._window = window_seconds

    def wait_if_needed(self) -> None:
        now = time.time()
        while self._timestamps and self._timestamps[0] < now - self._window:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max:
            sleep_time = self._timestamps[0] + self._window - now + 1
            log.info("ibkr_rate_limit_wait", seconds=round(sleep_time, 1))
            time.sleep(sleep_time)
        self._timestamps.append(time.time())


_rate_limiter = _RateLimiter()


class IBKRProvider:
    """DataProvider implementation backed by Interactive Brokers TWS/Gateway."""

    def __init__(self, config: IBKRConfig | None = None):
        self._config = config or get_settings().ibkr
        self._watchlist = load_watchlist()

    @contextmanager
    def _connection(self):
        """Context manager for IB connection. Connect-per-fetch pattern."""
        from ib_insync import IB

        ib = IB()
        try:
            ib.connect(
                self._config.host,
                self._config.port,
                clientId=self._config.client_id,
                timeout=self._config.timeout,
                readonly=self._config.readonly,
            )
            log.info("ibkr_connected", host=self._config.host, port=self._config.port)
            yield ib
        finally:
            if ib.isConnected():
                ib.disconnect()
                log.debug("ibkr_disconnected")

    def _make_contract(self, symbol: str):
        """Build an ib_insync Contract from symbol + watchlist config."""
        from ib_insync import ContFuture, Future, Stock

        inst = self._watchlist.get(symbol)
        ib_symbol = (inst.ib_symbol or symbol) if inst else symbol
        exchange = (inst.exchange if inst else "CME") or "CME"
        currency = (inst.ib_currency if inst else "USD") or "USD"
        sec_type = (inst.ib_sec_type if inst else "CONTFUT") or "CONTFUT"

        if sec_type == "CONTFUT":
            return ContFuture(symbol=ib_symbol, exchange=exchange, currency=currency)
        elif sec_type == "FUT":
            return Future(symbol=ib_symbol, exchange=exchange, currency=currency)
        elif sec_type == "STK":
            return Stock(symbol=ib_symbol, exchange="SMART", currency=currency)
        else:
            return ContFuture(symbol=ib_symbol, exchange=exchange, currency=currency)

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch historical bars from IBKR."""
        from ib_insync import util

        if timeframe not in TF_TO_IB_BAR_SIZE:
            raise ValueError(f"Unsupported timeframe {timeframe} for IBKR")

        contract = self._make_contract(symbol)
        bar_size = TF_TO_IB_BAR_SIZE[timeframe]
        duration = TF_TO_IB_DURATION[timeframe]

        # If start is specified, calculate duration from start to now
        end_dt = end or datetime.now()
        if start:
            delta = end_dt - start
            days = max(delta.days, 1)
            duration = f"{days} D"

        _rate_limiter.wait_if_needed()

        with self._connection() as ib:
            ib.qualifyContracts(contract)
            bars = ib.reqHistoricalData(
                contract,
                endDateTime=end_dt if end else "",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=False,  # include extended hours
                formatDate=1,
                timeout=120,  # 2 min timeout for large requests
            )

        if not bars:
            log.warning("ibkr_no_data", symbol=symbol, timeframe=timeframe.value)
            return EMPTY_DF.copy()

        df = util.df(bars)
        return self._normalize(df)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert ib_insync DataFrame to standard format."""
        df = df.rename(columns={"date": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        return df.sort_values("timestamp").reset_index(drop=True)

    def is_available(self) -> bool:
        """Check if TWS/Gateway is reachable."""
        from ib_insync import IB

        try:
            ib = IB()
            ib.connect(
                self._config.host,
                self._config.port,
                clientId=self._config.client_id + 100,  # different client_id for health check
                timeout=5,
                readonly=True,
            )
            ib.disconnect()
            return True
        except Exception:
            return False
