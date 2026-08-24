"""Local web UI: JSON API over the same files the CLI uses. Run via `python study.py ui`."""
import re
from datetime import date
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory

from . import dashboard, grades, mastery, store

WEBUI_DIR = Path(__file__).resolve().parent / "webui"

app = Flask(__name__)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        raise ValueError("empty name")
    return s


@app.get("/")
def index():
    return send_from_directory(WEBUI_DIR, "index.html")


@app.get("/planner.js")
def planner_js():
    return send_from_directory(WEBUI_DIR, "planner.js")


@app.get("/api/todos")
def get_todos():
    return jsonify(store.load_todos())


@app.post("/api/todos")
def add_todo():
    body = request.get_json(force=True)
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    items = store.load_todos()
    item = {
        "id": 1 + max((t["id"] for t in items), default=0),
        "title": title,
        "due": body.get("due") or None,
        "done": False,
    }
    items.append(item)
    store.save_todos(items)
    return jsonify(item)


@app.put("/api/todos/<int:tid>")
def update_todo(tid):
    body = request.get_json(force=True)
    items = store.load_todos()
    for t in items:
        if t["id"] == tid:
            if "done" in body:
                t["done"] = bool(body["done"])
                t["done_date"] = date.today().isoformat() if t["done"] else None
            if body.get("title", "").strip():
                t["title"] = body["title"].strip()
            if "due" in body:
                t["due"] = body["due"] or None
            store.save_todos(items)
            return jsonify(t)
    return jsonify({"error": "no such todo"}), 404


@app.delete("/api/todos/<int:tid>")
def delete_todo(tid):
    items = store.load_todos()
    kept = [t for t in items if t["id"] != tid]
    if len(kept) == len(items):
        return jsonify({"error": "no such todo"}), 404
    store.save_todos(kept)
    return jsonify({"ok": True})


@app.get("/api/overview")
def overview():
    today = date.today().isoformat()
    courses = []
    best_pick = None
    for course in store.list_courses():
        syl = store.load_syllabus(course)
        g = grades.course_grade(course, syl)
        m = mastery.course_summary(course, syl)
        per_topic = mastery.get_course_mastery(course)
        topics = [
            {**t, **per_topic.get(t["id"], {"mastery": 0.0})}
            for t in syl.get("topics", [])
        ]
        entries = store.load_grades().get(course, [])
        courses.append(
            {
                "id": course,
                "name": syl.get("name", course),
                "code": syl.get("code", ""),
                "term": syl.get("term", ""),
                "aplus_cutoff": syl.get("aplus_cutoff", grades.DEFAULT_APLUS_CUTOFF),
                "components": syl.get("components", []),
                "exams": [
                    {**e, "date": str(e["date"])} if e.get("date") else e
                    for e in syl.get("exams", [])
                ],
                "topics": topics,
                "grade": g,
                "mastery": m,
                "grade_entries": entries,
            }
        )
        if m["topics_due"] and (best_pick is None or m["avg_mastery"] < best_pick["avg_mastery"]):
            due_id = next(
                (t["id"] for t in syl.get("topics", []) if t["title"] == m["topics_due"][0]), None
            )
            best_pick = {
                "course": course,
                "course_name": syl.get("name", course),
                "topic_id": due_id,
                "topic_title": m["topics_due"][0],
                "avg_mastery": m["avg_mastery"],
            }
    timelog = store.load_timelog()
    hours = {name: round(sum(e["hours"] for e in entries), 1) for name, entries in timelog.items()}
    return jsonify({"today": today, "courses": courses, "study_next": best_pick, "hours": hours})


def _syllabus_from_request(body: dict) -> dict:
    syl = {
        "name": body["name"].strip(),
        "code": body.get("code", "").strip(),
        "term": body.get("term", "").strip(),
        "aplus_cutoff": float(body.get("aplus_cutoff", 90)),
        "components": [
            {"name": c["name"].strip(), "weight": float(c["weight"])}
            for c in body.get("components", [])
            if c.get("name", "").strip()
        ],
        "exams": [
            {"name": e["name"].strip(), "date": e["date"]}
            for e in body.get("exams", [])
            if e.get("name", "").strip() and e.get("date")
        ],
        "topics": [
            {"id": t.get("id", "").strip() or _slug(t["title"]), "title": t["title"].strip()}
            for t in body.get("topics", [])
            if t.get("title", "").strip()
        ],
    }
    total = sum(c["weight"] for c in syl["components"])
    if syl["components"] and abs(total - 100) > 0.01:
        raise ValueError(f"component weights sum to {total:g}, not 100")
    return syl


def _write_syllabus(course_id: str, syl: dict):
    course_dir = store.COURSES_DIR / course_id
    (course_dir / "notes").mkdir(parents=True, exist_ok=True)
    (course_dir / "syllabus.yaml").write_text(yaml.safe_dump(syl, sort_keys=False, allow_unicode=True))


@app.post("/api/courses")
def create_course():
    body = request.get_json(force=True)
    try:
        syl = _syllabus_from_request(body)
        course_id = body.get("id", "").strip() or _slug(syl["code"] or syl["name"])
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    if (store.COURSES_DIR / course_id / "syllabus.yaml").exists():
        return jsonify({"error": f"course '{course_id}' already exists"}), 409
    _write_syllabus(course_id, syl)
    return jsonify({"ok": True, "id": course_id})


@app.put("/api/courses/<course_id>")
def update_course(course_id):
    if not (store.COURSES_DIR / course_id / "syllabus.yaml").exists():
        return jsonify({"error": f"no such course: {course_id}"}), 404
    try:
        syl = _syllabus_from_request(request.get_json(force=True))
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    _write_syllabus(course_id, syl)
    return jsonify({"ok": True, "id": course_id})


@app.post("/api/grades")
def add_grade():
    body = request.get_json(force=True)
    try:
        grades.record_grade(
            body["course"], body["component"], body["name"], float(body["score"]), float(body["max"])
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@app.post("/api/quiz-result")
def quiz_result():
    body = request.get_json(force=True)
    try:
        t = mastery.record_quiz_result(body["course"], body["topic"], float(body["pct"]))
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True, "topic": t})


@app.post("/api/log")
def log_hours():
    body = request.get_json(force=True)
    try:
        name, hours = body["name"], float(body["hours"])
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    data = store.load_timelog()
    data.setdefault(name, []).append({"date": date.today().isoformat(), "hours": hours})
    store.save_timelog(data)
    return jsonify({"ok": True, "total": round(sum(e["hours"] for e in data[name]), 1)})


@app.get("/api/projects")
def list_projects():
    out = []
    for p in store.load_projects():
        p = dict(p)
        p["id"] = Path(p.pop("_file")).stem
        out.append(p)
    return jsonify(out)


def _write_project(project_id: str, body: dict):
    proj = {
        "name": body["name"].strip(),
        "status": body.get("status", "active"),
        "tasks": [
            {"title": t["title"].strip(), "done": bool(t.get("done"))}
            for t in body.get("tasks", [])
            if t.get("title", "").strip()
        ],
    }
    store.PROJECTS_DIR.mkdir(exist_ok=True)
    (store.PROJECTS_DIR / f"{project_id}.yaml").write_text(
        yaml.safe_dump(proj, sort_keys=False, allow_unicode=True)
    )


@app.post("/api/projects")
def create_project():
    body = request.get_json(force=True)
    try:
        project_id = _slug(body["name"])
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    if (store.PROJECTS_DIR / f"{project_id}.yaml").exists():
        return jsonify({"error": f"project '{project_id}' already exists"}), 409
    _write_project(project_id, body)
    return jsonify({"ok": True, "id": project_id})


@app.put("/api/projects/<project_id>")
def update_project(project_id):
    if not (store.PROJECTS_DIR / f"{project_id}.yaml").exists():
        return jsonify({"error": f"no such project: {project_id}"}), 404
    try:
        _write_project(project_id, request.get_json(force=True))
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@app.post("/api/dashboard")
def regen_dashboard():
    out = dashboard.write()
    return jsonify({"ok": True, "path": str(out)})


def run(port: int = 5000):
    import threading
    import webbrowser

    url = f"http://127.0.0.1:{port}"
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"StudyTrack UI → {url}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=port, debug=False)
