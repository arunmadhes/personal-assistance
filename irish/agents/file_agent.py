import os
import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"

STOP_WORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "for",
    "of",
    "about",
    "file",
    "text",
    "txt",
    "save",
    "it",
    "this",
    "that",
    "result",
    "output",
}


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _list_output_files():
    _ensure_output_dir()
    return sorted(
        OUTPUT_DIR.glob("*.txt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def generate_filename(command):
    text = command.lower().strip()
    words = re.findall(r"[a-z0-9]+", text)
    meaningful_words = [word for word in words if word not in STOP_WORDS]

    name_parts = meaningful_words[:6]
    base_name = "_".join(name_parts).strip("_")

    if not base_name:
        base_name = "output"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.txt"


def save_content(content, command):
    _ensure_output_dir()

    filename = generate_filename(command)
    file_path = OUTPUT_DIR / filename

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

    return file_path


def _read_latest_output():
    files = _list_output_files()
    if not files:
        return "There are no saved output files yet."

    latest_file = files[0]
    try:
        content = latest_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return f"I couldn't read the latest output file: {exc}"

    if not content:
        return f"The latest saved file is empty: {latest_file.name}"

    return f"Latest file: {latest_file.name}\n\n{content}"


def _list_recent_outputs(limit=5):
    files = _list_output_files()
    if not files:
        return "There are no saved output files yet."

    lines = ["Recent saved files:"]
    for path in files[:limit]:
        lines.append(f"- {path.name}")
    return "\n".join(lines)


def _open_outputs_folder():
    _ensure_output_dir()
    try:
        os.startfile(str(OUTPUT_DIR))
        return f"Opened outputs folder: {OUTPUT_DIR}"
    except OSError as exc:
        return f"I couldn't open the outputs folder: {exc}"


def handle(content=None, command=""):
    text = (command or "").lower().strip()

    if "open outputs" in text or "open output folder" in text or "open saved files" in text:
        yield _open_outputs_folder()
        return

    if "list outputs" in text or "show outputs" in text or "show saved files" in text or "list saved files" in text:
        yield _list_recent_outputs()
        return

    if "read latest output" in text or "open latest output" in text or "show latest output" in text:
        yield _read_latest_output()
        return

    if content is None:
        yield (
            "File command not recognized. Try save output, list outputs, show saved files, "
            "read latest output, or open outputs."
        )
        return

    file_path = save_content(content, command)
    yield f"Saved to {file_path}"
