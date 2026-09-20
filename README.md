# Signal Engine — Fidelity Paper Trading Assistant

Automated market-data → signal → risk-checked "what to order" engine, built for
**manual execution on Fidelity** (Fidelity has no public trading API, so this
tool never places real orders for you — it tells you exactly what to do and
you click the button yourself).

Alpaca is used only as a **free, real, paper-trading data + simulation backend**
so you can automate the boring part (watch the market, run the math) and
sanity-check the strategy logic against real fills before you ever risk a
dollar at Fidelity.

```
Market data (Alpaca / yfinance)
        │
        ▼
  Indicators (MA, RSI, BB, ATR, ADX)
        │
        ▼
  Regime detector (trending vs ranging)
        │
        ▼
  Strategy selector (trend-following OR mean-reversion)
        │
        ▼
  Signal (BUY/SELL/HOLD + entry/stop/target/size)
        │
        ▼
  Risk engine (Fidelity rules: PDT, position sizing, daily loss, drawdown)
        │
        ▼
  Console + CSV log  →  YOU place the order on Fidelity  →  you log the fill
```

## 1. Setup

**If you're on Ubuntu/WSL:** `python3` and `pip3` are usually pre-installed;
if not, `sudo apt update && sudo apt install python3 python3-pip python3-venv`.
Everything below runs the same as native Linux.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows (native, not WSL): venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Get **free Alpaca paper keys** (2 minutes, no funding required):
1. Sign up at https://alpaca.markets (paper-only accounts are free and instant)
2. Dashboard → "View API Keys" → generate paper key/secret
3. Either paste them into `.env` directly, or just launch the menu and use
   **option 8 (Set up API keys)** — same result, no file editing needed.

If you skip this, the engine automatically falls back to `yfinance`
(no key needed) for data-only mode — you lose Alpaca's simulated paper
fills but signal generation still works. Option 8 also lets you add any of
the other free providers listed in section 6 as extra fallbacks, all at once.

## 2. Run it — everything is menu-driven, no commands to remember

**Ubuntu/WSL or Mac/Linux:** `./risk-engine.sh` from inside the folder
(or double-click it in the WSL file explorer path `\\wsl$\...`).
**Windows (native):** double-click `risk-engine.bat`.

Either way you land on a numbered menu:

```
  1. Run one signal scan now
  2. Watch continuously (auto-scan on an interval)
  3. View account & risk status
  4. Set account equity
  5. Log a trade fill
  6. Edit watchlist
  7. View current risk config
  8. Set up API keys
  9. Help — detailed instructions for every option
  0. Exit
```

**First time setup, in order:**
1. Option **8** — add your free Alpaca keys (and any other providers you
   want as backup — Finnhub, Twelve Data, Alpha Vantage, Polygon, Tiingo,
   Financial Modeling Prep). You can set up as many as you like; the engine
   tries them in priority order and falls back automatically.
2. Option **4** — enter your current Fidelity account value. This is what
   the risk engine sizes and gates everything against.
3. Option **6** — enter your watchlist (comma-separated tickers). It's saved
   so you don't re-type it every time.
4. Option **1** or **2** — run a scan, or start continuous watching.

Forgot how something works? **Option 9** walks through every menu item and
the key concepts (regime, strategy selection, risk status) in plain English.

**Every time you place a trade at Fidelity:** come back and use option
**5** to log the fill (symbol, side, quantity, price). This is what keeps
the PDT count and daily-loss numbers accurate — there's no Fidelity feed
to fall back on, so the engine is only as good as what you log here.

### Want to type a word instead of double-clicking?
**Ubuntu/WSL or Mac/Linux:** add this line to `~/.bashrc` (WSL/Ubuntu) or
`~/.zshrc` (Mac) — replace the path with wherever you unzipped this folder,
e.g. `/home/<you>/algo_signal_engine` in WSL:
```bash
alias risk-engine="cd /path/to/algo_signal_engine && ./risk-engine.sh"
```
Then `source ~/.bashrc` (or open a new terminal) and just type `risk-engine`
from anywhere.

**Windows:** put `algo_signal_engine` on your PATH (System Properties →
Environment Variables → Path), then typing `risk-engine.bat` from any
Command Prompt window launches it.

### If you'd rather use raw commands
Everything the menu does is also available directly — `python main.py
--watchlist AAPL,MSFT --once` for a single scan, `python trade_log.py
set-equity 12500` / `log-trade AAPL BUY 10 189.40` / `status` for account
state. The menu just wraps these so you never have to type them.

## 3. Files

| File | Purpose |
|---|---|
| `menu.py` | **Start here.** Interactive menu (with ASCII banner) wrapping everything below |
| `risk-engine.sh` / `risk-engine.bat` | Double-clickable launchers for the menu |
| `env_setup.py` | Reads/writes `.env` and hot-reloads config — powers menu option 8 |
| `data_fetcher.py` | Pulls bars from Alpaca, Finnhub, Twelve Data, Alpha Vantage, Polygon, Tiingo, or yfinance — whichever configured provider responds first, in that priority order |
| `indicators.py` | SMA/EMA, RSI, Bollinger Bands, ATR, ADX |
| `regime.py` | Classifies each symbol as trending / ranging / choppy |
| `strategies.py` | Trend-following (MA crossover + breakout) and mean-reversion (RSI/BB) rule sets |
| `risk_engine.py` | Fidelity-appropriate rules — see below |
| `signal_engine.py` | Orchestrates the pipeline for one symbol |
| `main.py` | Watchlist loop, market-hours check, console output, CSV logging |
| `trade_log.py` | Raw CLI equivalent of the menu's equity/trade-logging options |
| `state.json` | Your account equity, peak equity, day-trade timestamps, trade log (auto-created) |
| `watchlist.json` | Your saved watchlist (auto-created via menu option 6) |

## 4. Risk rules implemented (Fidelity, not prop-firm)

| Rule | Why it matters at Fidelity |
|---|---|
| **PDT rule** | If equity < $25,000 in a margin account, you're limited to 3 day trades per rolling 5 business days — the 4th gets you flagged/frozen. The engine counts your logged day trades and **blocks** new day-trade signals once you're at the limit. Cash accounts skip PDT but face T+1 settlement — the engine flags that too. |
| **Position sizing** | Risk-per-trade % of *your actual equity* (from `state.json`), sized off ATR-based stop distance — not a flat share count. |
| **Max daily loss** | Halts new signals for the rest of the day once your logged daily loss hits your threshold. |
| **Max drawdown from peak** | Pauses signal generation if equity falls a set % below its recorded peak, until you reset. |
| **Max concentration** | Caps how much of your account one symbol/position can represent. |
| **Max open positions** | Simple cap on simultaneous ideas so you're not tracking 15 fills by hand. |

None of these are prop-firm trailing-drawdown or consistency-rule constructs —
they're retail-account constructs specific to a self-directed Fidelity
account. Edit the numbers in `config.py` to match your actual account type
and size.

## 5. Free market-data APIs — set up any of these via menu option 8

| Provider | Free tier | Key needed | Notes |
|---|---|---|---|
| **Alpaca Market Data** | Real-time IEX feed, ~7 yrs history, generous rate limit | Yes (free) | Used by this project. IEX ≈ 2% of consolidated volume — fine for signals, not for large/illiquid names. |
| **yfinance (Yahoo Finance)** | Delayed/EOD + decent intraday | No | Unofficial wrapper around Yahoo's endpoints; free but no SLA, can break/rate-limit without notice. Used here as the no-key fallback. |
| **Finnhub** | Real-time US stock quotes, 60 calls/min | Yes (free) | Good secondary quote source. |
| **Twelve Data** | 8 req/min, 800/day | Yes (free) | Broad global coverage, simple REST. |
| **Alpha Vantage** | 5 req/min, 25/day (current limits — verify) | Yes (free) | Good for indicators-as-a-service, but low daily cap for polling loops. |
| **Polygon.io** | Delayed data, 5 req/min | Yes (free) | Real-time/full history requires paid tier. |
| **Tiingo** | EOD + limited intraday | Yes (free) | Strong for EOD backtesting datasets. |
| **Financial Modeling Prep** | Limited daily calls | Yes (free) | Good for fundamentals alongside price data. |
| Google Finance | No public API | — | `GOOGLEFINANCE()` only works inside Google Sheets, not callable from a script. |

Check each provider's current docs before relying on limits above — free tiers
change often.

## Disclaimer

This is a decision-support and paper-trading tool, not a broker, not
investment advice, and it does not place real orders. You are solely
responsible for every trade you place at Fidelity. Backtest and paper-trade
extensively before committing real capital, and confirm the PDT/settlement
rules above reflect your actual account type.
