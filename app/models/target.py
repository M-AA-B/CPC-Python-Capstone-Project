"""S2 Domain Model: Target / ReductionTarget (Owner: Vanessa Mukamanzi · 7223964)."""
from __future__ import annotations


class Target:
    """Represents a company's carbon-reduction baseline and target percentage (UML S2)."""

    def __init__(self, target_id: int, baseline: float, target_percent: float):
        """Constructor: Proper state initialization."""
        self._target_id: int = int(target_id)
        self._baseline: float = 0.0
        self._target_percent: float = 0.0
        self.configure_target(baseline=baseline, target_percent=target_percent)

    def configure_target(self, baseline: float, target_percent: float) -> None:
        """Initialization method: validates baseline emissions and reduction percentage."""
        self.set_baseline(baseline)
        self.set_target(target_percent)

    def get_target_id(self) -> int:
        return self._target_id

    def get_baseline(self) -> float:
        return self._baseline

    def set_baseline(self, baseline: float) -> None:
        val = float(baseline)
        if val <= 0:
            raise ValueError("Baseline emissions must be greater than zero.")
        self._baseline = val

    def get_target(self) -> float:
        """UML getter: returns target reduction percentage."""
        return self._target_percent

    def set_target(self, target_percent: float) -> None:
        """UML setter: validates and updates target reduction percentage."""
        val = float(target_percent)
        if not 0 < val <= 100:
            raise ValueError("Target reduction percent must be in (0, 100].")
        self._target_percent = val


ReductionTarget = Target
