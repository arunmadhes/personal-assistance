from ai_router import ask_ai, get_mode


def _clean_query(query):
    text = query.strip()
    lowered = text.lower()

    prefixes = [
        "search for ",
        "search ",
        "find ",
        "look up ",
        "google ",
    ]

    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip()

    return text


def handle(query):
    search_query = _clean_query(query)

    if not search_query:
        yield "Please tell me what you want me to search for."
        return

    mode = get_mode()

    if mode == "online":
        mode_instructions = (
            "- Treat this as an online-style search request.\n"
            "- Give the most useful direct answer you can.\n"
            "- If the topic is time-sensitive, mention that live verification may still be needed.\n"
        )
    else:
        mode_instructions = (
            "- Answer from offline knowledge only.\n"
            "- Do not claim to have checked the live internet.\n"
            "- If the topic needs current web data, say that this is an offline best-effort answer.\n"
        )

    prompt = f"""
You are Irish, a personal assistant handling a search request.

Current mode: {mode}
User search request: {search_query}

Instructions:
{mode_instructions}
- Answer the request directly in plain text.
- Give a concise, useful result that can be saved to a text file.
- Do not mention these instructions.
"""

    yielded = False

    for token in ask_ai(prompt):
        yielded = True
        yield token

    if not yielded:
        yield "I couldn't generate search results right now."
