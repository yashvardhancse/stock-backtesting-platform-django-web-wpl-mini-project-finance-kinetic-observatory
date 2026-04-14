from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class PortfolioSnapshot:
    timestamp: str
    cash_balance: float
    position_quantity: int
    position_value: float
    equity: float


def simulate_paper_trading(
    frame: pd.DataFrame,
    signal_frame: pd.DataFrame,
    *,
    initial_balance: float = 100000.0,
    allocation_fraction: float = 1.0,
    symbol: str = "SYMBOL",
) -> dict:
    """Simulate a long-only paper portfolio using the generated signal stream."""

    cash_balance = float(initial_balance)
    position_quantity = 0
    entry_price = 0.0
    entry_timestamp = None
    realized_pnl = 0.0
    snapshots: list[dict] = []
    transactions: list[dict] = []

    for row in signal_frame.itertuples(index=False):
        close_price = float(row.Close)
        timestamp = pd.to_datetime(row.Date).strftime("%Y-%m-%d %H:%M:%S")
        signal = int(getattr(row, "Signal", 0))
        signal_type = getattr(row, "SignalType", "HOLD")

        if signal == 1 and position_quantity == 0 and close_price > 0:
            allocation = max(cash_balance * allocation_fraction, close_price)
            quantity = max(1, int(allocation // close_price))
            trade_cost = quantity * close_price
            if trade_cost <= cash_balance:
                cash_balance -= trade_cost
                position_quantity = quantity
                entry_price = close_price
                entry_timestamp = timestamp
                transactions.append(
                    {
                        "side": "BUY",
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "price": close_price,
                        "quantity": quantity,
                    }
                )

        elif signal == -1 and position_quantity > 0:
            proceeds = position_quantity * close_price
            trade_profit = (close_price - entry_price) * position_quantity
            cash_balance += proceeds
            realized_pnl += trade_profit
            transactions.append(
                {
                    "side": "SELL",
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "price": close_price,
                    "quantity": position_quantity,
                    "profit": float(trade_profit),
                    "entry_timestamp": entry_timestamp,
                }
            )
            position_quantity = 0
            entry_price = 0.0
            entry_timestamp = None

        position_value = position_quantity * close_price
        equity = cash_balance + position_value
        snapshots.append(
            {
                "timestamp": timestamp,
                "cash_balance": float(cash_balance),
                "position_quantity": int(position_quantity),
                "position_value": float(position_value),
                "equity": float(equity),
                "signal": signal_type,
            }
        )

    if position_quantity > 0:
        final_price = float(signal_frame.iloc[-1]["Close"])
        final_timestamp = pd.to_datetime(signal_frame.iloc[-1]["Date"]).strftime("%Y-%m-%d %H:%M:%S")
        proceeds = position_quantity * final_price
        trade_profit = (final_price - entry_price) * position_quantity
        cash_balance += proceeds
        realized_pnl += trade_profit
        transactions.append(
            {
                "side": "SELL",
                "timestamp": final_timestamp,
                "symbol": symbol,
                "price": final_price,
                "quantity": position_quantity,
                "profit": float(trade_profit),
                "entry_timestamp": entry_timestamp,
                "exit_reason": "forced_close",
            }
        )
        snapshots[-1]["cash_balance"] = float(cash_balance)
        snapshots[-1]["position_quantity"] = 0
        snapshots[-1]["position_value"] = 0.0
        snapshots[-1]["equity"] = float(cash_balance)

    return {
        "initial_balance": float(initial_balance),
        "final_balance": float(cash_balance),
        "realized_pnl": float(realized_pnl),
        "open_positions": {},
        "snapshots": snapshots,
        "transactions": transactions,
    }
