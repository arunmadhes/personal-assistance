import math


def ema(values, period):
    series = [value for value in values if isinstance(value, (int, float))]
    if not series:
        return []

    factor = 2 / (period + 1)
    result = [series[0]]
    for value in series[1:]:
        result.append(value * factor + result[-1] * (1 - factor))
    return result


def sma(values, period):
    series = [value for value in values if isinstance(value, (int, float))]
    result = []
    for index in range(len(series)):
        if index < period - 1:
            result.append(None)
        else:
            window = series[index - period + 1:index + 1]
            result.append(sum(window) / period)
    return result


def rsi(values, period=14):
    series = [value for value in values if isinstance(value, (int, float))]
    if len(series) < period + 1:
        return [None] * len(series)

    gains = 0
    losses = 0
    for index in range(1, period + 1):
        change = series[index] - series[index - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change

    avg_gain = gains / period
    avg_loss = losses / period
    result = [None] * period
    rs = avg_gain / (avg_loss or 1e-9)
    result.append(100 - 100 / (1 + rs))

    for index in range(period + 1, len(series)):
        change = series[index] - series[index - 1]
        avg_gain = (avg_gain * (period - 1) + (change if change > 0 else 0)) / period
        avg_loss = (avg_loss * (period - 1) + (-change if change < 0 else 0)) / period
        rs = avg_gain / (avg_loss or 1e-9)
        result.append(100 - 100 / (1 + rs))

    return result


def macd(values, fast=12, slow=26, signal_period=9):
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    limit = min(len(fast_ema), len(slow_ema))
    if limit == 0:
        return [], [], []

    line = [fast_ema[-limit + index] - slow_ema[-limit + index] for index in range(limit)]
    signal = ema(line, signal_period)
    hist_limit = min(len(line), len(signal))
    histogram = [line[-hist_limit + index] - signal[-hist_limit + index] for index in range(hist_limit)]
    return line, signal, histogram


def atr(highs, lows, closes, period=14):
    clean_highs = [value for value in highs if isinstance(value, (int, float))]
    clean_lows = [value for value in lows if isinstance(value, (int, float))]
    clean_closes = [value for value in closes if isinstance(value, (int, float))]

    limit = min(len(clean_highs), len(clean_lows), len(clean_closes))
    if limit == 0:
        return []

    clean_highs = clean_highs[-limit:]
    clean_lows = clean_lows[-limit:]
    clean_closes = clean_closes[-limit:]

    true_ranges = []
    for index in range(limit):
        if index == 0:
            true_ranges.append(clean_highs[index] - clean_lows[index])
        else:
            true_ranges.append(max(
                clean_highs[index] - clean_lows[index],
                abs(clean_highs[index] - clean_closes[index - 1]),
                abs(clean_lows[index] - clean_closes[index - 1]),
            ))
    return sma(true_ranges, period)


def vwap(closes, volumes):
    clean_closes = [value for value in closes if isinstance(value, (int, float))]
    clean_volumes = [value for value in volumes if isinstance(value, (int, float))]
    limit = min(len(clean_closes), len(clean_volumes))
    if limit == 0:
        return []

    clean_closes = clean_closes[-limit:]
    clean_volumes = clean_volumes[-limit:]

    cumulative_value = 0.0
    cumulative_volume = 0.0
    result = []
    for close, volume in zip(clean_closes, clean_volumes):
        cumulative_value += close * volume
        cumulative_volume += volume
        result.append(cumulative_value / (cumulative_volume or 1.0))
    return result


def stochastic(highs, lows, closes, period=14):
    limit = min(len(highs), len(lows), len(closes))
    if limit == 0:
        return []

    result = []
    for index in range(limit):
        if index < period - 1:
            result.append(None)
            continue
        highest_high = max(highs[index - period + 1:index + 1])
        lowest_low = min(lows[index - period + 1:index + 1])
        result.append((closes[index] - lowest_low) / ((highest_high - lowest_low) or 1) * 100)
    return result


def williams_r(highs, lows, closes, period=14):
    limit = min(len(highs), len(lows), len(closes))
    if limit == 0:
        return []

    result = []
    for index in range(limit):
        if index < period - 1:
            result.append(None)
            continue
        highest_high = max(highs[index - period + 1:index + 1])
        lowest_low = min(lows[index - period + 1:index + 1])
        result.append((highest_high - closes[index]) / ((highest_high - lowest_low) or 1) * -100)
    return result


def adx(highs, lows, closes, period=14):
    limit = min(len(highs), len(lows), len(closes))
    if limit < period * 2:
        return 20.0, 20.0, 20.0

    dm_plus = []
    dm_minus = []
    true_ranges = []
    for index in range(1, limit):
        up_move = highs[index] - highs[index - 1]
        down_move = lows[index - 1] - lows[index]
        dm_plus.append(max(up_move, 0) if up_move > down_move else 0)
        dm_minus.append(max(down_move, 0) if down_move > up_move else 0)
        true_ranges.append(max(
            highs[index] - lows[index],
            abs(highs[index] - closes[index - 1]),
            abs(lows[index] - closes[index - 1]),
        ))

    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus = sum(dm_plus[:period])
    smoothed_minus = sum(dm_minus[:period])

    di_plus_list = []
    di_minus_list = []
    dx_list = []
    for index in range(period, len(true_ranges)):
        smoothed_tr = smoothed_tr - smoothed_tr / period + true_ranges[index]
        smoothed_plus = smoothed_plus - smoothed_plus / period + dm_plus[index]
        smoothed_minus = smoothed_minus - smoothed_minus / period + dm_minus[index]

        di_plus = 100 * smoothed_plus / (smoothed_tr or 1)
        di_minus = 100 * smoothed_minus / (smoothed_tr or 1)
        di_plus_list.append(di_plus)
        di_minus_list.append(di_minus)
        dx_list.append(100 * abs(di_plus - di_minus) / ((di_plus + di_minus) or 1))

    adx_value = sum(dx_list[-period:]) / period if dx_list else 20.0
    return adx_value, di_plus_list[-1] if di_plus_list else 20.0, di_minus_list[-1] if di_minus_list else 20.0


def analyze_setup(closes, volumes, highs, lows):
    limit = min(len(closes), len(volumes), len(highs), len(lows))
    if limit < 5:
        return None

    closes = closes[-limit:]
    volumes = volumes[-limit:]
    highs = highs[-limit:]
    lows = lows[-limit:]

    rsi_values = rsi(closes, 14)
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, min(50, max(2, len(closes) - 1)))
    ema200 = ema(closes, min(200, max(2, len(closes) - 1)))
    macd_line, macd_signal, macd_hist = macd(closes)
    atr_values = atr(highs, lows, closes, 14)
    vwap_values = vwap(closes, volumes)
    stochastic_values = stochastic(highs, lows, closes, 14)
    williams_values = williams_r(highs, lows, closes, 14)
    adx_value, di_plus, di_minus = adx(highs, lows, closes, 14)

    latest_close = closes[-1]
    latest_rsi = rsi_values[-1] if rsi_values and rsi_values[-1] is not None else 50.0
    latest_macd_hist = macd_hist[-1] if macd_hist else 0.0
    previous_macd_hist = macd_hist[-2] if len(macd_hist) > 1 else 0.0
    latest_ema9 = ema9[-1] if ema9 else latest_close
    latest_ema21 = ema21[-1] if ema21 else latest_close
    latest_ema50 = ema50[-1] if ema50 else latest_close
    latest_ema200 = ema200[-1] if ema200 else latest_close
    latest_vwap = vwap_values[-1] if vwap_values else latest_close
    latest_atr = atr_values[-1] if atr_values and atr_values[-1] is not None else 1.0
    latest_stochastic = stochastic_values[-1] if stochastic_values and stochastic_values[-1] is not None else None
    latest_williams = williams_values[-1] if williams_values and williams_values[-1] is not None else None

    avg_volume = sum(volumes[-20:]) / max(len(volumes[-20:]), 1)
    current_volume = volumes[-1]

    bullish = 0
    bearish = 0
    notes = []

    def score(condition, weight, bullish_note, bearish_note):
        nonlocal bullish, bearish
        if condition:
            bullish += weight
            notes.append(("bull", bullish_note))
        else:
            bearish += weight
            notes.append(("bear", bearish_note))

    score(latest_rsi < 50, 2, "RSI below 50 with recovery room", "RSI above 50 and getting extended")
    score(latest_rsi < 30, 1, "RSI oversold bounce zone", "RSI overbought risk zone")
    score(latest_macd_hist > 0 and previous_macd_hist <= 0, 3, "MACD bullish crossover", "MACD bearish crossover")
    score(latest_macd_hist > 0, 1, "MACD histogram positive", "MACD histogram negative")
    score(latest_close > latest_ema9, 2, "Price above EMA9", "Price below EMA9")
    score(latest_ema9 > latest_ema21, 2, "EMA9 above EMA21", "EMA9 below EMA21")
    score(latest_close > latest_ema50, 1, "Price above EMA50", "Price below EMA50")
    score(latest_close > latest_ema200, 1, "Price above EMA200", "Price below EMA200")
    score(latest_close > latest_vwap, 1, "Price above VWAP", "Price below VWAP")
    score(current_volume > avg_volume * 1.3 and latest_close > closes[-2], 1, "Volume-backed move", "Weak volume context")
    score(di_plus > di_minus, 1, "Directional movement supports bulls", "Directional movement supports bears")

    total = bullish + bearish or 1
    score_percent = round(bullish / total * 100)

    if score_percent >= 75:
        signal = "STRONG BUY"
    elif score_percent >= 58:
        signal = "BUY"
    elif score_percent <= 25:
        signal = "STRONG SELL"
    elif score_percent <= 42:
        signal = "SELL"
    else:
        signal = "HOLD"

    support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)

    return {
        "signal": signal,
        "score": score_percent,
        "bullish_points": bullish,
        "bearish_points": bearish,
        "notes": notes,
        "rsi14": round(latest_rsi, 2),
        "macd_hist": round(latest_macd_hist, 4),
        "ema9": round(latest_ema9, 2),
        "ema21": round(latest_ema21, 2),
        "ema50": round(latest_ema50, 2),
        "ema200": round(latest_ema200, 2),
        "vwap": round(latest_vwap, 2),
        "atr14": round(latest_atr, 2),
        "stochastic_k": round(latest_stochastic, 2) if latest_stochastic is not None else None,
        "williams_r": round(latest_williams, 2) if latest_williams is not None else None,
        "adx": round(adx_value, 2),
        "di_plus": round(di_plus, 2),
        "di_minus": round(di_minus, 2),
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "volume_ratio": round(current_volume / (avg_volume or 1), 2),
    }
