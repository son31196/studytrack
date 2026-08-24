# StudyTrack — Semester A+ System

Personal progress-tracking + AI-quizzing system for the semester. Three modules:

1. **Course tracker** — syllabus topics, per-topic mastery scores, grades, and "what score do I need for A+".
2. **Side project tracker** — lightweight project boards so projects don't eat study time invisibly.
3. **Generative testing engine** — Claude-generated quizzes from your own notes; grading feeds back into mastery + spaced repetition.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # needed only for `study quiz`
```

## Daily use

```bash
python study.py ui                          # interactive web UI at localhost:5000
python study.py status                      # where am I? what should I study now?
python study.py quiz example-course         # quiz on the weakest due topic
python study.py quiz example-course --topic limits -n 5
python study.py grade example-course Homework HW1 95 100
python study.py log example-course 2.5      # log study hours
python study.py project list                # side projects board
python study.py dashboard                   # regenerate docs/index.html
python study.py sync                        # git pull --rebase, commit data, push
```

## Adding a course

Copy `courses/example-course/`, edit `syllabus.yaml` (components + weights + topics + exam dates), and drop your study notes as Markdown files in `notes/`. Notes are the source material for generated quizzes — the better the notes, the better the quiz.

## Sync between machines

This repo is the single source of truth. `python study.py sync` wraps `git pull --rebase` + commit + push. Run it at the start and end of each study session on either machine.

## Dashboard on GitHub Pages

`study.py dashboard` writes a static page to `docs/index.html`. The included GitHub Actions workflow rebuilds and publishes it on every push (enable Pages → "GitHub Actions" in repo settings).
