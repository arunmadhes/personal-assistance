import time
from pathlib import Path
import subprocess

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PHOTOS_DIR = OUTPUT_DIR / "photos"
VIDEOS_DIR = OUTPUT_DIR / "videos"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"


def _ensure_media_dirs():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _open_camera():
    for index in range(3):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return None


def take_photo():
    _ensure_media_dirs()

    cap = _open_camera()
    if not cap:
        return "Camera not accessible."

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return "Failed to capture image."

    filename = PHOTOS_DIR / f"photo_{int(time.time())}.jpg"
    cv2.imwrite(str(filename), frame)

    return f"Photo saved as {filename}"


def record_video(duration=5):
    _ensure_media_dirs()

    cap = _open_camera()
    if not cap:
        return "Camera not accessible."

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 1 else 20.0

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    filename = VIDEOS_DIR / f"video_{int(time.time())}.avi"
    out = cv2.VideoWriter(str(filename), fourcc, fps, (width, height))

    start_time = time.time()

    while int(time.time() - start_time) < duration:
        ret, frame = cap.read()
        if not ret:
            break

        out.write(frame)

    cap.release()
    out.release()

    return f"Video saved as {filename}"


def take_screenshot():
    _ensure_media_dirs()

    filename = SCREENSHOTS_DIR / f"screenshot_{int(time.time())}.png"
    powershell_command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
        "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
        f"$bitmap.Save('{filename}', [System.Drawing.Imaging.ImageFormat]::Png); "
        "$graphics.Dispose(); "
        "$bitmap.Dispose()"
    )

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", powershell_command],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return f"I couldn't take a screenshot: {exc.stderr.strip() or exc}"

    return f"Screenshot saved as {filename}"
