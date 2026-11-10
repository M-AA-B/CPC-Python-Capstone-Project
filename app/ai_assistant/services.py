"""S3 - AI Assistant. Owner: Junaid.

    AIClient                talks to OpenAI: timeout, token limit, daily limit, fallback message
    parse_recommendations   checks the AI's recommendation JSON before anything is saved
    AIAssistant             the AI Sustainability Coach: ask(), recommend(), summarise()

Settings (environment / .env, never in git):
    OPENAI_API_KEY          required for real answers; without it the pages explain the setup
    OPENAI_MODEL            default gpt-4o-mini
    OPENAI_TIMEOUT          seconds, default 10
    OPENAI_BASE_URL         optional; empty = OpenAI. Any OpenAI-compatible server works,
                            e.g. Google Gemini (free tier):
                            https://generativelanguage.googleapis.com/v1beta/openai/
    AI_MAX_TOKENS           per answer, default 600
    AI_DAILY_REQUEST_LIMIT  per company, default 200
"""
import calendar
import json
import logging
import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import openai
from flask import current_app

from app.ai_assistant.prompts import PromptBuilder
from app.extensions import db
from app.models.ai_request import AIRequest
from app.models.chat_message import ChatMessage, Sender
from app.models.department import Department
from app.models.recommendation import Effort, Recommendation

FALLBACK_MESSAGE = "The AI assistant is not available right now. Please try again in a few minutes."
MAX_QUESTION_LENGTH = 1000
HISTORY_LENGTH = 6  # earlier messages sent along so follow-up questions work
MAX_RECOMMENDATIONS = 5

DEFAULTS = {
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_TIMEOUT": "10",
    "OPENAI_BASE_URL": "",
    "AI_MAX_TOKENS": "600",
    "AI_DAILY_REQUEST_LIMIT": "200",
}

logger = logging.getLogger(__name__)


class AIUnavailable(Exception):
    """The AI could not give an answer. The message is safe to show to the user."""


def _setting(name: str) -> str:
    """App config first (used by tests), then the environment, then the default."""
    value = current_app.config.get(name)
    if value is None:
        value = os.getenv(name, DEFAULTS[name])
    return value


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- OpenAI client ---------------------------------------------------------

class AIClient:
    """Encapsulates OpenAI API communication, rate limits, and token budgets (S3 & Hometask 1)."""

    def __init__(self, api_key: str, model: str, timeout: float = 10.0,
                 max_tokens: int = 600, daily_limit: int = 200, base_url: str | None = None):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._model = "gpt-4o-mini"
        self._timeout = 10.0
        self._max_tokens = 600
        self._daily_limit = 200
        self.configure(model=model, timeout=timeout, max_tokens=max_tokens, daily_limit=daily_limit)
        # The key stays on the server; without one the assistant shows a message instead.
        # base_url=None means OpenAI itself; a URL points the same SDK at a compatible API (e.g. Gemini).
        api_key = (api_key or "").strip()
        self._base_url = (base_url or "").strip() or None
        self._client = openai.OpenAI(api_key=api_key, base_url=self._base_url, timeout=self._timeout,
                                     max_retries=1) if api_key else None

    # --- Initialization / Setup Methods (Hometask 1) ---
    def configure(
        self,
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        daily_limit: int | None = None,
    ) -> None:
        """Applies and validates OpenAI model, timeout, token, and daily limit settings."""
        if model is not None:
            self.model = model
        if timeout is not None:
            self.timeout = timeout
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if daily_limit is not None:
            self.daily_limit = daily_limit

    @classmethod
    def from_config(cls) -> "AIClient":
        return cls(
            _setting("OPENAI_API_KEY"),
            _setting("OPENAI_MODEL"),
            float(_setting("OPENAI_TIMEOUT")),
            int(_setting("AI_MAX_TOKENS")),
            int(_setting("AI_DAILY_REQUEST_LIMIT")),
            base_url=_setting("OPENAI_BASE_URL"),
        )

    @property
    def base_url(self) -> str | None:
        """None = OpenAI; otherwise the OpenAI-compatible server in use (e.g. Gemini)."""
        return self._base_url

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Model name cannot be empty.")
        self._model = cleaned

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        seconds = float(value)
        if seconds <= 0:
            raise ValueError("Timeout must be greater than 0 seconds.")
        self._timeout = seconds

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        tokens = int(value)
        if tokens <= 0:
            raise ValueError("max_tokens must be a positive integer.")
        self._max_tokens = tokens

    @property
    def daily_limit(self) -> int:
        return self._daily_limit

    @daily_limit.setter
    def daily_limit(self, value: int) -> None:
        limit = int(value)
        if limit < 0:
            raise ValueError("daily_limit cannot be negative.")
        self._daily_limit = limit

    def requests_today(self, company_id: str) -> int:
        midnight = datetime.combine(_utcnow().date(), time.min, tzinfo=timezone.utc)
        return db.session.scalar(
            db.select(db.func.count()).select_from(AIRequest)
            .where(AIRequest.company_id == company_id, AIRequest.created_at >= midnight)
        )

    def complete(self, messages: list[dict], company_id: str, kind: str,
                 user_id: str | None = None, json_output: bool = False) -> str:
        """Send `messages` to OpenAI and return the answer text, or raise AIUnavailable."""
        if self._client is None:
            raise AIUnavailable("The AI assistant is not set up yet (missing OPENAI_API_KEY).")
        if self.requests_today(company_id) >= self.daily_limit:
            raise AIUnavailable("Your company has reached today's AI request limit. Please try again tomorrow.")

        log = AIRequest(company_id=company_id, user_id=user_id, kind=kind)
        db.session.add(log)
        client: Any = self._client
        try:
            extra = {"response_format": {"type": "json_object"}} if json_output else {}
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self.max_tokens,
                **extra,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise AIUnavailable(FALLBACK_MESSAGE)
            log.succeeded = True
            log.total_tokens = response.usage.total_tokens if response.usage else None
            return content
        except openai.OpenAIError:
            logger.exception("OpenAI request failed")
            raise AIUnavailable(FALLBACK_MESSAGE) from None
        finally:
            db.session.commit()


# --- recommendation JSON validation ----------------------------------------

class InvalidAIOutput(ValueError):
    pass


def _number(value) -> float | None:
    # bool is a subclass of int, but True is not a valid saving
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def validate_recommendation(item, max_saving_kg: float) -> dict:
    if not isinstance(item, dict):
        raise InvalidAIOutput("recommendation is not an object")

    title = str(item.get("title") or "").strip()
    description = str(item.get("description") or "").strip()
    if not title or not description:
        raise InvalidAIOutput("title or description missing")

    saving = _number(item.get("est_saving_kg"))
    # A saving larger than the department's yearly emissions cannot come from our data
    if saving is None or not 0 <= saving <= max_saving_kg:
        raise InvalidAIOutput(f"est_saving_kg out of range: {item.get('est_saving_kg')!r}")

    cost = item.get("est_cost_eur")
    if cost is not None:
        cost = _number(cost)
        if cost is None or cost < 0:
            raise InvalidAIOutput(f"invalid est_cost_eur: {item.get('est_cost_eur')!r}")

    effort = str(item.get("effort") or "").strip().lower()
    if effort not in Effort.ALL:
        raise InvalidAIOutput(f"invalid effort: {item.get('effort')!r}")

    return {
        "title": title[:200],
        "description": description,
        "est_saving_kg": round(saving, 1),
        "est_cost_eur": cost,
        "effort": effort,
    }


def parse_recommendations(raw: str, max_saving_kg: float) -> list[dict]:
    """Return the valid recommendations; invalid ones are skipped. Raises if none are valid."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise InvalidAIOutput("answer is not valid JSON") from None

    items = parsed.get("recommendations") if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        raise InvalidAIOutput('missing "recommendations" list')

    valid = []
    for item in items:
        try:
            valid.append(validate_recommendation(item, max_saving_kg))
        except InvalidAIOutput as error:
            logger.warning("Skipped AI recommendation: %s", error)
        if len(valid) == MAX_RECOMMENDATIONS:
            break
    if not valid:
        raise InvalidAIOutput("no valid recommendations")
    return valid


# --- AI Sustainability Coach -----------------------------------------------

class AIAssistant:
    """AI Sustainability Coach service orchestrating chat, department tips, and monthly reports (UML S3 & Hometask 1)."""

    def __init__(self, client: AIClient, prompts: PromptBuilder | None = None,
                 history_limit: int = HISTORY_LENGTH):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._client: AIClient = client
        self._prompts: PromptBuilder = prompts or PromptBuilder()
        self._history_limit: int = HISTORY_LENGTH
        self.client = client
        self.prompts = prompts or PromptBuilder()
        self.history_limit = history_limit

    # --- Initialization / Setup Methods (Hometask 1) ---
    def reset_defaults(self) -> None:
        """Resets prompt builder and chat history depth to standard defaults."""
        self._prompts = PromptBuilder()
        self._history_limit = HISTORY_LENGTH

    @classmethod
    def from_app(cls) -> "AIAssistant":
        return cls(AIClient.from_config())

    # --- Encapsulation: Getters & Setters (UML S3 & Hometask 1) ---
    @property
    def client(self) -> AIClient:
        return self._client

    @client.setter
    def client(self, value: AIClient) -> None:
        if not isinstance(value, AIClient):
            raise TypeError("client must be an AIClient instance.")
        self._client = value

    @property
    def prompts(self) -> PromptBuilder:
        return self._prompts

    @prompts.setter
    def prompts(self, value: PromptBuilder) -> None:
        if not isinstance(value, PromptBuilder):
            raise TypeError("prompts must be a PromptBuilder instance.")
        self._prompts = value

    @property
    def model(self) -> str:
        """Accessor for active OpenAI model name (UML S3)."""
        return self._client.model

    @model.setter
    def model(self, value: str) -> None:
        """Mutator for active OpenAI model name (UML S3)."""
        self._client.model = value

    @property
    def history_limit(self) -> int:
        return self._history_limit

    @history_limit.setter
    def history_limit(self, value: int) -> None:
        limit = int(value)
        if limit < 0:
            raise ValueError("history_limit cannot be negative.")
        self._history_limit = limit

    @staticmethod
    def history(user_id: str, limit: int) -> list[ChatMessage]:
        """The user's last `limit` messages, oldest first."""
        newest_first = db.session.scalars(
            db.select(ChatMessage).filter_by(user_id=user_id)
            .order_by(ChatMessage.created_at.desc()).limit(limit)
        ).all()
        return list(reversed(newest_first))

    def ask(self, user, question: str) -> ChatMessage:
        """Answer a question about the user's company emissions. Saves question and answer."""
        question = (question or "").strip()
        if not question:
            raise ValueError("Please enter a question.")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Please keep questions under {MAX_QUESTION_LENGTH} characters.")

        summary = self.prompts.build_context(user.company_id)
        messages = self.prompts.chat_messages(summary, question, self.history(user.id, self._history_limit))

        asked_at = _utcnow()
        # Raises AIUnavailable; then nothing is saved
        answer = self.client.complete(messages, user.company_id, "chat", user.id)

        db.session.add(ChatMessage(user_id=user.id, sender=Sender.USER, content=question, created_at=asked_at))
        # The answer must sort after the question even if the clock has not moved on
        answered_at = max(_utcnow(), asked_at + timedelta(microseconds=1))
        reply = ChatMessage(user_id=user.id, sender=Sender.ASSISTANT, content=answer, created_at=answered_at)
        db.session.add(reply)
        db.session.commit()
        return reply

    def recommend(self, company_id: str, department_id: str, user_id: str | None = None) -> list[Recommendation]:
        """Generate and save reduction tips for one department."""
        department = db.session.get(Department, department_id) if department_id else None
        if department is None or department.company_id != company_id:
            raise ValueError("Unknown department.")

        summary = self.prompts.build_context(company_id)
        department_kg = summary["by_department"].get(department.name, 0.0)
        months = max(len(summary["by_month"]), 1)
        annual_kg = department_kg * 12 / months
        if annual_kg <= 0:
            raise AIUnavailable(f"There is no emission data for {department.name} yet.")

        raw = self.client.complete(
            self.prompts.advice_prompt(summary, department.name, annual_kg),
            company_id, "recommend", user_id, json_output=True,
        )
        try:
            items = parse_recommendations(raw, max_saving_kg=annual_kg)
        except InvalidAIOutput:
            raise AIUnavailable("The AI returned an unusable answer. Please try again.") from None

        recommendations = [Recommendation(company_id=company_id, department_id=department_id, **item)
                           for item in items]
        db.session.add_all(recommendations)
        db.session.commit()
        return recommendations

    def summarise(self, company_id: str, month: date, user_id: str | None = None) -> str:
        """Plain-language report for one month, compared with the month before."""
        start = month.replace(day=1)
        end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
        previous_start = (start - timedelta(days=1)).replace(day=1)
        summary = self.prompts.build_context(company_id, previous_start, end)
        return self.client.complete(
            self.prompts.summary_prompt(summary, start.strftime("%B %Y")), company_id, "summary", user_id
        )
