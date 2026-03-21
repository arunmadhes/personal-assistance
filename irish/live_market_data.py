from statistics import mean

import requests

from indicators import analyze_setup, ema
from market_data import normalize_symbol


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEFRAME_PROFILES = {
    "intraday": {"range": "5d", "interval": "15m", "range_window": 26},
    "swing": {"range": "6mo", "interval": "1d", "range_window": 20},
    "positional": {"range": "1y", "interval": "1d", "range_window": 50},
}

INDEX_SYMBOLS = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}


def _candidate_symbols(symbol):
    normalized = normalize_symbol(symbol)
    if not normalized:
        return []

    if normalized in INDEX_SYMBOLS:
        return [INDEX_SYMBOLS[normalized]]

    if normalized.endswith(".NS") or normalized.endswith(".BO"):
        return [normalized]

    return [f"{normalized}.NS", f"{normalized}.BO"]


def _safe_mean(values):
    clean = [value for value in values if isinstance(value, (int, float))]
    if not clean:
        return None
    return round(mean(clean), 2)


def _trend_label(price, sma20, sma50):
    if price is None or sma20 is None or sma50 is None:
        return "mixed"
    if price > sma20 > sma50:
        return "bullish"
    if price < sma20 < sma50:
        return "bearish"
    return "mixed"


def _setup_score(price, sma20, sma50, rsi_value):
    score = 50

    if price is not None and sma20 is not None:
        score += 10 if price >= sma20 else -10
    if sma20 is not None and sma50 is not None:
        score += 10 if sma20 >= sma50 else -10
    if rsi_value is not None:
        if 45 <= rsi_value <= 65:
            score += 10
        elif rsi_value >= 75 or rsi_value <= 25:
            score -= 10

    return max(0, min(100, score))


def _extract_snapshot(exchange_symbol, payload, timeframe="swing"):
    chart = payload.get("chart", {})
    result = (chart.get("result") or [{}])[0]
    meta = result.get("meta") or {}
    indicators = result.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    closes = [value for value in (quote.get("close") or []) if isinstance(value, (int, float))]
    highs = [value for value in (quote.get("high") or []) if isinstance(value, (int, float))]
    lows = [value for value in (quote.get("low") or []) if isinstance(value, (int, float))]
    volumes = [value for value in (quote.get("volume") or []) if isinstance(value, (int, float))]

    price = meta.get("regularMarketPrice")
    previous_close = meta.get("previousClose")

    if price is None and closes:
        price = closes[-1]

    if previous_close is None and len(closes) >= 2:
        previous_close = closes[-2]

    if price is None:
        return None

    change = None
    change_percent = None
    if isinstance(previous_close, (int, float)) and previous_close:
        change = round(price - previous_close, 2)
        change_percent = round((change / previous_close) * 100, 2)

    profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["swing"])
    range_window = profile["range_window"]
    sma20 = _safe_mean(closes[-20:])
    sma50 = _safe_mean(closes[-50:])
    recent_high = round(max(highs[-range_window:]), 2) if highs else None
    recent_low = round(min(lows[-range_window:]), 2) if lows else None
    average_volume_20 = _safe_mean(volumes[-20:]) if volumes else None
    trend = _trend_label(price, sma20, sma50)
    setup = analyze_setup(closes, volumes, highs, lows) or {}
    rsi14 = setup.get("rsi14")
    setup_score = setup.get("score", _setup_score(price, sma20, sma50, rsi14))
    breakout_bias = None
    if recent_high is not None and recent_low is not None and isinstance(price, (int, float)):
        if price >= recent_high:
            breakout_bias = "near breakout high"
        elif price <= recent_low:
            breakout_bias = "near breakdown low"
        else:
            breakout_bias = "inside recent range"

    return {
        "requested_symbol": normalize_symbol(meta.get("symbol") or exchange_symbol),
        "exchange_symbol": exchange_symbol,
        "price": round(price, 2),
        "previous_close": round(previous_close, 2) if isinstance(previous_close, (int, float)) else None,
        "change": change,
        "change_percent": change_percent,
        "currency": meta.get("currency", "INR"),
        "sma20": sma20,
        "sma50": sma50,
        "rsi14": rsi14,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "avg_volume_20": average_volume_20,
        "trend": trend,
        "setup_score": setup_score,
        "breakout_bias": breakout_bias,
        "signal": setup.get("signal"),
        "atr14": setup.get("atr14"),
        "vwap": setup.get("vwap"),
        "macd_hist": setup.get("macd_hist"),
        "stochastic_k": setup.get("stochastic_k"),
        "williams_r": setup.get("williams_r"),
        "adx": setup.get("adx"),
        "di_plus": setup.get("di_plus"),
        "di_minus": setup.get("di_minus"),
        "support": setup.get("support", recent_low),
        "resistance": setup.get("resistance", recent_high),
        "volume_ratio": setup.get("volume_ratio"),
        "timeframe": timeframe,
        "source": "Yahoo Finance chart",
    }


def fetch_quote_snapshot(symbol, timeout=5, timeframe="swing"):
    errors = []
    profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["swing"])
    for candidate in _candidate_symbols(symbol):
        try:
            response = requests.get(
                YAHOO_CHART_URL.format(symbol=candidate),
                params={"range": profile["range"], "interval": profile["interval"]},
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            snapshot = _extract_snapshot(candidate, response.json(), timeframe=timeframe)
            if snapshot:
                return snapshot
            errors.append(f"{candidate}: no usable quote data")
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")

    raise RuntimeError("; ".join(errors) if errors else "No market data sources were available.")


def fetch_price_series(symbol, timeout=5, timeframe="swing", max_points=80):
    errors = []
    profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["swing"])
    for candidate in _candidate_symbols(symbol):
        try:
            response = requests.get(
                YAHOO_CHART_URL.format(symbol=candidate),
                params={"range": profile["range"], "interval": profile["interval"]},
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            chart = response.json().get("chart", {})
            result = (chart.get("result") or [{}])[0]
            meta = result.get("meta") or {}
            indicators = result.get("indicators") or {}
            quote = (indicators.get("quote") or [{}])[0]
            closes = [value for value in (quote.get("close") or []) if isinstance(value, (int, float))]

            if not closes:
                errors.append(f"{candidate}: no close series")
                continue

            closes = closes[-max_points:]
            ema9 = ema(closes, 9)[-len(closes):] if closes else []
            ema21 = ema(closes, 21)[-len(closes):] if closes else []
            return {
                "symbol": meta.get("symbol") or candidate,
                "timeframe": timeframe,
                "closes": [round(value, 2) for value in closes],
                "ema9": [round(value, 2) for value in ema9 if isinstance(value, (int, float))],
                "ema21": [round(value, 2) for value in ema21 if isinstance(value, (int, float))],
            }
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")

    raise RuntimeError("; ".join(errors) if errors else "No market series sources were available.")


def format_quote_snapshot(snapshot):
    timeframe = snapshot.get("timeframe", "swing")
    lines = [
        f"Live market snapshot ({timeframe}):",
        f"- Symbol: {snapshot['exchange_symbol']}",
        f"- Price: {snapshot['price']:.2f} {snapshot.get('currency', 'INR')}",
    ]

    if snapshot.get("change") is not None and snapshot.get("change_percent") is not None:
        lines.append(
            f"- Day change: {snapshot['change']:+.2f} ({snapshot['change_percent']:+.2f}%)"
        )

    if snapshot.get("sma20") is not None:
        lines.append(f"- SMA20: {snapshot['sma20']:.2f}")
    if snapshot.get("sma50") is not None:
        lines.append(f"- SMA50: {snapshot['sma50']:.2f}")
    if snapshot.get("rsi14") is not None:
        lines.append(f"- RSI14: {snapshot['rsi14']:.2f}")
    if snapshot.get("recent_high") is not None and snapshot.get("recent_low") is not None:
        lines.append(f"- Recent range: {snapshot['recent_low']:.2f} to {snapshot['recent_high']:.2f}")
    if snapshot.get("trend"):
        lines.append(f"- Trend bias: {snapshot['trend']}")
    if snapshot.get("signal"):
        lines.append(f"- Signal: {snapshot['signal']}")
    if snapshot.get("breakout_bias"):
        lines.append(f"- Range context: {snapshot['breakout_bias']}")
    if snapshot.get("setup_score") is not None:
        lines.append(f"- Setup score: {snapshot['setup_score']}/100")
    if snapshot.get("support") is not None and snapshot.get("resistance") is not None:
        lines.append(f"- Support/Resistance: {snapshot['support']:.2f} / {snapshot['resistance']:.2f}")
    if snapshot.get("vwap") is not None:
        lines.append(f"- VWAP: {snapshot['vwap']:.2f}")
    if snapshot.get("atr14") is not None:
        lines.append(f"- ATR14: {snapshot['atr14']:.2f}")
    if snapshot.get("adx") is not None:
        lines.append(f"- ADX: {snapshot['adx']:.2f}")
    if snapshot.get("avg_volume_20") is not None:
        lines.append(f"- Avg volume 20D: {snapshot['avg_volume_20']:.0f}")
    if snapshot.get("volume_ratio") is not None:
        lines.append(f"- Volume ratio: {snapshot['volume_ratio']:.2f}x")

    lines.append(f"- Source: {snapshot.get('source', 'Unknown')}")
    return "\n".join(lines)


def summarize_watchlist_snapshots(symbols, timeout=5, timeframe="swing"):
    lines = ["Watchlist snapshots:"]

    for symbol in symbols:
        try:
            snapshot = fetch_quote_snapshot(symbol, timeout=timeout, timeframe=timeframe)
            signal = f" · {snapshot['signal']}" if snapshot.get("signal") else ""
            if snapshot.get("change_percent") is not None:
                lines.append(
                    f"- {symbol}: {snapshot['price']:.2f} ({snapshot['change_percent']:+.2f}%){signal}"
                )
            else:
                lines.append(f"- {symbol}: {snapshot['price']:.2f}{signal}")
        except Exception as exc:
            lines.append(f"- {symbol}: live data unavailable ({exc})")

    return "\n".join(lines)
