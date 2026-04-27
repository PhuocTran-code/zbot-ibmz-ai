"""
LLM abstraction layer for IBM Z Xplore AI assistant.

Supports Gemini (primary) and Groq (fallback), or vice-versa depending on
the LLM_PROVIDER environment variable.

Usage:
    from llm import get_llm_response
    result = get_llm_response(system_prompt="...", user_message="...")
    # result = {"text": "...", "provider": "gemini", "error": None}
"""

import os
import logging
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

Provider = Literal["gemini", "groq"]

# ── Provider configs ─────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.3
GEMINI_MAX_TOKENS = 1024

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.3
GROQ_MAX_TOKENS = 1024


# ── Individual callers ───────────────────────────────────────────────────────

def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Call Gemini and return the response text."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY not set in environment")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_TOKENS,
        ),
    )

    response = model.generate_content(user_message)
    return response.text


def _call_groq(system_prompt: str, user_message: str) -> str:
    """Call Groq and return the response text."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment")

    client = Groq(api_key=api_key)

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )
    return completion.choices[0].message.content


# ── Dispatch table ───────────────────────────────────────────────────────────

_CALLERS: dict[Provider, callable] = {
    "gemini": _call_gemini,
    "groq":   _call_groq,
}

_FALLBACK: dict[Provider, Provider] = {
    "gemini": "groq",
    "groq":   "gemini",
}


# ── Public interface ─────────────────────────────────────────────────────────

def get_llm_response(system_prompt: str, user_message: str) -> dict:
    """
    Call the configured LLM provider and return a response dict.

    Reads LLM_PROVIDER from the environment (default: "gemini").
    On failure, automatically retries with the other provider.

    Returns:
        {
            "text":     str   — model response (empty string on total failure),
            "provider": str   — provider that actually responded,
            "error":    str | None — last error message, or None on success,
        }
    """
    raw_provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    primary: Provider = raw_provider if raw_provider in _CALLERS else "gemini"
    fallback: Provider = _FALLBACK[primary]

    last_error: str | None = None

    for provider in (primary, fallback):
        caller = _CALLERS[provider]
        try:
            text = caller(system_prompt, user_message)
            if last_error:
                logger.warning(
                    "Primary provider '%s' failed; responded via fallback '%s'.",
                    primary, provider,
                )
            return {"text": text, "provider": provider, "error": None}
        except Exception as exc:
            last_error = f"[{provider}] {type(exc).__name__}: {exc}"
            logger.error("LLM call failed — %s", last_error)

    return {"text": "", "provider": primary, "error": last_error}
