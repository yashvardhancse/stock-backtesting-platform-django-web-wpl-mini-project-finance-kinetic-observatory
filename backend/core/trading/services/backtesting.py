from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .indicators import build_indicator_frame
from .portfolio import simulate_paper_trading
from .serialization import dataframe_records
from .simulation import run_monte_carlo_simulation


@dataclass(frozen=True)
class BacktestConfig:
    strategy: str = "ma_crossover"
    ma_type: str = "sma"
    short_window: int = 9
    long_window: int = 21
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    bb_window: int = 20
    bb_std_dev: float = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    initial_balance: float = 100000.0
    allocation_fraction: float = 1.0
    simulations: int = 150
    symbol: str = "SYMBOL"


def _cross_above(fast: pd.Series, slow: pd.Series) -> pd.Series:
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))


def _cross_below(fast: pd.Series, slow: pd.Series) -> pd.Series:
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))


def build_signal_frame(frame: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """Create a binary signal stream for the selected strategy."""

    enriched_frame = build_indicator_frame(
        frame,
        short_window=config.short_window,
        long_window=config.long_window,
        rsi_period=config.rsi_period,
        bb_window=config.bb_window,
        bb_std_dev=config.bb_std_dev,
        macd_fast=config.macd_fast,
        macd_slow=config.macd_slow,
        macd_signal=config.macd_signal,
    )

    signal_frame = enriched_frame.copy()
    signal_frame["Signal"] = 0
    signal_frame["SignalType"] = "HOLD"

    strategy = config.strategy
    short_label = f"SMA_{config.short_window}" if config.ma_type == "sma" else f"EMA_{config.short_window}"
    long_label = f"SMA_{config.long_window}" if config.ma_type == "sma" else f"EMA_{config.long_window}"

    if strategy == "ma_crossover":
        short_series = signal_frame[short_label]
        long_series = signal_frame[long_label]
        buy_mask = _cross_above(short_series, long_series)
        sell_mask = _cross_below(short_series, long_series)
    elif strategy == "rsi":
        buy_mask = _cross_below(signal_frame["RSI"], pd.Series(config.rsi_oversold, index=signal_frame.index))
        sell_mask = _cross_above(signal_frame["RSI"], pd.Series(config.rsi_overbought, index=signal_frame.index))
    elif strategy == "vwap":
        buy_mask = _cross_above(signal_frame["Close"], signal_frame["VWAP"])
        sell_mask = _cross_below(signal_frame["Close"], signal_frame["VWAP"])
    elif strategy == "bollinger":
        buy_mask = _cross_below(signal_frame["Close"], signal_frame["BB_LOWER"])
        sell_mask = _cross_above(signal_frame["Close"], signal_frame["BB_UPPER"])
    elif strategy == "macd":
        buy_mask = _cross_above(signal_frame["MACD"], signal_frame["MACD_SIGNAL"])
        sell_mask = _cross_below(signal_frame["MACD"], signal_frame["MACD_SIGNAL"])
    else:
        buy_mask = _cross_above(signal_frame[short_label], signal_frame[long_label])
        sell_mask = _cross_below(signal_frame[short_label], signal_frame[long_label])

    signal_frame.loc[buy_mask, "Signal"] = 1
    signal_frame.loc[buy_mask, "SignalType"] = "BUY"
    signal_frame.loc[sell_mask, "Signal"] = -1
    signal_frame.loc[sell_mask, "SignalType"] = "SELL"

    return signal_frame


def _calculate_max_drawdown(equity_series: pd.Series) -> float:
    running_max = equity_series.cummax()
    drawdown = equity_series / running_max - 1.0
    return float(drawdown.min() * 100.0)


def _calculate_sharpe_ratio(return_series: pd.Series) -> float:
    if return_series.empty:
        return 0.0
    volatility = float(return_series.std(ddof=0))
    if volatility == 0.0:
        return 0.0
    return float((return_series.mean() / volatility) * np.sqrt(252))


def _series_to_json_list(series: pd.Series) -> list[float | None]:
    values: list[float | None] = []
    for value in series.tolist():
        if value is None or pd.isna(value):
            values.append(None)
        else:
            values.append(float(value))
    return values


def run_backtest(frame: pd.DataFrame, config: BacktestConfig) -> dict:
    """Run a long-only backtest and return JSON-friendly analytics."""

    signal_frame = build_signal_frame(frame, config)

    cash_balance = float(config.initial_balance)
    position_quantity = 0
    entry_price = 0.0
    entry_timestamp = None
    trade_rows: list[dict] = []
    signal_rows: list[dict] = []
    equity_rows: list[dict] = []

    for row in signal_frame.itertuples(index=False):
        close_price = float(row.Close)
        timestamp = pd.to_datetime(row.Date)
        signal = int(getattr(row, "Signal", 0))
        signal_type = getattr(row, "SignalType", "HOLD")

        if signal == 1 and position_quantity == 0 and close_price > 0:
            quantity = max(1, int(max(cash_balance * config.allocation_fraction, close_price) // close_price))
            trade_cost = quantity * close_price
            if trade_cost <= cash_balance:
                cash_balance -= trade_cost
                position_quantity = quantity
                entry_price = close_price
                entry_timestamp = timestamp
                signal_rows.append(
                    {
                        "date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "price": close_price,
                        "type": "BUY",
                        "strategy": config.strategy,
                    }
                )

        elif signal == -1 and position_quantity > 0:
            exit_price = close_price
            proceeds = position_quantity * exit_price
            profit = (exit_price - entry_price) * position_quantity
            profit_pct = (profit / (entry_price * position_quantity)) * 100 if entry_price else 0.0
            cash_balance += proceeds
            trade_rows.append(
                {
                    "symbol": config.symbol,
                    "side": "LONG",
                    "entry_date": entry_timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry_timestamp else None,
                    "exit_date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "quantity": int(position_quantity),
                    "profit": float(profit),
                    "profit_pct": float(profit_pct),
                    "exit_reason": "signal",
                }
            )
            signal_rows.append(
                {
                    "date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "price": close_price,
                    "type": "SELL",
                    "strategy": config.strategy,
                }
            )
            position_quantity = 0
            entry_price = 0.0
            entry_timestamp = None

        position_value = position_quantity * close_price
        equity = cash_balance + position_value
        equity_rows.append(
            {
                "date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "cash": float(cash_balance),
                "position_value": float(position_value),
                "equity": float(equity),
            }
        )

    if position_quantity > 0:
        final_close = float(signal_frame.iloc[-1]["Close"])
        final_timestamp = pd.to_datetime(signal_frame.iloc[-1]["Date"])
        proceeds = position_quantity * final_close
        profit = (final_close - entry_price) * position_quantity
        profit_pct = (profit / (entry_price * position_quantity)) * 100 if entry_price else 0.0
        cash_balance += proceeds
        trade_rows.append(
            {
                "symbol": config.symbol,
                "side": "LONG",
                "entry_date": entry_timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry_timestamp else None,
                "exit_date": final_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price": float(entry_price),
                "exit_price": float(final_close),
                "quantity": int(position_quantity),
                "profit": float(profit),
                "profit_pct": float(profit_pct),
                "exit_reason": "forced_close",
            }
        )
        equity_rows[-1]["cash"] = float(cash_balance)
        equity_rows[-1]["position_value"] = 0.0
        equity_rows[-1]["equity"] = float(cash_balance)

    equity_series = pd.Series([row["equity"] for row in equity_rows], dtype="float64")
    daily_returns = equity_series.pct_change().fillna(0.0)
    trade_profits = [float(row["profit"]) for row in trade_rows]
    win_rate = (sum(profit > 0 for profit in trade_profits) / len(trade_profits) * 100.0) if trade_profits else 0.0

    metrics = {
        "initial_balance": float(config.initial_balance),
        "final_balance": float(cash_balance),
        "total_profit": float(cash_balance - float(config.initial_balance)),
        "total_return_pct": float(((cash_balance - float(config.initial_balance)) / float(config.initial_balance)) * 100.0),
        "win_rate": float(win_rate),
        "max_drawdown": _calculate_max_drawdown(equity_series),
        "sharpe_ratio": _calculate_sharpe_ratio(daily_returns),
        "trade_count": len(trade_rows),
    }

    indicators_payload = {
        "sma_short": _series_to_json_list(signal_frame[f"SMA_{config.short_window}"]),
        "sma_long": _series_to_json_list(signal_frame[f"SMA_{config.long_window}"]),
        "ema_short": _series_to_json_list(signal_frame[f"EMA_{config.short_window}"]),
        "ema_long": _series_to_json_list(signal_frame[f"EMA_{config.long_window}"]),
        "rsi": _series_to_json_list(signal_frame["RSI"]),
        "vwap": _series_to_json_list(signal_frame["VWAP"]),
        "bb_upper": _series_to_json_list(signal_frame["BB_UPPER"]),
        "bb_lower": _series_to_json_list(signal_frame["BB_LOWER"]),
        "macd": _series_to_json_list(signal_frame["MACD"]),
        "macd_signal": _series_to_json_list(signal_frame["MACD_SIGNAL"]),
        "macd_hist": _series_to_json_list(signal_frame["MACD_HIST"]),
    }

    monte_carlo_payload = run_monte_carlo_simulation(
        signal_frame["PRICE_CHANGE"],
        initial_capital=float(config.initial_balance),
        simulations=config.simulations,
    )

    paper_trading_payload = simulate_paper_trading(
        signal_frame,
        signal_frame,
        initial_balance=float(config.initial_balance),
        allocation_fraction=config.allocation_fraction,
        symbol=config.symbol,
    )

    price_payload = dataframe_records(signal_frame[["Date", "Close", "Open", "High", "Low", "Volume"]])
    signal_payload = signal_rows

    return {
        "frame": signal_frame,
        "price_payload": price_payload,
        "indicator_payload": indicators_payload,
        "signal_payload": signal_payload,
        "trade_rows": trade_rows,
        "equity_rows": equity_rows,
        "metrics": metrics,
        "monte_carlo_payload": monte_carlo_payload,
        "paper_trading_payload": paper_trading_payload,
    }
