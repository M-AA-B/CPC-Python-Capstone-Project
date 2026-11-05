"""S3 Service Class: AIAssistant (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

from app.models import ChatMessage, Recommendation, User
from .client import AIClient
from .prompts import PromptBuilder


class AIAssistant:
    """AI Sustainability Coach generating answers, department tips, and monthly summaries (UML S3).

    Composition: the assistant owns a PromptBuilder (what to ask) and an AIClient
    (how to ask OpenAI). Without an API key it answers offline from the figures.
    """

    HISTORY_LENGTH = 6  # earlier messages sent along so follow-up questions work

    def __init__(
        self,
        model: str | None = None,
        prompt_builder: PromptBuilder | None = None,
        client: AIClient | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._client: AIClient = client or AIClient()
        self._prompt_builder: PromptBuilder = prompt_builder or PromptBuilder()
        self._history: list[ChatMessage] = []
        self.configure_assistant(model=model)

    # --- Initialization / Setup Method ---
    def configure_assistant(self, model: str | None = None, clear_history: bool = False) -> None:
        """Configures active model identifier and optionally resets chat history."""
        if model is not None:
            self.set_model(model)
        if clear_history:
            self._history.clear()

    # --- Encapsulation: Getters & Setters ---
    def get_model(self) -> str:
        return self._client.get_model()

    def set_model(self, model: str) -> None:
        self._client.set_model(model)

    def get_client(self) -> AIClient:
        return self._client

    def set_client(self, client: AIClient) -> None:
        if not isinstance(client, AIClient):
            raise TypeError("client must be an AIClient instance.")
        self._client = client

    def get_prompt_builder(self) -> PromptBuilder:
        return self._prompt_builder

    def set_prompt_builder(self, builder: PromptBuilder) -> None:
        if not isinstance(builder, PromptBuilder):
            raise TypeError("builder must be a PromptBuilder instance.")
        self._prompt_builder = builder

    def get_history(self) -> list[ChatMessage]:
        return list(self._history)

    # --- UML Domain Methods ---
    def ask(self, user: User, question: str, context: dict) -> ChatMessage:
        """UML method: records user question and returns an AI coach ChatMessage answer."""
        user_msg = ChatMessage(user_id=user.get_id(), sender="user", content=question)
        earlier = self._history[-self.HISTORY_LENGTH:]
        self._history.append(user_msg)

        answer_text = None
        if self._client.is_available():
            messages = self._prompt_builder.chat_messages(context, user_msg.get_content(), earlier)
            try:
                answer_text = self._client.complete(messages)
            except RuntimeError:
                answer_text = None  # fall back to the offline answer below
        if answer_text is None:
            answer_text = self._offline_answer(context)

        reply = ChatMessage(user_id=user.get_id(), sender="assistant", content=answer_text)
        self._history.append(reply)
        return reply

    def _offline_answer(self, context: dict) -> str:
        """Answer built only from the aggregated figures, used when OpenAI is not available."""
        total = context.get("total_co2e_kg", 0.0)
        hotspots = context.get("top_hotspots", {})
        top_cat = next(iter(hotspots.keys()), "none")
        return (
            f"[{self.get_model()}] Total recorded footprint is {total} kg CO2e "
            f"(primary hotspot: {top_cat})."
        )

    def recommend(self, department_id: str, hotspots: dict[str, float]) -> list[Recommendation]:
        """UML method: creates structured department reduction Recommendations from hotspots."""
        _prompt = self._prompt_builder.advice_prompt(hotspots, department_id)
        tips: list[Recommendation] = []
        for cat, kg in hotspots.items():
            tips.append(
                Recommendation(
                    department_id=department_id,
                    title=f"Reduce {cat} consumption by 15%",
                    est_saving_kg=round(kg * 0.15, 1),
                    effort="medium",
                )
            )
        return tips

    def summarise(self, month: str, category_totals: dict[str, float]) -> str:
        """UML method: produces a plain-language monthly emissions summary."""
        total = round(sum(category_totals.values()), 2)
        return f"Monthly Summary ({month}): {total} kg CO2e recorded across {len(category_totals)} categories."
