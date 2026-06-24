#!/usr/bin/env python3
"""Command-line interface for the Robinhood trader.

Examples:
    python main.py price AAPL
    python main.py quote AAPL MSFT GOOG
    python main.py history AAPL --interval day --span 3month
    python main.py holdings
    python main.py balance
    python main.py orders
    python main.py buy AAPL --qty 1
    python main.py buy AAPL --dollars 25
    python main.py buy AAPL --qty 10 --limit 150.00
    python main.py sell AAPL --qty 1
    python main.py cancel <order_id>

Buy/sell place REAL orders with REAL money. They prompt for confirmation
unless you pass --yes.
"""
from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from trader import Trader

pd.set_option("display.max_rows", 100)
pd.set_option("display.width", 160)


def _confirm(action: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    reply = input(f"Confirm {action}? [y/N] ").strip().lower()
    return reply in {"y", "yes"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Robinhood stock trader")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("price", help="latest price for a symbol")
    p.add_argument("symbol")

    p = sub.add_parser("quote", help="quote table for one or more symbols")
    p.add_argument("symbols", nargs="+")

    p = sub.add_parser("history", help="historical OHLCV data")
    p.add_argument("symbol")
    p.add_argument("--interval", default="day")
    p.add_argument("--span", default="year")

    sub.add_parser("holdings", help="current stock holdings")
    sub.add_parser("balance", help="buying power and portfolio value")
    sub.add_parser("orders", help="open (unfilled) orders")

    for side in ("buy", "sell"):
        p = sub.add_parser(side, help=f"{side} shares or a dollar amount")
        p.add_argument("symbol")
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--qty", type=float, help="number of shares")
        g.add_argument("--dollars", type=float, help="dollar amount (fractional)")
        p.add_argument("--limit", type=float, help="limit price (shares only)")
        p.add_argument("--yes", action="store_true", help="skip confirmation prompt")

    p = sub.add_parser("cancel", help="cancel an open order (or 'all')")
    p.add_argument("order_id")

    return parser


def run(args: argparse.Namespace) -> int:
    with Trader.from_env() as t:
        if args.command == "price":
            print(f"{args.symbol.upper()}: ${t.price(args.symbol):,.2f}")

        elif args.command == "quote":
            print(t.quotes(args.symbols))

        elif args.command == "history":
            print(t.history(args.symbol, interval=args.interval, span=args.span))

        elif args.command == "holdings":
            holdings = t.holdings()
            print(holdings if not holdings.empty else "No holdings.")

        elif args.command == "balance":
            print(f"Buying power:    ${t.buying_power():,.2f}")
            print(f"Portfolio value: ${t.portfolio_value():,.2f}")

        elif args.command == "orders":
            orders = t.open_orders()
            print(orders if not orders.empty else "No open orders.")

        elif args.command in ("buy", "sell"):
            if args.dollars is not None:
                desc = f"{args.command} ${args.dollars} of {args.symbol.upper()}"
            else:
                limit = f" @ ${args.limit}" if args.limit else " at market"
                desc = f"{args.command} {args.qty} {args.symbol.upper()}{limit}"
            if not _confirm(desc, args.yes):
                print("Aborted.")
                return 1

            fn = t.buy if args.command == "buy" else t.sell
            dollars_fn = t.buy_dollars if args.command == "buy" else t.sell_dollars
            if args.dollars is not None:
                order = dollars_fn(args.symbol, args.dollars)
            else:
                order = fn(args.symbol, args.qty, limit_price=args.limit)
            print(f"Order placed: {order.get('id')} (state: {order.get('state')})")

        elif args.command == "cancel":
            result = t.cancel_all() if args.order_id == "all" else t.cancel(args.order_id)
            print(f"Cancelled: {result}")

    return 0


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return run(args)
    except Exception as exc:  # noqa: BLE001 - surface a clean CLI error
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
