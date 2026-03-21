import json

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi3"
REQUEST_TIMEOUT = 30


def ask_offline(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    yielded = False

    try:
        for line in response.iter_lines():
            if not line:
                continue

            data = json.loads(line.decode("utf-8"))

            if data.get("error"):
                raise RuntimeError(data["error"])

            token = data.get("response", "")
            if token:
                yielded = True
                yield token
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Ollama response: {exc}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama stream failed: {exc}") from exc

    if not yielded:
        raise RuntimeError("Ollama returned no content.")
