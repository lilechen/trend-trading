"""Market data fetcher with unified interface.

Supports:
- A-shares (6-digit codes like 600519, 000001) via akshare
- US / HK / global tickers (like AAPL, 0700.HK, ^GSPC) via yfinance
- Index codes (000300 沪深300, ^GSPC S&P 500) via respective sources

All returned DataFrames use a uniform schema:
    columns: [date, open, high, low, close, volume]
    date:   datetime64 (UTC-naive, daily bars)
    sorted ascending by date
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd

# Lazy imports: akshare / yfinance are heavy and not needed for every code path


def is_a_share(code: str) -> bool:
    """Return True if `code` looks like a 6-digit A-share ticker.

    Examples: '600519' (上交所), '000001' (深交所主板), '300750' (创业板).
    """
    return bool(re.fullmatch(r"[036]\d{5}", code))


def is_hk_share(code: str) -> bool:
    """Return True if `code` is an HK ticker like '00700' or '0700.HK'."""
    s = code.split(".")[0]
    return bool(re.fullmatch(r"\d{4,5}", s)) and not is_a_share(code)


def is_us_ticker(code: str) -> bool:
    """Return True if `code` looks like a US ticker (alphabetic, <=5 chars)."""
    return bool(re.fullmatch(r"[A-Za-z\^]{1,6}", code)) and not code.isdigit()


def normalize_a_share_code(code: str) -> str:
    """Normalize A-share code to 6-digit padded form.

    '519' -> '000519', '600519' -> '600519'.
    """
    if is_a_share(code):
        return code.zfill(6)
    return code


def fetch_ohlcv(
    code: str,
    years: int = 3,
    adjust: Literal["qfq", "hfq", "none"] = "qfq",
) -> pd.DataFrame:
    """Fetch daily OHLCV for `code`, returning a uniform DataFrame.

    Args:
        code: Ticker symbol. 6-digit A-share, or US ticker (AAPL/TSLA),
            or HK with .HK suffix, or index like ^GSPC.
        years: How many years of history to pull.
        adjust: For A-shares, qfq (前复权) | hfq (后复权) | none (不复权).
            yfinance data is already split/dividend adjusted.

    Returns:
        DataFrame with columns [date, open, high, low, close, volume],
        sorted ascending, with date as datetime64.
    """
    if is_a_share(code):
        return _fetch_akshare(code, years, adjust)
    if is_hk_share(code):
        return _fetch_yfinance(_to_yf_symbol(code), years)
    if is_us_ticker(code):
        return _fetch_yfinance(code, years)
    # Fallback: try yfinance with the raw symbol
    return _fetch_yfinance(code, years)


def _to_yf_symbol(code: str) -> str:
    """Convert '00700' -> '0700.HK', '09988' -> '9988.HK' etc."""
    s = code.split(".")[0]
    if s.isdigit() and len(s) == 5:
        return s + ".HK"
    if s.isdigit() and len(s) == 4:
        return "0" + s + ".HK"
    return code


def _fetch_akshare(code: str, years: int, adjust: str) -> pd.DataFrame:
    import akshare as ak  # heavy import

    code6 = normalize_a_share_code(code)
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=int(365.25 * years))).strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(
        symbol=code6,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    if df is None or df.empty:
        raise ValueError(f"akshare returned no data for {code6}")
    # Map akshare columns to our schema
    rename = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    }
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
    df["volume"] = df["volume"].astype(float)
    return df


def _fetch_yfinance(code: str, years: int) -> pd.DataFrame:
    import yfinance as yf

    period = f"{years}y"
    ticker = yf.Ticker(code)
    df = ticker.history(period=period, auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f"yfinance returned no data for {code}")
    df = df.reset_index()
    # yfinance columns: Date | Open | High | Low | Close | Volume
    rename = {"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    df = df.rename(columns=rename)
    if "Adj Close" in df.columns and "close" not in df.columns:
        df = df.rename(columns={"Adj Close": "close"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
    return df