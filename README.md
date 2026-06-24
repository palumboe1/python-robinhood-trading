# python-trader

A small, pandas-friendly toolkit for trading stocks on **Robinhood** from Python.

It wraps the community [`robin_stocks`](https://github.com/jmfernandes/robin_stocks)
library (Robinhood has no official public API) with a clean `Trader` class, a CLI,
and helpers that return tidy pandas DataFrames.

> ⚠️ **This places real orders with real money.** There is no official
> Robinhood API and no sandbox. Test with tiny quantities first, and never
> commit your credentials.

## Features

- **Login** with username/password and automatic TOTP 2FA
- **Buy / sell** — market, limit, and fractional (dollar-based) orders
- **Market data** — latest price, multi-symbol quotes, historical OHLCV (as DataFrames)
- **Account** — buying power, portfolio value, holdings, open positions
- **Orders** — list open orders, cancel one or all
- A CLI (`main.py`) and a Python API (`from trader import Trader`)

## Quick start

**1. Install dependencies**

```bash
cd python-trader
pip install -r requirements.txt
```

**2. Add your credentials**

```bash
cp .env.example .env        # then edit .env
```

```
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_SECRET=        # optional, see below
```

For 2FA, put the **TOTP secret** (the base32 string shown when you set up an
authenticator app — *not* a rotating 6-digit code) in `ROBINHOOD_MFA_SECRET`.
Codes are then generated automatically at login. Leave it blank to be prompted
for an SMS/app code on first login instead.

**3. Run it** — start with a read-only command to confirm login works:

```bash
python main.py price AAPL
python main.py balance
```

Then try a tiny real trade (see [CLI usage](#cli-usage) for the full list):

```bash
python main.py buy AAPL --dollars 5     # smallest real test: $5 of fractional shares
```

### First-run notes

- **New-device verification.** Robinhood often emails/texts a device-approval
  or code the first time you log in from a machine. Run an interactive
  read-only command (like `python main.py price AAPL`) first to clear that
  before scripting any trades.
- **Real money, no sandbox.** There is no Robinhood test environment — every
  buy/sell is live. Start with `buy AAPL --dollars 5` to validate the full
  pipeline at minimal risk.

## CLI usage

```bash
python main.py price AAPL
python main.py quote AAPL MSFT GOOG
python main.py history AAPL --interval day --span 3month
python main.py balance
python main.py holdings
python main.py orders

# Trading (prompts for confirmation unless --yes):
python main.py buy AAPL --qty 1
python main.py buy AAPL --dollars 25            # $25 of fractional shares
python main.py buy AAPL --qty 10 --limit 150    # limit order
python main.py sell AAPL --qty 1
python main.py cancel <order_id>                # or: cancel all
```

## Python API

```python
from trader import Trader

with Trader.from_env() as t:           # logs in, and logs out on exit
    print(t.price("AAPL"))             # -> float
    print(t.quotes(["AAPL", "MSFT"]))  # -> DataFrame
    print(t.history("AAPL", span="3month"))

    print(t.buying_power(), t.portfolio_value())
    print(t.holdings())                # -> DataFrame indexed by symbol

    t.buy("AAPL", 1)                   # 1 share at market
    t.buy_dollars("AAPL", 10)          # $10 fractional
    t.buy("AAPL", 5, limit_price=150)  # limit order
    t.sell("AAPL", 1)
```

## Scheduled moving-average dip-buyer (`cron_trade.py`)

`cron_trade.py` is a self-contained strategy meant to be run on a schedule
(e.g. every 5 minutes). Each run it appends the current price to a rolling
window stored on disk, recomputes a **simple moving average** with pandas, and
if the average has **fallen `DROP_PCT`% or more versus the previous run's
average**, places a real fractional buy of `BUY_DOLLARS` worth of the stock.

```bash
python cron_trade.py
```

Configure it with environment variables (or `.env`):

| Variable      | Default      | Meaning                                          |
| ------------- | ------------ | ------------------------------------------------ |
| `SYMBOL`      | `NFLX`       | ticker to watch                                  |
| `MA_WINDOW`   | `20`         | number of samples in the moving average          |
| `DROP_PCT`    | `5`          | percent the average must fall (vs the previous run) to buy |
| `BUY_DOLLARS` | `5`          | dollars of fractional shares to buy on a trigger |
| `STATE_FILE`  | `state.json` | where price history + average are persisted      |

**State & warm-up.** The recent prices and the last average are kept in a local
JSON file (`state.json`), so the average only accumulates on a host with a
**stable disk** — your own machine, a VM, or a container with a mounted volume.
The job needs `MA_WINDOW` runs to fill the window before the average exists, and
the **first full average just sets a baseline** (no trade); drops are detected
from the next run onward.

> ⚠️ Because a moving average is smoothed, it moving `DROP_PCT`% between two
> consecutive runs is **very rare** — more so than a raw price move. With a
> large `MA_WINDOW` the average barely budges per run, so this will seldom fire.
> Tune `MA_WINDOW` / `DROP_PCT` to taste. (Want "fell 5% off its recent peak"
> instead of "vs the last run"? That's a one-line change — ask.) Fractional
> orders also only execute during regular market hours.

## Portfolio analytics & value-over-time graph

`python main.py portfolio` enriches your holdings with **cost basis, unrealized
P&L, and portfolio weight** (all via pandas), prints the table plus a summary,
and records a **timestamped snapshot** to `portfolio_history.csv`. Because each
run appends a row "as of when it fetched," running it repeatedly builds a real
time series — which `--graph` renders to a PNG.

```bash
python main.py portfolio                  # analyze + record a snapshot
python main.py portfolio --graph          # also write portfolio.png
python main.py portfolio --no-record      # analyze only, don't append
```

| Column / metric      | Meaning                                            |
| -------------------- | -------------------------------------------------- |
| `market_value`       | `quantity × price`                                 |
| `cost_basis`         | `quantity × average_buy_price`                     |
| `unrealized_pnl`     | `market_value − cost_basis` (and `_pct`)           |
| `weight_pct`         | position's share of total market value             |

The same logic runs unattended as a **separate cron job**, `cron_portfolio.py`,
which appends a snapshot and (re)renders the graph each run — it is **read-only
and never places orders**:

```bash
python cron_portfolio.py    # HISTORY_FILE / GRAPH_FILE configurable via env
```

### Run them on a schedule (self-hosted)

Add lines to your crontab (`crontab -e`). Use absolute paths so the working
directory and `.env` resolve correctly:

```cron
# dip-buyer every 5 min; portfolio snapshot every 15 min
*/5  * * * * cd /path/to/python-robinhood-trading && /usr/bin/python3 cron_trade.py     >> cron.log 2>&1
*/15 * * * * cd /path/to/python-robinhood-trading && /usr/bin/python3 cron_portfolio.py >> cron.log 2>&1
```

Set `ROBINHOOD_MFA_SECRET` (the base32 TOTP secret) so the unattended login
needs no interactive 2FA prompt. `robin_stocks` caches its auth token under
`~/.tokens/`, so a stable home directory avoids re-authenticating every run.

### Render Blueprint (with a caveat)

`render.yaml` defines **two** Render **Cron Jobs** — the dip-buyer (`*/5`) and
the portfolio snapshotter (`*/15`). Render is wired up for credentials/config,
**but Render cron jobs have an ephemeral filesystem** — `state.json` and
`portfolio_history.csv` are wiped between runs, so the dip-buyer never sees a
prior price and the portfolio history never accumulates past one row. To run
these as designed, self-host the crontab above, or swap the file state for an
external store (e.g. Redis / a database). The blueprint is kept for reference.

## Project layout

```
trader/
  config.py       # loads credentials from env / .env
  client.py       # login/logout session management (RobinhoodClient)
  market_data.py  # prices, quotes, historicals -> pandas
  account.py      # buying power, holdings, positions -> pandas
  trading.py      # buy/sell/cancel order functions
  portfolio.py    # holdings analytics + value-over-time chart (pandas/matplotlib)
  trader.py       # Trader facade tying it all together
main.py           # command-line interface (incl. `portfolio` command)
cron_trade.py     # scheduled dip-buyer (buys NFLX on a 5% drop)
cron_portfolio.py # scheduled portfolio snapshotter (read-only, builds the graph)
render.yaml       # Render Blueprint (two cron jobs — see caveat above)
```

## Notes & safety

- Credentials live only in `.env` (git-ignored). Never hard-code them.
- Using an unofficial API may violate Robinhood's terms of service — use at
  your own risk.
- This is a starting point, not investment advice. Add your own risk checks
  (position sizing, stop losses, rate limiting) before trading seriously.
