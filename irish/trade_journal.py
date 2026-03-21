import json
from datetime import datetime
from pathlib import Path

from market_data import normalize_symbol


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
JOURNAL_FILE = DATA_DIR / "trade_journal.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_journal():
    _ensure_data_dir()
    if not JOURNAL_FILE.exists():
        return []

    try:
        data = json.loads(JOURNAL_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def save_journal(entries):
    _ensure_data_dir()
    JOURNAL_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=True), encoding="utf-8")


def add_journal_entry(symbol, thesis, details=None):
    normalized_symbol = normalize_symbol(symbol)
    if not normalized_symbol:
        return "Please include the symbol when you want me to journal a trade."

    entries = load_journal()
    entry = {
        "symbol": normalized_symbol,
        "thesis": str(thesis).strip(),
        "details": details or {},
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    entries.append(entry)
    save_journal(entries)
    return f"Saved a journal entry for {normalized_symbol}."


def summarize_recent_journal(limit=5):
    entries = load_journal()
    if not entries:
        return "Your trade journal is empty right now."

    lines = ["Recent trade journal entries:"]
    for entry in entries[-limit:][::-1]:
        thesis = str(entry.get("thesis", "")).strip() or "No thesis recorded."
        lines.append(f"- {entry.get('symbol', 'UNKNOWN')}: {thesis}")
    return "\n".join(lines)
