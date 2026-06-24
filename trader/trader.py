"""High-level Trader facade.

A single, friendly object that composes session management, market data,
account info, and order placement. This is the main entry point most code
should use.

Example::

    from trader import Trader

    with Trader.from_env() as t:
        print(t.price("AAPL"))
        print(t.holdings())
        t.buy("AAPL", 1)            # 1 share at market
        t.buy_dollars("AAPL", 10)   # $10 of fractional shares
        t.sell("AAPL", 1)
"""
from __future__ import annotations

from . import account, market_data, trading
from .client import RobinhoodClient
from .config import Config

import pandas as pd


class Trader:
    def __init__(self, config: Config) -> None:
        self._client = RobinhoodClient(config)

    @classmethod
    def from_env(cls) -> "Trader":
        """Build a Trader from ROBINHOOD_* environment variables / .env."""
        return cls(Config.from_env())

    # --- session ----------------------------------------------------------
    def login(self) -> "Trader":
        self._client.login()
        return self

    def logout(self) -> None:
        self._client.logout()

    def __enter__(self) -> "Trader":
        self._client.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._client.logout()

    # --- market data ------------------------------------------------------
    def price(self, symbol: str) -> float:
        return market_data.get_latest_price(symbol)

    def quotes(self, symbols: list[str]) -> pd.DataFrame:
        return market_data.get_quotes(symbols)

    def history(
        self, symbol: str, interval: str = "day", span: str = "year"
    ) -> pd.DataFrame:
        return market_data.get_historicals(symbol, interval=interval, span=span)

    # --- account ----------------------------------------------------------
    def buying_power(self) -> float:
        return account.get_buying_power()

    def portfolio_value(self) -> float:
        return account.get_portfolio_value()

    def holdings(self) -> pd.DataFrame:
        return account.get_holdings()

    def positions(self) -> pd.DataFrame:
        return account.get_open_positions()

    # --- trading ----------------------------------------------------------
    def buy(self, symbol: str, quantity: float, limit_price: float | None = None) -> dict:
        """Buy shares. Market order by default; limit order if limit_price given."""
        if limit_price is not None:
            return trading.buy_limit(symbol, quantity, limit_price)
        return trading.buy_market(symbol, quantity)

    def buy_dollars(self, symbol: str, amount: float) -> dict:
        """Buy a dollar amount of a stock using fractional shares."""
        return trading.buy_fractional_by_price(symbol, amount)

    def sell(self, symbol: str, quantity: float, limit_price: float | None = None) -> dict:
        """Sell shares. Market order by default; limit order if limit_price given."""
        if limit_price is not None:
            return trading.sell_limit(symbol, quantity, limit_price)
        return trading.sell_market(symbol, quantity)

    def sell_dollars(self, symbol: str, amount: float) -> dict:
        """Sell a dollar amount of a stock using fractional shares."""
        return trading.sell_fractional_by_price(symbol, amount)

    # --- order management -------------------------------------------------
    def open_orders(self) -> pd.DataFrame:
        return trading.get_open_orders()

    def cancel(self, order_id: str) -> dict:
        return trading.cancel_order(order_id)

    def cancel_all(self) -> dict:
        return trading.cancel_all_orders()
