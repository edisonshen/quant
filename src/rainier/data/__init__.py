"""Data providers for Rainier."""

from __future__ import annotations


def get_provider(provider_type: str = "auto"):
    """Build a data provider.

    Args:
        provider_type: "ibkr", "yfinance", or "auto" (yfinance with IBKR fallback).
    """
    if provider_type == "ibkr":
        from rainier.data.ibkr_provider import IBKRProvider

        return IBKRProvider()
    elif provider_type == "yfinance":
        from rainier.data.yfinance_provider import YFinanceProvider

        return YFinanceProvider()
    else:  # "auto"
        from rainier.data.fallback_provider import FallbackProvider
        from rainier.data.ibkr_provider import IBKRProvider
        from rainier.data.yfinance_provider import YFinanceProvider

        return FallbackProvider(
            primary=YFinanceProvider(),
            fallback=IBKRProvider(),
        )
