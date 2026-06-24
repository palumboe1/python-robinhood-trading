#!/usr/bin/env python3
"""Scheduled portfolio snapshotter — build a value-over-time series by fetch time.

A separate, READ-ONLY cron job (it never places orders). Each run:

  1. Logs in and fetches current holdings.
  2. Computes per-holding analytics (market value, cost basis, P&L, weight).
  3. Appends one timestamped row per holding to the history CSV (HISTORY_FILE).
  4. Optionally (re)renders the portfolio-value PNG (GRAPH_FILE).

The timeseries grows by *when this runs*, so scheduling it (e.g. every 15
minutes during market hours) traces your portfolio's value over time.

Config (environment variables / .env):

  ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET  credentials
  HISTORY_FILE   CSV where snapshots accumulate    (default: portfolio_history.csv)
  GRAPH_FILE     PNG to (re)render each run; set empty to skip the chart
                                                   (default: portfolio.png)

NOTE ON STATE: like cron_trade.py, the CSV/PNG are local files — they only
accumulate on a host with a stable disk (your crontab / a VM / a mounted
volume), NOT on a Render cron job, whose filesystem is wiped between runs.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from trader import Trader, portfolio

logger = logging.getLogger("trader.cron.portfolio")

DEFAULT_HISTORY_FILE = Path(__file__).resolve().parent / "portfolio_history.csv"
DEFAULT_GRAPH_FILE = Path(__file__).resolve().parent / "portfolio.png"


def run() -> int:
    history_file = Path(os.getenv("HISTORY_FILE", str(DEFAULT_HISTORY_FILE)))
    graph_env = os.getenv("GRAPH_FILE", str(DEFAULT_GRAPH_FILE))
    graph_file = Path(graph_env) if graph_env.strip() else None

    with Trader.from_env() as t:
        analyzed = portfolio.analyze_holdings(t.holdings())
        if analyzed.empty:
            logger.info("No holdings; nothing to snapshot.")
            return 0

        summary = portfolio.portfolio_summary(analyzed)
        logger.info(
            "Snapshot: %d positions, value $%.2f, unrealized $%.2f (%+.2f%%)",
            summary["positions"], summary["market_value"],
            summary["unrealized_pnl"], summary["unrealized_pnl_pct"],
        )

        added = portfolio.append_snapshot(
            history_file, datetime.now(timezone.utc), analyzed
        )
        logger.info("Appended %d rows to %s", added, history_file)

        if graph_file is not None:
            history = portfolio.load_history(history_file)
            portfolio.plot_value_over_time(history, graph_file)
            logger.info("Updated graph %s", graph_file)

    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        return run()
    except Exception as exc:  # noqa: BLE001 - log and exit non-zero for the scheduler
        logger.error("Run failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
