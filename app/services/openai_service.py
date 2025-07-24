"""app/services/openai_service.py
Purpose: Central gateway for OpenAI chat & embeddings.
Provides convenience wrappers with automatic retry/back-off.
"""
from __future__ import annotations

import logging
from typing import List, Iterable

from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

from app.constants import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBED_MODEL

logger = logging.getLogger(__name__)

# Initialise client (works for both secret and project keys)
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- Helpers ----------------

@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
def chat(messages: List[dict], tools: list | None = None, stream: bool = False):
    """Generate chat completion via OpenAI."""
    try:
        return client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools,
            stream=stream,
        )
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        raise


@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
def embed(texts: List[str]):
    """Return list of embedding vectors for given texts."""
    if not texts:
        return []
    try:
        response = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.error(f"OpenAI embeddings error: {e}")
        raise


@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
def complete(prompt: str, model: str = "gpt-4o") -> str:
    """Single-prompt completion helper."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI completion error: {e}")
        raise


@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
def ai_explain(row: dict, context: list[dict], checks: list[str]) -> str:
    """Return one-sentence explanation for a flagged row covering all failed checks."""
    from pathlib import Path
    prompt_tpl = Path("app/prompts/row_enrich.md").read_text()
    prompt = (
        prompt_tpl
        .replace("{{row}}", str(row))
        .replace("{{checks}}", ", ".join(checks))
        .replace("{{context}}", str(context))
    )
    return complete(prompt, model=OPENAI_MODEL)


# Trend summary helper
@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
def ai_trend(context: list[dict]) -> str:
    """Return one-sentence trend summary for 7-day context."""
    from pathlib import Path
    prompt_tpl = Path("app/prompts/trend_enrich.md").read_text()
    prompt = prompt_tpl.replace("{{context}}", str(context))
    return complete(prompt, model=OPENAI_MODEL) 