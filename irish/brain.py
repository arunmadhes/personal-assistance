from ai_router import get_mode
from memory import get_recent_memory


FOLLOW_UP_MARKERS = {
    "continue",
    "go on",
    "what about that",
    "what about it",
    "tell me more",
    "more on that",
    "same thing",
}

SHORT_CLARIFY_MESSAGES = {
    "ok",
    "okay",
    "hmm",
    "huh",
    "help",
}


def decide_strategy(message, memory=None):
    text = str(message).strip()
    lowered = text.lower()
    memory = memory or []

    if not lowered:
        return "empty"

    if any(marker in lowered for marker in FOLLOW_UP_MARKERS):
        return "follow_up"

    if lowered in SHORT_CLARIFY_MESSAGES:
        return "clarify_short"

    if len(lowered.split()) <= 2 and memory and lowered in {"continue", "next", "and then", "what next"}:
        return "follow_up"

    return "normal"


def build_request_context(
    message,
    *,
    source="chat",
    tab_id=None,
    memory_limit=5,
    metadata=None,
    memory=None,
    mode=None,
):
    text = str(message).strip()
    shared_memory = list(memory) if memory is not None else get_recent_memory(memory_limit)
    strategy = decide_strategy(text, shared_memory)

    return {
        "message": text,
        "memory": shared_memory,
        "mode": mode or get_mode(),
        "source": source,
        "tab_id": tab_id,
        "strategy": strategy,
        "metadata": metadata or {},
    }


def agent_brain(request):
    if isinstance(request, dict):
        return build_request_context(
            request.get("message", ""),
            source=request.get("source", "chat"),
            tab_id=request.get("tab_id"),
            memory_limit=request.get("memory_limit", 5),
            metadata=request.get("metadata"),
            memory=request.get("memory"),
            mode=request.get("mode"),
        )

    return build_request_context(request)
