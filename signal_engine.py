"""Runs the full pipeline for a single symbol and returns one signal record."""
from datetime import datetime

import data_fetcher
import indicators
import regime as regime_mod
import strategies
import risk_engine


def run_for_symbol(symbol: str) -> dict:
    raw = data_fetcher.get_bars(symbol)
    if raw.empty or len(raw) < 55:
        return {
            "symbol": symbol, "timestamp": datetime.now().isoformat(),
            "bar_time": None,
            "regime": "unknown", "adx": None, "bb_width_pct": None,
            "strategy": "none", "side": "HOLD",
            "reason": "Insufficient bar data returned", "entry": None,
            "stop": None, "target": None, "risk_status": "SKIPPED",
            "risk_reason": "", "suggested_qty": 0,
        }

    df = indicators.compute_all(raw)
    current_regime = regime_mod.classify(df)
    strat_result = strategies.select_and_run(df, current_regime)

    risk_result = risk_engine.evaluate(
        symbol=symbol,
        side=strat_result["side"],
        entry=strat_result["entry"],
        stop=strat_result["stop"],
    )

    last = df.iloc[-1]
    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "bar_time": df.index[-1].isoformat(),
        "regime": current_regime,
        "adx": round(last["adx_14"], 1) if not (last["adx_14"] != last["adx_14"]) else None,  # NaN-safe
        "bb_width_pct": round(last["bb_width"] * 100, 2) if not (last["bb_width"] != last["bb_width"]) else None,
        "strategy": strat_result["strategy"],
        "side": strat_result["side"],
        "reason": strat_result["reason"],
        "entry": round(strat_result["entry"], 2) if strat_result["entry"] is not None else None,
        "stop": round(strat_result["stop"], 2) if strat_result["stop"] is not None else None,
        "target": round(strat_result["target"], 2) if strat_result["target"] is not None else None,
        "risk_status": risk_result["status"],
        "risk_reason": risk_result["reason"],
        "suggested_qty": risk_result["suggested_qty"],
    }
