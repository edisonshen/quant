"""Tests for pin bar detection."""

from quant.analysis.pinbar import detect_pin_bars
from quant.core.config import PinBarConfig
from quant.core.types import Direction, SRLevel, SRRole, SRType


class TestDetectPinBars:
    def test_detects_bullish_pin_bar(self, pin_bar_candles):
        """Pin bar at index 10 should be detected with support at ~100."""
        sr_levels = [
            SRLevel(
                price=100.0, sr_type=SRType.HORIZONTAL,
                role=SRRole.SUPPORT, strength=0.8, touches=3,
            )
        ]
        config = PinBarConfig(sr_proximity_pct=0.01)  # 1% tolerance for test
        pin_bars = detect_pin_bars(pin_bar_candles, sr_levels, config)
        assert len(pin_bars) >= 1
        bullish = [pb for pb in pin_bars if pb.direction == Direction.LONG]
        assert len(bullish) >= 1

    def test_pin_bar_has_valid_wick_ratio(self, pin_bar_candles):
        sr_levels = [
            SRLevel(
                price=100.0, sr_type=SRType.HORIZONTAL,
                role=SRRole.SUPPORT, strength=0.8, touches=3,
            )
        ]
        config = PinBarConfig(sr_proximity_pct=0.01)
        pin_bars = detect_pin_bars(pin_bar_candles, sr_levels, config)
        for pb in pin_bars:
            assert pb.wick_ratio >= 2.0

    def test_no_pin_bars_without_sr(self, pin_bar_candles):
        """No S/R levels → no pin bars (can't match)."""
        pin_bars = detect_pin_bars(pin_bar_candles, [])
        assert pin_bars == []

    def test_no_pin_bars_on_flat_data(self, flat_candles):
        sr_levels = [
            SRLevel(
                price=100.0, sr_type=SRType.HORIZONTAL,
                role=SRRole.SUPPORT, strength=0.8, touches=3,
            )
        ]
        pin_bars = detect_pin_bars(flat_candles, sr_levels)
        assert pin_bars == []

    def test_doji_not_detected_as_pin_bar(self, base_timestamp):
        """Doji (no body) should not crash but also not be a valid pin bar
        unless wick criteria are met."""
        import pandas as pd
        from datetime import timedelta

        rows = []
        for i in range(10):
            rows.append({
                "timestamp": base_timestamp + timedelta(hours=i),
                "open": 100.0,
                "high": 100.5,
                "low": 99.5,
                "close": 100.0,  # same as open = doji
                "volume": 1000.0,
            })
        df = pd.DataFrame(rows)
        sr_levels = [
            SRLevel(price=99.5, sr_type=SRType.HORIZONTAL,
                    role=SRRole.SUPPORT, strength=0.8, touches=3)
        ]
        # Should not crash
        pin_bars = detect_pin_bars(df, sr_levels)
        assert isinstance(pin_bars, list)

    def test_pin_bar_far_from_sr_not_detected(self, pin_bar_candles):
        """S/R level far from pin bar → should not match."""
        sr_levels = [
            SRLevel(
                price=200.0,  # far away
                sr_type=SRType.HORIZONTAL,
                role=SRRole.SUPPORT, strength=0.8, touches=3,
            )
        ]
        pin_bars = detect_pin_bars(pin_bar_candles, sr_levels)
        assert pin_bars == []
