"""Pure executable-cost arithmetic; callers supply opens, never intraday lows."""
import math


def best_executable_improvement(baseline, opens):
    """Fractional improvement of the cheapest supplied economic fill cost."""
    values = tuple(opens)
    if not values or any(isinstance(v, bool) or not isinstance(v, (float, int))
                         or not math.isfinite(v) or v <= 0 for v in (baseline, *values)):
        raise ValueError('INVALID_EXECUTABLE_COST')
    return (baseline - min(values)) / baseline
