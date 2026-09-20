"""
Two strategy families. The regime detector decides which one gets a vote;
each returns a dict: side ("BUY"/"SELL"/"HOLD"), reason, entry, stop, target.
"""
import config


def _levels(entry: float, atr_val: float, side: str):
    if side == "BUY":
        stop = entry - config.ATR_STOP_MULTIPLIER * atr_val
        target = entry + config.ATR_TARGET_MULTIPLIER * atr_val
    elif side == "SELL":
        stop = entry + config.ATR_STOP_MULTIPLIER * atr_val
        target = entry - config.ATR_TARGET_MULTIPLIER * atr_val
    else:
        stop = target = None
    return stop, target


def trend_following(df) -> dict:
    """EMA(9/21) crossover confirmed by price vs SMA50, ADX already confirmed trending by caller."""
    last, prev = df.iloc[-1], df.iloc[-2]
    entry = last["Close"]
    atr_val = last["atr_14"]

    crossed_up = prev["ema_9"] <= prev["ema_21"] and last["ema_9"] > last["ema_21"]
    crossed_down = prev["ema_9"] >= prev["ema_21"] and last["ema_9"] < last["ema_21"]
    above_trend = last["Close"] > last["sma_50"]
    below_trend = last["Close"] < last["sma_50"]

    if crossed_up and above_trend:
        side, reason = "BUY", "EMA9 crossed above EMA21 with price above SMA50 (trend continuation long)"
    elif crossed_down and below_trend:
        side, reason = "SELL", "EMA9 crossed below EMA21 with price below SMA50 (trend continuation short)"
    else:
        side, reason = "HOLD", "No fresh EMA crossover aligned with the prevailing trend"

    stop, target = _levels(entry, atr_val, side)
    return dict(strategy="trend_following", side=side, reason=reason,
                entry=entry, stop=stop, target=target, atr=atr_val)


def mean_reversion(df) -> dict:
    """RSI extremes at Bollinger Band edges, regime already confirmed ranging by caller."""
    last = df.iloc[-1]
    entry = last["Close"]
    atr_val = last["atr_14"]
    rsi_val = last["rsi_14"]

    at_lower_band = last["Close"] <= last["bb_lower"]
    at_upper_band = last["Close"] >= last["bb_upper"]

    if rsi_val <= config.RSI_OVERSOLD and at_lower_band:
        side, reason = "BUY", f"RSI {rsi_val:.1f} oversold at lower Bollinger Band (mean-reversion long)"
    elif rsi_val >= config.RSI_OVERBOUGHT and at_upper_band:
        side, reason = "SELL", f"RSI {rsi_val:.1f} overbought at upper Bollinger Band (mean-reversion short)"
    else:
        side, reason = "HOLD", f"RSI {rsi_val:.1f} not at a confirmed extreme with band touch"

    stop, target = _levels(entry, atr_val, side)
    return dict(strategy="mean_reversion", side=side, reason=reason,
                entry=entry, stop=stop, target=target, atr=atr_val)


def select_and_run(df_with_indicators, regime: str) -> dict:
    if regime == "trending":
        return trend_following(df_with_indicators)
    elif regime == "ranging":
        return mean_reversion(df_with_indicators)
    else:  # choppy
        last = df_with_indicators.iloc[-1]
        return dict(strategy="none", side="HOLD",
                    reason="Choppy regime (low ADX, narrow Bollinger width) — no strategy has an edge here",
                    entry=last["Close"], stop=None, target=None, atr=last.get("atr_14"))
