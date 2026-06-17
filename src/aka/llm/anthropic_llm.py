"""Claude adapter behind the LLM contract. The anthropic import is lazy so the
package and the fake path work without the SDK or an API key present.
"""

from __future__ import annotations

import os

from aka.contracts.llm import Message


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
