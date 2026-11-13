import asyncio
import time

# 보통 함수를 체인처럼 .invoke()/.ainvoke()로 부를 수 있게 감싸줌
from langchain_core.runnables import RunnableLambda

from app.core.config import Settings
from app.schemas.answer import AiFeedbackResponse


# 가짜 질문 생성 체인
def build_fake_question_chain(settings: Settings):
    def fake_question(input: dict) -> str:
        time.sleep(settings.fake_llm_delay_seconds)
        return f"(가짜 응답) '{input['topic']}' 주제 질문입니다."

    return RunnableLambda(fake_question)


# 가짜 피드백-리뷰 그래프
def build_fake_feedback_review_graph(settings: Settings):
    async def fake_feedback_review(input: dict) -> dict:
        await asyncio.sleep(settings.fake_llm_delay_seconds)
        return {
            "draft": AiFeedbackResponse(
                feedback="(가짜 응답) 피드백과 리뷰입니다.", score=80
            ),
            "attempts": 1,
        }

    return RunnableLambda(fake_feedback_review)
