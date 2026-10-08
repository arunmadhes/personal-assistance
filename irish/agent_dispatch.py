from memory import load_memory


def finalize_output(message, content, offer_save, *, set_pending):
    if offer_save and content.strip():
        set_pending("confirm_save", {
            "content": content.strip(),
            "command": message,
        })
        yield "\nDo you want me to save this output to a text file?"


def handle_intent(
    message,
    intent,
    request_context,
    *,
    stream_agent,
    arduino_agent,
    describe_scene,
    market_agent,
    system_agent,
    file_agent,
    search_agent,
    device_agent,
    ai_agent,
    finalize_output_fn,
):
    if intent == "arduino":
        def arduino_stream():
            result = ""
            for token in arduino_agent(message, request_context=request_context):
                result += token
                yield token
            yield from finalize_output_fn(message, result.strip(), offer_save=True)

        return stream_agent("arduino", message, arduino_stream(), "Generating Arduino code...")

    if intent == "vision":
        return stream_agent("vision", message, describe_scene(), "Looking...")

    if intent == "market":
        def market_stream():
            result = ""
            for token in market_agent(message, request_context=request_context):
                result += token
                yield token
            yield from finalize_output_fn(message, result.strip(), offer_save=False)

        return stream_agent("market", message, market_stream(), "Reviewing the market setup...")

    if intent == "memory":
        def memory_stream():
            memory = request_context.get("memory") or load_memory()
            if memory:
                yield memory[-1]["user"]
            else:
                yield "I don't have any memory yet."

        return stream_agent("memory", message, memory_stream(), "Checking memory...")

    if intent == "system":
        return stream_agent("system", message, system_agent(message), "Executing system command...")

    if intent == "file":
        return stream_agent("file", message, file_agent(command=message), "Handling file command...")

    if intent == "search":
        def search_stream():
            result = ""
            for token in search_agent(message):
                result += token
                yield token
            yield from finalize_output_fn(message, result.strip(), offer_save=True)

        return stream_agent("search", message, search_stream(), "Searching...")

    if intent == "device":
        return stream_agent("device", message, device_agent(message), "Executing device command...")

    def ai_stream():
        result = ""
        for token in ai_agent(message, request_context=request_context):
            result += token
            yield token
        yield from finalize_output_fn(message, result.strip(), offer_save=True)

    return stream_agent("ai", message, ai_stream(), "Thinking...")
