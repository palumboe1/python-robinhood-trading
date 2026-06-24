"""Account, portfolio, and holdings helpers — returns pandas where it makes sense."""
from __future__ import annotations

import robin_stocks.robinhood as rh
import pandas as pd


def get_account_profile() -> dict:
    """Raw account profile (buying power, cash, etc.)."""
    return rh.profiles.load_account_profile()


def get_buying_power() -> float:
    profile = rh.profiles.load_account_profile()
    return float(profile.get("buying_power", 0.0))


def get_portfolio_value() -> float:
    """Total equity (positions + cash) from the portfolio profile."""
    profile = rh.profiles.load_portfolio_profile()
    equity = profile.get("equity") or profile.get("extended_hours_equity")
    return float(equity) if equity else 0.0


def get_holdings() -> pd.DataFrame:
    """Current stock holdings as a DataFrame indexed by symbol.

    Columns include quantity, average_buy_price, price, equity,
    percent_change, and equity_change.
    """
    holdings = rh.account.build_holdings()  # {symbol: {...}}
    if not holdings:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(holdings, orient="index")
    df.index.name = "symbol"

    numeric_cols = [
        "price",
        "quantity",
        "average_buy_price",
        "equity",
        "percent_change",
        "equity_change",
        "percentage",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_open_positions() -> pd.DataFrame:
    """Open positions with a non-zero share quantity."""
    positions = rh.account.get_open_stock_positions()
    df = pd.DataFrame(positions)
    if df.empty:
        return df

    for col in ["quantity", "average_buy_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
