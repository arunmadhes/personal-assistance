from offline_llm import ask_offline
from online_llm import ask_online

# Modes: "offline" or "online"
_current_mode = "offline"


def set_mode(mode: str):
    """Switch between 'offline' and 'online' mode."""
    global _current_mode

    if mode not in ("offline", "online"):
        raise ValueError(f"Invalid mode '{mode}'. Use 'offline' or 'online'.")

    _current_mode = mode
    print(f"[AI Router] Mode set to: {_current_mode}")


def get_mode() -> str:
    return _current_mode


def _provider_for_mode(mode):
    return ask_online if mode == "online" else ask_offline


def _fallback_mode(mode):
    return "offline" if mode == "online" else "online"


def _stream_provider(mode, prompt):
    provider = _provider_for_mode(mode)
    yielded = False

    for token in provider(prompt):
        yielded = True
        yield token

    if not yielded:
        raise RuntimeError(f"{mode} provider returned no output.")


def ask_ai(prompt):
    """
    Route the prompt to the correct LLM based on current mode.
    Falls back to the alternate mode if the selected provider fails
    before producing any output.
    """

    primary_mode = _current_mode
    secondary_mode = _fallback_mode(primary_mode)

    try:
        yield from _stream_provider(primary_mode, prompt)
        return
    except Exception as primary_error:
        fallback_notice = (
            f"[Irish] {primary_mode.capitalize()} mode failed, "
            f"trying {secondary_mode} mode.\n"
        )
        yield fallback_notice

        try:
            yield from _stream_provider(secondary_mode, prompt)
            return
        except Exception as secondary_error:
            yield (
                f"[Irish] Both AI modes failed.\n"
                f"Primary error: {primary_error}\n"
                f"Fallback error: {secondary_error}"
            )
