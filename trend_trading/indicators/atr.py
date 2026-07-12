"""Average True Range (ATR) with EMA smoothing."""

from __future__ import annotations

import pandas as pd


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True range per bar.

    TR_t = max(high_t - low_t,
               |high_t - close_{t-1}|,
               |low_t  - close_{t-1}|)
    """
    prev_close = close.shift(1)
    hl = high - low
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20,
    smoothing: str = "ema",
) -> pd.Series:
    """Average True Range.

    Args:
        high, low, close: OHLC series.
        window: Lookback period.
        smoothing: "ema" (default, matches Clenow) or "sma" (simple).

    Returns:
        ATR series aligned to the input.
    """
    tr = true_range(high, low, close)
    if smoothing == "sma":
        return tr.rolling(window=window, min_periods=window).mean()
    if smoothing == "ema":
        # adjust=False matches the recursive TA formula
        return tr.ewm(span=window, adjust=False, min_periods=window).mean()
    raise ValueError(f"smoothing must be 'ema' or 'sma', got {smoothing!r}")