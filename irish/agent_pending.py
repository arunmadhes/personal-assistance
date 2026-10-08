import re

from ai_router import get_mode
from conversation_state import clear_pending, get_pending
from memory import add_memory, remember_resolution


def handle_pending_action(
    request_context,
    *,
    resolve_command_choice,
    resolve_clarification_choice,
    request_with_message,
    process_command,
    handle_intent,
    is_affirmative,
    is_negative,
    file_agent,
    stream_agent,
):
    message = request_context["message"]
    pending, data = get_pending()

    if pending == "clarify_command":
        choice = resolve_command_choice(message, data.get("options", []))
        if not choice:
            choices = " or ".join(
                f"{index}. {option['label']}" for index, option in enumerate(data.get("options", []), start=1)
            )
            return [f"Please tell me which one you want: {choices}."]

        clear_pending()
        original_message = data.get("message", message)
        resolved_command = choice["command"]
        if resolved_command.strip().lower() != original_message.strip().lower():
            remember_resolution(original_message, resolved_command, choice["label"])
        add_memory(
            original_message,
            f"Clarified as: {choice['label']} -> {resolved_command}",
            mode=get_mode(),
            intent="device",
            source="clarification",
        )
        return process_command(request_with_message(request_context, resolved_command))

    if pending == "clarify_intent":
        choice = resolve_clarification_choice(message, data.get("options", []))
        if not choice:
            options_text = ", ".join(data.get("options", []))
            return [f"Please reply with one of these options: {options_text}."]

        clear_pending()
        original_message = data.get("message", message)
        return handle_intent(original_message, choice, request_with_message(request_context, original_message))

    if pending == "confirm_save":
        reply = message.lower().strip()

        if is_affirmative(reply):
            clear_pending()
            content = data.get("content", "").strip()
            source_command = data.get("command", "output")

            if not content:
                return ["I do not have any output ready to save."]

            def save_pending_stream():
                yield "Saving result..."
                for token in file_agent(content, source_command):
                    yield token

            return stream_agent("file", source_command, save_pending_stream(), "Saving saved output...")

        if is_negative(reply):
            clear_pending()
            return ["Okay, I will not save it."]

        return ["Please say yes to save it or no to skip saving."]

    if pending != "record_video":
        return None

    match = re.search(r"(\d+)", message)

    if not match:
        return ["Please tell duration in seconds."]

    duration = int(match.group(1))
    clear_pending()

    from camera_utils import record_video

    def pending_stream():
        yield f"Recording for {duration} seconds..."
        yield record_video(duration)

    return stream_agent(
        "device",
        f"record video {duration}s",
        pending_stream(),
        f"Recording for {duration} seconds...",
    )
