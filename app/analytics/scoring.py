"""S2 Service Class: CarbonScorer (Owner: Vanessa Mukamanzi · 7223964)."""
from __future__ import annotations


class CarbonScorer:
    """Computes bounded Carbon Score (0..100) measuring progress towards a ReductionTarget."""

    def __init__(self, min_score: float = 0.0, max_score: float = 100.0):
        """Constructor: Proper state initialization."""
        self._min_score: float = 0.0
        self._max_score: float = 100.0
        self.configure_bounds(min_score=min_score, max_score=max_score)

    def configure_bounds(self, min_score: float = 0.0, max_score: float = 100.0) -> None:
        """Initialization method: configures minimum and maximum score bounds."""
        if float(min_score) >= float(max_score):
            raise ValueError("min_score must be strictly less than max_score.")
        self._min_score = float(min_score)
        self._max_score = float(max_score)

    def reset_defaults(self) -> None:
        self.configure_bounds(0.0, 100.0)

    @property
    def min_score(self) -> float:
        return self._min_score

    @min_score.setter
    def min_score(self, value: float) -> None:
        self.configure_bounds(float(value), self._max_score)

    @property
    def max_score(self) -> float:
        return self._max_score

    @max_score.setter
    def max_score(self, value: float) -> None:
        self.configure_bounds(self._min_score, float(value))

    def calculate(self, baseline_kg: float, current_kg: float, target_percent: float) -> float:
        """Returns bounded progress score in [min_score, max_score]."""
        required_reduction = baseline_kg * (target_percent / 100.0)
        achieved_reduction = baseline_kg - current_kg
        raw = (achieved_reduction / required_reduction) * 100.0
        return round(max(self._min_score, min(self._max_score, raw)), 1)
