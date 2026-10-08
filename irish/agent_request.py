from ai_router import get_mode


def normalize_request(input_data):
    if isinstance(input_data, dict):
        memory = input_data.get("memory") if "memory" in input_data else None
        return {
            "message": str(input_data.get("message", "")).strip(),
            "memory": list(memory) if memory is not None else None,
            "mode": input_data.get("mode", get_mode()),
            "source": input_data.get("source", "chat"),
            "tab_id": input_data.get("tab_id"),
            "strategy": input_data.get("strategy", "normal"),
            "metadata": dict(input_data.get("metadata", {})),
        }

    return {
        "message": str(input_data).strip(),
        "memory": None,
        "mode": get_mode(),
        "source": "chat",
        "tab_id": None,
        "strategy": "normal",
        "metadata": {},
    }


def request_with_message(request_context, message):
    updated = dict(request_context)
    updated["message"] = message
    return updated


def apply_strategy(request_context):
    strategy = request_context.get("strategy", "normal")
    message = request_context["message"]
    memory = request_context.get("memory") or []

    if strategy == "empty":
        return ["Please tell me what you want me to do."]

    if strategy == "clarify_short":
        return [
            "I can help with chat, files, device controls, or market analysis.",
            "Tell me what you want in a bit more detail.",
        ]

    if strategy != "follow_up" or not memory:
        return None

    last_memory = memory[-1]
    last_user = last_memory.get("user", "").strip()
    last_assistant = last_memory.get("assistant", "").strip()

    if not last_user and not last_assistant:
        return None

    merged_message = (
        f"{message}\n\n"
        f"Follow-up context:\n"
        f"Previous user message: {last_user}\n"
        f"Previous assistant reply: {last_assistant}"
    ).strip()

    updated = request_with_message(request_context, merged_message)
    updated["metadata"] = dict(updated.get("metadata", {}))
    updated["metadata"]["follow_up"] = True
    return updated
