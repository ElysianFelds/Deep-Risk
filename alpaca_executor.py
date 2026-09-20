"""
Optional: automatically submits orders to Alpaca's PAPER account (simulated
fills, fake money) when a new signal is approved, so you can observe what
the risk engine's decisions would produce with real execution authority —
entirely separate from Fidelity, which always requires manual execution
regardless of this setting.

HARD SAFETY RULE, enforced in code, not just config:
submit_paper_order() refuses to run unless config.ALPACA_PAPER is True.
There is no path here that can submit a live order. If you ever set
ALPACA_PAPER=false in .env, this module stops working entirely rather
than silently switching to live trading.
"""
import config


def _get_trading_client():
    from alpaca.trading.client import TradingClient
    # paper=True is hard-coded here, not read from config, on purpose —
    # see the safety check in submit_paper_order() below.
    return TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)


def submit_paper_order(symbol: str, side: str, qty: float) -> dict:
    if not config.USE_ALPACA:
        return {"status": "SKIPPED", "reason": "Alpaca keys not configured"}

    if not config.ALPACA_PAPER:
        return {
            "status": "REFUSED",
            "reason": ("ALPACA_PAPER is not 'true' in .env — refusing to submit any order. "
                       "This feature only ever operates in paper mode; it will not run "
                       "against a live account under any configuration."),
        }

    if not config.ALPACA_AUTO_EXECUTE:
        return {"status": "SKIPPED", "reason": "Auto-execution is toggled off (menu option 11)"}

    if qty <= 0:
        return {"status": "SKIPPED", "reason": "Quantity is zero — nothing to submit"}

    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client = _get_trading_client()
        order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = client.submit_order(req)
        return {"status": "SUBMITTED", "order_id": str(order.id), "reason": ""}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def get_paper_account_summary() -> dict:
    """Fetches current Alpaca paper account state — equity, cash, positions,
    unrealized P&L — so you can see the outcome directly without needing to
    log into Alpaca's own dashboard."""
    if not config.USE_ALPACA:
        return {"error": "Alpaca keys not configured (menu option 8)"}
    if not config.ALPACA_PAPER:
        return {"error": "ALPACA_PAPER is not true — refusing to query for safety"}

    try:
        client = _get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price) if p.current_price else None,
                    "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else None,
                }
                for p in positions
            ],
        }
    except Exception as e:
        return {"error": str(e)}
