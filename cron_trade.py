#!/usr/bin/env python3
"""Scheduled moving-average dip-buyer — run on a schedule (e.g. every 5 minutes).

Each run:

  1. Loads the recent price history and the last moving average from a local
     JSON state file.
  2. Fetches the current price and appends it to the rolling window.
  3. Recomputes the simple moving average (SMA) with pandas over the last
     ``MA_WINDOW`` samples.
  4. If the moving average has fallen at least ``DROP_PCT`` percent since the
     previous run's average, places a REAL fractional buy of ``BUY_DOLLARS``.
  5. Saves the trimmed price history and the new average for the next run.

Config (environment variables / .env):

  ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET  credentials
  SYMBOL        ticker to watch                                 (default: NFLX)
  MA_WINDOW     number of samples in the moving average         (default: 20)
  DROP_PCT      percent the average must fall (vs the previous
                run's average) to trigger a buy                 (default: 5)
  BUY_DOLLARS   dollars of fractional shares to buy on a trigger (default: 5)
  STATE_FILE    where price history + average are persisted     (default:
                state.json next to this script)

⚠️  This places REAL orders with REAL money.

NOTE ON STATE: the price history and average live in a local file, so they only
survive on a host with a stable disk — your own machine's crontab, a VM, a
container with a mounted volume. They will NOT persist on a Render cron job (its
filesystem is wiped between runs), so there the average never accumulates.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from trader import Trader

logger = logging.getLogger("trader.cron")

DEFAULT_STATE_FILE = Path(__file__).resolve().parent / "state.json"


def load_state(path: Path) -> tuple[list[float], float | None]:
    """Return (recent prices, last moving average) from the state file.

    Missing or corrupt state is treated as a fresh start: ``([], None)``.
    """
    try:
        data = json.loads(path.read_text())
        prices = [float(p) for p in data.get("prices", [])]
        last_ma = data.get("last_ma")
        return prices, (float(last_ma) if last_ma is not None else None)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        return [], None


def save_state(
    path: Path, symbol: str, prices: list[float], last_ma: float | None
) -> None:
    """Persist the rolling price window and the latest average for next run."""
    path.write_text(
        json.dumps({"symbol": symbol, "prices": prices, "last_ma": last_ma})
    )


def moving_average(prices: list[float], window: int) -> float | None:
    """Simple moving average over the last `window` prices via pandas.

    Returns None while the window is still filling (fewer than `window`
    samples), matching pandas' ``rolling(...).mean()`` warm-up behaviour.
    """
    series = pd.Series(prices, dtype="float64")
    ma = series.rolling(window=window).mean().iloc[-1]
    return None if pd.isna(ma) else float(ma)


def run() -> int:
    symbol = os.getenv("SYMBOL", "NFLX").upper()
    window = int(os.getenv("MA_WINDOW", "20"))
    drop_pct = float(os.getenv("DROP_PCT", "5"))
    buy_dollars = float(os.getenv("BUY_DOLLARS", "5"))
    state_file = Path(os.getenv("STATE_FILE", str(DEFAULT_STATE_FILE)))

    prices, last_ma = load_state(state_file)

    with Trader.from_env() as t:
        price = t.price(symbol)

        # Append the new price; keep only what the moving average needs.
        prices.append(price)
        prices = prices[-window:]

        ma_now = moving_average(prices, window)
        logger.info(
            "%s price: $%.2f | samples: %d/%d | MA: %s",
            symbol, price, len(prices), window,
            f"${ma_now:.2f}" if ma_now is not None else "warming up",
        )

        # Not enough samples yet — just keep collecting.
        if ma_now is None:
            logger.info("Moving average not ready; need %d samples.", window)
            save_state(state_file, symbol, prices, last_ma)
            return 0

        # First full average — record a baseline to compare against next time.
        if last_ma is None:
            logger.info("First full average ($%.2f); setting baseline, no trade.", ma_now)
            save_state(state_file, symbol, prices, ma_now)
            return 0

        change_pct = (ma_now - last_ma) / last_ma * 100.0
        logger.info(
            "MA change since last run: %+.2f%% ($%.2f -> $%.2f) | buy threshold: -%.2f%%",
            change_pct, last_ma, ma_now, drop_pct,
        )

        if ma_now <= last_ma * (1 - drop_pct / 100.0):
            logger.warning(
                "%s average fell %.2f%% — buying $%.2f", symbol, change_pct, buy_dollars
            )
            order = t.buy_dollars(symbol, buy_dollars)
            logger.warning(
                "Order placed: %s (state: %s)", order.get("id"), order.get("state")
            )
        else:
            logger.info("Threshold not met; no trade.")

        # The current average becomes the baseline for the next run.
        save_state(state_file, symbol, prices, ma_now)

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
