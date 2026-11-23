from typing import TypedDict


class QuestionState(TypedDict):
    topic: str
    question: str
    attempts: int
    reason: str
    passed: bool
