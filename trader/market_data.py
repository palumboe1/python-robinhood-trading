"""Market data helpers — everything returns pandas objects."""
from __future__ import annotations

import robin_stocks.robinhood as rh
import pandas as pd


def get_latest_price(symbol: str) -> float:
    """Return the latest trade price for a single symbol."""
    prices = rh.stocks.get_latest_price(symbol.upper())
    if not prices or prices[0] is None:
        raise ValueError(f"No price available for {symbol!r}")
    return float(prices[0])


def get_quotes(symbols: list[str]) -> pd.DataFrame:
    """Return a DataFrame of current quote data, indexed by symbol.

    Columns include ask_price, bid_price, last_trade_price, previous_close,
    and the derived columns ``change`` and ``change_pct``.
    """
    symbols = [s.upper() for s in symbols]
    quotes = rh.stocks.get_quotes(symbols)
    quotes = [q for q in quotes if q]  # drop unknown symbols (None entries)

    df = pd.DataFrame(quotes)
    if df.empty:
        return df

    numeric_cols = [
        "ask_price",
        "bid_price",
        "last_trade_price",
        "previous_close",
        "adjusted_previous_close",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if {"last_trade_price", "previous_close"}.issubset(df.columns):
        df["change"] = df["last_trade_price"] - df["previous_close"]
        df["change_pct"] = (df["change"] / df["previous_close"]) * 100

    return df.set_index("symbol")


def get_historicals(
    symbol: str,
    interval: str = "day",
    span: str = "year",
    bounds: str = "regular",
) -> pd.DataFrame:
    """Return historical OHLCV data as a time-indexed DataFrame.

    Args:
        symbol: Ticker, e.g. "AAPL".
        interval: "5minute", "10minute", "hour", "day", or "week".
        span: "day", "week", "month", "3month", "year", or "5year".
        bounds: "regular", "trading", or "extended".
    """
    raw = rh.stocks.get_stock_historicals(
        symbol.upper(), interval=interval, span=span, bounds=bounds
    )
    df = pd.DataFrame(raw)
    if df.empty:
        return df

    df["begins_at"] = pd.to_datetime(df["begins_at"])
    df = df.rename(columns={"begins_at": "timestamp"}).set_index("timestamp")

    for col in ["open_price", "close_price", "high_price", "low_price", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
