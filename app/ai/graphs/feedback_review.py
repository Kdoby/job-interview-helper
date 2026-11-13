from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.ai.chains.feedback_chain import build_feedback_chain
from app.ai.outputs.feedback import FeedbackReview
from app.ai.prompts.feedback import REVIEW_PROMPT, REVISION_NOTE
from app.core.thread_log import log
from app.schemas.answer import AiFeedbackResponse


# 상태 정의
class FeedbackState(TypedDict):
    question: str
    answer: str
    confidence: int
    confidence_guide: str
    draft: AiFeedbackResponse
    attempts: int
    passed: bool
    review_reason: str


# 그래프 조립
def build_feedback_review_graph(llm, max_reviews: int):

    # 체인 생성
    draft_chain = build_feedback_chain(llm)
    review_chain = REVIEW_PROMPT | llm.with_structured_output(FeedbackReview)
    print("[lifespan] review_chain 생성")

    # 피드백 초안 작성 노드
    async def draft_feedback(state: FeedbackState):

        # 시도 횟수 증가
        attempts = state.get("attempts", 0) + 1
        log("draft_feedback", f"attempts={attempts}")

        # 재작성이면 review_reason을 프롬프트에 넣음
        review_reason = state.get("review_reason", "")
        revision_note = (
            REVISION_NOTE.format(reason=review_reason) if review_reason else ""
        )

        draft = await draft_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "confidence_guide": state["confidence_guide"],
                "revision_note": revision_note,
            }
        )
        return {"draft": draft, "attempts": attempts}

    # 리뷰-피드백 노드
    async def review_feedback(state: FeedbackState):
        draft = state["draft"]

        # 1. 코드 검사
        if state["confidence"] >= 4 and "꼬리 질문:" not in draft.feedback:
            reason = "자신감이 높은 지원자인데 '꼬리 질문:'으로 시작하는 꼬리 질문이 없다. 피드백 마지막에 추가한다."
            log("review_feedback", f"코드 검사 실패: {reason}")
            return {"passed": False, "review_reason": reason}

        # 2. LLM 검토
        review = await review_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "feedback": draft.feedback,
                "score": draft.score,
            }
        )

        # LLM 판정 결과
        log("review_feedback", f"passed={review.passed}, reason={review.reason}")
        return {"passed": review.passed, "review_reason": review.reason}

    # 리뷰 라우터
    def route_after_review(state: FeedbackState):
        if state["passed"] or state["attempts"] >= max_reviews:
            return END

        # 피드백 작성 노드로 돌아감
        return "draft_feedback"

    # 그래프 조립
    builder = StateGraph(FeedbackState)

    # 노드 등록
    builder.add_node("draft_feedback", draft_feedback)
    builder.add_node("review_feedback", review_feedback)

    # 엣지 등록
    builder.add_edge(START, "draft_feedback")
    builder.add_edge("draft_feedback", "review_feedback")
    builder.add_conditional_edges(
        "review_feedback", route_after_review, ["draft_feedback", END]
    )

    return builder.compile()
