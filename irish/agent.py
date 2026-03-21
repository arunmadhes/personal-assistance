import re
from difflib import get_close_matches

from agent_manager import create_task, update_task
from agents.ai_agent import handle as ai_agent
from agents.device_agent import handle as device_agent
from agents.file_agent import handle as file_agent
from agents.market_agent import handle as market_agent
from agents.search_agent import handle as search_agent
from agents.system_agent import handle as system_agent
from ai_router import get_mode, set_mode
from conversation_state import clear_pending, get_pending, set_pending
from intent_classifier import (
    DEVICE_PHRASES,
    FILE_HINTS,
    MARKET_PHRASES,
    MEMORY_HINTS,
    SEARCH_HINTS,
    SYSTEM_PHRASES,
    VISION_PHRASES,
    classify_intent,
)
from market_data import looks_like_market_request
from language_rules import (
    COMMAND_CLARIFICATIONS,
    COMMAND_REPLY_HINTS,
    COMMAND_STYLE_PREFIXES,
    COMMON_TYPO_MAP,
    DEVICE_KEYWORDS,
    INTENT_FRIENDLY_LABELS,
    INTENT_REPLY_HINTS,
    NATURAL_LANGUAGE_ALIASES,
    NO_WORDS,
    PLAN_KEYWORDS,
    YES_WORDS,
)
from memory import add_memory, get_learned_resolution, load_memory, remember_resolution
from vision_agent import describe_scene

SPELLCHECK_PHRASES = (
    *VISION_PHRASES,
    *MARKET_PHRASES,
    *DEVICE_PHRASES,
    *SYSTEM_PHRASES,
    *FILE_HINTS,
    *SEARCH_HINTS,
    *MEMORY_HINTS,
    *PLAN_KEYWORDS,
    *YES_WORDS,
    *NO_WORDS,
    *COMMAND_STYLE_PREFIXES,
)

SPELLCHECK_VOCAB = {
    token
    for phrase in SPELLCHECK_PHRASES
    for token in re.findall(r"[a-z]+", phrase.lower())
    if len(token) >= 3
}


def _stream_agent(agent_type, task_message, stream, start_message, task_id=None):
    task_id = task_id or create_task(agent_type, task_message)
    yield f"[Task {task_id}] {start_message}"
    update_task(task_id, "running")
    result_parts = []

    try:
        for token in stream:
            result_parts.append(token)
            yield token
        update_task(task_id, "completed", result="".join(result_parts).strip())
        yield f"\n[Task {task_id}] Completed"
    except Exception as exc:
        update_task(task_id, "failed", result="".join(result_parts).strip())
        yield f"\n[Task {task_id}] Failed: {exc}"


def _handle_pending_action(message):
    pending, data = get_pending()

    if pending == "clarify_command":
        choice = _resolve_command_choice(message, data.get("options", []))
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
        return process_command(resolved_command)

    if pending == "clarify_intent":
        choice = _resolve_clarification_choice(message, data.get("options", []))
        if not choice:
            options_text = ", ".join(data.get("options", []))
            return [f"Please reply with one of these options: {options_text}."]

        clear_pending()
        original_message = data.get("message", message)
        return _handle_intent(original_message, choice)

    if pending == "confirm_save":
        reply = message.lower().strip()

        if _is_affirmative(reply):
            clear_pending()
            content = data.get("content", "").strip()
            source_command = data.get("command", "output")

            if not content:
                return ["I do not have any output ready to save."]

            def save_pending_stream():
                yield "Saving result..."
                for token in file_agent(content, source_command):
                    yield token

            return _stream_agent("file", source_command, save_pending_stream(), "Saving saved output...")

        if _is_negative(reply):
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

    return _stream_agent(
        "device",
        f"record video {duration}s",
        pending_stream(),
        f"Recording for {duration} seconds...",
    )


def _handle_mode_switch(text):
    if "go online" in text or text.strip() == "online":
        set_mode("online")
        return ["Switched to online mode."]

    if "go offline" in text or text.strip() == "offline":
        set_mode("offline")
        return ["Switched to offline mode."]

    return None


def _should_use_planner(text):
    return any(word in text for word in PLAN_KEYWORDS)


def _spell_correct_text(text):
    def replace_token(match):
        token = match.group(0)
        if len(token) < 4:
            return token

        if token.lower() in COMMON_TYPO_MAP:
            return COMMON_TYPO_MAP[token.lower()]

        matches = get_close_matches(token.lower(), SPELLCHECK_VOCAB, n=1, cutoff=0.8)
        if not matches:
            return token

        corrected = matches[0]
        if corrected == token.lower():
            return token

        return corrected

    return re.sub(r"[A-Za-z]+", replace_token, text)


def _normalize_natural_language(text):
    normalized = text.strip()

    for pattern, replacement in NATURAL_LANGUAGE_ALIASES:
        updated = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        if updated != normalized:
            normalized = updated

    normalized = re.sub(r"\b(can you|could you|would you|please|for me)\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_affirmative(text):
    reply = text.lower().strip()
    return reply in YES_WORDS or reply.startswith("yes ") or "save it" in reply


def _is_negative(text):
    reply = text.lower().strip()
    return reply in NO_WORDS or reply.startswith("no ")


def _finalize_output(message, content, offer_save):
    if offer_save and content.strip():
        set_pending("confirm_save", {
            "content": content.strip(),
            "command": message,
        })
        yield "\nDo you want me to save this output to a text file?"


def _get_command_clarification(text):
    for item in COMMAND_CLARIFICATIONS:
        if any(trigger in text for trigger in item["triggers"]):
            return item["options"]
    return []


def _match_intents(text):
    matches = []
    phrase_groups = {
        "vision": VISION_PHRASES,
        "market": MARKET_PHRASES,
        "device": DEVICE_PHRASES,
        "system": SYSTEM_PHRASES,
        "file": FILE_HINTS,
        "search": SEARCH_HINTS,
        "memory": MEMORY_HINTS,
    }

    for intent, phrases in phrase_groups.items():
        if any(phrase in text for phrase in phrases):
            matches.append(intent)

    return matches


def _get_ambiguous_intents(text):
    matches = _match_intents(text)
    return matches if len(matches) > 1 else []


def _looks_like_command(text):
    return text.startswith(COMMAND_STYLE_PREFIXES)


def _looks_like_information_request(text):
    informational_markers = (
        " about ",
        " in ",
        " on ",
        " of ",
        " for ",
        " with ",
        " from ",
        " why ",
        " how ",
        " what ",
        " who ",
        "when ",
        "where ",
    )

    lowered = f" {text.strip().lower()} "

    if re.match(r"^\s*list\s+\d+", text.lower()):
        return True

    if re.match(r"^\s*list\s+[a-zA-Z].+", text.lower()):
        return True

    if re.match(r"^\s*list\s+\w+\s+\w+", text.lower()):
        return True

    if any(marker in lowered for marker in informational_markers):
        return True

    words = re.findall(r"[a-zA-Z]+", text)
    return len(words) >= 4


def _resolve_clarification_choice(message, options):
    text = message.lower().strip()

    if text in options:
        return text

    for index, option in enumerate(options, start=1):
        if text == str(index):
            return option
        if option in text:
            return option
        for hint in INTENT_REPLY_HINTS.get(option, ()):
            if hint in text:
                return option

    return None


def _resolve_command_choice(message, options):
    text = message.lower().strip()

    for index, option in enumerate(options, start=1):
        if text == str(index):
            return option
        if option["key"] == text:
            return option
        if option["key"] in text or option["label"] in text:
            return option
        for hint in COMMAND_REPLY_HINTS.get(option["key"], ()):
            if hint in text:
                return option

    return None


def _ask_for_clarification(message, options):
    set_pending("clarify_intent", {"message": message, "options": options})
    options_text = " or ".join(
        f"{index}. {INTENT_FRIENDLY_LABELS.get(option, option)}"
        for index, option in enumerate(options, start=1)
    )
    return [
        "I’m not fully sure what you want me to do with that.",
        f"Did you mean {options_text}?",
        "You can reply with the number or just say it naturally.",
    ]


def _ask_for_command_clarification(message, options):
    set_pending("clarify_command", {"message": message, "options": options})
    choices = " or ".join(
        f"{index}. {option['label']}" for index, option in enumerate(options, start=1)
    )
    return [
        "I want to make sure I do the right thing.",
        f"Did you mean {choices}?",
        "You can reply with the number or just say it naturally.",
    ]


def _ask_for_unknown_command_clarification(message):
    options = [
        {
            "key": "photo",
            "label": "take or show a camera photo",
            "command": "take photo",
        },
        {
            "key": "screenshot",
            "label": "take a screenshot",
            "command": "take screenshot",
        },
        {
            "key": "saved_files",
            "label": "open or read a saved file",
            "command": "list outputs",
        },
        {
            "key": "search",
            "label": "search for information about it",
            "command": f"search {message}",
        },
        {
            "key": "normal",
            "label": "just answer it normally",
            "command": message,
        },
    ]
    return _ask_for_command_clarification(message, options)


def _handle_direct_save(message):
    text = message.lower()
    if "save" not in text or "and" in text:
        return None

    source_message = re.sub(r"\bsave\b", "", message, flags=re.IGNORECASE).strip()
    if not source_message:
        return ["Please tell me what you want me to save."]

    source_intent = classify_intent(source_message).strip().lower().split()[0]
    source_stream = search_agent(source_message) if source_intent == "search" else ai_agent(source_message)

    def save_stream():
        result = ""
        for token in source_stream:
            result += token
            yield token

        yield "\nSaving result..."
        for token in file_agent(result.strip(), message):
            yield token

    return _stream_agent("file", message, save_stream(), "Preparing content...")


def _handle_planned_command(message):
    from planner import create_plan
    from planner_executor import execute_step
    from agent_manager import add_context_entry

    task_id = create_task("plan", message)

    def planned_stream():
        yield "Creating plan..."
        add_context_entry(task_id, "coordinator", f"Goal received: {message}", kind="goal")

        steps = create_plan(message)
        if not steps:
            yield "I could not create a plan for that request."
            return

        context_parts = []

        for index, step in enumerate(steps, 1):
            yield f"\nStep {index}: {step}"
            yield " Executing..."

            context = "\n".join(part for part in context_parts if part).strip()
            result = execute_step(step, context, message, task_id=task_id).strip()

            if result:
                context_parts.append(result)
                yield result
            else:
                yield "No result returned."

        final_output = context_parts[-1] if context_parts else ""
        if final_output:
            yield "\nTask completed."

        wants_save = "save" not in message.lower() and "store" not in message.lower()
        if final_output and wants_save:
            set_pending("confirm_save", {
                "content": final_output,
                "command": message,
            })
            yield "\nDo you want me to save this output to a text file?"

    return _stream_agent("plan", message, planned_stream(), "Planning...", task_id=task_id)


def _handle_intent(message, intent):
    if intent == "vision":
        return _stream_agent("vision", message, describe_scene(), "Looking...")

    if intent == "market":
        def market_stream():
            result = ""
            for token in market_agent(message):
                result += token
                yield token
            yield from _finalize_output(message, result.strip(), offer_save=False)

        return _stream_agent("market", message, market_stream(), "Reviewing the market setup...")

    if intent == "memory":
        def memory_stream():
            memory = load_memory()
            if memory:
                yield memory[-1]["user"]
            else:
                yield "I don't have any memory yet."

        return _stream_agent("memory", message, memory_stream(), "Checking memory...")

    if intent == "system":
        return _stream_agent("system", message, system_agent(message), "Executing system command...")

    if intent == "file":
        return _stream_agent("file", message, file_agent(command=message), "Handling file command...")

    if intent == "search":
        def search_stream():
            result = ""
            for token in search_agent(message):
                result += token
                yield token
            yield from _finalize_output(message, result.strip(), offer_save=True)

        return _stream_agent("search", message, search_stream(), "Searching...")

    if intent == "device":
        return _stream_agent("device", message, device_agent(message), "Executing device command...")

    def ai_stream():
        result = ""
        for token in ai_agent(message):
            result += token
            yield token
        yield from _finalize_output(message, result.strip(), offer_save=True)

    return _stream_agent("ai", message, ai_stream(), "Thinking...")


def process_command(message):
    original_message = message.strip()
    normalized_message = _normalize_natural_language(original_message)
    corrected_message = _spell_correct_text(normalized_message)
    message = corrected_message if corrected_message else original_message
    text = message.lower().strip()

    learned_resolution = get_learned_resolution(text)
    if learned_resolution and learned_resolution.get("command"):
        message = learned_resolution["command"]
        text = message.lower().strip()

    pending_stream = _handle_pending_action(message)
    if pending_stream is not None:
        yield from pending_stream
        return

    if text in YES_WORDS or text in NO_WORDS:
        yield "There is no pending action right now."
        return

    mode_stream = _handle_mode_switch(text)
    if mode_stream is not None:
        yield from mode_stream
        return

    command_options = _get_command_clarification(text)
    if command_options:
        yield from _ask_for_command_clarification(message, command_options)
        return

    ambiguous_intents = _get_ambiguous_intents(text)
    if ambiguous_intents:
        yield from _ask_for_clarification(message, ambiguous_intents)
        return

    if _looks_like_command(text) and not _match_intents(text) and not _looks_like_information_request(text):
        yield from _ask_for_unknown_command_clarification(message)
        return

    if any(keyword in text for keyword in DEVICE_KEYWORDS):
        yield from _stream_agent("device", message, device_agent(message), "Executing device command...")
        return

    direct_save_stream = _handle_direct_save(message)
    if direct_save_stream is not None:
        yield from direct_save_stream
        return

    if looks_like_market_request(text) and not any(word in text for word in (" and ", " then ", " after ")):
        yield from _handle_intent(message, "market")
        return

    if _should_use_planner(text):
        yield from _handle_planned_command(message)
        return

    intent = classify_intent(message).strip().lower().split()[0]
    if intent == "general" and looks_like_market_request(text):
        yield from _handle_intent(message, "market")
        return

    if intent == "general" and _looks_like_information_request(text):
        yield from _handle_intent(message, "general")
        return

    if intent == "general" and re.match(r"^(take|show|display|open|list|read|record|launch|capture)\b", text):
        fallback_options = [
            {"key": "search", "label": "search for information about it", "command": f"search {message}"},
            {"key": "normal", "label": "just answer it normally", "command": message},
        ]
        yield from _ask_for_command_clarification(message, fallback_options)
        return
    print("[Intent Detected]:", intent)
    yield from _handle_intent(message, intent)
