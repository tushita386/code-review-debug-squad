"""Gemini LLM access through LangChain. Model + key come from environment variables.
If the primary model is overloaded (503) or unavailable, LangChain fallbacks try the next model automatically."""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACKS = "gemini-3.7-flash,gemini-3.5-flash,gemini-3.1-flash-lite"


class LLMConfigError(Exception):
    pass


def api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    return "" if key.startswith("your_") else key.strip()


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def fallback_models():
    raw = os.getenv("GEMINI_FALLBACK_MODELS", DEFAULT_FALLBACKS)
    return [m.strip() for m in raw.split(",") if m.strip() and m.strip() != model_name()]


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.2):
    key = api_key()
    if not key:
        raise LLMConfigError(
            "GOOGLE_API_KEY is missing. Copy .env.example to .env and paste your Gemini API key "
            "(free key: https://aistudio.google.com/apikey), then restart the app."
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    def make(name):
        return ChatGoogleGenerativeAI(model=name, google_api_key=key, temperature=temperature,
                                      max_retries=2, timeout=90)

    primary = make(model_name())
    fallbacks = [make(m) for m in fallback_models()]
    return primary.with_fallbacks(fallbacks) if fallbacks else primary


def explain_error(exc: Exception) -> str:
    """Turn raw exceptions into a message a student can act on."""
    msg = str(exc)
    low = msg.lower()
    if isinstance(exc, LLMConfigError):
        return msg
    if any(s in low for s in ("api key not valid", "api_key_invalid", "permission_denied", "401", "403")):
        return "Gemini rejected the API key. Check GOOGLE_API_KEY in your .env file."
    if any(s in low for s in ("429", "resource_exhausted", "quota", "rate limit")):
        return "Gemini rate limit / quota reached. Wait about a minute and try again."
    if "503" in low or "high demand" in low or "overloaded" in low:
        return "Gemini is overloaded right now (503), even after trying fallback models. Wait a minute and retry."
    if "404" in low and "model" in low:
        return (f"Model not found / retired for this key. Run `python check_models.py`, then set GEMINI_MODEL "
                f"in .env. Raw error: {msg[:250]}")
    if any(s in low for s in ("connect", "timeout", "timed out", "network", "dns")):
        return "Network problem while contacting Gemini. Check your internet connection and retry."
    return f"{type(exc).__name__}: {msg[:300]}"