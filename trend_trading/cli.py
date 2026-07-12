"""CLI for trend-trading: analyze a ticker and print the stage report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from .analysis.stage import analyze, format_report
from .systems.clenow import ClenowSystem, DEFAULT_RISK_FACTORS

app = typer.Typer(
    name="trend-trading",
    help="Trend trading analysis toolkit.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command(name="analyze")
def analyze_cmd(
    code: str = typer.Argument(..., help="Ticker code (A-share 6 digits, US ticker, etc.)"),
    system: str = typer.Option("clenow", "--system", "-s", help="Trend system: clenow (more later)"),
    years: int = typer.Option(3, "--years", "-y", help="Years of history to fetch"),
    risk_bp: float = typer.Option(15.0, "--risk-bp", "-r", help="Default risk factor in basis points"),
    equity: float = typer.Option(100_000.0, "--equity", "-e", help="Account equity for sizing"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force refresh data, ignore cache"),
    json_out: bool = typer.Option(False, "--json", help="Output machine-readable JSON instead of text"),
) -> None:
    """Analyze the current trend stage of a ticker.

    Example:

        trend-trading analyze 600519
        trend-trading analyze AAPL --years 5 --equity 500000
    """
    if system != "clenow":
        typer.echo(f"Unknown system: {system}", err=True)
        raise typer.Exit(code=1)

    sys_obj = ClenowSystem(risk_factor=risk_bp / 10_000, equity=equity)

    try:
        result = analyze(code, system=sys_obj, years=years, use_cache=not no_cache)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_out:
        typer.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        typer.echo(format_report(result))


@app.command()
def systems() -> None:
    """List available trend systems."""
    typer.echo("Available systems:")
    typer.echo("  - clenow: Andreas F. Clenow《Following the Trend》Ch.4 (EMA50/100 + Donchian 100/50 + ATR20)")
    typer.echo("  - (more coming)")


if __name__ == "__main__":
    app()