import re
from difflib import get_close_matches

from ai_router import set_mode
from conversation_state import set_pending
from intent_classifier import (
    ARDUINO_PHRASES,
    DEVICE_PHRASES,
    FILE_HINTS,
    MARKET_PHRASES,
    MEMORY_HINTS,
    SEARCH_HINTS,
    SYSTEM_PHRASES,
    VISION_PHRASES,
)
from language_rules import (
    COMMAND_CLARIFICATIONS,
    COMMAND_REPLY_HINTS,
    COMMAND_STYLE_PREFIXES,
    COMMON_TYPO_MAP,
    INTENT_FRIENDLY_LABELS,
    INTENT_REPLY_HINTS,
    NATURAL_LANGUAGE_ALIASES,
    NO_WORDS,
    PLAN_KEYWORDS,
    YES_WORDS,
)


SPELLCHECK_PHRASES = (
    *ARDUINO_PHRASES,
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


def handle_mode_switch(text):
    if "go online" in text or text.strip() == "online":
        set_mode("online")
        return ["Switched to online mode."]

    if "go offline" in text or text.strip() == "offline":
        set_mode("offline")
        return ["Switched to offline mode."]

    return None


def should_use_planner(text):
    return any(word in text for word in PLAN_KEYWORDS)


def spell_correct_text(text):
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


def normalize_natural_language(text):
    normalized = text.strip()

    for pattern, replacement in NATURAL_LANGUAGE_ALIASES:
        updated = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        if updated != normalized:
            normalized = updated

    normalized = re.sub(r"\b(can you|could you|would you|please|for me)\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def is_affirmative(text):
    reply = text.lower().strip()
    return reply in YES_WORDS or reply.startswith("yes ") or "save it" in reply


def is_negative(text):
    reply = text.lower().strip()
    return reply in NO_WORDS or reply.startswith("no ")


def get_command_clarification(text):
    for item in COMMAND_CLARIFICATIONS:
        if any(trigger in text for trigger in item["triggers"]):
            return item["options"]
    return []


def match_intents(text):
    matches = []
    phrase_groups = {
        "arduino": ARDUINO_PHRASES,
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


def get_ambiguous_intents(text):
    matches = match_intents(text)
    return matches if len(matches) > 1 else []


def looks_like_command(text):
    return text.startswith(COMMAND_STYLE_PREFIXES)


def looks_like_information_request(text):
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


def resolve_clarification_choice(message, options):
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


def resolve_command_choice(message, options):
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


def ask_for_clarification(message, options):
    set_pending("clarify_intent", {"message": message, "options": options})
    options_text = " or ".join(
        f"{index}. {INTENT_FRIENDLY_LABELS.get(option, option)}"
        for index, option in enumerate(options, start=1)
    )
    return [
        "Iâ€™m not fully sure what you want me to do with that.",
        f"Did you mean {options_text}?",
        "You can reply with the number or just say it naturally.",
    ]


def ask_for_command_clarification(message, options):
    set_pending("clarify_command", {"message": message, "options": options})
    choices = " or ".join(
        f"{index}. {option['label']}" for index, option in enumerate(options, start=1)
    )
    return [
        "I want to make sure I do the right thing.",
        f"Did you mean {choices}?",
        "You can reply with the number or just say it naturally.",
    ]


def ask_for_unknown_command_clarification(message):
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
    return ask_for_command_clarification(message, options)
