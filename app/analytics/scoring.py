from math import isfinite



class CarbonScorer:
    """OOP calculator for company carbon reduction target progress scores (S2 & Hometask 1)."""

    def __init__(self, min_score: float = 0.0, max_score: float = 100.0):
        """Constructor: Initializes score clamping bounds (Hometask 1)."""
        self._min_score = 0.0
        self._max_score = 100.0
        self.configure_bounds(min_score, max_score)

    # --- Initialization / Setup Methods (Hometask 1) ---
    def configure_bounds(self, min_score: float = 0.0, max_score: float = 100.0) -> None:
        """Configures lower and upper score clamping bounds."""
        low = float(min_score)
        high = float(max_score)
        if not (isfinite(low) and isfinite(high)) or low < 0 or low >= high:
            raise ValueError("Score bounds must be finite with 0 <= min_score < max_score.")
        self._min_score = low
        self._max_score = high

    def reset_defaults(self) -> None:
        """Resets score bounds to the standard 0..100 scale."""
        self._min_score = 0.0
        self._max_score = 100.0

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def min_score(self) -> float:
        return self._min_score

    @min_score.setter
    def min_score(self, value: float) -> None:
        self.configure_bounds(value, self._max_score)

    @property
    def max_score(self) -> float:
        return self._max_score

    @max_score.setter
    def max_score(self, value: float) -> None:
        self.configure_bounds(self._min_score, value)

    def calculate(
        self,
        baseline_kg,
        current_kg,
        reduction_percent,
        data_complete: bool = False,
    ) -> dict:
        """Calculate progress towards the company's reduction target."""
        if not data_complete:
            return {
                "available": False,
                "score": None,
                "reason": "Confirm complete, comparable data for both periods.",
            }

        try:
            baseline = float(baseline_kg)
            current = float(current_kg)
            reduction = float(reduction_percent)
        except (TypeError, ValueError):
            return {
                "available": False,
                "score": None,
                "reason": "Valid emissions and a reduction target are required.",
            }

        if not all(isfinite(value) for value in (baseline, current, reduction)):
            return {
                "available": False,
                "score": None,
                "reason": "Emissions and reduction values must be finite numbers.",
            }

        if baseline <= 0 or current < 0 or not 0 < reduction <= 100:
            return {
                "available": False,
                "score": None,
                "reason": (
                    "Baseline must exceed zero, emissions cannot be negative, "
                    "and reduction must be greater than 0% and at most 100%."
                ),
            }

        required_reduction = baseline * reduction / 100
        target_kg = baseline - required_reduction
        achieved_reduction = baseline - current
        progress = achieved_reduction / required_reduction * 100

        return {
            "available": True,
            "score": max(self._min_score, min(self._max_score, progress)),
            "baseline_kg": baseline,
            "current_kg": current,
            "target_kg": target_kg,
            "reduction_percent": reduction,
            "achieved_reduction_kg": achieved_reduction,
            "actual_reduction_percent": achieved_reduction / baseline * 100,
            "remaining_reduction_kg": max(0.0, current - target_kg),
            "target_met": current <= target_kg,
        }


_default_scorer = CarbonScorer()


def calculate_target_progress(
    baseline_kg,
    current_kg,
    reduction_percent,
    data_complete=False,
):
    """Calculate progress towards the company's reduction target."""
    return _default_scorer.calculate(
        baseline_kg,
        current_kg,
        reduction_percent,
        data_complete=data_complete,
    )
