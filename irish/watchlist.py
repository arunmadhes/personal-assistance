import json
from datetime import datetime
from pathlib import Path

from market_data import normalize_symbol


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_watchlist():
    _ensure_data_dir()
    if not WATCHLIST_FILE.exists():
        return []

    try:
        data = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = normalize_symbol(item.get("symbol", ""))
        if not symbol:
            continue
        normalized.append({
            "symbol": symbol,
            "notes": str(item.get("notes", "")).strip(),
            "added_at": item.get("added_at") or datetime.now().isoformat(timespec="seconds"),
        })
    return normalized


def save_watchlist(items):
    _ensure_data_dir()
    WATCHLIST_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=True), encoding="utf-8")


def add_to_watchlist(symbol, notes=""):
    normalized_symbol = normalize_symbol(symbol)
    if not normalized_symbol:
        return "Please tell me which NSE or BSE symbol you want to add."

    items = load_watchlist()
    for item in items:
        if item["symbol"] == normalized_symbol:
            return f"{normalized_symbol} is already in your watchlist."

    items.append({
        "symbol": normalized_symbol,
        "notes": str(notes).strip(),
        "added_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_watchlist(items)
    return f"Added {normalized_symbol} to your watchlist."


def remove_from_watchlist(symbol):
    normalized_symbol = normalize_symbol(symbol)
    if not normalized_symbol:
        return "Please tell me which symbol you want to remove."

    items = load_watchlist()
    filtered = [item for item in items if item["symbol"] != normalized_symbol]

    if len(filtered) == len(items):
        return f"{normalized_symbol} is not in your watchlist."

    save_watchlist(filtered)
    return f"Removed {normalized_symbol} from your watchlist."


def summarize_watchlist():
    items = load_watchlist()
    if not items:
        return "Your watchlist is empty right now."

    lines = ["Indian market watchlist:"]
    for item in items[:15]:
        suffix = f" - {item['notes']}" if item["notes"] else ""
        lines.append(f"- {item['symbol']}{suffix}")
    return "\n".join(lines)
