"""Generate a static HTML dashboard at docs/index.html (published via GitHub Pages).

The page mirrors the local web UI's design (tabs, cards, mastery bars) with the
data baked in as JSON and rendered client-side — interactive to browse, but
read-only: edits happen in `python study.py ui`, then `study.py sync` republishes.
"""
import json
from datetime import date

from . import grades, mastery, store

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StudyTrack</title>
<style>
  :root {
    color-scheme: light;
    --page: #f9f9f7; --surface: #fcfcfb;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --hairline: #e1e0d9; --ring: rgba(11,11,11,0.10);
    --accent: #2a78d6; --accent-deep: #1c5cab; --track: #f0efec;
    --good: #0ca30c; --good-text: #006300; --critical: #d03b3b; --warning: #fab219;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --page: #0d0d0d; --surface: #1a1a19;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --hairline: #2c2c2a; --ring: rgba(255,255,255,0.10);
      --accent: #3987e5; --accent-deep: #86b6ef; --track: #383835;
      --good: #0ca30c; --good-text: #0ca30c; --critical: #d03b3b; --warning: #fab219;
    }
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--page); color: var(--ink);
    font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 24px 20px 80px; }
  main { max-width: 1080px; margin: 0 auto; }
  h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.01em; }
  .topbar { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; margin-bottom: 18px; }
  .topbar .date { color: var(--muted); font-size: 13px; }
  .topbar .spacer { flex: 1; }
  .ro { font-size: 12px; color: var(--muted); }
  nav.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--hairline); margin-bottom: 20px; }
  nav.tabs button { appearance: none; background: none; border: none; cursor: pointer;
    font: inherit; font-weight: 600; color: var(--ink-2);
    padding: 8px 14px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
  nav.tabs button.on { color: var(--ink); border-bottom-color: var(--accent); }
  .banner { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px;
    padding: 14px 18px; margin-bottom: 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .banner .lead { font-weight: 600; }
  .banner .why { color: var(--ink-2); font-size: 13px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px;
    padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; }
  .card h3 { font-size: 15px; font-weight: 700; }
  .card .code { color: var(--muted); font-size: 12px; font-weight: 500; margin-left: 6px; }
  .frow { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .chip { font-size: 11px; font-weight: 600; color: var(--ink-2);
    border: 1px solid var(--hairline); border-radius: 999px; padding: 1px 8px; white-space: nowrap; }
  .statrow { display: flex; gap: 22px; }
  .stat .v { font-size: 22px; font-weight: 700; }
  .stat .l { font-size: 11.5px; color: var(--muted); }
  .need { font-size: 13px; color: var(--ink-2); }
  .need.out { color: var(--critical); font-weight: 600; }
  .need .ok { color: var(--good-text); font-weight: 600; }
  .exam { font-size: 12.5px; color: var(--ink-2); }
  .exam b.soon { color: var(--critical); }
  .bar { height: 6px; border-radius: 4px; background: var(--track); overflow: hidden; }
  .bar > i { display: block; height: 100%; border-radius: 4px; background: var(--accent); }
  .topicline { display: grid; grid-template-columns: 1fr 120px 34px; gap: 10px; align-items: center; font-size: 13px; }
  .topicline .t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .topicline .pct { color: var(--muted); font-size: 12px; text-align: right; font-variant-numeric: tabular-nums; }
  .due-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    background: var(--warning); margin-right: 6px; vertical-align: 1px; }
  .projcard .task { display: flex; align-items: center; gap: 9px; font-size: 14px; padding: 3px 0; }
  .projcard .task .box { width: 15px; height: 15px; border: 1.5px solid var(--muted); border-radius: 4px;
    display: inline-flex; align-items: center; justify-content: center; font-size: 11px; color: var(--good-text); flex: none; }
  .projcard .task.done .box { border-color: var(--good-text); }
  .projcard .task.done span:last-child { color: var(--muted); text-decoration: line-through; }
  .projcard .meta { font-size: 12px; color: var(--muted); }
  .status-pill { font-size: 11px; font-weight: 700; border-radius: 999px; padding: 1px 9px; }
  .status-pill.active { color: var(--good-text); border: 1px solid var(--good); }
  .status-pill.paused { color: var(--ink-2); border: 1px solid var(--hairline); }
  .status-pill.done { color: var(--muted); border: 1px solid var(--hairline); }
  table.hours { border-collapse: collapse; font-size: 14px; min-width: 320px; }
  table.hours th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 600;
    padding: 6px 18px 6px 0; border-bottom: 1px solid var(--hairline); }
  table.hours td { padding: 7px 18px 7px 0; border-bottom: 1px solid var(--hairline); font-variant-numeric: tabular-nums; }
  .empty { color: var(--muted); font-size: 14px; padding: 30px 0; text-align: center; }
  .filters { display: flex; gap: 6px; margin-bottom: 16px; }
  .filters button { font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer;
    color: var(--ink-2); background: var(--surface); border: 1px solid var(--hairline);
    border-radius: 999px; padding: 3px 12px; }
  .filters button.on { color: #fff; background: var(--accent); border-color: var(--accent); }
  section[hidden] { display: none; }
</style>
</head>
<body>
<main>
  <div class="topbar">
    <h1>StudyTrack</h1>
    <span class="date" id="today"></span>
    <span class="spacer"></span>
    <span class="ro">read-only · edit with <b>study.py ui</b>, publish with <b>study.py sync</b></span>
  </div>
  <nav class="tabs" id="tabs">
    <button data-tab="overview" class="on">Overview</button>
    <button data-tab="projects">Side projects</button>
    <button data-tab="hours">Hours</button>
  </nav>
  <section id="tab-overview">
    <div class="banner" id="studynext" hidden></div>
    <div class="filters" id="termfilter">
      <button data-t="" class="on">All terms</button>
      <button data-t="fall">Fall</button>
      <button data-t="winter">Winter</button>
      <button data-t="full-year">Full year</button>
    </div>
    <div class="grid" id="courses"></div>
  </section>
  <section id="tab-projects" hidden><div class="grid" id="projects"></div></section>
  <section id="tab-hours" hidden>
    <table class="hours"><thead><tr><th>Course / project</th><th>Total hours</th></tr></thead><tbody id="hoursBody"></tbody></table>
  </section>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let TERM = "";

document.getElementById("tabs").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b === btn));
  ["overview","projects","hours"].forEach(t => $("#tab-"+t).hidden = t !== btn.dataset.tab);
});
document.getElementById("termfilter").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  TERM = btn.dataset.t;
  document.querySelectorAll("#termfilter button").forEach(b => b.classList.toggle("on", b === btn));
  renderCourses();
});

function daysUntil(iso) {
  return Math.round((new Date(iso + "T00:00:00") - new Date(DATA.today + "T00:00:00")) / 864e5);
}
function nextExam(c) {
  const up = (c.exams || []).map(e => ({...e, days: daysUntil(e.date)})).filter(e => e.days >= 0)
    .sort((a, b) => a.days - b.days);
  return up[0] || null;
}
function termChip(term) {
  const label = {fall:"Fall", winter:"Winter", "full-year":"Full year"}[term] || term;
  return term ? `<span class="chip">${esc(label)}</span>` : "";
}
function renderCourses() {
  const host = $("#courses");
  const courses = DATA.courses.filter(c => !TERM || c.term === TERM);
  if (!courses.length) { host.innerHTML = `<div class="empty">No courses.</div>`; return; }
  host.innerHTML = courses.map(c => {
    const g = c.grade, m = c.mastery;
    const grade = g.current !== null ? g.current + "%" : "—";
    let need = "";
    if (g.needed_for_aplus !== null) {
      need = g.aplus_achievable
        ? `<div class="need">need <span class="ok">≥${g.needed_for_aplus}%</span> on remaining for A+ (cutoff ${g.cutoff}%)</div>`
        : `<div class="need out">A+ out of reach — needs ${g.needed_for_aplus}% on remaining</div>`;
    } else if (g.current !== null) {
      need = g.aplus_achievable ? `<div class="need"><span class="ok">A+ secured 🎉</span></div>`
                                : `<div class="need out">final grade below A+ cutoff</div>`;
    }
    const ex = nextExam(c);
    const exam = ex ? `<div class="exam">${esc(ex.name)} in <b class="${ex.days <= 14 ? "soon" : ""}">${ex.days} day${ex.days === 1 ? "" : "s"}</b> (${esc(ex.date)})</div>` : "";
    const dueSet = new Set(m.topics_due);
    const topics = c.topics.map(t => `
      <div class="topicline">
        <span class="t">${dueSet.has(t.title) ? '<span class="due-dot" title="due for review"></span>' : ""}${esc(t.title)}</span>
        <span class="bar"><i style="width:${t.mastery || 0}%"></i></span>
        <span class="pct">${Math.round(t.mastery || 0)}</span>
      </div>`).join("");
    return `<div class="card">
      <div class="frow" style="justify-content:space-between">
        <h3>${esc(c.name)}<span class="code">${esc(c.code)}</span></h3>${termChip(c.term)}
      </div>
      <div class="statrow">
        <div class="stat"><div class="v">${grade}</div><div class="l">current grade</div></div>
        <div class="stat"><div class="v">${m.avg_mastery}%</div><div class="l">avg mastery</div></div>
        <div class="stat"><div class="v">${m.topics_due.length}</div><div class="l">topics due</div></div>
      </div>
      ${need}${exam}
      <div>${topics}</div>
    </div>`;
  }).join("");
}
function renderProjects() {
  const host = $("#projects");
  if (!DATA.projects.length) { host.innerHTML = `<div class="empty">No side projects yet.</div>`; return; }
  host.innerHTML = DATA.projects.map(p => {
    const done = p.tasks.filter(t => t.done).length;
    const tasks = p.tasks.map(t =>
      `<div class="task ${t.done ? "done" : ""}"><span class="box">${t.done ? "✓" : ""}</span><span>${esc(t.title)}</span></div>`).join("");
    return `<div class="card projcard">
      <div class="frow" style="justify-content:space-between">
        <h3>${esc(p.name)}</h3><span class="status-pill ${esc(p.status)}">${esc(p.status)}</span>
      </div>
      <div class="meta">${done}/${p.tasks.length} tasks · <b>${Math.round(100*done/Math.max(p.tasks.length,1))}%</b></div>
      <div class="bar"><i style="width:${100*done/Math.max(p.tasks.length,1)}%"></i></div>
      <div>${tasks}</div>
    </div>`;
  }).join("");
}
function renderHours() {
  const rows = Object.entries(DATA.hours).sort((a,b) => b[1]-a[1]);
  $("#hoursBody").innerHTML = rows.length
    ? rows.map(([n,h]) => `<tr><td>${esc(n)}</td><td>${h}</td></tr>`).join("")
    : `<tr><td colspan="2" class="empty">Nothing logged yet.</td></tr>`;
}
$("#today").textContent = "generated " + DATA.today;
const sn = $("#studynext");
if (DATA.study_next) {
  sn.hidden = false;
  sn.innerHTML = `<span class="lead">Study next: ${esc(DATA.study_next.topic_title)}</span>
    <span class="why">${esc(DATA.study_next.course_name)} — weakest course with topics due (avg mastery ${DATA.study_next.avg_mastery}%)</span>`;
}
renderCourses(); renderProjects(); renderHours();
</script>
</body>
</html>
"""


def build_data() -> dict:
    today = date.today().isoformat()
    courses = []
    best_pick = None
    for course in store.list_courses():
        syl = store.load_syllabus(course)
        g = grades.course_grade(course, syl)
        m = mastery.course_summary(course, syl)
        per_topic = mastery.get_course_mastery(course)
        topics = [{**t, **per_topic.get(t["id"], {"mastery": 0.0})} for t in syl.get("topics", [])]
        courses.append(
            {
                "id": course,
                "name": syl.get("name", course),
                "code": syl.get("code", ""),
                "term": syl.get("term", ""),
                "exams": [
                    {**e, "date": str(e["date"])} if e.get("date") else e
                    for e in syl.get("exams", [])
                ],
                "topics": topics,
                "grade": g,
                "mastery": m,
            }
        )
        if m["topics_due"] and (best_pick is None or m["avg_mastery"] < best_pick["avg_mastery"]):
            best_pick = {
                "course": course,
                "course_name": syl.get("name", course),
                "topic_title": m["topics_due"][0],
                "avg_mastery": m["avg_mastery"],
            }
    projects = []
    for p in store.load_projects():
        p = dict(p)
        p.pop("_file", None)
        p.setdefault("tasks", [])
        p.setdefault("status", "active")
        projects.append(p)
    timelog = store.load_timelog()
    hours = {name: round(sum(e["hours"] for e in entries), 1) for name, entries in timelog.items()}
    return {"today": today, "courses": courses, "study_next": best_pick, "projects": projects, "hours": hours}


def render() -> str:
    payload = json.dumps(build_data()).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)


def write(path=None):
    out = path or (store.ROOT / "docs" / "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(render())
    return out
