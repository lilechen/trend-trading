"""Slope / momentum indicators."""

from __future__ import annotations

import pandas as pd


def slope(series: pd.Series, window: int) -> pd.Series:
    """Simple slope over the last `window` bars (absolute, not normalized).

    Useful for slope-based MA filters ("MA flattening" detection).
    """
    return series - series.shift(window)


def normalized_slope(series: pd.Series, window: int) -> pd.Series:
    """Slope normalized by series level (dimensionless, comparable across instruments).

    Returns (series_t - series_{t-window}) / series_{t-window}.
    """
    return (series - series.shift(window)) / series.shift(window)