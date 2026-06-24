"""Portfolio analytics and a value-over-time timeseries.

Pure-pandas analytics over the holdings DataFrame, plus a small append-only
history log and a matplotlib chart of total portfolio value over time.

The timeseries is built from *when you fetch*: each call to ``append_snapshot``
writes one timestamped row per holding, so running the ``portfolio`` command on
a schedule accumulates the curve over time. Nothing here places orders.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

HISTORY_COLUMNS = [
    "timestamp", "symbol", "quantity", "price", "market_value", "cost_basis",
]


def analyze_holdings(holdings: pd.DataFrame) -> pd.DataFrame:
    """Enrich a holdings frame with cost basis, unrealized P&L, and weight.

    ``holdings`` is the symbol-indexed frame from ``Trader.holdings()`` (it has
    ``quantity``, ``average_buy_price`` and ``price`` columns). Returns a new
    frame adding ``market_value``, ``cost_basis``, ``unrealized_pnl``,
    ``unrealized_pnl_pct`` and ``weight_pct``, sorted by market value.
    """
    if holdings.empty:
        return holdings

    df = holdings.copy()
    df["market_value"] = df["quantity"] * df["price"]
    df["cost_basis"] = df["quantity"] * df["average_buy_price"]
    df["unrealized_pnl"] = df["market_value"] - df["cost_basis"]
    df["unrealized_pnl_pct"] = (
        df["unrealized_pnl"] / df["cost_basis"].replace(0, pd.NA) * 100
    )
    total = df["market_value"].sum()
    df["weight_pct"] = (df["market_value"] / total * 100) if total else 0.0
    return df.sort_values("market_value", ascending=False)


def portfolio_summary(analyzed: pd.DataFrame) -> dict:
    """Roll an analyzed holdings frame up into portfolio-level totals."""
    if analyzed.empty:
        return {
            "positions": 0, "market_value": 0.0, "cost_basis": 0.0,
            "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0,
            "top_symbol": None, "top_weight_pct": 0.0,
        }

    market_value = float(analyzed["market_value"].sum())
    cost_basis = float(analyzed["cost_basis"].sum())
    pnl = market_value - cost_basis
    top = analyzed["weight_pct"].idxmax()
    return {
        "positions": int(len(analyzed)),
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": pnl,
        "unrealized_pnl_pct": (pnl / cost_basis * 100) if cost_basis else 0.0,
        "top_symbol": str(top),
        "top_weight_pct": float(analyzed.loc[top, "weight_pct"]),
    }


def append_snapshot(path: Path, when: datetime, analyzed: pd.DataFrame) -> int:
    """Append one timestamped row per holding to the history CSV.

    Returns the number of rows written. The file is created with a header on
    first use; later calls append without a header.
    """
    if analyzed.empty:
        return 0

    rows = pd.DataFrame(
        {
            "timestamp": pd.Timestamp(when).isoformat(),
            "symbol": analyzed.index,
            "quantity": analyzed["quantity"].to_numpy(),
            "price": analyzed["price"].to_numpy(),
            "market_value": analyzed["market_value"].to_numpy(),
            "cost_basis": analyzed["cost_basis"].to_numpy(),
        },
        columns=HISTORY_COLUMNS,
    )
    rows.to_csv(path, mode="a", header=not path.exists(), index=False)
    return len(rows)


def load_history(path: Path) -> pd.DataFrame:
    """Load the snapshot history CSV (empty frame with headers if missing)."""
    if not path.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    return pd.read_csv(path, parse_dates=["timestamp"])


def plot_value_over_time(history: pd.DataFrame, out_path: str | Path) -> Path:
    """Render total portfolio value over time to a PNG; return the path.

    The total at each fetch is the sum of every holding's market value for that
    timestamp. Raises ValueError if there is no history yet.
    """
    if history.empty:
        raise ValueError("No snapshot history yet — run `portfolio` at least once.")

    series = history.groupby("timestamp")["market_value"].sum().sort_index()

    # Imported lazily (and with a headless backend) so the rest of the CLI does
    # not pay matplotlib's import cost and it works on a server with no display.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(series.index, series.to_numpy(), marker="o", linewidth=1.5)
    ax.set_title("Portfolio value over time")
    ax.set_xlabel("Fetched at")
    ax.set_ylabel("Total market value ($)")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    out_path = Path(out_path)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    logger.info("Wrote portfolio chart to %s", out_path)
    return out_path
