"""S3 Domain Model: Recommendation (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

import uuid


class Recommendation:
    """Represents a tailored emission-reduction tip for a department (UML S3)."""

    VALID_EFFORTS = ("low", "medium", "high")
    VALID_STATUSES = ("proposed", "accepted", "rejected", "done")
    # Which status may follow which: a rejected or finished tip cannot be reopened.
    ALLOWED_TRANSITIONS = {
        "proposed": ("accepted", "rejected"),
        "accepted": ("done", "rejected"),
        "rejected": (),
        "done": (),
    }

    def __init__(
        self,
        department_id: str,
        title: str,
        est_saving_kg: float,
        effort: str = "medium",
        est_cost_eur: float | None = None,
        recommendation_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = recommendation_id or str(uuid.uuid4())
        self._department_id: str = department_id
        self._title: str = ""
        self._est_saving_kg: float = 0.0
        self._est_cost_eur: float | None = None
        self._effort: str = "medium"
        self._status: str = "proposed"
        self.initialize_recommendation(title=title, est_saving_kg=est_saving_kg,
                                       effort=effort, est_cost_eur=est_cost_eur)

    # --- Initialization / Setup Method ---
    def initialize_recommendation(self, title: str, est_saving_kg: float, effort: str,
                                  est_cost_eur: float | None = None) -> None:
        """Validates recommendation attributes and resets workflow status to proposed."""
        self.set_title(title)
        self.set_est_saving_kg(est_saving_kg)
        self.set_est_cost_eur(est_cost_eur)
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

    def get_est_cost_eur(self) -> float | None:
        return self._est_cost_eur

    def set_est_cost_eur(self, cost_eur: float | None) -> None:
        """None means the cost is unknown."""
        if cost_eur is None:
            self._est_cost_eur = None
            return
        val = float(cost_eur)
        if val < 0:
            raise ValueError("Estimated cost cannot be negative.")
        self._est_cost_eur = round(val, 2)

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
        if cleaned not in self.ALLOWED_TRANSITIONS[self._status]:
            raise ValueError(f"A {self._status} recommendation cannot become {cleaned}.")
        self._status = cleaned

    # --- UML Domain Methods ---
    def accept(self) -> None:
        """UML method: the department agrees to implement the tip."""
        self.set_status("accepted")

    def mark_done(self) -> None:
        """UML method: marks an accepted recommendation as implemented."""
        self.set_status("done")

    def reject(self) -> None:
        """UML method: marks the recommendation as rejected."""
        self.set_status("rejected")

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "department_id": self._department_id,
            "title": self._title,
            "est_saving_kg": self._est_saving_kg,
            "est_cost_eur": self._est_cost_eur,
            "effort": self._effort,
            "status": self._status,
        }
