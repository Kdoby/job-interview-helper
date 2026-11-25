import asyncio
import re
import time
from collections.abc import Callable

from langchain_core.documents import Document
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
from app.agents.feedback.state import FeedbackState
from app.agents.feedback.outputs import FeedbackAnalysis
from app.agents.interview.graph import build_interview_graph
from app.agents.interview.outputs import InterviewQuestion, InterviewReport, TurnGrade
from app.agents.rubric.graph import build_rubric_graph
from app.agents.rubric.outputs import (
    ConceptMatch,
    GroundedCheck,
    RelevanceGrade,
    RewrittenQuery,
    RubricFeedback,
)
from app.core.config import Settings
from app.core.thread_log import log
from app.shared.data import load_rubrics

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
# interview
# ==================================================


# 프롬프트에서 <answer>...</answer> 안의 지원자 답변만 꺼낸다
# (시스템 프롬프트에도 "모르겠습니다"라는 예시가 있어서 전체 문자열로 검사하면 안 된다)
def extract_answer(prompt) -> str:
    match = re.search(r"<answer>(.*?)</answer>", prompt.to_string(), re.DOTALL)
    return match.group(1) if match else ""


# 가짜 채점: 답변에 "모르"가 있으면 막힌 경우(→ 힌트), 아니면 잘한 경우(→ 꼬리 질문)
# 고정 점수 하나로는 route의 분기 하나만 타므로, 답변 내용으로 경로를 고를 수 있게 한다
def fake_turn_grade(prompt) -> TurnGrade:
    if "모르" in extract_answer(prompt):
        return TurnGrade(
            score=30,
            comment="(가짜 응답) 핵심 개념이 빠졌습니다.",
            missing_concepts=["(가짜 응답) 빠진 개념"],
        )
    return TurnGrade(
        score=85,
        comment="(가짜 응답) 핵심을 잘 설명했습니다.",
        missing_concepts=[],
    )


# ==================================================
# rubric
# ==================================================

# 가짜 리트리버가 항상 돌려주는 루브릭. ConceptMatch의 가짜 covered는 이 문서의 개념 이름이다
FAKE_RUBRIC_SOURCE = "jpa_n_plus_1.md"


# 프롬프트에서 마지막 <tag>...</tag> 안의 값만 꺼낸다
# (시스템 프롬프트의 INJECTION_RULE에도 "<question>" 글자가 있어서 뒤에서부터 찾는다)
def extract_last_tag(prompt, tag: str) -> str:
    text = prompt.to_string()
    start = text.rfind(f"<{tag}>")
    if start == -1:
        return ""
    start += len(f"<{tag}>")
    end = text.find(f"</{tag}>", start)
    return text[start:end] if end != -1 else text[start:]


# 가짜 관련성 판정: 질문에 "AOP"가 있으면 관련 없음(→ rewrite → 기존 피드백 그래프), 아니면 관련 있음
def fake_relevance_grade(prompt) -> RelevanceGrade:
    return RelevanceGrade(
        reason="(가짜 응답) 판정 근거",
        relevant="AOP" not in extract_last_tag(prompt, "question"),
    )


# ==================================================
# 가짜 구조화 출력 모델 (coaching, interview, rubric 공용)
# ==================================================

# 스키마별 가짜 응답. 고정 객체 또는 프롬프트를 받아 객체를 만드는 함수
# coaching: 점수를 목표(80)보다 낮게 둬서 시도 상한 → summary 경로를 확인할 수 있게 한다
FakeOutput = BaseModel | Callable[..., BaseModel]
FAKE_STRUCTURED_OUTPUTS: dict[type[BaseModel], FakeOutput] = {
    # coaching
    RetryGrade: RetryGrade(
        score=70,
        feedback="(가짜 응답) 재답변 피드백입니다.",
        missing_concepts=["(가짜 응답) 빠진 개념"],
    ),
    CompareResult: CompareResult(improvements=["(가짜 응답) 나아진 점"]),
    CoachResult: CoachResult(next_focus="(가짜 응답) 빠진 개념을 설명해 보세요."),
    CoachSummary: CoachSummary(summary="(가짜 응답) 코칭 요약입니다."),
    # interview
    TurnGrade: fake_turn_grade,
    InterviewQuestion: InterviewQuestion(question="(가짜 응답) 면접 질문입니다."),
    InterviewReport: InterviewReport(
        strong_topics=[],
        weak_concepts=["(가짜 응답) 빠진 개념"],
        summary="(가짜 응답) 면접 총평입니다.",
    ),
    # rubric: 개념 5개 중 2개를 다룬 것으로 둬서 score=40과 missing을 확인할 수 있게 한다
    RelevanceGrade: fake_relevance_grade,
    RewrittenQuery: RewrittenQuery(query="(가짜 응답) 재작성한 검색어"),
    ConceptMatch: ConceptMatch(covered=["지연 로딩과 추가 쿼리", "fetch join"]),
    RubricFeedback: RubricFeedback(
        feedback="(가짜 응답) 루브릭 기반 피드백입니다.",
        strengths=["(가짜 응답) 잘한 점 1"],
        follow_up_questions=[],
    ),
    GroundedCheck: GroundedCheck(grounded=True, reason=""),
}


class FakeStructuredChatModel:
    """with_structured_output(스키마)만 지원하는 가짜 모델. 스키마별 가짜 응답을 돌려준다."""

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds

    def with_structured_output(self, schema: type[BaseModel]) -> RunnableLambda:
        # 등록 안 된 스키마면 그래프를 만들 때 바로 KeyError가 나도록 여기서 꺼낸다
        output = FAKE_STRUCTURED_OUTPUTS[schema]

        def make(prompt) -> BaseModel:
            if callable(output):  # 함수면 프롬프트를 보고 만든다
                return output(prompt)
            return output.model_copy(deep=True)  # 리스트 필드를 호출마다 새로 만든다

        # 동기 경로(invoke)는 time.sleep, 비동기 경로(ainvoke)는 asyncio.sleep
        def fake(prompt) -> BaseModel:
            time.sleep(self.delay_seconds)
            return make(prompt)

        async def afake(prompt) -> BaseModel:
            await asyncio.sleep(self.delay_seconds)
            return make(prompt)

        return RunnableLambda(fake, afunc=afake)


# 가짜 코칭 그래프: 진짜 build_coaching_graph에 가짜 모델만 넣는다 (노드, 라우팅, 리듀서는 진짜)
def build_fake_coaching_graph(settings: Settings, checkpointer):
    return build_coaching_graph(
        FakeStructuredChatModel(settings.fake_llm_delay_seconds),
        settings.retry_max_attempts,
        checkpointer,
    )


# 가짜 면접 그래프: 진짜 build_interview_graph에 가짜 모델만 넣는다 (노드, 라우팅, 이중 상한은 진짜)
def build_fake_interview_graph(settings: Settings, checkpointer):
    return build_interview_graph(
        FakeStructuredChatModel(settings.fake_llm_delay_seconds),
        settings.interview_max_depth,
        settings.interview_max_turns,
        settings.interview_follow_up_score,
        checkpointer,
    )


# 가짜 루브릭 그래프: 진짜 build_rubric_graph에 가짜 모델과 가짜 리트리버를 넣는다 (노드, 라우팅, 상한은 진짜)
# 임베딩과 Chroma를 쓰지 않으므로 API 키와 색인이 없어도 동작한다
def build_fake_rubric_graph(settings: Settings):
    fixed = [
        doc
        for doc in load_rubrics(settings.rubric_docs)
        if doc.metadata["source"] == FAKE_RUBRIC_SOURCE
    ]

    async def fake_retrieve(query: str) -> list[Document]:
        return list(fixed)

    return build_rubric_graph(
        FakeStructuredChatModel(settings.fake_llm_delay_seconds),
        RunnableLambda(fake_retrieve),
        settings.rag_max_rewrites,
        settings.rag_max_generations,
    )
