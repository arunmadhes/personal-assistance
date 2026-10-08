import re
from pathlib import Path

from camera_utils import record_video, take_photo, take_screenshot
from conversation_state import set_pending
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PHOTOS_DIR = OUTPUT_DIR / "photos"
VIDEOS_DIR = OUTPUT_DIR / "videos"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"


def _list_media_files(folder, label):
    if not folder.exists():
        return f"There are no saved {label} yet."

    files = sorted(folder.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        return f"There are no saved {label} yet."

    lines = [f"Recent {label}:"]
    for path in files[:5]:
        lines.append(f"- {path.name}")
    return "\n".join(lines)


def _open_folder(folder, label):
    folder.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(str(folder))
        return f"Opened {label} folder: {folder}"
    except OSError as exc:
        return f"I couldn't open the {label} folder: {exc}"


def handle(message):
    text = message.lower()

    if "light on" in text:
        yield "Turning on light (simulated)."
        return

    if "light off" in text:
        yield "Turning off light (simulated)."
        return

    if "take photo" in text or "take pic" in text or "capture image" in text:
        yield "Capturing photo..."
        yield take_photo()
        return

    if "take screenshot" in text or "capture screenshot" in text or "screen shot" in text:
        yield "Capturing screenshot..."
        yield take_screenshot()
        return

    if "show photo" in text or "show photos" in text or "list photo" in text or "list photos" in text:
        yield _list_media_files(PHOTOS_DIR, "photos")
        return

    if "show video" in text or "show videos" in text or "list video" in text or "list videos" in text:
        yield _list_media_files(VIDEOS_DIR, "videos")
        return

    if "show screenshot" in text or "show screenshots" in text or "list screenshot" in text or "list screenshots" in text:
        yield _list_media_files(SCREENSHOTS_DIR, "screenshots")
        return

    if "open photo" in text or "open photos" in text or "open photo folder" in text:
        yield _open_folder(PHOTOS_DIR, "photos")
        return

    if "open video" in text or "open videos" in text or "open video folder" in text:
        yield _open_folder(VIDEOS_DIR, "videos")
        return

    if "open screenshot" in text or "open screenshots" in text or "open screenshot folder" in text:
        yield _open_folder(SCREENSHOTS_DIR, "screenshots")
        return

    if "record video" in text or "start recording" in text:
        match = re.search(r"(\d+)", text)

        if match:
            duration = int(match.group(1))
            yield f"Recording for {duration} seconds..."
            yield record_video(duration)
        else:
            set_pending("record_video")
            yield "How many seconds should I record?"
        return

    yield "Device command not recognized."
