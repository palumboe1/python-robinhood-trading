"""Order placement and management.

Thin, well-documented wrappers over the robin_stocks order functions. Every
function returns the raw order dict from Robinhood (which contains the order
id, state, etc.).
"""
from __future__ import annotations

import logging

import robin_stocks.robinhood as rh
import pandas as pd

logger = logging.getLogger(__name__)


def _check(order: dict, action: str, symbol: str) -> dict:
    """Log the result and surface Robinhood-side rejections as errors."""
    if not order or "id" not in order:
        # Robinhood returns a dict of field errors when an order is rejected.
        raise RuntimeError(f"{action} {symbol} failed: {order}")
    logger.info("%s %s -> order %s (%s)", action, symbol, order["id"],
                order.get("state", "unknown"))
    return order


# --- Buying -----------------------------------------------------------------

def buy_market(symbol: str, quantity: float) -> dict:
    """Buy `quantity` whole shares at the current market price."""
    symbol = symbol.upper()
    order = rh.orders.order_buy_market(symbol, quantity)
    return _check(order, "BUY market", symbol)


def buy_limit(symbol: str, quantity: float, limit_price: float) -> dict:
    """Buy `quantity` shares, but only at or below `limit_price`."""
    symbol = symbol.upper()
    order = rh.orders.order_buy_limit(symbol, quantity, limit_price)
    return _check(order, "BUY limit", symbol)


def buy_fractional_by_price(symbol: str, amount_dollars: float) -> dict:
    """Buy approximately `amount_dollars` worth of a stock (fractional shares)."""
    symbol = symbol.upper()
    order = rh.orders.order_buy_fractional_by_price(symbol, amount_dollars)
    return _check(order, "BUY fractional $", symbol)


# --- Selling ----------------------------------------------------------------

def sell_market(symbol: str, quantity: float) -> dict:
    """Sell `quantity` whole shares at the current market price."""
    symbol = symbol.upper()
    order = rh.orders.order_sell_market(symbol, quantity)
    return _check(order, "SELL market", symbol)


def sell_limit(symbol: str, quantity: float, limit_price: float) -> dict:
    """Sell `quantity` shares, but only at or above `limit_price`."""
    symbol = symbol.upper()
    order = rh.orders.order_sell_limit(symbol, quantity, limit_price)
    return _check(order, "SELL limit", symbol)


def sell_fractional_by_price(symbol: str, amount_dollars: float) -> dict:
    """Sell approximately `amount_dollars` worth of a stock (fractional shares)."""
    symbol = symbol.upper()
    order = rh.orders.order_sell_fractional_by_price(symbol, amount_dollars)
    return _check(order, "SELL fractional $", symbol)


# --- Order management -------------------------------------------------------

def get_open_orders() -> pd.DataFrame:
    """All currently open (unfilled) stock orders."""
    orders = rh.orders.get_all_open_stock_orders()
    df = pd.DataFrame(orders)
    if df.empty:
        return df
    for col in ["price", "quantity", "average_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def cancel_order(order_id: str) -> dict:
    """Cancel a single open order by id."""
    result = rh.orders.cancel_stock_order(order_id)
    logger.info("Cancelled order %s", order_id)
    return result


def cancel_all_orders() -> dict:
    """Cancel every open stock order."""
    result = rh.orders.cancel_all_stock_orders()
    logger.info("Cancelled all open stock orders")
    return result
