"""Trend trading system implementations."""

from .base import TrendSystem, AnalysisResult
from .clenow import ClenowSystem

__all__ = ["TrendSystem", "AnalysisResult", "ClenowSystem"]