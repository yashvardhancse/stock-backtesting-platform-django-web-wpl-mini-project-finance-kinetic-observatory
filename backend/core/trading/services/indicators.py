from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Wilder-style RSI using exponentially smoothed gains and losses."""

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    average_loss = losses.ewm(alpha=1 / period, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.fillna(100.0)


def compute_indicators(
    frame: pd.DataFrame,
    *,
    short_window: int = 9,
    long_window: int = 21,
    rsi_period: int = 14,
    bb_window: int = 20,
    bb_std_dev: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
) -> pd.DataFrame:
    """Compute the indicator suite required by the platform."""

    enriched = frame.copy()
    close = enriched["Close"]
    volume = enriched["Volume"]
    high = enriched["High"]
    low = enriched["Low"]

    enriched[f"SMA_{short_window}"] = close.rolling(window=short_window, min_periods=short_window).mean()
    enriched[f"SMA_{long_window}"] = close.rolling(window=long_window, min_periods=long_window).mean()
    enriched[f"EMA_{short_window}"] = close.ewm(span=short_window, adjust=False).mean()
    enriched[f"EMA_{long_window}"] = close.ewm(span=long_window, adjust=False).mean()
    enriched["RSI"] = compute_rsi(close, period=rsi_period)

    typical_price = (high + low + close) / 3
    enriched["VWAP"] = (typical_price * volume).cumsum() / volume.cumsum().replace(0, np.nan)

    rolling_mean = close.rolling(window=bb_window, min_periods=bb_window).mean()
    rolling_std = close.rolling(window=bb_window, min_periods=bb_window).std(ddof=0)
    enriched["BB_MIDDLE"] = rolling_mean
    enriched["BB_UPPER"] = rolling_mean + (bb_std_dev * rolling_std)
    enriched["BB_LOWER"] = rolling_mean - (bb_std_dev * rolling_std)

    macd_line = close.ewm(span=macd_fast, adjust=False).mean() - close.ewm(span=macd_slow, adjust=False).mean()
    macd_signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
    enriched["MACD"] = macd_line
    enriched["MACD_SIGNAL"] = macd_signal_line
    enriched["MACD_HIST"] = macd_line - macd_signal_line
    enriched["PRICE_CHANGE"] = close.pct_change().fillna(0.0)

    return enriched


def build_indicator_frame(frame: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Alias retained for readability in the service layer."""

    return compute_indicators(frame, **kwargs)
