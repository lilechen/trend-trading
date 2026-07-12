"""Parquet-based local cache for OHLCV data.

Avoids re-fetching from remote APIs on every run. Cache key = code + (start, end).
TTL: cache is considered fresh for `ttl_hours` after last write.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from .fetcher import fetch_ohlcv

DEFAULT_CACHE_DIR = Path("data/cache")
DEFAULT_TTL_HOURS = 12  # half-day; data refreshes nightly for A-shares


def _cache_path(cache_dir: Path, code: str) -> Path:
    safe = code.replace(".", "_").replace("^", "_idx_").replace("/", "_")
    return cache_dir / f"{safe}.parquet"


def _is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime) < timedelta(hours=ttl_hours)


def get_ohlcv(
    code: str,
    years: int = 3,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch OHLCV, using parquet cache when fresh.

    Args:
        code: Ticker symbol (see fetcher.fetch_ohlcv for supported formats).
        years: History window.
        cache_dir: Where parquet files live.
        ttl_hours: Cache freshness window.
        force_refresh: If True, ignore cache and re-fetch.

    Returns:
        OHLCV DataFrame (uniform schema).
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, code)

    if not force_refresh and _is_fresh(path, ttl_hours):
        return pd.read_parquet(path)

    df = fetch_ohlcv(code, years=years)
    df.to_parquet(path, index=False)
    return df