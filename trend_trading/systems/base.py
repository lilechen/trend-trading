"""Abstract base class for a documented trend system.

Each system encodes the rules extracted from a trading book or paper
(see the research-to-backtest project). Given an OHLCV DataFrame,
the system's `analyze()` returns a snapshot of its current state
(regime, signal, recommended action, key indicator values).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AnalysisResult:
    """Snapshot of a trend system's current state for one instrument.

    Attributes:
        code: Ticker symbol analyzed.
        as_of: Date of the analysis (last bar in the input).
        last_close: Most recent close price.
        system: System name (e.g., "clenow").
        regime: One of "trend_up", "trend_down", "no_trend".
        position: Recommended position: "long", "short", "flat".
        signal: Current signal: "entry_long", "entry_short",
            "exit_long", "exit_short", or "none".
        indicators: Current values of key indicators (name -> value or formula string).
        levels: Key price levels (e.g., entry trigger, stop, take profit).
        notes: Human-readable notes (caveats, regime warnings, etc.).
    """

    code: str
    as_of: pd.Timestamp
    last_close: float
    system: str
    regime: str
    position: str
    signal: str
    indicators: dict[str, Any] = field(default_factory=dict)
    levels: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "as_of": self.as_of.strftime("%Y-%m-%d"),
            "last_close": self.last_close,
            "system": self.system,
            "regime": self.regime,
            "position": self.position,
            "signal": self.signal,
            "indicators": self.indicators,
            "levels": self.levels,
            "notes": self.notes,
        }


class TrendSystem(ABC):
    """Abstract base class for a documented trend trading system."""

    #: Display name of the system
    name: str = ""
    #: Source reference (book / paper / chapter)
    source: str = ""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, code: str = "") -> AnalysisResult:
        """Analyze the latest state of `df` and return an AnalysisResult.

        Args:
            df: OHLCV DataFrame (uniform schema: date, open, high, low, close, volume).
            code: Ticker code (for display).

        Returns:
            AnalysisResult with regime / position / signal / levels / notes.
        """

    def required_history_days(self) -> int:
        """Minimum calendar days of OHLCV history this system needs."""
        return 365 * 3  # default 3 years