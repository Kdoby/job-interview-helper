from app.core.config import get_settings
from app.shared.data import load_rubrics, parse_concepts
from app.shared.models import build_embeddings
from app.shared.retrieval import open_vectorstore

# ==============================================
# Embedding + vectorstore 저장
# ==============================================

TEST_QUERIES = [
    "목록 조회할 때 댓글 때문에 쿼리가 100번 나가요. 왜 그런가요?",
    "Spring AOP 프록시는 어떻게 동작하나요?",
]


def main() -> None:
    settings = get_settings()
    docs = load_rubrics(settings.rubric_docs)

    for doc in docs:
        concepts = parse_concepts(doc)
        if not concepts:
            raise ValueError(f"{doc.metadata['source']}: '핵심 개념:' 줄이 없습니다.")
        print(
            f"{doc.metadata['source']} | {doc.metadata['topic']} | 개념 {len(concepts)}개"
        )

    # 벡터 스토어에 문서 임베딩해서 저장
    store = open_vectorstore(settings, build_embeddings(settings))
    # 지운 루브릭이 남지 않게 비우고 다시 저장
    store.reset_collection()
    store.add_documents(docs, ids=[d.metadata["source"] for d in docs])

    # 저장된 루브릭: N개
    print(len(store.get()["ids"]))

    for q in TEST_QUERIES:
        for doc, score in store.similarity_search_with_score(q, k=settings.rag_top_k):
            print(f"score: {score}, source: {doc.metadata['source']}")


if __name__ == "__main__":
    main()
