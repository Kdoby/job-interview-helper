from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.core.config import Settings

RUBRIC_COLLECTION = "rubrics"


def open_vectorstore(settings: Settings, embeddings: Embeddings) -> Chroma:
    return Chroma(
        collection_name=RUBRIC_COLLECTION,
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_persist_dir),
    )


def is_empty(store: Chroma) -> bool:
    return not store.get(limit=1)["ids"]
