"""Verify the configured Gemini model with a real API call outside regression tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.errors import ChatbotUnavailableError
from app.ai.gemini_client import GeminiClient
from app.core.config import get_settings


async def main() -> None:
    try:
        await GeminiClient(get_settings()).verify_model()
    except ChatbotUnavailableError as exc:
        raise SystemExit(f"NOT READY: {exc.detail}") from None
    print("PASS: configured Gemini model is available and returned text.")


if __name__ == "__main__":
    asyncio.run(main())
