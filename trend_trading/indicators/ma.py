"""Moving average indicators (SMA, EMA)."""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average.

    Args:
        series: Price series (typically close).
        window: Lookback period in bars.

    Returns:
        SMA series aligned to the input.
    """
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int, adjust: bool = False) -> pd.Series:
    """Exponential moving average.

    Uses adjust=False to match the recursive formula used in classic TA:
        EMA_t = price_t * k + EMA_{t-1} * (1 - k),  k = 2 / (window + 1)
    which is what most charting platforms display.

    The first non-NaN value is `series.iloc[0]` (seeded with first bar).
    Use ema(...).iloc[window-1:] for a fully-warmed series.

    Args:
        series: Price series (typically close).
        window: EMA period.
        adjust: If True, use pandas adjusted (weighted historical) formula.
            Default False to match Clenow / Weinstein / standard TA.

    Returns:
        EMA series aligned to the input.
    """
    return series.ewm(span=window, adjust=adjust, min_periods=1).mean()


def ema_slope(series: pd.Series, window: int, slope_bars: int) -> pd.Series:
    """Slope of EMA over the last `slope_bars` bars, expressed as a fraction of the EMA value.

    Returns NaN until `window + slope_bars` bars are available.

    Args:
        series: Price series.
        window: EMA period.
        slope_bars: Number of bars to look back for the slope.

    Returns:
        Series of slope fractions (e.g., 0.012 means +1.2%).
    """
    e = ema(series, window)
    return (e - e.shift(slope_bars)) / e.shift(slope_bars)