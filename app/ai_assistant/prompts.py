"""S3 - builds the messages sent to OpenAI. Owner: Junaid.

Only the aggregated summary from data.py goes into a prompt: never single records,
names, emails or IDs.
"""
import json
from collections.abc import Iterable
from datetime import date

from app.ai_assistant import data
from app.models.chat_message import ChatMessage, Sender

SYSTEM_PROMPT = """You are the Sustainability Coach inside a carbon accounting app for small and mid-sized companies.
Rules:
- Use ONLY the figures in the company data below. Never invent numbers. If the data cannot answer the question, say so.
- All emissions are in kg CO2e. Always mention units and round sensibly.
- Scope 1 = direct (own fuel, heating), Scope 2 = purchased energy, Scope 3 = value chain (travel, waste, goods).
- Be concise: at most 150 words unless the user asks for more.
- Only answer questions about the company's emissions, carbon accounting and how to reduce emissions."""

ADVICE_PROMPT = """Suggest 3 practical measures to reduce emissions in the "{department}" department.

The department emitted {department_kg:.0f} kg CO2e in the period, about {annual_kg:.0f} kg CO2e per year.
The company's biggest emission sources are: {hotspots}.

Answer ONLY with JSON in exactly this format:
{{"recommendations": [
  {{"title": "short title, max 80 characters",
    "description": "2-3 sentences: what to do and why it helps",
    "est_saving_kg": <estimated CO2e saving per year in kg, a number between 0 and {annual_kg:.0f}>,
    "est_cost_eur": <estimated one-off cost in EUR as a number, or null if unknown>,
    "effort": "low" | "medium" | "high"}}
]}}"""

SUMMARY_PROMPT = """Write a short monthly report for {month} for the management, in plain language (max 120 words).
The company data covers {month} and the month before it; take the month totals from "by_month".
Cover: total emissions, the change compared with the previous month and its most likely reason,
the biggest departments and categories, and one concrete next step.
No headings, no bullet points, no markdown."""


def default_period(today: date | None = None) -> tuple[date, date]:
    """The last 12 months including the current one."""
    today = today or date.today()
    year, month = today.year, today.month - 11
    if month < 1:
        year, month = year - 1, month + 12
    return date(year, month, 1), today


class PromptBuilder:
    """Builds structured OpenAI prompt payloads from aggregated company emissions (UML S3 & Hometask 1)."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT, max_hotspots: int = 3):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._system_prompt = SYSTEM_PROMPT
        self._max_hotspots = 3
        self.system_prompt = system_prompt
        self.max_hotspots = max_hotspots

    # --- Initialization / Setup Methods (Hometask 1) ---
    def reset_templates(self) -> None:
        """Resets prompt configuration back to default instructions and hotspot count."""
        self._system_prompt = SYSTEM_PROMPT
        self._max_hotspots = 3

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("System prompt cannot be empty.")
        self._system_prompt = cleaned

    @property
    def max_hotspots(self) -> int:
        return self._max_hotspots

    @max_hotspots.setter
    def max_hotspots(self, value: int) -> None:
        count = int(value)
        if count < 1:
            raise ValueError("max_hotspots must be at least 1.")
        self._max_hotspots = count

    @staticmethod
    def build_context(company_id: str, start: date | None = None, end: date | None = None) -> dict:
        if start is None or end is None:
            start, end = default_period()
        return data.emission_summary(company_id, start, end)

    @staticmethod
    def hotspots(summary: dict, top: int = 3) -> list[tuple[str, float, float]]:
        """Biggest categories as (name, kg, share in %)."""
        total = summary["total_kg"] or 0.0
        ranked = sorted(summary["by_category"].items(), key=lambda item: item[1], reverse=True)
        return [(name, kg, kg / total * 100 if total else 0.0) for name, kg in ranked[:top]]

    @staticmethod
    def data_block(summary: dict) -> str:
        return "Company data (aggregated, kg CO2e):\n" + json.dumps(summary, default=str)

    def system_message(self, summary: dict) -> dict:
        return {"role": "system", "content": f"{self._system_prompt}\n\n{self.data_block(summary)}"}

    def chat_messages(self, summary: dict, question: str,
                      history: Iterable[ChatMessage] = ()) -> list[dict]:
        messages = [self.system_message(summary)]
        for message in history:
            role = "user" if message.sender == Sender.USER else "assistant"
            messages.append({"role": role, "content": message.content})
        messages.append({"role": "user", "content": question})
        return messages

    def advice_prompt(self, summary: dict, department: str, annual_kg: float) -> list[dict]:
        hotspots = ", ".join(
            f"{name} ({share:.0f} %)"
            for name, _kg, share in self.hotspots(summary, top=self._max_hotspots)
        )
        instruction = ADVICE_PROMPT.format(
            department=department,
            department_kg=summary["by_department"].get(department, 0.0),
            annual_kg=annual_kg,
            hotspots=hotspots or "no data yet",
        )
        return [self.system_message(summary), {"role": "user", "content": instruction}]

    def summary_prompt(self, summary: dict, month_label: str) -> list[dict]:
        return [self.system_message(summary),
                {"role": "user", "content": SUMMARY_PROMPT.format(month=month_label)}]
