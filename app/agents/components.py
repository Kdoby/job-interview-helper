from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.agents.coaching.graph import build_coaching_graph
from app.agents.fakes import (
    build_fake_coaching_graph,
    build_fake_feedback_review_graph,
    build_fake_feedback_stream_graph,
    build_fake_interview_graph,
    build_fake_question_check_graph,
    build_fake_rubric_graph,
)
from app.agents.feedback.graph import build_feedback_review_graph
from app.agents.interview.graph import build_interview_graph
from app.agents.rubric.graph import build_rubric_graph
from app.shared.models import build_chat_model, build_embeddings
from app.agents.question.graph import build_question_check_graph
from app.core.config import Settings
from app.shared.retrieval import is_empty, open_vectorstore

# state에 Pydantic 객체를 넣으면 여기에 추가
CHECKPOINT_ALLOWED_TYPES = [
    ("app.agents.coaching.outputs", "RetryGrade"),
    ("app.agents.interview.outputs", "TurnGrade"),
    ("app.agents.interview.outputs", "InterviewReport"),
]


def build_checkpointer() -> InMemorySaver:
    return InMemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_ALLOWED_TYPES)
    )


@dataclass
class AiComponents:
    question_graph: Runnable  # 질문 API가 꺼내서 씀
    feedback_graph: Runnable  # 피드백 그래프
    feedback_stream_graph: Runnable  # 피드백 스트림 그래프
    coaching_graph: Runnable  # 코칭 그래프
    interview_graph: Runnable  # 인터뷰 그래프
    rubric_graph: Runnable  # 루브릭 그래프(RAG)


def build_ai_components(settings: Settings) -> AiComponents:

    # LLM 불러오기
    llm = build_chat_model(settings)
    checkpointer = build_checkpointer()

    # 질문 그래프
    question_graph = build_question_check_graph(
        llm, settings.question_max_regenerations
    )
    print("[lifespan] question-check 그래프 생성")

    # 피드백 그래프
    feedback_graph = build_feedback_review_graph(llm, settings.feedback_max_reviews)
    print("[lifespan] feedback-review 그래프 생성")

    # 피드백 스트림 그래프
    feedback_stream_graph = build_feedback_review_graph(llm, 1)
    print("[lifespan] feedback-stream 그래프 생성")

    # 코칭 그래프
    coaching_graph = build_coaching_graph(
        llm,
        settings.retry_max_attempts,
        checkpointer=checkpointer,
    )
    print("[lifespan] coaching 그래프 생성")

    interview_graph = build_interview_graph(
        llm,
        settings.interview_max_depth,
        settings.interview_max_turns,
        settings.interview_follow_up_score,
        checkpointer=checkpointer,
    )
    print("[lifespan] interview 그래프 생성")

    store = open_vectorstore(settings, build_embeddings(settings))
    if is_empty(store):
        print(
            "[lifespan] 경고: 루브릭 색인이 비어 있음. scripts.build_rubric_index를 먼저 실행하세요"
        )

    rubric_graph = build_rubric_graph(
        llm,
        store.as_retriever(search_kwargs={"k": settings.rag_top_k}),
        settings.rag_max_rewrites,
        settings.rag_max_generations,
    )
    print("[lifespan] rubric 그래프 생성")

    return AiComponents(
        question_graph=question_graph,
        feedback_graph=feedback_graph,
        feedback_stream_graph=feedback_stream_graph,
        coaching_graph=coaching_graph,
        interview_graph=interview_graph,
        rubric_graph=rubric_graph,
    )


def build_fake_ai_components(settings: Settings) -> AiComponents:

    checkpointer = build_checkpointer()

    question_graph = build_fake_question_check_graph(settings)
    print("[lifespan] 가짜 question-check 그래프 생성")
    feedback_graph = build_fake_feedback_review_graph(settings)
    print("[lifespan] 가짜 feedback-review 그래프 생성")
    feedback_stream_graph = build_fake_feedback_stream_graph(settings)
    print("[lifespan] 가짜 feedback-stream 그래프 생성")
    coaching_graph = build_fake_coaching_graph(
        settings,
        checkpointer=checkpointer,
    )
    print("[lifespan] 가짜 coaching 그래프 생성")
    interview_graph = build_fake_interview_graph(settings, checkpointer=checkpointer)
    print("[lifespan] 가짜 interview 그래프 생성")
    rubric_graph = build_fake_rubric_graph(settings)
    print("[lifespan] 가짜 rubric 그래프 생성")

    return AiComponents(
        question_graph=question_graph,
        feedback_graph=feedback_graph,
        feedback_stream_graph=feedback_stream_graph,
        coaching_graph=coaching_graph,
        interview_graph=interview_graph,
        rubric_graph=rubric_graph,
    )
