"""Pluggable LLM layer.

Priority chain (Business decision): Gemini -> OpenRouter -> Ollama -> template.
Every provider is wrapped so a missing key / dead server / bad response simply
falls through to the next. `generate()` never raises; callers inspect
`.provider == "none"` to build a deterministic template answer instead.
"""
from dataclasses import dataclass

import requests

from ..config import settings

_probe_cache: dict[str, bool] = {}


@dataclass
class LLMResult:
    text: str
    provider: str  # "gemini" | "openrouter" | "ollama" | "none"


# --------------------------------------------------------------------------- #
def _try_gemini(prompt: str, system: str | None) -> str | None:
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        contents = f"{system}\n\n{prompt}" if system else prompt
        resp = client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=contents
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:  # noqa: BLE001 — provider is best-effort
        print(f"[llm] gemini failed: {e}")
        return None


def _try_openrouter(prompt: str, system: str | None) -> str | None:
    if not settings.OPENROUTER_API_KEY:
        return None
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            json={"model": settings.OPENROUTER_MODEL, "messages": messages},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip() or None
    except Exception as e:  # noqa: BLE001
        print(f"[llm] openrouter failed: {e}")
        return None


def _ollama_up() -> bool:
    if "ollama" in _probe_cache:
        return _probe_cache["ollama"]
    try:
        r = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=1.5)
        up = r.status_code == 200
    except Exception:  # noqa: BLE001
        up = False
    _probe_cache["ollama"] = up
    return up


def _try_ollama(prompt: str, system: str | None) -> str | None:
    if not _ollama_up():
        return None
    try:
        full = f"{system}\n\n{prompt}" if system else prompt
        r = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": full, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip() or None
    except Exception as e:  # noqa: BLE001
        print(f"[llm] ollama failed: {e}")
        return None


# --------------------------------------------------------------------------- #
def generate(prompt: str, system: str | None = None) -> LLMResult:
    """Run the fallback chain. Never raises."""
    for name, fn in (
        ("gemini", _try_gemini),
        ("openrouter", _try_openrouter),
        ("ollama", _try_ollama),
    ):
        text = fn(prompt, system)
        if text:
            return LLMResult(text=text, provider=name)
    return LLMResult(text="", provider="none")


def active_provider() -> str:
    """Report which provider would be used (for the UI status badge)."""
    if settings.GEMINI_API_KEY:
        return "gemini"
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    if _ollama_up():
        return "ollama"
    return "template"
