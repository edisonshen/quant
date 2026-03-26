"""Walk-forward cross-validation — out-of-sample backtesting.

Splits data into sequential train/test windows. On each fold:
  1. Train: run parameter sweep to find best params
  2. Test: backtest with those params on unseen data (out-of-sample)

Prevents overfitting by ensuring metrics come from data never seen during optimization.

Dependency rule: imports only from core/ and backtest/.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from rainier.core.config import BacktestConfig, WalkForwardConfig
from rainier.core.protocols import BacktestMetrics, TradeRecord
from rainier.core.types import Timeframe

from .engine import compute_metrics, run_backtest
from .sweep import EmitterFactory, SweepParams, run_sweep

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class WalkForwardFold:
    """Results from a single train/test fold."""
    fold_index: int
    train_start: int  # bar index
    train_end: int
    test_start: int
    test_end: int
    best_params: SweepParams
    in_sample_metrics: BacktestMetrics
    oos_metrics: BacktestMetrics


@dataclass
class WalkForwardResult:
    """Aggregate results from walk-forward cross-validation."""
    folds: list[WalkForwardFold] = field(default_factory=list)
    aggregate_oos: BacktestMetrics | None = None
    aggregate_is: BacktestMetrics | None = None


# ---------------------------------------------------------------------------
# Window computation
# ---------------------------------------------------------------------------


def _compute_fold_boundaries(
    n_bars: int,
    wf_config: WalkForwardConfig,
) -> list[tuple[int, int, int, int]]:
    """Compute (train_start, train_end, test_start, test_end) for each fold.

    Returns list of 4-tuples. train_end and test_end are exclusive (slice-style).
    """
    folds: list[tuple[int, int, int, int]] = []
    fold = 0

    while True:
        if wf_config.mode == "rolling":
            train_start = fold * wf_config.step_bars
            train_end = train_start + wf_config.train_bars
        else:  # anchored
            train_start = 0
            train_end = wf_config.train_bars + fold * wf_config.step_bars

        test_start = train_end
        test_end = test_start + wf_config.test_bars

        if test_end > n_bars:
            break

        folds.append((train_start, train_end, test_start, test_end))
        fold += 1

    return folds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_walk_forward(
    df: pd.DataFrame,
    symbol: str,
    timeframe: Timeframe,
    emitter_factory: EmitterFactory,
    config: BacktestConfig | None = None,
    wf_config: WalkForwardConfig | None = None,
) -> WalkForwardResult:
    """Run walk-forward cross-validation.

    Args:
        df: Full OHLCV dataset
        symbol: Instrument symbol
        timeframe: Bar timeframe
        emitter_factory: Creates SignalEmitter for given (min_confidence, min_rr_ratio)
        config: Backtest config (slippage, commission, etc.)
        wf_config: Walk-forward config (window sizes, mode)

    Returns:
        WalkForwardResult with per-fold and aggregate metrics

    Raises:
        ValueError: If dataset is too small for even one fold
    """
    if config is None:
        config = BacktestConfig()
    if wf_config is None:
        wf_config = WalkForwardConfig()

    folds_bounds = _compute_fold_boundaries(len(df), wf_config)

    if not folds_bounds:
        min_needed = wf_config.train_bars + wf_config.test_bars
        raise ValueError(
            f"Dataset has {len(df)} bars, need at least {min_needed} "
            f"for one fold (train={wf_config.train_bars}, test={wf_config.test_bars})"
        )

    result = WalkForwardResult()
    all_oos_trades: list[TradeRecord] = []
    all_is_trades: list[TradeRecord] = []
    all_oos_equity_deltas: list[float] = []
    all_is_equity_deltas: list[float] = []

    # Metric name -> SweepResult attribute for best selection
    metric_to_best = {
        "sharpe_ratio": "best_by_sharpe",
        "total_net_pnl": "best_by_pnl",
        "profit_factor": "best_by_profit_factor",
    }
    best_attr = metric_to_best.get(wf_config.optimize_metric, "best_by_sharpe")

    for fold_idx, (tr_start, tr_end, te_start, te_end) in enumerate(folds_bounds):
        train_df = df.iloc[tr_start:tr_end].reset_index(drop=True)
        test_df = df.iloc[te_start:te_end].reset_index(drop=True)

        # --- Train: sweep to find best params ---
        sweep_result = run_sweep(
            train_df, symbol, timeframe, emitter_factory, config,
        )

        best_params: SweepParams | None = getattr(sweep_result, best_attr, None)
        if best_params is None:
            # Fallback: use first sweep params if no best found
            best_params = SweepParams(
                min_confidence=config.sweep_min_confidence[0],
                min_rr_ratio=config.sweep_min_rr_ratio[0],
            )

        # In-sample metrics (best params on train data)
        is_emitter = emitter_factory(best_params.min_confidence, best_params.min_rr_ratio)
        is_metrics = run_backtest(train_df, symbol, timeframe, is_emitter, config)

        # --- Test: evaluate best params out-of-sample ---
        oos_emitter = emitter_factory(best_params.min_confidence, best_params.min_rr_ratio)
        oos_metrics = run_backtest(test_df, symbol, timeframe, oos_emitter, config)

        fold = WalkForwardFold(
            fold_index=fold_idx,
            train_start=tr_start,
            train_end=tr_end,
            test_start=te_start,
            test_end=te_end,
            best_params=best_params,
            in_sample_metrics=is_metrics,
            oos_metrics=oos_metrics,
        )
        result.folds.append(fold)

        all_oos_trades.extend(oos_metrics.trades)
        all_is_trades.extend(is_metrics.trades)

        # Collect equity deltas for aggregation
        if len(oos_metrics.equity_curve) > 1:
            deltas = [
                oos_metrics.equity_curve[i] - oos_metrics.equity_curve[i - 1]
                for i in range(1, len(oos_metrics.equity_curve))
            ]
            all_oos_equity_deltas.extend(deltas)
        if len(is_metrics.equity_curve) > 1:
            deltas = [
                is_metrics.equity_curve[i] - is_metrics.equity_curve[i - 1]
                for i in range(1, len(is_metrics.equity_curve))
            ]
            all_is_equity_deltas.extend(deltas)

    # --- Aggregate OOS metrics ---
    oos_equity = [config.initial_capital]
    for delta in all_oos_equity_deltas:
        oos_equity.append(oos_equity[-1] + delta)
    result.aggregate_oos = compute_metrics(all_oos_trades, oos_equity, config)

    is_equity = [config.initial_capital]
    for delta in all_is_equity_deltas:
        is_equity.append(is_equity[-1] + delta)
    result.aggregate_is = compute_metrics(all_is_trades, is_equity, config)

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_walk_forward_report(result: WalkForwardResult) -> str:
    """Format walk-forward results as a readable text report."""
    lines = [
        "=" * 100,
        "WALK-FORWARD CROSS-VALIDATION RESULTS",
        "=" * 100,
        "",
        f"{'Fold':>5} {'Train':>12} {'Test':>12} {'Conf':>6} {'R:R':>5} "
        f"{'OOS Trades':>10} {'OOS WR':>8} {'OOS PnL':>12} {'OOS Sharpe':>10} "
        f"{'IS PnL':>12}",
        "-" * 100,
    ]

    for fold in result.folds:
        oos = fold.oos_metrics
        is_m = fold.in_sample_metrics
        lines.append(
            f"{fold.fold_index:>5} "
            f"{fold.train_start:>5}-{fold.train_end:<5} "
            f"{fold.test_start:>5}-{fold.test_end:<5} "
            f"{fold.best_params.min_confidence:>6.2f} "
            f"{fold.best_params.min_rr_ratio:>5.1f} "
            f"{oos.total_trades:>10} "
            f"{oos.win_rate:>7.1%} "
            f"{oos.total_net_pnl:>+12,.2f} "
            f"{oos.sharpe_ratio:>10.2f} "
            f"{is_m.total_net_pnl:>+12,.2f}"
        )

    lines.append("=" * 100)
    lines.append("")

    # Aggregate comparison
    if result.aggregate_oos and result.aggregate_is:
        oos = result.aggregate_oos
        is_m = result.aggregate_is
        lines.append("AGGREGATE COMPARISON (In-Sample vs Out-of-Sample)")
        lines.append("-" * 60)
        lines.append(f"  {'':20} {'In-Sample':>15} {'OOS':>15}")
        lines.append(f"  {'Total trades':20} {is_m.total_trades:>15} {oos.total_trades:>15}")
        lines.append(f"  {'Win rate':20} {is_m.win_rate:>14.1%} {oos.win_rate:>14.1%}")
        lines.append(
            f"  {'Profit factor':20} {is_m.profit_factor:>15.2f} {oos.profit_factor:>15.2f}"
        )
        lines.append(
            f"  {'Net P&L':20} {is_m.total_net_pnl:>+15,.2f} {oos.total_net_pnl:>+15,.2f}"
        )
        lines.append(
            f"  {'Sharpe ratio':20} {is_m.sharpe_ratio:>15.2f} {oos.sharpe_ratio:>15.2f}"
        )
        lines.append(
            f"  {'Max drawdown':20} {is_m.max_drawdown_pct:>14.2%} {oos.max_drawdown_pct:>14.2%}"
        )

        # Robustness ratio
        if is_m.total_net_pnl != 0:
            robustness = oos.total_net_pnl / is_m.total_net_pnl
            lines.append(f"\n  Robustness ratio (OOS/IS P&L): {robustness:.2f}")
            if robustness > 0.5:
                lines.append("  → Strategy shows robustness (ratio > 0.5)")
            elif robustness > 0:
                lines.append("  → Strategy degrades out-of-sample (0 < ratio < 0.5)")
            else:
                lines.append("  → Strategy fails out-of-sample (negative OOS)")

    return "\n".join(lines)
