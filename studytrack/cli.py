"""StudyTrack CLI. Run via `python study.py <command>`."""
import argparse
import subprocess
from datetime import date

from . import dashboard, grades, mastery, store


def cmd_status(args):
    print(f"Semester status — {date.today().isoformat()}\n")
    best_pick = None
    for course in store.list_courses():
        syl = store.load_syllabus(course)
        g = grades.course_grade(course, syl)
        m = mastery.course_summary(course, syl)
        current = f'{g["current"]}%' if g["current"] is not None else "no grades yet"
        print(f"  {syl.get('name', course)} [{course}]")
        print(f"    grade: {current}", end="")
        if g["needed_for_aplus"] is not None:
            flag = "" if g["aplus_achievable"] else "  (!) above 100% — A+ out of reach"
            print(f"  |  need ≥{g['needed_for_aplus']}% on remaining for A+{flag}")
        else:
            print()
        due = ", ".join(m["topics_due"]) or "none"
        print(f"    avg mastery: {m['avg_mastery']}%  |  due for review: {due}")
        if m["topics_due"] and (best_pick is None or m["avg_mastery"] < best_pick[2]):
            best_pick = (course, m["topics_due"][0], m["avg_mastery"])
        print()
    if best_pick:
        print(f"→ Study next: '{best_pick[1]}' in {best_pick[0]}  (python study.py quiz {best_pick[0]})")


def cmd_quiz(args):
    from . import quiz as quiz_mod  # imported lazily so other commands work without the SDK/key

    syl = store.load_syllabus(args.course)
    topics = {t["id"]: t for t in syl.get("topics", [])}
    if args.topic:
        if args.topic not in topics:
            raise SystemExit(f"Unknown topic '{args.topic}'. Topics: {', '.join(topics)}")
        topic = topics[args.topic]
    else:
        topic = mastery.pick_topic(args.course, syl)
        print(f"Picked weakest/due topic: {topic['title']}")

    print(f"Generating {args.n} questions on '{topic['title']}'...\n")
    q = quiz_mod.generate_quiz(syl.get("name", args.course), topic["title"], store.load_notes(args.course), args.n)

    total = 0.0
    for i, question in enumerate(q.questions, 1):
        print(f"Q{i}. {question.question}")
        if question.type == "mcq" and question.choices:
            for letter, choice in zip("ABCD", question.choices):
                print(f"   {letter}) {choice}")
        answer = input("your answer> ").strip()
        result = quiz_mod.grade_answer(question, answer)
        total += result.score
        print(f"   [{result.score * 100:.0f}%] {result.feedback}\n")

    pct = 100.0 * total / len(q.questions)
    t = mastery.record_quiz_result(args.course, topic["id"], pct)
    print(f"Quiz score: {pct:.0f}%  |  mastery for '{topic['title']}' → {t['mastery']}%")
    print(f"Next review: {t['next_review']}")


def cmd_record_quiz(args):
    syl = store.load_syllabus(args.course)
    topic_ids = [t["id"] for t in syl.get("topics", [])]
    if args.topic not in topic_ids:
        raise SystemExit(f"Unknown topic '{args.topic}'. Topics: {', '.join(topic_ids)}")
    t = mastery.record_quiz_result(args.course, args.topic, args.pct)
    print(f"Recorded {args.pct:.0f}% on '{args.topic}' — mastery now {t['mastery']}%, next review {t['next_review']}.")


def cmd_grade(args):
    grades.record_grade(args.course, args.component, args.name, args.score, args.max)
    syl = store.load_syllabus(args.course)
    g = grades.course_grade(args.course, syl)
    print(f"Recorded {args.name}: {args.score}/{args.max} under {args.component}.")
    print(f"Current weighted grade: {g['current']}%", end="")
    if g["needed_for_aplus"] is not None:
        print(f"  |  need ≥{g['needed_for_aplus']}% on remaining for A+")
    else:
        print()


def cmd_log(args):
    data = store.load_timelog()
    data.setdefault(args.name, []).append({"date": date.today().isoformat(), "hours": args.hours})
    store.save_timelog(data)
    total = sum(e["hours"] for e in data[args.name])
    print(f"Logged {args.hours}h on {args.name} (total {total:.1f}h).")


def cmd_project(args):
    projects = store.load_projects()
    if not projects:
        print("No projects yet. Add a YAML file under projects/.")
        return
    for p in projects:
        tasks = p.get("tasks", [])
        done = sum(1 for t in tasks if t.get("done"))
        print(f"  {p.get('name')} ({p.get('status', 'active')}) — {done}/{len(tasks)} tasks")
        for t in tasks:
            print(f"    [{'x' if t.get('done') else ' '}] {t.get('title')}")


def cmd_ui(args):
    from . import webapp  # imported lazily so other commands work without Flask

    webapp.run(port=args.port)


def cmd_dashboard(args):
    out = dashboard.write()
    print(f"Dashboard written to {out}")


def cmd_sync(args):
    dashboard.write()
    run = lambda *cmd: subprocess.run(cmd, cwd=store.ROOT, check=False)
    run("git", "pull", "--rebase")
    run("git", "add", "-A")
    run("git", "commit", "-m", f"study session {date.today().isoformat()}")
    run("git", "push")


def main():
    parser = argparse.ArgumentParser(prog="study", description="Semester A+ tracking system")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="overview + what to study next").set_defaults(func=cmd_status)

    p = sub.add_parser("quiz", help="take a generated quiz")
    p.add_argument("course")
    p.add_argument("--topic", help="topic id (default: weakest due topic)")
    p.add_argument("-n", type=int, default=5, help="number of questions")
    p.set_defaults(func=cmd_quiz)

    p = sub.add_parser("record-quiz", help="record a quiz result: course topic-id percent")
    p.add_argument("course"), p.add_argument("topic"), p.add_argument("pct", type=float)
    p.set_defaults(func=cmd_record_quiz)

    p = sub.add_parser("grade", help="record a grade: course component name score max")
    p.add_argument("course"), p.add_argument("component"), p.add_argument("name")
    p.add_argument("score", type=float), p.add_argument("max", type=float)
    p.set_defaults(func=cmd_grade)

    p = sub.add_parser("log", help="log study hours: name hours")
    p.add_argument("name"), p.add_argument("hours", type=float)
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("project", help="side projects board")
    p.add_argument("action", nargs="?", default="list")
    p.set_defaults(func=cmd_project)

    p = sub.add_parser("ui", help="launch the local web UI")
    p.add_argument("--port", type=int, default=5000)
    p.set_defaults(func=cmd_ui)

    sub.add_parser("dashboard", help="regenerate docs/index.html").set_defaults(func=cmd_dashboard)
    sub.add_parser("sync", help="git pull --rebase, commit, push").set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)
