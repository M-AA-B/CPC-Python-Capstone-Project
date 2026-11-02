"""S3 Service Class: AIAssistant (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

from app.models import ChatMessage, Recommendation, User
from .prompts import PromptBuilder


class AIAssistant:
    """AI Sustainability Coach generating answers, department tips, and monthly summaries (UML S3)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        prompt_builder: PromptBuilder | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._model: str = "gpt-4o-mini"
        self._prompt_builder: PromptBuilder = prompt_builder or PromptBuilder()
        self._history: list[ChatMessage] = []
        self.configure_assistant(model=model)

    # --- Initialization / Setup Method ---
    def configure_assistant(self, model: str = "gpt-4o-mini", clear_history: bool = False) -> None:
        """Configures active model identifier and optionally resets chat history."""
        self.set_model(model)
        if clear_history:
            self._history.clear()

    # --- Encapsulation: Getters & Setters ---
    def get_model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        cleaned = (model or "").strip()
        if not cleaned:
            raise ValueError("Model name cannot be empty.")
        self._model = cleaned

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
        self._history.append(user_msg)

        total = context.get("total_co2e_kg", 0.0)
        hotspots = context.get("top_hotspots", {})
        top_cat = next(iter(hotspots.keys()), "none")
        answer_text = (
            f"[{self._model}] Total recorded footprint is {total} kg CO2e "
            f"(primary hotspot: {top_cat})."
        )
        reply = ChatMessage(user_id=user.get_id(), sender="assistant", content=answer_text)
        self._history.append(reply)
        return reply

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
