import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MEMORY_FILE = DATA_DIR / "memory_store.json"
LEGACY_MEMORY_FILE = PROJECT_ROOT / "memory_store.json"
RESOLUTION_FILE = DATA_DIR / "learned_resolutions.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_memory():
    _ensure_data_dir()

    memory_path = MEMORY_FILE if MEMORY_FILE.exists() else LEGACY_MEMORY_FILE

    if not memory_path.exists():
        return []

    try:
        with open(memory_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue

        user = str(item.get("user", "")).strip()
        assistant = str(item.get("assistant", "")).strip()
        if not user and not assistant:
            continue

        normalized.append({
            "user": user,
            "assistant": assistant,
            "timestamp": item.get("timestamp") or datetime.now().isoformat(timespec="seconds"),
            "mode": item.get("mode", "unknown"),
            "intent": item.get("intent", "general"),
            "source": item.get("source", "chat"),
        })

    return normalized


def save_memory(data):
    _ensure_data_dir()
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=True)


def add_memory(user, assistant, mode="unknown", intent="general", source="chat"):
    user = str(user).strip()
    assistant = str(assistant).strip()

    if len(user) < 3 or not assistant:
        return

    memory = load_memory()
    memory.append({
        "user": user,
        "assistant": assistant,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "intent": intent,
        "source": source,
    })
    save_memory(memory)


def get_recent_memory(limit=5):
    memory = load_memory()
    return memory[-limit:]


def load_learned_resolutions():
    _ensure_data_dir()

    if not RESOLUTION_FILE.exists():
        return {}

    try:
        with open(RESOLUTION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def save_learned_resolutions(data):
    _ensure_data_dir()
    with open(RESOLUTION_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=True)


def get_learned_resolution(phrase):
    key = str(phrase).strip().lower()
    if not key:
        return None

    resolutions = load_learned_resolutions()
    item = resolutions.get(key)
    return item if isinstance(item, dict) else None


def remember_resolution(phrase, resolved_command, label):
    key = str(phrase).strip().lower()
    if not key:
        return

    resolutions = load_learned_resolutions()
    resolutions[key] = {
        "command": str(resolved_command).strip(),
        "label": str(label).strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_learned_resolutions(resolutions)
