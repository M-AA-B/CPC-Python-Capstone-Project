from math import isfinite


def calculate_target_progress(
    baseline_kg,
    current_kg,
    reduction_percent,
    data_complete=False,
):
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
        "score": max(0.0, min(100.0, progress)),
        "baseline_kg": baseline,
        "current_kg": current,
        "target_kg": target_kg,
        "reduction_percent": reduction,
        "achieved_reduction_kg": achieved_reduction,
        "actual_reduction_percent": achieved_reduction / baseline * 100,
        "remaining_reduction_kg": max(0.0, current - target_kg),
        "target_met": current <= target_kg,
    }