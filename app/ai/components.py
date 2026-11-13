from dataclasses import dataclass

from langchain_core.runnables import Runnable

from app.ai.chains.feedback_chain import build_feedback_chain
from app.ai.chains.question_chain import build_question_chain
from app.ai.fakes import build_fake_feedback_chain, build_fake_question_chain
from app.ai.llm import build_chat_model
from app.core.config import Settings

# 체인 등록


@dataclass
class AiComponents:
    feedback_chain: Runnable  # 피드백 API가 꺼내서 씀
    question_chain: Runnable  # 질문 API가 꺼내서 씀


def build_ai_components(settings: Settings) -> AiComponents:
    llm = build_chat_model(settings)
    feedback = build_feedback_chain(llm)
    print("[lifespan] feedback 체인 생성")
    question = build_question_chain(llm)
    print("[lifespan] question 체인 생성")

    return AiComponents(feedback_chain=feedback, question_chain=question)


def build_fake_ai_components(settings: Settings) -> AiComponents:
    feedback = build_fake_feedback_chain(settings)
    print("[lifespan] 가짜 feedback 체인 생성")
    question = build_fake_question_chain(settings)
    print("[lifespan] 가짜 question 체인 생성")

    return AiComponents(feedback_chain=feedback, question_chain=question)
