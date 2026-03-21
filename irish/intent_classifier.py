from ai_router import ask_ai


VISION_PHRASES = (
    "what do you see",
    "look around",
    "describe the scene",
    "what is in front of me",
    "what's in front of me",
    "what can you see",
)

MARKET_PHRASES = (
    "stock",
    "stocks",
    "share market",
    "stock market",
    "market price",
    "market analysis",
    "trading",
    "trading setup",
    "trade setup",
    "intraday",
    "swing trade",
    "swing setup",
    "support and resistance",
    "position size",
    "risk reward",
    "ltp",
    "cmp",
    "price of",
    "quote",
    "watchlist",
    "trade journal",
    "journal trade",
    "nifty",
    "banknifty",
    "bank nifty",
    "sensex",
    "nse",
    "bse",
)

DEVICE_PHRASES = (
    "take a photo",
    "take photo",
    "take a pic",
    "take pic",
    "capture image",
    "take screenshot",
    "capture screenshot",
    "screen shot",
    "record video",
    "start recording",
    "show photo",
    "show photos",
    "list photo",
    "list photos",
    "show video",
    "show videos",
    "list video",
    "list videos",
    "show screenshot",
    "show screenshots",
    "list screenshot",
    "list screenshots",
    "open photo",
    "open photos",
    "open photo folder",
    "open video",
    "open videos",
    "open video folder",
    "open screenshot",
    "open screenshots",
    "open screenshot folder",
    "light on",
    "light off",
)

SYSTEM_PHRASES = (
    "go online",
    "go offline",
    "open chrome",
    "open notepad",
    "open calculator",
    "open calc",
    "open explorer",
    "open file explorer",
    "open settings",
    "open task manager",
    "open cmd",
    "open command prompt",
    "open powershell",
    "open control panel",
    "launch chrome",
    "launch notepad",
    "launch calculator",
    "launch explorer",
    "launch settings",
    "wifi",
    "volume",
    "bluetooth",
)

SEARCH_HINTS = (
    "news",
    "latest news",
    "current news",
    "today news",
    "latest update",
    "current update",
    "search",
    "look up",
    "find on internet",
    "find online",
)

MEMORY_HINTS = (
    "remember",
    "memory",
    "what did i ask",
    "what did i say",
    "recall",
    "history",
    "previous chat",
)

FILE_HINTS = (
    "save to file",
    "save output",
    "save this",
    "show outputs",
    "list outputs",
    "show saved files",
    "list saved files",
    "read latest output",
    "show latest output",
    "open latest output",
    "open outputs",
    "open output folder",
    "open saved files",
)

GENERAL_HINTS = (
    "tell me",
    "about",
    "explain",
    "write",
    "who is",
    "what is",
    "how does",
    "summarize",
)


def _contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def classify_intent(text):
    normalized = text.strip().lower()

    if not normalized:
        return "general"

    if _contains_any(normalized, VISION_PHRASES):
        return "vision"

    if _contains_any(normalized, MARKET_PHRASES):
        return "market"

    if _contains_any(normalized, DEVICE_PHRASES):
        return "device"

    if _contains_any(normalized, SYSTEM_PHRASES):
        return "system"

    if _contains_any(normalized, MEMORY_HINTS):
        return "memory"

    if _contains_any(normalized, FILE_HINTS):
        return "file"

    if _contains_any(normalized, SEARCH_HINTS):
        return "search"

    if _contains_any(normalized, GENERAL_HINTS):
        return "general"

    prompt = f"""
You are an intent classifier.

Classify the user request into EXACTLY ONE of these intents:
- vision
- market
- device
- system
- file
- search
- memory
- general

Rules:
- vision is only for camera/surroundings requests
- market is for Indian stock market analysis, trading help, watchlists, journaling, and risk sizing
- device is for hardware/app/device control
- system is for settings or mode switching
- file is for saved files, outputs, or reading/opening saved text files
- search is for internet/current-info requests
- memory is for recalling earlier conversation
- general is everything else
- Reply with exactly one word

User: {text}
Intent:
"""

    response = ""

    for token in ask_ai(prompt):
        response += token

    intent = response.strip().lower()
    valid_intents = ["vision", "market", "device", "system", "file", "search", "memory", "general"]

    for valid_intent in valid_intents:
        if valid_intent in intent:
            return valid_intent

    return "general"
