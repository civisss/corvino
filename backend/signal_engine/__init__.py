"""
Signal engine: orchestrate data, indicators, patterns, AI, risk; produce final signals.
"""
from .generator import SignalGenerator
from .schemas import RawSignal

__all__ = ["SignalGenerator", "RawSignal"]
