"""Generate a static HTML dashboard at docs/index.html (published via GitHub Pages)."""
from datetime import date

from . import grades, mastery, store

CSS = """
:root { --bg:#fff; --fg:#1a1a1a; --muted:#666; --card:#f6f6f8; --bar:#4f7cff; --ok:#1a9950; --warn:#cc8800; --bad:#cc3344; }
@media (prefers-color-scheme: dark) { :root { --bg:#15161a; --fg:#eee; --muted:#999; --card:#22242a; } }
body { background:var(--bg); color:var(--fg); font-family:system-ui,sans-serif; max-width:860px; margin:2rem auto; padding:0 1rem; }
h1 { font-size:1.5rem; } h2 { font-size:1.15rem; margin-top:2rem; }
.card { background:var(--card); border-radius:10px; padding:1rem 1.25rem; margin:0.75rem 0; }
.bar { background:rgba(128,128,128,.25); border-radius:4px; height:10px; overflow:hidden; }
.bar span { display:block; height:100%; background:var(--bar); }
.row { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin:.35rem 0; }
.row .label { flex:0 0 40%; } .row .bar { flex:1; }
.muted { color:var(--muted); font-size:.9rem; }
.big { font-size:1.6rem; font-weight:700; }
.ok { color:var(--ok); } .warn { color:var(--warn); } .bad { color:var(--bad); }
"""


def _bar(pct: float) -> str:
    return f'<div class="bar"><span style="width:{max(0, min(100, pct))}%"></span></div>'


def render() -> str:
    parts = [
        f"<style>{CSS}</style>",
        "<h1>Semester Dashboard</h1>",
        f'<p class="muted">Generated {date.today().isoformat()} · Goal: full A+</p>',
    ]

    for course in store.list_courses():
        syl = store.load_syllabus(course)
        g = grades.course_grade(course, syl)
        m = mastery.course_summary(course, syl)

        current = f'{g["current"]}%' if g["current"] is not None else "—"
        if g["needed_for_aplus"] is None:
            need = "final grade locked in" if g["aplus_achievable"] else "A+ not reached"
        elif not g["aplus_achievable"]:
            need = f'<span class="bad">needs {g["needed_for_aplus"]}% on remaining — above 100%</span>'
        else:
            cls = "ok" if g["needed_for_aplus"] <= 90 else "warn"
            need = f'<span class="{cls}">need ≥{g["needed_for_aplus"]}% on remaining work for A+</span>'

        rows = "".join(
            f'<div class="row"><div class="label">{title}</div>{_bar(score)}'
            f'<div class="muted">{score:.0f}</div></div>'
            for title, score in m["topic_scores"].items()
        )
        due = ", ".join(m["topics_due"]) or "nothing due — ahead of schedule"
        parts.append(
            f'<div class="card"><h2 style="margin-top:0">{syl.get("name", course)}</h2>'
            f'<div class="row"><span class="big">{current}</span><span>{need}</span></div>'
            f'<p class="muted">Avg mastery {m["avg_mastery"]}% · Due for review: {due}</p>'
            f"{rows}</div>"
        )

    projects = store.load_projects()
    if projects:
        parts.append("<h2>Side Projects</h2>")
        for p in projects:
            tasks = p.get("tasks", [])
            done = sum(1 for t in tasks if t.get("done"))
            pct = 100 * done / len(tasks) if tasks else 0
            parts.append(
                f'<div class="card"><strong>{p.get("name", "?")}</strong> '
                f'<span class="muted">({p.get("status", "active")})</span>'
                f"{_bar(pct)}<p class='muted'>{done}/{len(tasks)} tasks done</p></div>"
            )

    timelog = store.load_timelog()
    if timelog:
        parts.append("<h2>Study Hours</h2><div class='card'>")
        for name, entries in sorted(timelog.items()):
            total = sum(e["hours"] for e in entries)
            parts.append(f'<div class="row"><div class="label">{name}</div><div>{total:.1f} h</div></div>')
        parts.append("</div>")

    return "\n".join(parts)


def write(path=None):
    out = path or (store.ROOT / "docs" / "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text("<!doctype html><meta charset='utf-8'><title>Semester Dashboard</title>" + render())
    return out
