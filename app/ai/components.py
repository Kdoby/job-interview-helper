from dataclasses import dataclass

from langchain_core.runnables import Runnable

from app.ai.chains.question_chain import build_question_chain
from app.ai.fakes import build_fake_feedback_review_graph, build_fake_question_chain
from app.ai.graphs.feedback_review import build_feedback_review_graph
from app.ai.llm import build_chat_model
from app.core.config import Settings


@dataclass
class AiComponents:
    # feedback_chain: Runnable  # 피드백 API가 꺼내서 씀
    question_chain: Runnable  # 질문 API가 꺼내서 씀
    feedback_graph: Runnable  # 피드백 그래프


def build_ai_components(settings: Settings) -> AiComponents:

    # LLM 불러오기
    llm = build_chat_model(settings)

    question = build_question_chain(llm)
    print("[lifespan] question 체인 생성")

    feedback_graph = build_feedback_review_graph(llm, settings.feedback_max_reviews)
    print("[lifespan] feedback-review 그래프 생성")

    return AiComponents(question_chain=question, feedback_graph=feedback_graph)


def build_fake_ai_components(settings: Settings) -> AiComponents:

    question = build_fake_question_chain(settings)
    print("[lifespan] 가짜 question 체인 생성")
    feedback_graph = build_fake_feedback_review_graph(settings)
    print("[lifespan] 가짜 feedback-review 그래프 생성")

    return AiComponents(question_chain=question, feedback_graph=feedback_graph)
