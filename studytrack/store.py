"""File-backed data store: courses/*/syllabus.yaml, data/*.json, projects/*.yaml."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COURSES_DIR = ROOT / "courses"
PROJECTS_DIR = ROOT / "projects"
DATA_DIR = ROOT / "data"


def list_courses():
    return sorted(p.name for p in COURSES_DIR.iterdir() if (p / "syllabus.yaml").exists())


def load_syllabus(course: str) -> dict:
    path = COURSES_DIR / course / "syllabus.yaml"
    if not path.exists():
        raise SystemExit(f"No such course: {course} (expected {path})")
    return yaml.safe_load(path.read_text())


def load_notes(course: str) -> str:
    notes_dir = COURSES_DIR / course / "notes"
    if not notes_dir.exists():
        return ""
    parts = []
    for f in sorted(notes_dir.glob("*.md")):
        parts.append(f"## {f.stem}\n\n{f.read_text()}")
    return "\n\n".join(parts)


def _load_json(name: str) -> dict:
    path = DATA_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_json(name: str, data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_mastery() -> dict:
    return _load_json("mastery.json")


def save_mastery(data: dict):
    _save_json("mastery.json", data)


def load_grades() -> dict:
    return _load_json("grades.json")


def save_grades(data: dict):
    _save_json("grades.json", data)


def load_timelog() -> dict:
    return _load_json("timelog.json")


def save_timelog(data: dict):
    _save_json("timelog.json", data)


def load_todos() -> list:
    return _load_json("todos.json").get("items", [])


def save_todos(items: list):
    _save_json("todos.json", {"items": items})


def load_projects() -> list:
    if not PROJECTS_DIR.exists():
        return []
    out = []
    for f in sorted(PROJECTS_DIR.glob("*.yaml")):
        proj = yaml.safe_load(f.read_text())
        proj["_file"] = str(f)
        out.append(proj)
    return out
