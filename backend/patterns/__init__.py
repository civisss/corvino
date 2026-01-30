"""
Chart pattern recognition: trendline, breakout, double top/bottom, H&S, channels.
"""
from .detector import PatternDetector
from .types import PatternResult, PatternType

__all__ = ["PatternDetector", "PatternResult", "PatternType"]
