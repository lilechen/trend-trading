"""Clenow's CTA trend-following system (Ch.4 of "Following the Trend").

Core rules (per `research-to-backtest/examples/Clenow/Clenow.system-spec.yaml`):

  Trend filter:    EMA 50 vs EMA 100 (exponential MA)
                   bullish = EMA50 > EMA100
                   bearish = EMA50 < EMA100
  Entry long:      close >= max(close, 100)  AND  regime == bullish
  Entry short:     close <= min(close, 100)  AND  regime == bearish
  Exit long:       close <= min(close, 50)   OR  regime == bearish
  Exit short:      close >= max(close, 50)   OR  regime == bullish
  Sizing:          Contracts = 0.0015 * Equity / (ATR20 * PointValue)
                   Round DOWN.  4 risk levels: 7.5 / 10 / 15 / 30 bp.

The current stage is reported in human-readable terms:

  - regime        : "trend_up" / "trend_down" / "no_trend"
  - signal        : "entry_long" / "exit_long" / "entry_short" / "exit_short" / "none"
  - recommended   : "long" / "short" / "flat"
  - key levels    : entry trigger (100-day hi/lo), exit trigger (50-day lo/hi),
                    ATR20, EMA50, EMA100, sizing at default 15bp.
"""

from __future__ import annotations

import pandas as pd

from ..indicators.atr import atr
from ..indicators.donchian import rolling_max, rolling_min
from ..indicators.ma import ema, ema_slope
from .base import AnalysisResult, TrendSystem

# Default risk levels the user can pick from (Table 4.5 of the book)
DEFAULT_RISK_FACTORS = {
    "7.5bp": 0.00075,
    "10bp": 0.0010,
    "15bp (core)": 0.0015,
    "30bp (aggressive)": 0.0030,
}


class ClenowSystem(TrendSystem):
    """Clenow's core trend-following system (Ch.4)."""

    name = "Clenow CTA (Ch.4)"
    source = "Andreas F. Clenow《Following the Trend》Ch.4 (核心策略)"

    def __init__(self, risk_factor: float = 0.0015, equity: float = 100_000.0):
        """Args:
            risk_factor: 风险因子,默认 15bp (Clenow 核心值)。
            equity: 账户资金(用于 sizing 计算)。
        """
        self.risk_factor = risk_factor
        self.equity = equity

    def required_history_days(self) -> int:
        # 200-day MA is the longest lookback, but 3 years gives comfortable margin
        return 365 * 3

    def analyze(self, df: pd.DataFrame, code: str = "") -> AnalysisResult:
        """Apply Clenow's rules to the latest state of `df`."""
        if len(df) < 110:
            raise ValueError(
                f"need at least 110 bars of history (have {len(df)}); "
                "Clenow uses 100-day Donchian + 100-day EMA"
            )

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Indicators
        ema50 = ema(close, 50)
        ema100 = ema(close, 100)
        slope_ema50_4w = ema_slope(close, 50, slope_bars=20)  # ~ 4 weeks
        donchian_high_100 = rolling_max(close, 100)
        donchian_low_100 = rolling_min(close, 100)
        donchian_high_50 = rolling_max(close, 50)
        donchian_low_50 = rolling_min(close, 50)
        atr20 = atr(high, low, close, window=20, smoothing="ema")

        # Latest values
        last_close = float(close.iloc[-1])
        e50 = float(ema50.iloc[-1])
        e100 = float(ema100.iloc[-1])
        slope_val = float(slope_ema50_4w.iloc[-1]) if not pd.isna(slope_ema50_4w.iloc[-1]) else 0.0
        hi100 = float(donchian_high_100.iloc[-1])
        lo100 = float(donchian_low_100.iloc[-1])
        hi50 = float(donchian_high_50.iloc[-1])
        lo50 = float(donchian_low_50.iloc[-1])
        a20 = float(atr20.iloc[-1])

        # Regime
        if e50 > e100:
            regime = "trend_up"
        elif e50 < e100:
            regime = "trend_down"
        else:
            regime = "no_trend"

        # Entry / exit signal (rule evaluation)
        signal = "none"
        notes: list[str] = []

        # Long side
        long_entry = (last_close >= hi100) and (regime == "trend_up")
        long_exit = (last_close <= lo50) or (regime != "trend_up")

        # Short side
        short_entry = (last_close <= lo100) and (regime == "trend_down")
        short_exit = (last_close >= hi50) or (regime != "trend_down")

        if long_entry:
            signal = "entry_long"
        elif short_entry:
            signal = "entry_short"
        elif long_exit and regime != "trend_up":
            # We were in a long regime and just flipped — exit long signal
            signal = "exit_long"
        elif short_exit and regime != "trend_down":
            signal = "exit_short"
        # else: signal remains "none" (no fresh entry or exit today)

        # Recommended position
        if regime == "trend_up":
            position = "long" if long_exit is False else "flat"
            if long_exit:
                notes.append("已在 long,但 exit 触发已满足 — 应清仓或反手")
        elif regime == "trend_down":
            position = "short" if not short_exit else "flat"
            if short_exit:
                notes.append("已在 short,但 exit 触发已满足 — 应回补或反手")
        else:
            position = "flat"
            notes.append("EMA50 与 EMA100 接近或交叉 — 趋势不明,观望")

        # Stage / human-readable verdict
        if regime == "trend_up" and not long_exit:
            stage = "Stage 2(上升趋势,持仓等待)"
        elif regime == "trend_up" and long_exit:
            stage = "Stage 3(转弱/震荡,准备减仓或退出)"
        elif regime == "trend_down" and not short_exit:
            stage = "Stage 2(下降趋势,可做空)"
        elif regime == "trend_down" and short_exit:
            stage = "Stage 1(底部反转信号出现)"
        else:
            stage = "无明确趋势(EMA50 ≈ EMA100)"

        # Sizing at 4 risk levels
        sizing_table: dict[str, str] = {}
        for label, rf in DEFAULT_RISK_FACTORS.items():
            contracts = (rf * self.equity) / max(a20, 1e-9)
            sizing_table[label] = f"{int(contracts)} 手" if contracts >= 1 else "< 1 手(资金过小)"

        # Indicator dump
        indicators = {
            "EMA50": round(e50, 4),
            "EMA100": round(e100, 4),
            "EMA50 4周斜率": f"{slope_val*100:+.2f}%",
            "Donchian High (100d)": round(hi100, 4),
            "Donchian Low (100d)": round(lo100, 4),
            "Donchian High (50d)": round(hi50, 4),
            "Donchian Low (50d)": round(lo50, 4),
            "ATR20": round(a20, 4),
            "距 100d 高": f"{(last_close/hi100 - 1)*100:+.2f}%",
            "距 50d 低": f"{(last_close/lo50 - 1)*100:+.2f}%",
        }

        # Key levels
        levels = {
            "long_entry_trigger": round(hi100, 4),
            "short_entry_trigger": round(lo100, 4),
            "long_exit_trigger": round(lo50, 4),
            "short_exit_trigger": round(hi50, 4),
        }

        # Risk-level sizing
        indicators["仓位建议(4 档风控)"] = sizing_table

        # Cautions
        if abs(e50 - e100) / e100 < 0.005:
            notes.append("EMA50 与 EMA100 距离 <0.5%,趋势边界,避免追单")
        if slope_val < -0.02:
            notes.append("EMA50 4 周斜率 < -2%,上升趋势走弱,警惕")
        if last_close > hi100 * 1.05:
            notes.append("价格已远超 100 日高 +5%,可能过度延伸,不要追价")

        as_of = pd.Timestamp(df["date"].iloc[-1])
        return AnalysisResult(
            code=code,
            as_of=as_of,
            last_close=last_close,
            system="clenow",
            regime=regime,
            position=position,
            signal=signal,
            indicators=indicators,
            levels=levels,
            notes=[stage] + notes,
        )