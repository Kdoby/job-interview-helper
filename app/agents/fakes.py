import asyncio
import time

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.coaching.graph import build_coaching_graph
from app.agents.coaching.outputs import (
    CoachResult,
    CoachSummary,
    CompareResult,
    RetryGrade,
)
from app.agents.feedback.graph import FeedbackState
from app.agents.feedback.outputs import FeedbackAnalysis
from app.core.config import Settings
from app.core.thread_log import log

# ==================================================
# feedback
# ==================================================

FAKE_STREAM_FEEDBACK = (
    "(가짜 응답) 스트리밍 피드백입니다. 이 문장은 단어 단위로 나뉘어 도착합니다."
)


# 가짜 그래프들이 같이 쓰는 고정 분석 결과
def build_fake_analysis() -> FeedbackAnalysis:
    return FeedbackAnalysis(
        score=80,
        strengths=["(가짜 응답) 잘한 부분 1"],
        missing_concepts=["(가짜 응답) 놓친 개념 1"],
        follow_up_questions=["(가짜 응답) 꼬리 질문 1"],
        level="보통",
    )


# (기존) 가짜 피드백-리뷰 그래프: "analysis"에 build_fake_analysis()를 쓰도록만 바꾼다
def build_fake_feedback_review_graph(settings: Settings):
    async def fake_feedback_review(input: dict) -> dict:
        await asyncio.sleep(settings.fake_llm_delay_seconds)
        return {
            "feedback": "(가짜 응답) 피드백입니다.",
            "analysis": build_fake_analysis(),
            "attempts": 1,
        }

    return RunnableLambda(fake_feedback_review)


# 가짜 피드백 스트림 그래프
# RunnableLambda는 stream_mode="messages"의 (chunk, metadata) 모양을 못 내므로 진짜 StateGraph로 만든다
def build_fake_feedback_stream_graph(settings: Settings):

    async def generate(state: FeedbackState):
        log("feedback.generate", "가짜 feedback 스트리밍 시작...")

        # iter는 한 번 쓰면 끝나므로 호출마다 새로 만든다
        llm = GenericFakeChatModel(
            messages=iter([AIMessage(content=FAKE_STREAM_FEEDBACK)])
        )

        feedback = ""
        # GenericFakeChatModel은 공백 기준으로 잘라 청크를 낸다
        async for chunk in llm.astream("ignored"):
            feedback += chunk.text
            await asyncio.sleep(0.1)  # 토큰이 나눠 오는 걸 눈으로 보려고 넣는 지연
        return {"feedback": feedback}

    async def analyze(state: FeedbackState):
        log("feedback.analyze", "가짜 analysis 반환")
        return {"analysis": build_fake_analysis(), "attempts": 1}

    builder = StateGraph(FeedbackState)
    builder.add_node("generate", generate)
    builder.add_node("analyze", analyze)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()


# ==================================================
# question
# ==================================================


# 가짜 질문-검증 그래프
def build_fake_question_check_graph(settings: Settings):
    def fake_question_check(input: dict) -> dict:
        time.sleep(settings.fake_llm_delay_seconds)
        return {
            "question": "(가짜 응답) 가짜 질문과 검증입니다.",
            "attempts": 1,
        }

    return RunnableLambda(fake_question_check)


# ==================================================
# coaching
# ==================================================

# 스키마별 고정 응답. 점수는 목표(80)보다 낮게 둬서 시도 상한 → summary 경로를 확인할 수 있게 한다
FAKE_STRUCTURED_OUTPUTS: dict[type[BaseModel], BaseModel] = {
    RetryGrade: RetryGrade(
        score=70,
        feedback="(가짜 응답) 재답변 피드백입니다.",
        missing_concepts=["(가짜 응답) 빠진 개념"],
    ),
    CompareResult: CompareResult(improvements=["(가짜 응답) 나아진 점"]),
    CoachResult: CoachResult(next_focus="(가짜 응답) 빠진 개념을 설명해 보세요."),
    CoachSummary: CoachSummary(summary="(가짜 응답) 코칭 요약입니다."),
}


class FakeStructuredChatModel:
    """with_structured_output(스키마)만 지원하는 가짜 모델. 스키마별 고정 객체를 돌려준다."""

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds

    def with_structured_output(self, schema: type[BaseModel]) -> RunnableLambda:
        # 등록 안 된 스키마면 그래프를 만들 때 바로 KeyError가 나도록 여기서 꺼낸다
        output = FAKE_STRUCTURED_OUTPUTS[schema]

        # 동기 경로(invoke)는 time.sleep, 비동기 경로(ainvoke)는 asyncio.sleep
        def fake(_prompt) -> BaseModel:
            time.sleep(self.delay_seconds)
            return output.model_copy(deep=True)  # 리스트 필드를 호출마다 새로 만든다

        async def afake(_prompt) -> BaseModel:
            await asyncio.sleep(self.delay_seconds)
            return output.model_copy(deep=True)

        return RunnableLambda(fake, afunc=afake)


# 가짜 코칭 그래프: 진짜 build_coaching_graph에 가짜 모델만 넣는다 (노드, 라우팅, 리듀서는 진짜)
def build_fake_coaching_graph(settings: Settings, checkpointer):
    return build_coaching_graph(
        FakeStructuredChatModel(settings.fake_llm_delay_seconds),
        settings.retry_max_attempts,
        checkpointer,
    )
