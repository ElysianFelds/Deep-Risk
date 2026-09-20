"""
Signal engine main loop.

    python main.py --watchlist AAPL,MSFT,SPY,QQQ,NVDA --interval 300
    python main.py --watchlist AAPL,MSFT --once

Prints a signal table to console and appends every row to signals_log.csv.
Nothing here places real orders — Fidelity has no API. This tells you what
to do; you do it.
"""
import argparse
import csv
import os
import time
from datetime import datetime

import pytz
from tabulate import tabulate

import config
import signal_engine
import data_fetcher
import notifier
import alpaca_executor


def market_is_open(now_utc: datetime) -> bool:
    tz = pytz.timezone(config.MARKET_TZ)
    now_local = now_utc.astimezone(tz)
    if now_local.weekday() >= 5:  # Sat/Sun
        return False
    open_h, open_m = map(int, config.MARKET_OPEN.split(":"))
    close_h, close_m = map(int, config.MARKET_CLOSE.split(":"))
    open_t = now_local.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    close_t = now_local.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
    return open_t <= now_local <= close_t


def append_csv(rows: list):
    file_exists = os.path.exists(config.SIGNAL_LOG_CSV)
    with open(config.SIGNAL_LOG_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


_alerted_bars = set()  # (symbol, bar_time) already surfaced as ACTIONABLE this run


def run_once(watchlist: list) -> list:
    results = [signal_engine.run_for_symbol(sym) for sym in watchlist]
    table = [[r["symbol"], r["regime"], r["adx"], r["bb_width_pct"], r["strategy"], r["side"],
              r["entry"], r["stop"], r["target"], r["suggested_qty"],
              r["risk_status"], r["risk_reason"][:50]] for r in results]
    headers = ["Symbol", "Regime", "ADX", "BB Width%", "Strategy", "Side", "Entry", "Stop",
               "Target", "Qty", "Risk", "Risk reason"]
    print(f"\n=== Signal scan @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
          f"(data sources: {', '.join(data_fetcher.active_sources())}) ===")
    print(tabulate(table, headers=headers, tablefmt="simple"))
    append_csv(results)

    new_actionable = []
    for r in results:
        if r["side"] != "HOLD" and r["risk_status"] == "APPROVED":
            key = (r["symbol"], r["bar_time"])
            if key not in _alerted_bars:
                _alerted_bars.add(key)
                new_actionable.append(r)

    if new_actionable:
        print("\n>>> NEW ACTIONABLE — place these manually on Fidelity:")
        for r in new_actionable:
            print(f"    {r['side']} {r['suggested_qty']} {r['symbol']} @ ~{r['entry']} "
                  f"| stop {r['stop']} | target {r['target']}  ({r['strategy']})")
            if config.ALPACA_AUTO_EXECUTE:
                exec_result = alpaca_executor.submit_paper_order(r["symbol"], r["side"], r["suggested_qty"])
                if exec_result["status"] == "SUBMITTED":
                    print(f"       [ALPACA PAPER] Order submitted (id {exec_result['order_id']}) "
                          f"— this is a SIMULATED fill, separate from Fidelity")
                else:
                    print(f"       [ALPACA PAPER] {exec_result['status']}: {exec_result['reason']}")
        notifier.maybe_send(new_actionable)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", required=True, help="Comma-separated tickers, e.g. AAPL,MSFT,SPY")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between scans")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit")
    parser.add_argument("--ignore-market-hours", action="store_true",
                         help="Run even outside 9:30-16:00 ET (useful for testing)")
    args = parser.parse_args()

    watchlist = [s.strip().upper() for s in args.watchlist.split(",") if s.strip()]

    if args.once:
        run_once(watchlist)
        return

    print(f"Watching {watchlist} every {args.interval}s. Ctrl+C to stop.")
    while True:
        now_utc = datetime.now(pytz.utc)
        if args.ignore_market_hours or market_is_open(now_utc):
            try:
                run_once(watchlist)
            except Exception as e:
                print(f"[main] Scan error: {e}")
        else:
            print(f"[{now_utc.strftime('%H:%M:%S UTC')}] Market closed — sleeping.")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
