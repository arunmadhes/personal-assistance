import re

from ai_router import ask_ai, get_mode
from live_market_data import format_quote_snapshot, fetch_quote_snapshot, summarize_watchlist_snapshots
from market_data import build_market_prompt, extract_symbol, extract_timeframe, extract_trade_numbers
from memory import add_memory
from online_llm import ask_online
from trade_journal import add_journal_entry, summarize_recent_journal
from watchlist import add_to_watchlist, load_watchlist, remove_from_watchlist, summarize_watchlist


def _risk_response(text, symbol):
    numbers = extract_trade_numbers(text)
    entry = numbers["entry"]
    stop_loss = numbers["stop_loss"]
    capital = numbers["capital"]
    risk_percent = numbers["risk_percent"]
    target = numbers["target"]

    if entry is None or stop_loss is None:
        return (
            "To calculate trade risk, please give me at least entry and stop-loss. "
            "Example: risk for RELIANCE entry 2900 stop 2840 capital 100000 risk 1"
        )

    per_unit_risk = abs(entry - stop_loss)
    if per_unit_risk == 0:
        return "Entry and stop-loss cannot be the same."

    lines = [f"Risk review for {symbol or 'this trade'}:"]
    lines.append(f"- Entry: {entry:.2f}")
    lines.append(f"- Stop-loss: {stop_loss:.2f}")
    lines.append(f"- Risk per share: {per_unit_risk:.2f}")

    if capital is not None and risk_percent is not None:
        rupee_risk = capital * (risk_percent / 100.0)
        quantity = int(rupee_risk // per_unit_risk)
        lines.append(f"- Capital: {capital:.2f}")
        lines.append(f"- Risk budget at {risk_percent:.2f}%: {rupee_risk:.2f}")
        lines.append(f"- Approx position size: {max(quantity, 0)} shares")

    if target is not None:
        reward = abs(target - entry)
        ratio = reward / per_unit_risk if per_unit_risk else 0
        lines.append(f"- Target: {target:.2f}")
        lines.append(f"- Reward-to-risk: {ratio:.2f}R")

    lines.append("- This is a sizing aid, not a buy or sell instruction.")
    return "\n".join(lines)


def _build_setup_summary(snapshot):
    timeframe = snapshot.get("timeframe", "swing")
    lines = [f"Structured setup view ({timeframe}):"]

    trend = snapshot.get("trend")
    if trend:
        lines.append(f"- Trend: {trend}")

    if snapshot.get("signal"):
        lines.append(f"- Signal: {snapshot['signal']}")

    if snapshot.get("setup_score") is not None:
        lines.append(f"- Setup score: {snapshot['setup_score']}/100")

    support = snapshot.get("support", snapshot.get("recent_low"))
    resistance = snapshot.get("resistance", snapshot.get("recent_high"))
    if support is not None and resistance is not None:
        lines.append(
            f"- Key range: support near {support:.2f}, resistance near {resistance:.2f}"
        )

    if snapshot.get("sma20") is not None and snapshot.get("sma50") is not None:
        lines.append(
            f"- Moving averages: price vs SMA20 {snapshot['sma20']:.2f}, SMA50 {snapshot['sma50']:.2f}"
        )

    if snapshot.get("rsi14") is not None:
        lines.append(f"- RSI14: {snapshot['rsi14']:.2f}")

    if snapshot.get("macd_hist") is not None:
        lines.append(f"- MACD histogram: {snapshot['macd_hist']:.4f}")

    if snapshot.get("adx") is not None:
        lines.append(f"- ADX / DI: {snapshot['adx']:.2f} with +DI {snapshot.get('di_plus', 0):.2f} and -DI {snapshot.get('di_minus', 0):.2f}")

    if snapshot.get("vwap") is not None:
        lines.append(f"- VWAP: {snapshot['vwap']:.2f}")

    if snapshot.get("atr14") is not None:
        lines.append(f"- ATR14: {snapshot['atr14']:.2f}")

    if snapshot.get("volume_ratio") is not None:
        lines.append(f"- Volume ratio: {snapshot['volume_ratio']:.2f}x")

    if snapshot.get("breakout_bias"):
        lines.append(f"- Context: {snapshot['breakout_bias']}")

    lines.append("- Use this as a planning aid, not a guaranteed trade signal.")
    return "\n".join(lines)


def _stream_market_reasoning(prompt):
    try:
        yielded = False
        for token in ask_online(prompt):
            yielded = True
            yield token
        if yielded:
            return
        raise RuntimeError("online provider returned no content")
    except Exception as exc:
        yield f"[Irish] Online market analysis unavailable, using {get_mode()} mode reasoning.\n"
        yield from ask_ai(prompt)


def _analysis_response(text, symbol):
    mode = get_mode()
    timeframe = extract_timeframe(text)
    snapshot_note = ""
    market_mode = "online"
    setup_summary = ""

    if symbol:
        try:
            snapshot = fetch_quote_snapshot(symbol, timeframe=timeframe)
            snapshot_note = f"\n\n{format_quote_snapshot(snapshot)}"
            setup_summary = _build_setup_summary(snapshot)
        except Exception as exc:
            snapshot_note = f"\n\nLive market snapshot unavailable right now: {exc}"
            market_mode = mode

    prompt = build_market_prompt(
        f"{text}{snapshot_note}",
        symbol=symbol,
        mode=market_mode,
        timeframe=timeframe,
    )
    response = ""

    if snapshot_note:
        yield snapshot_note + "\n\n"
    if setup_summary:
        yield setup_summary + "\n\n"

    for token in _stream_market_reasoning(prompt):
        response += token
        yield token

    add_memory(
        text,
        response,
        mode=market_mode,
        intent="market",
        source="market_agent",
    )


def handle(text):
    command = (text or "").strip()
    lowered = command.lower()
    symbol = extract_symbol(command)
    timeframe = extract_timeframe(command)

    if any(phrase in lowered for phrase in ("add to watchlist", "watchlist add", "add watchlist")):
        yield add_to_watchlist(symbol)
        return

    if "add " in lowered and " watchlist" in lowered:
        yield add_to_watchlist(symbol)
        return

    if any(phrase in lowered for phrase in ("remove from watchlist", "delete from watchlist", "remove watchlist")):
        yield remove_from_watchlist(symbol)
        return

    if (
        "watchlist" in lowered
        and any(re.search(rf"\b{word}\b", lowered) for word in ("show", "review", "list", "check"))
    ):
        summary = summarize_watchlist()
        items = load_watchlist()
        symbols = [item["symbol"] for item in items[:8]]
        if symbols:
            try:
                summary += "\n\n" + summarize_watchlist_snapshots(symbols, timeframe=timeframe)
            except Exception as exc:
                summary += f"\n\nLive watchlist snapshot unavailable right now: {exc}"
        yield summary
        return

    if "journal" in lowered and any(word in lowered for word in ("show", "list", "review", "recent")):
        yield summarize_recent_journal()
        return

    if "journal" in lowered and symbol:
        numbers = extract_trade_numbers(command)
        yield add_journal_entry(symbol, command, details=numbers)
        return

    if any(term in lowered for term in ("quote", "price", "ltp", "cmp")) and symbol:
        try:
            yield format_quote_snapshot(fetch_quote_snapshot(symbol, timeframe=timeframe))
        except Exception as exc:
            yield f"I couldn't fetch a live quote for {symbol} right now: {exc}"
        return

    if any(word in lowered for word in ("risk", "position size", "quantity")):
        yield _risk_response(command, symbol)
        return

    for token in _analysis_response(command, symbol):
        yield token
