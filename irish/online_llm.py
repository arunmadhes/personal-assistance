import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Always load .env from the same folder as this script
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

PROVIDER = "groq"

PROVIDERS = {
    "openai": {
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
}


def ask_online(prompt):
    config = PROVIDERS.get(PROVIDER)

    if not config:
        raise RuntimeError(
            f"Unknown provider '{PROVIDER}'. Choose from: {list(PROVIDERS.keys())}"
        )

    api_key = os.getenv(config["api_key_env"])

    if not api_key:
        get_key_urls = {
            "groq": "https://console.groq.com",
            "gemini": "https://aistudio.google.com",
            "openai": "https://platform.openai.com/api-keys",
            "deepseek": "https://platform.deepseek.com",
        }
        raise RuntimeError(
            f"API key not found for '{PROVIDER}'. "
            f"Set {config['api_key_env']} in .env. "
            f"Get a key at: {get_key_urls.get(PROVIDER, '')}"
        )

    kwargs = {"api_key": api_key}
    if config["base_url"]:
        kwargs["base_url"] = config["base_url"]

    client = OpenAI(**kwargs)

    try:
        stream = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
    except Exception as exc:
        raise RuntimeError(f"{PROVIDER} request failed: {exc}") from exc

    yielded = False

    try:
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yielded = True
                yield token
    except Exception as exc:
        raise RuntimeError(f"{PROVIDER} stream failed: {exc}") from exc

    if not yielded:
        raise RuntimeError(f"{PROVIDER} returned no content.")
