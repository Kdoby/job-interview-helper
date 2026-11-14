from dataclasses import dataclass

from langchain_core.runnables import Runnable

from app.ai.fakes import (
    build_fake_feedback_review_graph,
    build_fake_question_check_graph,
)
from app.ai.graphs.feedback_review import build_feedback_review_graph
from app.ai.graphs.question_check import build_question_check_graph
from app.ai.llm import build_chat_model
from app.core.config import Settings


@dataclass
class AiComponents:
    question_graph: Runnable  # 질문 API가 꺼내서 씀
    feedback_graph: Runnable  # 피드백 그래프


def build_ai_components(settings: Settings) -> AiComponents:

    # LLM 불러오기
    llm = build_chat_model(settings)

    # 질문 그래프
    question_graph = build_question_check_graph(
        llm, settings.question_max_regenerations
    )
    print("[lifespan] question-check 그래프 생성")

    # 피드백 그래프
    feedback_graph = build_feedback_review_graph(llm, settings.feedback_max_reviews)
    print("[lifespan] feedback-review 그래프 생성")

    return AiComponents(question_graph=question_graph, feedback_graph=feedback_graph)


def build_fake_ai_components(settings: Settings) -> AiComponents:

    question_graph = build_fake_question_check_graph(settings)
    print("[lifespan] 가짜 question-check 그래프 생성")
    feedback_graph = build_fake_feedback_review_graph(settings)
    print("[lifespan] 가짜 feedback-review 그래프 생성")

    return AiComponents(question_graph=question_graph, feedback_graph=feedback_graph)
