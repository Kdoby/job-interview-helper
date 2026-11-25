from typing import TypedDict

from langchain_core.documents import Document

from app.agents.rubric.outputs import RubricFeedback


class RubricState(TypedDict):
    # 서비스가 채움
    question: str
    answer: str
    confidence: int
    confidence_guide: str
    query: str  # 처음에는 question과 같음. rewrite가 덮어씀
    rewrite_count: int
    generation_count: int
    reason: str  # verify가 채움. 첫 write에서 읽으므로 ""로 시작

    # 노드가 채움
    documents: list[Document]
    relevant: bool
    concepts: list[str]
    covered: list[str]
    missing: list[str]
    score: int
    result: RubricFeedback | None
    grounded: bool
