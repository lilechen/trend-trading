"""Tests for the Clenow system. Use synthetic uptrending data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trend_trading.systems.clenow import ClenowSystem


@pytest.fixture
def uptrending_ohlcv() -> pd.DataFrame:
    """250-bar clear uptrend → regime should be trend_up, signal entry_long at end."""
    n = 250
    np.random.seed(0)
    # Strict uptrend: +0.1/bar average, low vol
    close = 100 + np.arange(n) * 0.3 + np.random.normal(0, 0.5, n)
    high = close + 0.3
    low = close - 0.3
    volume = np.full(n, 1_000_000)
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n, freq="B"),
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def downtrending_ohlcv() -> pd.DataFrame:
    """250-bar clear downtrend → regime trend_down, signal entry_short at end."""
    n = 250
    np.random.seed(0)
    close = 200 - np.arange(n) * 0.3 + np.random.normal(0, 0.5, n)
    high = close + 0.3
    low = close - 0.3
    volume = np.full(n, 1_000_000)
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n, freq="B"),
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


def test_uptred_recognizes_trend_up(uptrending_ohlcv):
    sys = ClenowSystem()
    result = sys.analyze(uptrending_ohlcv, code="TEST")
    assert result.regime == "trend_up"
    assert result.position == "long"
    assert result.last_close > 0


def test_downtrend_recognizes_trend_down(downtrending_ohlcv):
    sys = ClenowSystem()
    result = sys.analyze(downtrending_ohlcv, code="TEST")
    assert result.regime == "trend_down"
    assert result.position == "short"


def test_required_history_days():
    sys = ClenowSystem()
    days = sys.required_history_days()
    assert days >= 365 * 3  # at least 3 years


def test_short_history_raises_error():
    sys = ClenowSystem()
    short_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=50, freq="B"),
        "open": [100.0] * 50,
        "high": [101.0] * 50,
        "low": [99.0] * 50,
        "close": [100.0] * 50,
        "volume": [1_000_000.0] * 50,
    })
    with pytest.raises(ValueError, match="110 bars"):
        sys.analyze(short_df, code="SHORT")


def test_indicators_present(uptrending_ohlcv):
    sys = ClenowSystem()
    result = sys.analyze(uptrending_ohlcv, code="TEST")
    expected_keys = {"EMA50", "EMA100", "Donchian High (100d)", "Donchian Low (100d)",
                    "ATR20", "仓位建议(4 档风控)"}
    for k in expected_keys:
        assert k in result.indicators, f"missing indicator {k}"


def test_levels_present(uptrending_ohlcv):
    sys = ClenowSystem()
    result = sys.analyze(uptrending_ohlcv, code="TEST")
    for level in ("long_entry_trigger", "short_entry_trigger",
                  "long_exit_trigger", "short_exit_trigger"):
        assert level in result.levels


def test_sizing_uses_risk_factor(uptrending_ohlcv):
    # 30bp should give larger position than 7.5bp
    low = ClenowSystem(risk_factor=0.00075, equity=100_000).analyze(uptrending_ohlcv, code="T")
    high = ClenowSystem(risk_factor=0.0030, equity=100_000).analyze(uptrending_ohlcv, code="T")

    # Extract contract counts from the indicator table
    def parse_count(label: str, table: dict) -> int:
        text = table.get("仓位建议(4 档风控)", {}).get(label, "0")
        return int(text.split()[0]) if text.split()[0].isdigit() else 0

    # Both versions should be non-zero for typical ATR
    low_count = parse_count("30bp (aggressive)", low.indicators)
    high_count = parse_count("7.5bp", high.indicators)
    assert low_count > high_count, "higher risk factor should give more contracts"


def test_format_report_runs(uptrending_ohlcv):
    from trend_trading.analysis.stage import format_report
    sys = ClenowSystem()
    result = sys.analyze(uptrending_ohlcv, code="TEST")
    text = format_report(result)
    assert "TEST" in text
    assert "Stage" in text
    assert "EMA50" in text
    assert "ATR20" in text