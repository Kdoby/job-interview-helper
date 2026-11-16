import asyncio
import time

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph

from app.agents.feedback.graph import FeedbackState
from app.agents.feedback.outputs import FeedbackAnalysis
from app.core.config import Settings
from app.core.thread_log import log

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


# 가짜 질문-검증 그래프
def build_fake_question_check_graph(settings: Settings):
    def fake_question_check(input: dict) -> dict:
        time.sleep(settings.fake_llm_delay_seconds)
        return {
            "question": "(가짜 응답) 가짜 질문과 검증입니다.",
            "attempts": 1,
        }

    return RunnableLambda(fake_question_check)
