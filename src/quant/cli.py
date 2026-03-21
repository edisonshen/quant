"""CLI interface: quant scan, chart, backtest, report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
import pandas as pd

from quant.core.config import load_settings
from quant.core.types import Timeframe


@click.group()
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.pass_context
def cli(ctx, config_path):
    """Quant — price action auto-trading system."""
    ctx.ensure_object(dict)
    path = Path(config_path) if config_path else Path("config/settings.yaml")
    ctx.obj["settings"] = load_settings(path)


@cli.command()
@click.option("--symbol", required=True, help="Instrument symbol (NQ, ES, GC)")
@click.option("--timeframe", "tf", required=True, help="Timeframe (1D, 4H, 1H, 15m)")
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True), help="CSV file")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--end", default=None, help="End date (YYYY-MM-DD)")
@click.pass_context
def scan(ctx, symbol, tf, csv_path, start, end):
    """Scan a CSV file for pin bar setups near S/R levels."""
    from quant.analysis.analyzer import analyze
    from quant.signals.generator import generate_signals

    settings = ctx.obj["settings"]
    timeframe = Timeframe(tf)
    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

    # Load data
    from quant.data.csv_provider import CSVProvider

    provider = CSVProvider(Path(csv_path).parent)
    df = provider._read_csv(Path(csv_path), start_dt, end_dt)

    click.echo(f"Loaded {len(df)} candles for {symbol} {tf}")

    # Analyze
    result = analyze(df, symbol, timeframe, settings.analysis)
    click.echo(f"Found {len(result.pivots)} pivots, {len(result.sr_levels)} S/R levels, "
               f"{len(result.pin_bars)} pin bars, {len(result.inside_bars)} inside bars")

    if result.bias:
        click.echo(f"Bias: {result.bias.value}")

    # Generate signals
    signals = generate_signals(result, df, settings.signal)
    click.echo(f"\nSignals: {len(signals)}")

    for sig in signals:
        side = "BUY" if sig.direction.value == "LONG" else "SELL"
        click.echo(
            f"  {side} @ {sig.entry_price:.2f} | "
            f"SL {sig.stop_loss:.2f} | TP {sig.take_profit:.2f} | "
            f"R:R {sig.rr_ratio:.1f} | Conf {sig.confidence:.0%}"
        )


@cli.command()
@click.option("--symbol", required=True)
@click.option("--timeframe", "tf", required=True)
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True))
@click.option("--start", default=None)
@click.option("--end", default=None)
@click.option("--output", "output_path", default=None, help="Output HTML path")
@click.pass_context
def chart(ctx, symbol, tf, csv_path, start, end, output_path):
    """Generate an interactive chart with S/R lines and pin bars."""
    from quant.analysis.analyzer import analyze
    from quant.signals.generator import generate_signals
    from quant.viz.charts import create_chart

    settings = ctx.obj["settings"]
    timeframe = Timeframe(tf)
    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

    from quant.data.csv_provider import CSVProvider

    provider = CSVProvider(Path(csv_path).parent)
    df = provider._read_csv(Path(csv_path), start_dt, end_dt)

    result = analyze(df, symbol, timeframe, settings.analysis)
    signals = generate_signals(result, df, settings.signal)

    out = Path(output_path) if output_path else Path(f"charts/{symbol}_{tf}.html")
    fig = create_chart(df, result, signals, out)

    click.echo(f"Chart saved to {out}")


@cli.command()
@click.option("--symbol", required=True)
@click.option("--timeframe", "tf", required=True)
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True))
@click.option("--start", default=None)
@click.option("--end", default=None)
@click.option("--capital", default=100_000.0)
@click.pass_context
def backtest(ctx, symbol, tf, csv_path, start, end, capital):
    """Run a backtest on historical data."""
    from quant.backtest.engine import run_backtest
    from quant.backtest.report import format_report, plot_equity_curve

    settings = ctx.obj["settings"]
    timeframe = Timeframe(tf)
    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

    from quant.data.csv_provider import CSVProvider

    provider = CSVProvider(Path(csv_path).parent)
    df = provider._read_csv(Path(csv_path), start_dt, end_dt)

    click.echo(f"Running backtest: {symbol} {tf}, {len(df)} candles...")

    bt_result = run_backtest(
        df, symbol, timeframe,
        analysis_config=settings.analysis,
        signal_config=settings.signal,
        initial_capital=capital,
    )

    click.echo(format_report(bt_result))

    # Save equity curve
    eq_path = Path(f"charts/{symbol}_{tf}_equity.html")
    plot_equity_curve(bt_result, eq_path)
    click.echo(f"\nEquity curve saved to {eq_path}")


@cli.command()
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True))
@click.option("--symbol", required=True)
@click.option("--timeframe", "tf", required=True)
@click.pass_context
def report(ctx, csv_path, symbol, tf):
    """Generate a daily report for a symbol."""
    from quant.analysis.analyzer import analyze
    from quant.reports.daily import generate_daily_report
    from quant.signals.generator import generate_signals

    settings = ctx.obj["settings"]
    timeframe = Timeframe(tf)

    from quant.data.csv_provider import CSVProvider

    provider = CSVProvider(Path(csv_path).parent)
    df = provider._read_csv(Path(csv_path), None, None)

    result = analyze(df, symbol, timeframe, settings.analysis)
    signals = generate_signals(result, df, settings.signal)

    report_text = generate_daily_report({symbol: result}, {symbol: signals})
    click.echo(report_text)
