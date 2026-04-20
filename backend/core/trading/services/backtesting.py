from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    strategy: str = "ma"
    short_window: int = 9
    long_window: int = 21
    rsi_period: int = 14
    ema_window: int = 20
    initial_balance: float = 100000.0
    symbol: str = "NSE"


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _position_size(capital: float, buy_price: float) -> int:
    if buy_price <= 0:
        return 1
    return max(int(capital // buy_price), 1)


def _trade_payload(entry_time, exit_time, buy_price, sell_price, quantity: int) -> dict:
    buy_price_value = float(buy_price)
    sell_price_value = float(sell_price)
    quantity_value = max(int(quantity), 1)
    profit_value = (sell_price_value - buy_price_value) * quantity_value

    return {
        "entry_time": pd.to_datetime(entry_time).strftime("%Y-%m-%d %H:%M:%S"),
        "exit_time": pd.to_datetime(exit_time).strftime("%Y-%m-%d %H:%M:%S"),
        "buy_price": round(buy_price_value, 2),
        "sell_price": round(sell_price_value, 2),
        "quantity": quantity_value,
        "capital_used": round(buy_price_value * quantity_value, 2),
        "profit": round(profit_value, 2),
    }


def build_signal_frame(frame: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """Prepare indicator columns for selected strategy."""

    signal_frame = frame.copy()
    signal_frame["short_ma"] = signal_frame["Close"].rolling(config.short_window).mean()
    signal_frame["long_ma"] = signal_frame["Close"].rolling(config.long_window).mean()
    signal_frame["rsi"] = _compute_rsi(signal_frame["Close"], period=config.rsi_period)
    signal_frame["ema"] = signal_frame["Close"].ewm(span=config.ema_window, adjust=False).mean()
    return signal_frame


def run_ma_strategy(frame: pd.DataFrame, short: int = 9, long: int = 21, capital: float = 100000.0) -> list[dict]:
    working_frame = frame.copy()
    working_frame["short_ma"] = working_frame["Close"].rolling(short).mean()
    working_frame["long_ma"] = working_frame["Close"].rolling(long).mean()

    trades: list[dict] = []
    position = None

    for row in working_frame.itertuples(index=False):
        if pd.isna(row.short_ma) or pd.isna(row.long_ma):
            continue

        if position is None and float(row.short_ma) > float(row.long_ma):
            buy_price = float(row.Close)
            quantity = _position_size(capital, buy_price)
            position = (row.Date, buy_price, quantity)
            continue

        if position is not None and float(row.short_ma) < float(row.long_ma):
            entry_time, buy_price, quantity = position
            trades.append(_trade_payload(entry_time, row.Date, buy_price, float(row.Close), quantity))
            position = None

    if position is not None and not working_frame.empty:
        entry_time, buy_price, quantity = position
        final_row = working_frame.iloc[-1]
        trades.append(_trade_payload(entry_time, final_row["Date"], buy_price, float(final_row["Close"]), quantity))

    return trades


def run_rsi_strategy(frame: pd.DataFrame, period: int = 14, capital: float = 100000.0) -> list[dict]:
    working_frame = frame.copy()
    working_frame["rsi"] = _compute_rsi(working_frame["Close"], period=period)

    trades: list[dict] = []
    position = None

    for row in working_frame.itertuples(index=False):
        if pd.isna(row.rsi):
            continue

        if position is None and float(row.rsi) < 30:
            buy_price = float(row.Close)
            quantity = _position_size(capital, buy_price)
            position = (row.Date, buy_price, quantity)
            continue

        if position is not None and float(row.rsi) > 70:
            entry_time, buy_price, quantity = position
            trades.append(_trade_payload(entry_time, row.Date, buy_price, float(row.Close), quantity))
            position = None

    if position is not None and not working_frame.empty:
        entry_time, buy_price, quantity = position
        final_row = working_frame.iloc[-1]
        trades.append(_trade_payload(entry_time, final_row["Date"], buy_price, float(final_row["Close"]), quantity))

    return trades


def run_ema_strategy(frame: pd.DataFrame, window: int = 20, capital: float = 100000.0) -> list[dict]:
    working_frame = frame.copy()
    working_frame["ema"] = working_frame["Close"].ewm(span=window, adjust=False).mean()

    trades: list[dict] = []
    position = None

    for row in working_frame.itertuples(index=False):
        if pd.isna(row.ema):
            continue

        if position is None and float(row.Close) > float(row.ema):
            buy_price = float(row.Close)
            quantity = _position_size(capital, buy_price)
            position = (row.Date, buy_price, quantity)
            continue

        if position is not None and float(row.Close) < float(row.ema):
            entry_time, buy_price, quantity = position
            trades.append(_trade_payload(entry_time, row.Date, buy_price, float(row.Close), quantity))
            position = None

    if position is not None and not working_frame.empty:
        entry_time, buy_price, quantity = position
        final_row = working_frame.iloc[-1]
        trades.append(_trade_payload(entry_time, final_row["Date"], buy_price, float(final_row["Close"]), quantity))

    return trades


def run_backtest(frame: pd.DataFrame, config: BacktestConfig) -> dict:
    """Run selected strategy and return JSON-safe summary."""

    if frame.empty:
        return {
            "initial_balance": float(config.initial_balance),
            "total_profit": 0.0,
            "num_trades": 0,
            "win_percent": 0.0,
            "trades": [],
        }

    working_frame = frame.copy()
    working_frame["Date"] = pd.to_datetime(working_frame["Date"], errors="coerce")
    working_frame["Close"] = pd.to_numeric(working_frame["Close"], errors="coerce")
    working_frame = working_frame.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)

    strategy = config.strategy
    if strategy == "ma":
        trades = run_ma_strategy(
            working_frame,
            short=config.short_window,
            long=config.long_window,
            capital=float(config.initial_balance),
        )
    elif strategy == "rsi":
        trades = run_rsi_strategy(
            working_frame,
            period=config.rsi_period,
            capital=float(config.initial_balance),
        )
    elif strategy == "ema":
        trades = run_ema_strategy(
            working_frame,
            window=config.ema_window,
            capital=float(config.initial_balance),
        )
    else:
        trades = []

    total_profit = float(sum(trade["profit"] for trade in trades))
    win_trades = sum(1 for trade in trades if float(trade.get("profit", 0.0)) > 0)
    win_percent = (win_trades / len(trades) * 100.0) if trades else 0.0

    return {
        "initial_balance": float(config.initial_balance),
        "total_profit": round(total_profit, 2),
        "num_trades": len(trades),
        "win_percent": round(win_percent, 2),
        "trades": trades,
    }
