"""Fallback data provider — tries primary, falls back to secondary on failure."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import structlog

from rainier.core.types import Timeframe

log = structlog.get_logger()


def _provider_name(provider) -> str:
    return type(provider).__name__.replace("Provider", "").lower()


class FallbackProvider:
    """Tries primary provider, falls back to secondary on failure or empty result."""

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        primary_name = _provider_name(self._primary)
        fallback_name = _provider_name(self._fallback)

        try:
            df = self._primary.get_candles(symbol, timeframe, start, end)
            if not df.empty:
                log.info(
                    "data_source",
                    provider=primary_name,
                    symbol=symbol,
                    tf=timeframe.value,
                    rows=len(df),
                )
                return df
        except Exception as exc:
            log.warning(
                "primary_provider_failed",
                provider=primary_name,
                symbol=symbol,
                tf=timeframe.value,
                error=str(exc),
            )

        # Fallback
        log.info("falling_back", provider=fallback_name, symbol=symbol, tf=timeframe.value)
        df = self._fallback.get_candles(symbol, timeframe, start, end)
        log.info(
            "data_source",
            provider=fallback_name,
            symbol=symbol,
            tf=timeframe.value,
            rows=len(df),
        )
        return df
