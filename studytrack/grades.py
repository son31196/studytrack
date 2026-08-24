"""Grade tracking and the 'what do I need for A+' calculator."""
from . import store

DEFAULT_APLUS_CUTOFF = 97.0


def record_grade(course: str, component: str, name: str, score: float, max_score: float):
    data = store.load_grades()
    data.setdefault(course, []).append(
        {"component": component, "name": name, "score": score, "max": max_score}
    )
    store.save_grades(data)


def course_grade(course: str, syllabus: dict) -> dict:
    """Weighted current grade + score needed on remaining work for A+."""
    entries = store.load_grades().get(course, [])
    components = syllabus.get("components", [])
    cutoff = syllabus.get("aplus_cutoff", DEFAULT_APLUS_CUTOFF)

    earned = 0.0        # weighted points earned so far
    weight_done = 0.0   # total weight of graded components (fractional for partial)
    per_component = {}

    for comp in components:
        scores = [e for e in entries if e["component"] == comp["name"]]
        if not scores:
            per_component[comp["name"]] = None
            continue
        pct = 100.0 * sum(e["score"] for e in scores) / sum(e["max"] for e in scores)
        per_component[comp["name"]] = round(pct, 1)
        earned += pct * comp["weight"] / 100.0
        weight_done += comp["weight"]

    current = round(100.0 * earned / weight_done, 1) if weight_done else None
    weight_left = 100.0 - weight_done
    if weight_left > 0:
        needed = (cutoff - earned) / (weight_left / 100.0)
        needed_for_aplus = round(max(needed, 0.0), 1)
        achievable = needed <= 100.0
    else:
        needed_for_aplus = None
        achievable = (current or 0) >= cutoff

    return {
        "current": current,
        "per_component": per_component,
        "needed_for_aplus": needed_for_aplus,
        "aplus_achievable": achievable,
        "cutoff": cutoff,
    }
