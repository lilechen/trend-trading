"""High-level stage analysis: fetch data + run system + format report."""

from __future__ import annotations

from typing import Literal

import pandas as pd

from ..data.cache import get_ohlcv
from ..systems.base import AnalysisResult, TrendSystem
from ..systems.clenow import ClenowSystem


def analyze(
    code: str,
    system: TrendSystem | Literal["clenow"] = "clenow",
    years: int = 3,
    use_cache: bool = True,
) -> AnalysisResult:
    """Fetch OHLCV for `code` and run the given trend system.

    Args:
        code: Ticker symbol (A-share 6-digit, US ticker, etc.).
        system: A TrendSystem instance, or the string "clenow" (default).
        years: How many years of history to pull.
        use_cache: If True, use parquet cache when fresh.

    Returns:
        AnalysisResult from the system's analyze().
    """
    if system == "clenow":
        sys_obj: TrendSystem = ClenowSystem()
    elif isinstance(system, TrendSystem):
        sys_obj = system
    else:
        raise ValueError(f"Unknown system: {system!r}")

    df = get_ohlcv(code, years=years, force_refresh=not use_cache)
    return sys_obj.analyze(df, code=code)


# --- report formatting ----------------------------------------------------

_BAR = "=" * 60
_SUB = "-" * 60


def format_report(result: AnalysisResult) -> str:
    """Format an AnalysisResult as a human-readable text report."""
    lines: list[str] = []
    lines.append(_BAR)
    lines.append(f"  {result.code}  —  {result.system} 阶段分析")
    lines.append(_BAR)
    lines.append(f"数据截止: {result.as_of.strftime('%Y-%m-%d')}")
    lines.append(f"当前价:   {result.last_close:.2f}")
    lines.append("")

    # Stage + regime + signal
    lines.append("[阶段判定]")
    if result.notes:
        lines.append(f"  阶段:    {result.notes[0]}")
    lines.append(f"  Regime:  {result.regime}")
    lines.append(f"  Signal:  {result.signal}")
    lines.append(f"  建议持仓: {result.position}")
    lines.append("")

    # Indicators
    lines.append("[关键指标]")
    skip_keys = {"仓位建议(4 档风控)"}
    sizing_table: dict | None = None
    for k, v in result.indicators.items():
        if k in skip_keys:
            sizing_table = v
            continue
        if isinstance(v, float):
            lines.append(f"  {k:<24} {v:>12.4f}")
        else:
            lines.append(f"  {k:<24} {str(v):>12}")
    lines.append("")

    # Sizing
    if sizing_table:
        lines.append("[仓位建议(risk factor 4 档)]")
        for label, contracts in sizing_table.items():
            lines.append(f"  {label:<24} {contracts:>12}")
        lines.append("")

    # Levels
    lines.append("[关键价位]")
    for k, v in result.levels.items():
        lines.append(f"  {k:<24} {v:>12.2f}")
    lines.append("")

    # Notes (excluding the stage which is already shown)
    extra_notes = [n for n in result.notes[1:]] if result.notes else []
    if extra_notes:
        lines.append("[注意]")
        for n in extra_notes:
            lines.append(f"  - {n}")
        lines.append("")

    lines.append(_BAR)
    return "\n".join(lines)