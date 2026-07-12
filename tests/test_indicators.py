"""Tests for technical indicators. Use synthetic data — no network required."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trend_trading.indicators.atr import atr, true_range
from trend_trading.indicators.donchian import rolling_max, rolling_min, three_weeks_tight
from trend_trading.indicators.ma import ema, ema_slope, sma
from trend_trading.indicators.slope import normalized_slope, slope


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """150-bar synthetic uptrending OHLCV for tests."""
    n = 150
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.normal(0.05, 1.0, n))  # mild uptrend
    high = close + np.abs(np.random.normal(0.5, 0.2, n))
    low = close - np.abs(np.random.normal(0.5, 0.2, n))
    volume = np.random.randint(1_000_000, 5_000_000, n)
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n, freq="B"),
        "open": close + np.random.normal(0, 0.3, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


# --- SMA / EMA ------------------------------------------------------------

def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = sma(s, 3)
    # SMA at index 2: (1+2+3)/3 = 2.0
    assert out.iloc[2] == pytest.approx(2.0)
    # SMA at index 4: (3+4+5)/3 = 4.0
    assert out.iloc[4] == pytest.approx(4.0)
    # First window-1 values are NaN
    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])


def test_ema_matches_recursive_formula():
    s = pd.Series([10, 20, 30, 40, 50], dtype=float)
    out = ema(s, 3)
    # k = 2/(3+1) = 0.5
    # Seed: EMA[0] = 10
    # EMA[1] = 20*0.5 + 10*0.5 = 15
    # EMA[2] = 30*0.5 + 15*0.5 = 22.5
    # EMA[3] = 40*0.5 + 22.5*0.5 = 31.25
    # EMA[4] = 50*0.5 + 31.25*0.5 = 40.625
    assert out.iloc[0] == pytest.approx(10.0)
    assert out.iloc[1] == pytest.approx(15.0)
    assert out.iloc[2] == pytest.approx(22.5)
    assert out.iloc[3] == pytest.approx(31.25)
    assert out.iloc[4] == pytest.approx(40.625)


def test_ema_slope(synthetic_ohlcv):
    s = synthetic_ohlcv["close"]
    slope_series = ema_slope(s, window=20, slope_bars=20)
    # Just check it produces a finite value (sign depends on noise in synthetic data)
    last = slope_series.dropna().iloc[-1]
    assert np.isfinite(last)
    # And that the series has the right length
    assert slope_series.notna().sum() > 0


# --- ATR / True Range -----------------------------------------------------

def test_true_range(synthetic_ohlcv):
    df = synthetic_ohlcv
    tr = true_range(df["high"], df["low"], df["close"])
    # First value is well-defined: just high - low (no prev close for cross terms)
    assert not pd.isna(tr.iloc[0])
    # All values should be positive
    assert (tr > 0).all()


def test_atr_positive(synthetic_ohlcv):
    df = synthetic_ohlcv
    for smoothing in ("ema", "sma"):
        a = atr(df["high"], df["low"], df["close"], window=20, smoothing=smoothing)
        valid = a.dropna()
        assert (valid > 0).all()
        assert len(valid) == len(df) - 20 + 1


# --- Donchian -------------------------------------------------------------

def test_rolling_max_excludes_current(synthetic_ohlcv):
    close = synthetic_ohlcv["close"]
    m = rolling_max(close, 5)  # excludes current bar
    # At index 5, the max should be over close[0:5] (not including close[5])
    expected = close.iloc[0:5].max()
    assert m.iloc[5] == pytest.approx(expected)


def test_rolling_min_excludes_current(synthetic_ohlcv):
    close = synthetic_ohlcv["close"]
    m = rolling_min(close, 5)
    expected = close.iloc[0:5].min()
    assert m.iloc[5] == pytest.approx(expected)


def test_three_weeks_tight_returns_bool(synthetic_ohlcv):
    close = synthetic_ohlcv["close"]
    tight = three_weeks_tight(close, window=15, max_range_pct=0.01)
    assert tight.dtype == bool
    # Random data shouldn't be tight in most windows
    assert tight.sum() < len(close) / 2


# --- Slope ----------------------------------------------------------------

def test_normalized_slope(synthetic_ohlcv):
    s = synthetic_ohlcv["close"]
    sl = normalized_slope(s, window=20)
    valid = sl.dropna()
    assert len(valid) > 0
    # Most recent value should be in a reasonable range
    assert -0.5 < valid.iloc[-1] < 0.5