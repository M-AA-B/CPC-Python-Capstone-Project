"""S3 Domain Model: Recommendation (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

import uuid


class Recommendation:
    """Represents a tailored emission-reduction tip for a department (UML S3)."""

    VALID_EFFORTS = ("low", "medium", "high")
    VALID_STATUSES = ("proposed", "accepted", "rejected", "done")

    def __init__(
        self,
        department_id: str,
        title: str,
        est_saving_kg: float,
        effort: str = "medium",
        recommendation_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = recommendation_id or str(uuid.uuid4())
        self._department_id: str = department_id
        self._title: str = ""
        self._est_saving_kg: float = 0.0
        self._effort: str = "medium"
        self._status: str = "proposed"
        self.initialize_recommendation(title=title, est_saving_kg=est_saving_kg, effort=effort)

    # --- Initialization / Setup Method ---
    def initialize_recommendation(self, title: str, est_saving_kg: float, effort: str) -> None:
        """Validates recommendation attributes and resets workflow status to proposed."""
        self.set_title(title)
        self.set_est_saving_kg(est_saving_kg)
        self.set_effort(effort)
        self._status = "proposed"

    # --- Encapsulation: Getters & Setters ---
    def get_id(self) -> str:
        return self._id

    def get_department_id(self) -> str:
        return self._department_id

    def get_title(self) -> str:
        return self._title

    def set_title(self, title: str) -> None:
        cleaned = (title or "").strip()
        if not cleaned:
            raise ValueError("Recommendation title cannot be empty.")
        self._title = cleaned

    def get_est_saving_kg(self) -> float:
        return self._est_saving_kg

    def set_est_saving_kg(self, saving_kg: float) -> None:
        val = float(saving_kg)
        if val < 0:
            raise ValueError("Estimated CO2e saving cannot be negative.")
        self._est_saving_kg = round(val, 1)

    def get_effort(self) -> str:
        return self._effort

    def set_effort(self, effort: str) -> None:
        cleaned = (effort or "").strip().lower()
        if cleaned not in self.VALID_EFFORTS:
            raise ValueError(f"Effort must be one of {self.VALID_EFFORTS}.")
        self._effort = cleaned

    def get_status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        cleaned = (status or "").strip().lower()
        if cleaned not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of {self.VALID_STATUSES}.")
        self._status = cleaned

    # --- UML Domain Methods ---
    def accept(self) -> None:
        self._status = "accepted"

    def mark_done(self) -> None:
        """UML method: marks the recommendation as implemented."""
        self._status = "done"

    def reject(self) -> None:
        """UML method: marks the recommendation as rejected."""
        self._status = "rejected"
