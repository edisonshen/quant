"""Tests for walk-forward cross-validation."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from rainier.backtest.walk_forward import (
    WalkForwardResult,
    _compute_fold_boundaries,
    format_walk_forward_report,
    run_walk_forward,
)
from rainier.core.config import BacktestConfig, WalkForwardConfig
from rainier.core.protocols import SignalEmitter
from rainier.core.types import Direction, Signal, Timeframe

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_dataset(n_bars: int = 800) -> pd.DataFrame:
    """Create a zigzag dataset long enough for walk-forward."""
    rows = []
    price = 100.0
    base = datetime(2025, 1, 1)

    for i in range(n_bars):
        cycle = i % 40
        move = 1.0 if cycle < 20 else -1.0

        o = price
        h = price + abs(move) + 1.0
        low = price - abs(move) - 0.5
        c = price + move

        rows.append({
            "timestamp": base + timedelta(hours=i),
            "open": o, "high": h, "low": low, "close": c,
            "volume": 1000.0 + (i % 10) * 100,
        })
        price = c

    return pd.DataFrame(rows)


class FakeEmitter:
    """Emitter that generates a signal on every call."""

    def emit(self, df: pd.DataFrame, symbol: str, timeframe: Timeframe) -> list[Signal]:
        last_bar = df.iloc[-1]
        return [
            Signal(
                symbol=symbol,
                timeframe=timeframe,
                direction=Direction.LONG,
                entry_price=float(last_bar["close"]) - 0.5,
                stop_loss=float(last_bar["close"]) - 5.0,
                take_profit=float(last_bar["close"]) + 5.0,
                confidence=0.75,
                timestamp=pd.Timestamp(last_bar["timestamp"]).to_pydatetime(),
            ),
        ]


def _fake_factory(min_conf: float, min_rr: float) -> SignalEmitter:
    return FakeEmitter()


class EmptyEmitter:
    """Never emits signals."""

    def emit(self, df: pd.DataFrame, symbol: str, timeframe: Timeframe) -> list[Signal]:
        return []


def _empty_factory(min_conf: float, min_rr: float) -> SignalEmitter:
    return EmptyEmitter()


# ---------------------------------------------------------------------------
# Window splitting tests
# ---------------------------------------------------------------------------


class TestWindowSplitting:
    def test_anchored_mode_boundaries(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=50, step_bars=50, mode="anchored")
        folds = _compute_fold_boundaries(500, wf)

        # Fold 0: train=[0,200), test=[200,250)
        assert folds[0] == (0, 200, 200, 250)
        # Fold 1: train=[0,250), test=[250,300) — anchored grows
        assert folds[1] == (0, 250, 250, 300)
        # All folds start at 0
        assert all(f[0] == 0 for f in folds)

    def test_rolling_mode_boundaries(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=50, step_bars=50, mode="rolling")
        folds = _compute_fold_boundaries(500, wf)

        # Fold 0: train=[0,200), test=[200,250)
        assert folds[0] == (0, 200, 200, 250)
        # Fold 1: train=[50,250), test=[250,300) — rolling slides
        assert folds[1] == (50, 250, 250, 300)
        # Train window is always 200 bars
        assert all(f[1] - f[0] == 200 for f in folds)

    def test_fold_count_anchored(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100, mode="anchored")
        folds = _compute_fold_boundaries(600, wf)
        # Fold 0: train=[0,200), test=[200,300)
        # Fold 1: train=[0,300), test=[300,400)
        # Fold 2: train=[0,400), test=[400,500)
        # Fold 3: train=[0,500), test=[500,600)
        assert len(folds) == 4

    def test_fold_count_rolling(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100, mode="rolling")
        folds = _compute_fold_boundaries(600, wf)
        # Fold 0: train=[0,200), test=[200,300)
        # Fold 1: train=[100,300), test=[300,400)
        # Fold 2: train=[200,400), test=[400,500)
        # Fold 3: train=[300,500), test=[500,600)
        assert len(folds) == 4

    def test_insufficient_data_returns_empty(self):
        wf = WalkForwardConfig(train_bars=500, test_bars=100, step_bars=100)
        folds = _compute_fold_boundaries(400, wf)
        assert len(folds) == 0

    def test_test_window_must_fit(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)
        # 299 bars: train fits (200), but test needs 100 more → 300 > 299
        folds = _compute_fold_boundaries(299, wf)
        assert len(folds) == 0

    def test_exact_fit_produces_one_fold(self):
        wf = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)
        folds = _compute_fold_boundaries(300, wf)
        assert len(folds) == 1
        assert folds[0] == (0, 200, 200, 300)


# ---------------------------------------------------------------------------
# End-to-end walk-forward tests
# ---------------------------------------------------------------------------


class TestWalkForwardRunner:
    def test_runs_with_fake_emitter(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)
        config = BacktestConfig(sr_recompute_interval=50)

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, config, wf_cfg,
        )

        assert isinstance(result, WalkForwardResult)
        assert len(result.folds) > 0
        assert result.aggregate_oos is not None
        assert result.aggregate_is is not None

    def test_fold_count_matches_expected(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=300, test_bars=100, step_bars=100)

        expected_folds = len(_compute_fold_boundaries(len(df), wf_cfg))
        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
        )

        assert len(result.folds) == expected_folds

    def test_oos_trade_count_equals_sum_of_folds(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
        )

        fold_trade_sum = sum(f.oos_metrics.total_trades for f in result.folds)
        assert result.aggregate_oos.total_trades == fold_trade_sum

    def test_insufficient_data_raises(self):
        df = _make_dataset(100)
        wf_cfg = WalkForwardConfig(train_bars=500, test_bars=200)

        with pytest.raises(ValueError, match="need at least"):
            run_walk_forward(
                df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
            )

    def test_empty_emitter_produces_zero_trades(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _empty_factory, wf_config=wf_cfg,
        )

        assert result.aggregate_oos.total_trades == 0
        assert len(result.folds) > 0

    def test_folds_have_best_params(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
        )

        for fold in result.folds:
            assert fold.best_params is not None
            assert fold.best_params.min_confidence > 0
            assert fold.best_params.min_rr_ratio > 0

    def test_rolling_mode_works(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(
            train_bars=200, test_bars=100, step_bars=100, mode="rolling",
        )

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
        )

        assert len(result.folds) > 0
        assert result.aggregate_oos is not None


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


class TestWalkForwardReport:
    def test_format_report_produces_output(self):
        df = _make_dataset(800)
        wf_cfg = WalkForwardConfig(train_bars=200, test_bars=100, step_bars=100)

        result = run_walk_forward(
            df, "TEST", Timeframe.H1, _fake_factory, wf_config=wf_cfg,
        )

        report = format_walk_forward_report(result)
        assert "WALK-FORWARD" in report
        assert "AGGREGATE" in report
        assert "Robustness" in report

    def test_format_empty_result(self):
        result = WalkForwardResult()
        report = format_walk_forward_report(result)
        assert "WALK-FORWARD" in report
