from live_market_data import fetch_price_series, fetch_quote_snapshot
from watchlist import load_watchlist


def build_market_cards_payload(symbol, token):
    payload = {"symbol": symbol, "token": token, "cards": {}}

    for timeframe in ("intraday", "swing", "positional"):
        try:
            payload["cards"][timeframe] = {
                "ok": True,
                "snapshot": fetch_quote_snapshot(symbol, timeframe=timeframe),
            }
        except Exception as exc:
            payload["cards"][timeframe] = {
                "ok": False,
                "error": str(exc),
            }

    return payload


def build_market_watchlist_payload(token, limit=12, timeframe="swing"):
    items = load_watchlist()
    payload = {"token": token, "rows": [], "count": len(items)}

    for item in items[:limit]:
        symbol = item["symbol"]
        try:
            snapshot = fetch_quote_snapshot(symbol, timeframe=timeframe)
            payload["rows"].append({
                "symbol": symbol,
                "ok": True,
                "snapshot": snapshot,
            })
        except Exception as exc:
            payload["rows"].append({
                "symbol": symbol,
                "ok": False,
                "error": str(exc),
            })

    return payload


def build_market_chart_payload(symbol, timeframe, token):
    try:
        series = fetch_price_series(symbol, timeframe=timeframe)
        return {"token": token, "ok": True, "series": series}
    except Exception as exc:
        return {
            "token": token,
            "ok": False,
            "symbol": symbol,
            "timeframe": timeframe,
            "error": str(exc),
        }
