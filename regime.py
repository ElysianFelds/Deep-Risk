"""
Classifies the current regime for a symbol so the strategy selector knows
whether to hand the signal to the trend-following or mean-reversion logic.

Bollinger Band width is judged RELATIVE to the symbol's own recent history,
not against a fixed percentage — a 0.5% width is tight for one name and
wide for another, so an absolute cutoff misclassifies almost everything.
"""
import pandas as pd
import config


def classify(df_with_indicators: pd.DataFrame) -> str:
    """
    Returns one of: "trending", "ranging", "choppy"

    - choppy:   current Bollinger width is in the bottom slice of its own
                recent range (unusually tight even for this symbol) -> no
                strategy has a reliable edge
    - trending: not unusually tight, and ADX above threshold -> trend-following
    - ranging:  not unusually tight, ADX below threshold -> mean-reversion
    """
    last = df_with_indicators.iloc[-1]
    adx_val = last.get("adx_14")
    bb_width = last.get("bb_width")

    if pd.isna(adx_val) or pd.isna(bb_width):
        return "choppy"

    width_history = df_with_indicators["bb_width"].dropna()
    if len(width_history) < 20:
        return "choppy"

    # What fraction of recent bars had a width <= today's width?
    # A low percentile means today is unusually tight for THIS symbol.
    percentile = (width_history <= bb_width).mean()

    if percentile <= config.CHOP_WIDTH_PERCENTILE:
        return "choppy"

    if adx_val >= config.ADX_TREND_THRESHOLD:
        return "trending"

    return "ranging"
