import re

from agent_clarifications import (
    ask_for_clarification as clarification_ask_for_clarification,
    ask_for_command_clarification as clarification_ask_for_command_clarification,
    ask_for_unknown_command_clarification as clarification_ask_for_unknown_command_clarification,
    get_ambiguous_intents as clarification_get_ambiguous_intents,
    get_command_clarification as clarification_get_command_clarification,
    handle_mode_switch as clarification_handle_mode_switch,
    is_affirmative as clarification_is_affirmative,
    is_negative as clarification_is_negative,
    looks_like_command as clarification_looks_like_command,
    looks_like_information_request as clarification_looks_like_information_request,
    match_intents as clarification_match_intents,
    normalize_natural_language as clarification_normalize_natural_language,
    resolve_clarification_choice as clarification_resolve_clarification_choice,
    resolve_command_choice as clarification_resolve_command_choice,
    should_use_planner as clarification_should_use_planner,
    spell_correct_text as clarification_spell_correct_text,
)
from agent_dispatch import finalize_output as dispatch_finalize_output, handle_intent as dispatch_handle_intent
from agent_pending import handle_pending_action as pending_handle_pending_action
from agent_request import (
    apply_strategy as request_apply_strategy,
    normalize_request as request_normalize_request,
    request_with_message as request_request_with_message,
)
from agent_manager import create_task, update_task
from agents.arduino_agent import handle as arduino_agent
from agents.ai_agent import handle as ai_agent
from agents.device_agent import handle as device_agent
from agents.file_agent import handle as file_agent
from agents.market_agent import handle as market_agent
from agents.search_agent import handle as search_agent
from agents.system_agent import handle as system_agent
from conversation_state import set_pending
from intent_classifier import classify_intent
from market_data import looks_like_market_request
from language_rules import DEVICE_KEYWORDS, NO_WORDS, YES_WORDS
from memory import get_learned_resolution
from vision_agent import describe_scene


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


def _normalize_request(input_data):
    return request_normalize_request(input_data)


def _request_with_message(request_context, message):
    return request_request_with_message(request_context, message)


def _apply_strategy(request_context):
    return request_apply_strategy(request_context)


def _handle_pending_action(request_context):
    return pending_handle_pending_action(
        request_context,
        resolve_command_choice=_resolve_command_choice,
        resolve_clarification_choice=_resolve_clarification_choice,
        request_with_message=_request_with_message,
        process_command=process_command,
        handle_intent=_handle_intent,
        is_affirmative=_is_affirmative,
        is_negative=_is_negative,
        file_agent=file_agent,
        stream_agent=_stream_agent,
    )


def _handle_mode_switch(text):
    return clarification_handle_mode_switch(text)


def _should_use_planner(text):
    return clarification_should_use_planner(text)


def _spell_correct_text(text):
    return clarification_spell_correct_text(text)


def _normalize_natural_language(text):
    return clarification_normalize_natural_language(text)


def _is_affirmative(text):
    return clarification_is_affirmative(text)


def _is_negative(text):
    return clarification_is_negative(text)


def _finalize_output(message, content, offer_save):
    yield from dispatch_finalize_output(message, content, offer_save, set_pending=set_pending)


def _get_command_clarification(text):
    return clarification_get_command_clarification(text)


def _match_intents(text):
    return clarification_match_intents(text)


def _get_ambiguous_intents(text):
    return clarification_get_ambiguous_intents(text)


def _looks_like_command(text):
    return clarification_looks_like_command(text)


def _looks_like_information_request(text):
    return clarification_looks_like_information_request(text)


def _resolve_clarification_choice(message, options):
    return clarification_resolve_clarification_choice(message, options)


def _resolve_command_choice(message, options):
    return clarification_resolve_command_choice(message, options)


def _ask_for_clarification(message, options):
    return clarification_ask_for_clarification(message, options)


def _ask_for_command_clarification(message, options):
    return clarification_ask_for_command_clarification(message, options)


def _ask_for_unknown_command_clarification(message):
    return clarification_ask_for_unknown_command_clarification(message)


def _handle_direct_save(message, request_context):
    text = message.lower()
    if "save" not in text or "and" in text:
        return None

    source_message = re.sub(r"\bsave\b", "", message, flags=re.IGNORECASE).strip()
    if not source_message:
        return ["Please tell me what you want me to save."]

    source_intent = classify_intent(source_message).strip().lower().split()[0]
    shared_request = _request_with_message(request_context, source_message)
    source_stream = search_agent(source_message) if source_intent == "search" else ai_agent(source_message, shared_request)

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


def _handle_intent(message, intent, request_context):
    return dispatch_handle_intent(
        message,
        intent,
        request_context,
        stream_agent=_stream_agent,
        arduino_agent=arduino_agent,
        describe_scene=describe_scene,
        market_agent=market_agent,
        system_agent=system_agent,
        file_agent=file_agent,
        search_agent=search_agent,
        device_agent=device_agent,
        ai_agent=ai_agent,
        finalize_output_fn=_finalize_output,
    )


def process_command(input_data):
    request_context = _normalize_request(input_data)
    strategy_result = _apply_strategy(request_context)
    if isinstance(strategy_result, list):
        yield from strategy_result
        return
    if isinstance(strategy_result, dict):
        request_context = strategy_result

    original_message = request_context["message"]
    normalized_message = _normalize_natural_language(original_message)
    corrected_message = _spell_correct_text(normalized_message)
    message = corrected_message if corrected_message else original_message
    text = message.lower().strip()
    request_context = _request_with_message(request_context, message)

    learned_resolution = get_learned_resolution(text)
    if learned_resolution and learned_resolution.get("command"):
        message = learned_resolution["command"]
        text = message.lower().strip()
        request_context = _request_with_message(request_context, message)

    pending_stream = _handle_pending_action(request_context)
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

    direct_save_stream = _handle_direct_save(message, request_context)
    if direct_save_stream is not None:
        yield from direct_save_stream
        return

    early_intent = classify_intent(message).strip().lower().split()[0]
    if early_intent == "arduino":
        yield from _handle_intent(message, "arduino", request_context)
        return

    if looks_like_market_request(text) and not any(word in text for word in (" and ", " then ", " after ")):
        yield from _handle_intent(message, "market", request_context)
        return

    if _should_use_planner(text):
        yield from _handle_planned_command(message)
        return

    if _looks_like_information_request(text) and not _match_intents(text):
        yield from _handle_intent(message, "general", request_context)
        return

    intent = early_intent
    if intent == "general" and looks_like_market_request(text):
        yield from _handle_intent(message, "market", request_context)
        return

    if intent == "general" and _looks_like_information_request(text):
        yield from _handle_intent(message, "general", request_context)
        return

    if intent == "general" and re.match(r"^(take|show|display|open|list|read|record|launch|capture)\b", text):
        fallback_options = [
            {"key": "search", "label": "search for information about it", "command": f"search {message}"},
            {"key": "normal", "label": "just answer it normally", "command": message},
        ]
        yield from _ask_for_command_clarification(message, fallback_options)
        return
    print("[Intent Detected]:", intent)
    yield from _handle_intent(message, intent, request_context)
