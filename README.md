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

## Project layout

```
trader/
  config.py       # loads credentials from env / .env
  client.py       # login/logout session management (RobinhoodClient)
  market_data.py  # prices, quotes, historicals -> pandas
  account.py      # buying power, holdings, positions -> pandas
  trading.py      # buy/sell/cancel order functions
  trader.py       # Trader facade tying it all together
main.py           # command-line interface
```

## Notes & safety

- Credentials live only in `.env` (git-ignored). Never hard-code them.
- Using an unofficial API may violate Robinhood's terms of service — use at
  your own risk.
- This is a starting point, not investment advice. Add your own risk checks
  (position sizing, stop losses, rate limiting) before trading seriously.
