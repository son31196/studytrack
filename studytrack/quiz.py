"""Generative testing engine: Claude generates quizzes from your notes and grades answers."""
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-5"


class Question(BaseModel):
    type: Literal["mcq", "short"]
    question: str
    choices: Optional[List[str]] = None  # for mcq: 4 choices, letters implied A-D
    correct_choice: Optional[int] = None  # for mcq: 0-based index
    reference_answer: str  # ideal answer, used for grading + feedback


class Quiz(BaseModel):
    topic: str
    questions: List[Question]


class Grade(BaseModel):
    score: float  # 0.0 to 1.0
    feedback: str


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def generate_quiz(course_name: str, topic_title: str, notes: str, n: int = 5) -> Quiz:
    """Generate an n-question quiz on one topic, grounded in the student's notes."""
    client = _client()
    source = notes.strip() or "(no notes available — use standard curriculum for this topic)"
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=(
            "You are a rigorous university tutor writing exam-style quiz questions. "
            "Ground questions in the provided course notes when possible; target "
            "A+-level understanding (application and reasoning, not rote recall). "
            "Mix multiple-choice and short-answer questions. For mcq questions give "
            "exactly 4 choices with one correct answer."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Course: {course_name}\nTopic: {topic_title}\n"
                    f"Number of questions: {n}\n\nCourse notes:\n\n{source}"
                ),
            }
        ],
        output_format=Quiz,
    )
    return response.parsed_output


def grade_answer(question: Question, student_answer: str) -> Grade:
    """Grade one answer. MCQ is graded locally; free-response goes to Claude."""
    if question.type == "mcq":
        try:
            picked = "abcd".index(student_answer.strip().lower()[0])
        except (ValueError, IndexError):
            return Grade(score=0.0, feedback="Answer not understood — expected A, B, C, or D.")
        if picked == question.correct_choice:
            return Grade(score=1.0, feedback="Correct.")
        correct_letter = "ABCD"[question.correct_choice or 0]
        return Grade(
            score=0.0,
            feedback=f"Incorrect — the answer is {correct_letter}. {question.reference_answer}",
        )

    client = _client()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=(
            "You are grading a student's short answer on a university quiz. "
            "Score 0.0-1.0 (partial credit allowed) against the reference answer, "
            "judging understanding rather than exact wording. Give one or two "
            "sentences of specific, constructive feedback."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question.question}\n\n"
                    f"Reference answer: {question.reference_answer}\n\n"
                    f"Student answer: {student_answer}"
                ),
            }
        ],
        output_format=Grade,
    )
    return response.parsed_output
