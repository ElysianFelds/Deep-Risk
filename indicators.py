"""Technical indicators computed with plain pandas/numpy (no extra deps)."""
import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    mid = sma(series, window)
    std = series.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return upper, mid, lower, width


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = atr(df, window) * window  # un-smoothed true range approximation via ATR scale
    atr_series = atr(df, window)

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean() / atr_series
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean() / atr_series

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1 / window, adjust=False).mean()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Adds indicator columns to a copy of the OHLCV dataframe."""
    out = df.copy()
    out["sma_20"] = sma(out["Close"], 20)
    out["sma_50"] = sma(out["Close"], 50)
    out["ema_9"] = ema(out["Close"], 9)
    out["ema_21"] = ema(out["Close"], 21)
    out["rsi_14"] = rsi(out["Close"], 14)
    bb_u, bb_m, bb_l, bb_w = bollinger_bands(out["Close"], 20, 2.0)
    out["bb_upper"], out["bb_mid"], out["bb_lower"], out["bb_width"] = bb_u, bb_m, bb_l, bb_w
    out["atr_14"] = atr(out, 14)
    out["adx_14"] = adx(out, 14)
    return out
