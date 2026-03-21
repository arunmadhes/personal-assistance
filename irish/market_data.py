import re


INDIAN_INDEXES = {
    "NIFTY",
    "NIFTY50",
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
    "SENSEX",
}

MARKET_TERMS = (
    "stock",
    "stocks",
    "share",
    "shares",
    "market",
    "trading",
    "trade",
    "intraday",
    "swing",
    "investment",
    "investing",
    "portfolio",
    "watchlist",
    "journal",
    "nifty",
    "sensex",
    "banknifty",
    "bank nifty",
    "finnifty",
    "nse",
    "bse",
)

TIMEFRAME_KEYWORDS = {
    "intraday": ("intraday", "day trade", "scalp", "scalping", "15m", "5m"),
    "swing": ("swing", "swing trade", "short term"),
    "positional": ("positional", "position", "positional trade", "long term", "longterm", "investment"),
}


def looks_like_market_request(text):
    normalized = text.lower().strip()
    if not normalized:
        return False

    return any(term in normalized for term in MARKET_TERMS)


def normalize_symbol(raw_symbol):
    symbol = re.sub(r"[^A-Za-z0-9]", "", str(raw_symbol or "")).upper()
    return symbol


def extract_symbol(text):
    normalized = str(text or "")
    if not normalized.strip():
        return ""

    watchlist_style = re.search(
        r"\b(?:add|remove|delete)\s+([A-Za-z][A-Za-z0-9&.-]{1,14})\s+(?:to|from)\s+(?:my\s+)?watchlist\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if watchlist_style:
        symbol = normalize_symbol(watchlist_style.group(1))
        if symbol:
            return symbol

    explicit = re.search(
        r"\b(?:for|of|on|analyze|analyse|review|check|trade|buy|sell|journal|watchlist|add|remove|delete)\s+([A-Za-z][A-Za-z0-9&.-]{1,14})\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if explicit:
        symbol = normalize_symbol(explicit.group(1))
        if symbol:
            return symbol

    fallback = re.search(
        r"\b([A-Za-z][A-Za-z0-9&.-]{1,14})\s+(?:stock|share|chart|symbol|watchlist)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if fallback:
        symbol = normalize_symbol(fallback.group(1))
        if symbol and symbol.lower() not in {"stock", "share", "chart", "symbol", "watchlist"}:
            return symbol

    uppercase_tokens = re.findall(r"\b[A-Z][A-Z0-9]{1,14}\b", normalized)
    for token in uppercase_tokens:
        symbol = normalize_symbol(token)
        if symbol and (len(symbol) >= 2 or symbol in INDIAN_INDEXES):
            return symbol

    lowered = normalized.lower()
    for index_name in INDIAN_INDEXES:
        if index_name.lower() in lowered:
            return index_name

    return ""


def extract_timeframe(text):
    normalized = str(text or "").lower()
    for timeframe, hints in TIMEFRAME_KEYWORDS.items():
        if any(hint in normalized for hint in hints):
            return timeframe
    return "swing"


def extract_named_number(text, labels):
    label_group = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"\b(?:{label_group})\s*(?:is|at|of|=)?\s*([0-9]+(?:\.[0-9]+)?)\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return float(match.group(1))


def extract_trade_numbers(text):
    return {
        "entry": extract_named_number(text, ("entry", "buy", "sell", "price")),
        "stop_loss": extract_named_number(text, ("stop", "stoploss", "stop loss", "sl")),
        "target": extract_named_number(text, ("target", "tgt")),
        "capital": extract_named_number(text, ("capital", "account", "fund", "funds")),
        "risk_percent": extract_named_number(text, ("risk", "risk percent", "risk percentage")),
    }


def build_market_prompt(user_request, symbol="", mode="offline", timeframe="swing"):
    symbol_text = symbol or "the requested Indian-market instrument"
    if mode == "online":
        data_note = (
            "You may answer in an online-analysis style, but be honest if exact live price data is not available "
            "inside the prompt."
        )
    else:
        data_note = (
            "Answer from offline knowledge only and do not pretend you fetched live market data or latest prices."
        )

    return f"""
You are Irish Market Analyst, a careful Indian-market trading assistant.

User request: {user_request}
Primary instrument: {symbol_text}
Market context: India (NSE/BSE, index names like NIFTY, BANKNIFTY, SENSEX)
Mode: {mode}
Requested timeframe: {timeframe}

Rules:
- This is educational analysis, not guaranteed financial advice.
- {data_note}
- Never promise profit or certainty.
- Always mention risk and an invalidation condition.
- If exact live price or news is missing, say that clearly.
- Keep the answer practical and concise.
- Use this structure when relevant:
  1. Market view
  2. Key levels or focus areas
  3. Setup idea
  4. Confidence or setup quality
  5. Risk note
- If live market metrics like RSI, SMA, setup score, or range context are present in the request context, use them directly.

Answer:
"""
