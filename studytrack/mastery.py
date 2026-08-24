"""Mastery scores + spaced-repetition scheduling (simplified SM-2)."""
from datetime import date, timedelta

from . import store

# Mastery is an exponential moving average of quiz scores (0-100).
EMA_WEIGHT = 0.4  # weight of the newest quiz result


def get_course_mastery(course: str) -> dict:
    return store.load_mastery().get(course, {})


def record_quiz_result(course: str, topic_id: str, score_pct: float):
    """Update mastery + schedule next review after a quiz on one topic."""
    data = store.load_mastery()
    course_data = data.setdefault(course, {})
    t = course_data.setdefault(
        topic_id, {"mastery": 0.0, "reps": 0, "interval_days": 1}
    )
    t["mastery"] = round((1 - EMA_WEIGHT) * t["mastery"] + EMA_WEIGHT * score_pct, 1)
    t["reps"] += 1
    # Passing (>=70%) grows the interval; failing resets it to tomorrow.
    if score_pct >= 70:
        t["interval_days"] = min(t["interval_days"] * 2, 21)
    else:
        t["interval_days"] = 1
    t["last_quizzed"] = date.today().isoformat()
    t["next_review"] = (date.today() + timedelta(days=t["interval_days"])).isoformat()
    store.save_mastery(data)
    return t


def pick_topic(course: str, syllabus: dict) -> dict:
    """Pick what to study: due-for-review topics first, then lowest mastery."""
    mastery = get_course_mastery(course)
    today = date.today().isoformat()

    def key(topic):
        m = mastery.get(topic["id"], {})
        due = m.get("next_review", "0000-00-00") <= today  # never-quizzed counts as due
        return (not due, m.get("mastery", 0.0))

    return min(syllabus.get("topics", []), key=key)


def course_summary(course: str, syllabus: dict) -> dict:
    mastery = get_course_mastery(course)
    topics = syllabus.get("topics", [])
    today = date.today().isoformat()
    scores = [mastery.get(t["id"], {}).get("mastery", 0.0) for t in topics]
    due = [
        t["title"]
        for t in topics
        if mastery.get(t["id"], {}).get("next_review", "0000-00-00") <= today
    ]
    return {
        "avg_mastery": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "topics_due": due,
        "topic_scores": {
            t["title"]: mastery.get(t["id"], {}).get("mastery", 0.0) for t in topics
        },
    }
