# quant

Automated price action trading system for futures (NQ, ES, GC). Detects support/resistance levels (horizontal + diagonal trendlines), finds pin bar reversals near those levels, and generates counter-trend limit order signals.

Built around the 小酱 pin bar methodology: S/R detection → pin bar confirmation → signal generation → (eventually) auto-execution.

## What it does

1. **S/R Detection** — Finds horizontal support/resistance zones via pivot clustering and diagonal trendlines via swing-point regression
2. **Pin Bar Scanner** — Identifies pin bar candles forming near S/R levels with configurable wick/body ratios
3. **Signal Generation** — Produces trade signals with entry, stop loss, take profit, R:R ratio, and confidence score
4. **Visualization** — Plotly charts overlaying S/R lines, pin bars, and signals for visual validation against TradingView
5. **Backtesting** — Event-driven backtest engine with pre-computed S/R for performance
6. **Alerts** — Discord webhook notifications when signals fire

## Status

**Phase 1: In Progress** — Building the analysis engine (S/R detection, pin bar scanning, signal generation) using TradingView CSV exports for offline development.

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation + Data Layer + Analysis Engine + Signals + Viz | 🔨 Building |
| 2 | Backtesting + Alerts + Daily Reports | Planned |
| 3 | Live Trading via IB TWS API | Planned |

## Quickstart

```bash
# requires python 3.12+, uv
cd quant
uv sync

# scan a TradingView CSV export for setups
uv run quant scan --symbol NQ --timeframe 1H --csv data/csv/NQ_1H.csv

# generate an interactive chart
uv run quant chart --symbol NQ --timeframe 1H

# run backtest
uv run quant backtest --symbol NQ --start 2024-01-01 --end 2026-03-01
```

## Project Structure

```
quant/
├── config/
│   ├── settings.yaml          # All tunable parameters (grouped by module)
│   └── watchlists/default.yaml
├── data/
│   ├── csv/                   # TradingView exports (gitignored)
│   └── labels/                # Hand-labeled ground truth for validation
├── src/quant/
│   ├── core/                  # Types, config, database, ORM models
│   ├── data/                  # DataProvider protocol, CSV reader, DB ingest
│   ├── analysis/              # Pivots, S/R (horizontal + diagonal), pin bars, inside bars, bias
│   ├── signals/               # Confidence scorer, signal generator, TraderSync journal export
│   ├── viz/                   # Plotly charts
│   ├── alerts/                # Discord webhooks
│   ├── reports/               # Daily review + next-day outlook
│   ├── backtest/              # Event-driven backtest engine
│   └── trader/                # (Phase 3) IB executor, risk manager, reconciler
└── tests/
```

## Configuration

All parameters live in `config/settings.yaml` and are loaded via pydantic-settings with nested models. Each module receives only its own config section. Key tunables:

- **Pivot lookback**: bars each side for swing high/low detection (default: 5)
- **S/R clustering**: cluster within `0.3 × ATR(14)` (default)
- **Pin bar**: wick/body ratio > 2:1, body < 30% of range, within 0.5% of S/R
- **Signal confidence threshold**: minimum 0.5 to generate a signal
- **Risk**: max 3 positions, 1% risk per trade, $1000 max daily loss

## Data Sources

| Source | Use | Phase |
|--------|-----|-------|
| TradingView CSV | Offline development & backtesting | 1 |
| Interactive Brokers TWS | Real-time futures data + execution | 3 |
| Alpaca | Equities (secondary, deferred) | — |

## Tech Stack

Python 3.12 · pandas/numpy · SQLAlchemy 2.0 + PostgreSQL 16 · plotly · pydantic-settings · click · httpx · pytest

## License

Private — not open source.
