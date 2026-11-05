"""S3 Service Class: PromptBuilder (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

import hashlib
import json


class PromptBuilder:
    """Builds privacy-safe aggregated emission prompts for the AI coach (UML S3)."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are an enterprise Sustainability Coach. Use only aggregated company CO2e figures."
    )

    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT, max_hotspots: int = 3):
        """Constructor: Proper state initialization."""
        self._system_prompt: str = self.DEFAULT_SYSTEM_PROMPT
        self._max_hotspots: int = 3
        self.configure_templates(system_prompt=system_prompt, max_hotspots=max_hotspots)

    # --- Initialization / Setup Method ---
    def configure_templates(self, system_prompt: str, max_hotspots: int = 3) -> None:
        """Configures system instruction template and hotspot ranking limit."""
        self.set_system_prompt(system_prompt)
        self.set_max_hotspots(max_hotspots)

    # --- Encapsulation: Getters & Setters ---
    def get_system_prompt(self) -> str:
        return self._system_prompt

    def set_system_prompt(self, prompt: str) -> None:
        cleaned = (prompt or "").strip()
        if not cleaned:
            raise ValueError("System prompt cannot be empty.")
        self._system_prompt = cleaned

    def get_max_hotspots(self) -> int:
        return self._max_hotspots

    def set_max_hotspots(self, count: int) -> None:
        val = int(count)
        if val < 1:
            raise ValueError("max_hotspots must be at least 1.")
        self._max_hotspots = val

    # --- UML Domain Methods ---
    @staticmethod
    def anonymise(company_id: str) -> str:
        """Stable pseudonym for a company, so the real id never leaves the server.

        sha256 instead of hash(): Python randomises hash() for strings on every run.
        """
        return hashlib.sha256(company_id.encode("utf-8")).hexdigest()[:12]

    def build_context(self, company_id: str, category_totals: dict[str, float]) -> dict:
        """UML method: builds an anonymized aggregated emission summary context."""
        total = round(sum(category_totals.values()), 2)
        ranked = sorted(category_totals.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "company_ref": self.anonymise(company_id),
            "total_co2e_kg": total,
            "top_hotspots": dict(ranked[: self._max_hotspots]),
        }

    def chat_messages(self, context: dict, question: str, history: list | None = None) -> list[dict]:
        """Turns the aggregated context, earlier messages and the new question into OpenAI chat messages."""
        messages = [{
            "role": "system",
            "content": f"{self._system_prompt}\n\nCompany data (aggregated, kg CO2e):\n{json.dumps(context)}",
        }]
        for message in history or []:
            messages.append({"role": message.get_sender(), "content": message.get_content()})
        messages.append({"role": "user", "content": question})
        return messages

    def advice_prompt(self, hotspots: dict[str, float], department_name: str = "General") -> str:
        """UML method: formats an advice prompt targeting the highest-emitting categories."""
        return (
            f"{self._system_prompt}\n"
            f"Department: {department_name}\n"
            f"Aggregated hotspots (kg CO2e): {json.dumps(hotspots)}"
        )
