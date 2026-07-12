"""Donchian channel (rolling high/low) indicators."""

from __future__ import annotations

import pandas as pd


def rolling_max(series: pd.Series, window: int) -> pd.Series:
    """Highest value over the last `window` bars (excluding current bar by default in Clenow's spec).

    Args:
        series: Price series.
        window: Lookback window. The Clenow spec uses window=100 for entry
            and window=50 for exit. The current bar is NOT included in the
            window — see `rolling_max_no_current` if you need inclusive.

    Returns:
        Rolling max series (current bar excluded).
    """
    return series.shift(1).rolling(window=window, min_periods=window).max()


def rolling_min(series: pd.Series, window: int) -> pd.Series:
    """Lowest value over the last `window` bars (current bar excluded)."""
    return series.shift(1).rolling(window=window, min_periods=window).min()


def rolling_max_inclusive(series: pd.Series, window: int) -> pd.Series:
    """Rolling max INCLUDING the current bar (used for some checks)."""
    return series.rolling(window=window, min_periods=window).max()


def rolling_min_inclusive(series: pd.Series, window: int) -> pd.Series:
    """Rolling min INCLUDING the current bar."""
    return series.rolling(window=window, min_periods=window).min()


def three_weeks_tight(close: pd.Series, window: int = 15, max_range_pct: float = 0.01) -> pd.Series:
    """O'Neil's three-weeks-tight proxy: rolling close range < max_range_pct of mean.

    Args:
        close: Close series.
        window: Lookback in bars (15 ~ 3 weeks of trading days).
        max_range_pct: Max (max-min)/mean threshold (default 1%).

    Returns:
        Boolean series, True when the range is tight.
    """
    hi = rolling_max_inclusive(close, window)
    lo = rolling_min_inclusive(close, window)
    rng = (hi - lo) / close.rolling(window=window, min_periods=window).mean()
    return rng < max_range_pct