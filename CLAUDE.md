# CLAUDE.md

## Project Overview

Automated Price Action trading system for NQ/ES/GC futures using 小酱 (xiaoping) pin bar methodology. Evolving from rule-based to AI-adaptive with a three-layer hybrid architecture: Feature Extraction → ML Model Ensemble → LLM Meta-Strategist.

## Architecture

```
Layer 3: LLM Meta-Strategist (periodic — hourly/daily)
  │  Regime interpretation, strategy weights, hypothesis generation
  │
Layer 2: ML Model Ensemble (per-bar — fast, deterministic)
  │  HMM regime detector, XGBoost pattern scorer, RF direction predictor
  │
Layer 1: Feature Extraction (per-bar — existing codebase)
     Pivots, S/R levels, pin bars, inside bars, bias, multi-TF confluence
```

## Module Map

```
src/quant/
├── core/           types.py (all shared dataclasses), config.py (Pydantic), models.py (ORM), database.py
├── data/           provider.py (protocol), csv_provider.py, yfinance_provider.py
├── analysis/       analyzer.py (orchestrator), pivots.py, pinbar.py, sr_horizontal.py, sr_diagonal.py, bias.py, inside_bar.py
├── features/       extractor.py (AnalysisResult→ML features), labels.py (backtest→training labels)
├── signals/        generator.py (entry/SL/TP), scorer.py (weighted confidence + multi-TF confluence)
├── backtest/       engine.py (event-driven, S/R recompute every 50 bars)
├── viz/            charts.py (Plotly interactive)
├── alerts/         discord.py (webhook notifications)
├── reports/        daily.py (daily review + next-day outlook)
├── trader/         (Phase 3 placeholder — IB TWS execution)
└── scheduler/      jobs.py (cron.yaml → system crontab sync)
```

## Commands

```bash
# Run tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_pinbar.py -v

# Lint
uv run ruff check src/ tests/

# CLI commands
uv run quant fetch --symbol MES --plot           # fetch latest data from yfinance + chart
uv run quant scan --symbol NQ --timeframe 1H --csv data/csv/NQ_1H.csv
uv run quant daytrade --symbol NQ --data-dir data/csv
uv run quant backtest --symbol NQ --start 2024-01-01 --end 2026-03-01
uv run quant chart --symbol NQ --timeframe 1H
uv run quant report

# Scheduled jobs (config/cron.yaml)
uv run quant jobs list                            # show all jobs and status
uv run quant jobs sync                            # sync cron.yaml → system crontab
uv run quant jobs stop --name fetch-mes           # remove job from crontab
```

## Key Conventions

- All shared types live in `src/quant/core/types.py` — do not scatter dataclasses across modules
- Config via `config/settings.yaml`, loaded by Pydantic models in `core/config.py`
- Per-symbol overrides in `config/watchlists/default.yaml` (tick_size, point_value, min_touches)
- Tests use synthetic fixtures from `tests/conftest.py` (flat_candles, trending_up, swing, pin_bar, inside_bar)
- S/R levels tagged with `source_tf` for multi-TF chart rendering
- Pin bar lines use wick-tip mode (most common price), not average
- Python 3.12+, ruff for linting, line length 100

## Design Decisions (from eng review 2026-03-22)

- Pipeline-first: build full pipeline with book strategy scorer, then swap in ML models
- FeatureExtractor consumes AnalysisResult (not parallel extraction)
- ScoringStrategy protocol: book scorer and ML scorer interchangeable in generator
- Single XGBoost model with regime as feature (split to per-regime at 200+ samples/regime)
- Walk-forward cross-validation mandatory for all ML models (no random splits)
- NaN policy: fill with meaningful defaults + assert no NaN before model input
- LLM output: Pydantic validation + 3x retry
- Threshold history: append-only JSONL (not overwrite config)
- Degraded mode: phase-aware, deferred to Phase 3
- Feature store: Parquet files for training/backtesting
