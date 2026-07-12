"""Pluggable LLM layer.

Priority chain (Business decision): Gemini -> OpenRouter -> Ollama -> template.
Every provider is wrapped so a missing key / dead server / bad response simply
falls through to the next. `generate()` never raises; callers inspect
`.provider == "none"` to build a deterministic template answer instead.
"""
import concurrent.futures
import time
from dataclasses import dataclass

import requests

from ..config import settings

_probe_cache: dict[str, bool] = {}
_last_provider: str | None = None      # last provider that actually produced text
_gemini_cooldown_until: float = 0.0    # skip Gemini until this time (rate-limit backoff)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
GEMINI_TIMEOUT = 8                     # seconds — cap so a slow 429-retry can't hang the demo


@dataclass
class LLMResult:
    text: str
    provider: str  # "gemini" | "openrouter" | "ollama" | "none"


def _gemini_ready() -> bool:
    return bool(settings.GEMINI_API_KEY) and time.time() >= _gemini_cooldown_until


# --------------------------------------------------------------------------- #
def _gemini_call(prompt: str, system: str | None) -> str | None:
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    contents = f"{system}\n\n{prompt}" if system else prompt
    resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=contents)
    return (resp.text or "").strip() or None


def _try_gemini(prompt: str, system: str | None) -> str | None:
    global _gemini_cooldown_until
    if not _gemini_ready():
        return None
    try:
        # Hard timeout so Gemini's internal 429 back-off retries can't hang a request.
        return _executor.submit(_gemini_call, prompt, system).result(timeout=GEMINI_TIMEOUT)
    except concurrent.futures.TimeoutError:
        _gemini_cooldown_until = time.time() + 300
        print("[llm] gemini slow/timed out — backing off 5 min, using next provider")
        return None
    except Exception as e:  # noqa: BLE001 — provider is best-effort
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper() or "quota" in msg.lower():
            _gemini_cooldown_until = time.time() + 300  # rate-limited: back off 5 min
            print("[llm] gemini rate-limited (429) — backing off 5 min, using next provider")
        else:
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
    global _last_provider
    for name, fn in (
        ("gemini", _try_gemini),
        ("openrouter", _try_openrouter),
        ("ollama", _try_ollama),
    ):
        text = fn(prompt, system)
        if text:
            _last_provider = name
            return LLMResult(text=text, provider=name)
    _last_provider = "template"
    return LLMResult(text="", provider="none")


def active_provider() -> str:
    """Which provider will actually serve answers (for the UI status badge).
    Prefers the last one that really produced text; otherwise predicts from the
    fallback chain, honouring the Gemini rate-limit cooldown."""
    if _last_provider:
        return _last_provider
    if _gemini_ready():
        return "gemini"
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    if _ollama_up():
        return "ollama"
    return "template"
