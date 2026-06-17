"""Claude adapter behind the LLM contract. The anthropic import is lazy so the
package and the fake path work without the SDK or an API key present.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from aka.contracts.llm import Message

_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class AnthropicLLM:
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        temperature: float = 0.0,
        api_key: str | None = None,
    ) -> None:
        from anthropic import Anthropic  # lazy

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it, or use the 'fake' LLM provider "
                "to run the pipeline offline."
            )
        self._client = Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    def complete(self, system: str, messages: list[Message]) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system,
            messages=messages,
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete_with_images(
        self, system: str, prompt: str, image_paths: list[Path]
    ) -> str:
        """Vision completion: send images + a prompt, return text. Used by the
        preprocessing vision structurer; the text-only LLM Protocol is untouched.
        """
        content: list[dict] = []
        for path in image_paths:
            path = Path(path)
            media = _MEDIA_TYPES.get(path.suffix.lower(), "image/png")
            data = base64.standard_b64encode(path.read_bytes()).decode()
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media, "data": data},
                }
            )
        content.append({"type": "text", "text": prompt})
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")
