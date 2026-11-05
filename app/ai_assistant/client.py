"""S3 Service Class: AIClient (Owner: Junaid Ahmad · 7222074).

Wraps the OpenAI chat API for the AI Sustainability Coach. The API key stays
inside this class and is never returned by a getter. Without a key, or without
the optional `openai` package, the client reports itself unavailable and the
AIAssistant answers offline from the aggregated figures instead.
"""
from __future__ import annotations

import os

FALLBACK_MESSAGE = "The AI assistant is not available right now. Please try again in a few minutes."


class AIClient:
    """Sends prompts to OpenAI with a timeout, a token budget and a daily request limit (UML S3)."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 10.0,
        max_tokens: int = 600,
        daily_limit: int = 200,
    ):
        """Constructor: Proper state initialization."""
        self._api_key: str = ""
        self._model: str = self.DEFAULT_MODEL
        self._timeout: float = 10.0
        self._max_tokens: int = 600
        self._daily_limit: int = 200
        self._requests_today: int = 0
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
        self.configure(api_key=api_key, model=model, timeout=timeout,
                       max_tokens=max_tokens, daily_limit=daily_limit)

    # --- Initialization / Setup Methods ---
    def configure(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        daily_limit: int | None = None,
    ) -> None:
        """Applies and validates any of the connection settings that are given."""
        if api_key is not None:
            self.set_api_key(api_key)
        if model is not None:
            self.set_model(model)
        if timeout is not None:
            self.set_timeout(timeout)
        if max_tokens is not None:
            self.set_max_tokens(max_tokens)
        if daily_limit is not None:
            self.set_daily_limit(daily_limit)

    def reset_usage(self) -> None:
        """Starts a new day: sets the request counter back to zero."""
        self._requests_today = 0

    # --- Encapsulation: Getters & Setters ---
    def set_api_key(self, api_key: str) -> None:
        """Write-only: the key can be replaced but is never handed out again."""
        self._api_key = (api_key or "").strip()

    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def get_model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        cleaned = (model or "").strip()
        if not cleaned:
            raise ValueError("Model name cannot be empty.")
        self._model = cleaned

    def get_timeout(self) -> float:
        return self._timeout

    def set_timeout(self, seconds: float) -> None:
        value = float(seconds)
        if value <= 0:
            raise ValueError("Timeout must be greater than 0 seconds.")
        self._timeout = value

    def get_max_tokens(self) -> int:
        return self._max_tokens

    def set_max_tokens(self, tokens: int) -> None:
        value = int(tokens)
        if value <= 0:
            raise ValueError("max_tokens must be a positive integer.")
        self._max_tokens = value

    def get_daily_limit(self) -> int:
        return self._daily_limit

    def set_daily_limit(self, limit: int) -> None:
        value = int(limit)
        if value < 0:
            raise ValueError("daily_limit cannot be negative.")
        self._daily_limit = value

    def get_requests_today(self) -> int:
        return self._requests_today

    # --- UML Domain Methods ---
    def is_available(self) -> bool:
        """True when a key is set and today's request limit is not reached yet."""
        return self.has_api_key() and self._requests_today < self._daily_limit

    def complete(self, messages: list[dict]) -> str:
        """Sends chat `messages` to OpenAI and returns the answer text.

        Raises RuntimeError with a message that is safe to show to the user.
        """
        if not self.has_api_key():
            raise RuntimeError("The AI assistant is not set up yet (missing OPENAI_API_KEY).")
        if self._requests_today >= self._daily_limit:
            raise RuntimeError("Today's AI request limit is reached. Please try again tomorrow.")
        try:
            import openai
        except ImportError:
            raise RuntimeError("The AI assistant needs the 'openai' package (pip install openai).") from None

        # Built per request so that changed settings (e.g. the timeout) always apply.
        client = openai.OpenAI(api_key=self._api_key, timeout=self._timeout, max_retries=1)
        self._requests_today += 1
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_completion_tokens=self._max_tokens,
            )
        except openai.OpenAIError:
            raise RuntimeError(FALLBACK_MESSAGE) from None
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError(FALLBACK_MESSAGE)
        return content
