import cv2
from ai_router import ask_ai
from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")


def capture_image():

    for i in range(3):  # try camera 0,1,2
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()

            if ret:
                path = "captured.jpg"
                cv2.imwrite(path, frame)
                return path

    return None


def describe_scene():

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        yield "Camera not accessible."
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        yield "Failed to capture image."
        return

    results = model(frame)

    detected = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            name = model.names[cls]
            detected.append(name)

    if not detected:
        yield "I don't see anything clearly."
    else:
        unique = list(set(detected))
        yield "I see: " + ", ".join(unique)