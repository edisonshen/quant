"""Tests for fallback data provider."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from rainier.core.types import Timeframe
from rainier.data.fallback_provider import FallbackProvider


@pytest.fixture
def sample_df():
    """Sample candle DataFrame."""
    return pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-01-02 09:00:00", tz="UTC"),
         "open": 5000.0, "high": 5010.0, "low": 4990.0, "close": 5005.0, "volume": 1000},
        {"timestamp": pd.Timestamp("2025-01-02 10:00:00", tz="UTC"),
         "open": 5005.0, "high": 5020.0, "low": 4995.0, "close": 5015.0, "volume": 1200},
    ])


@pytest.fixture
def empty_df():
    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


class TestFallbackProvider:
    def test_primary_success_no_fallback(self, sample_df):
        primary = MagicMock()
        fallback = MagicMock()
        primary.get_candles.return_value = sample_df

        provider = FallbackProvider(primary, fallback)
        df = provider.get_candles("MES", Timeframe.H1)

        assert len(df) == 2
        primary.get_candles.assert_called_once_with("MES", Timeframe.H1, None, None)
        fallback.get_candles.assert_not_called()

    def test_primary_exception_triggers_fallback(self, sample_df):
        primary = MagicMock()
        fallback = MagicMock()
        primary.get_candles.side_effect = ConnectionError("TWS not running")
        fallback.get_candles.return_value = sample_df

        provider = FallbackProvider(primary, fallback)
        df = provider.get_candles("MES", Timeframe.H1)

        assert len(df) == 2
        primary.get_candles.assert_called_once()
        fallback.get_candles.assert_called_once_with("MES", Timeframe.H1, None, None)

    def test_primary_empty_triggers_fallback(self, empty_df, sample_df):
        primary = MagicMock()
        fallback = MagicMock()
        primary.get_candles.return_value = empty_df
        fallback.get_candles.return_value = sample_df

        provider = FallbackProvider(primary, fallback)
        df = provider.get_candles("MES", Timeframe.H1)

        assert len(df) == 2
        fallback.get_candles.assert_called_once()

    def test_both_fail_raises(self, empty_df):
        primary = MagicMock()
        fallback = MagicMock()
        primary.get_candles.side_effect = ConnectionError("TWS not running")
        fallback.get_candles.side_effect = RuntimeError("yfinance down")

        provider = FallbackProvider(primary, fallback)

        with pytest.raises(RuntimeError, match="yfinance down"):
            provider.get_candles("MES", Timeframe.H1)

    def test_passes_start_end_to_providers(self, sample_df):
        primary = MagicMock()
        fallback = MagicMock()
        primary.get_candles.return_value = sample_df

        provider = FallbackProvider(primary, fallback)
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        provider.get_candles("MES", Timeframe.H1, start, end)

        primary.get_candles.assert_called_once_with("MES", Timeframe.H1, start, end)
