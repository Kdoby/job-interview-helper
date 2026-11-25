from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter


# ==============================================
# Data 로드 + Chunking
# ==============================================

CONCEPTS_PREFIX = "핵심 개념:"


def load_rubrics(rubric_dir: Path) -> list[Document]:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "topic")])
    docs = []

    # rubric 문서들의 주제(section) 불러옴
    for path in sorted(rubric_dir.glob("*.md")):
        sections = splitter.split_text(path.read_text(encoding="utf-8"))

        # 파일 하나당 주제는 하나만 존재해야 함
        if len(sections) != 1:
            raise ValueError(
                f"{path.name}: '## 주제'는 파일당 하나여야 합니다. ({len(sections)}개)"
            )
        topic = sections[0].metadata["topic"]
        docs.append(
            Document(
                page_content=f"{topic}\n{sections[0].page_content}",
                metadata={"source": path.name, "topic": topic},
            )
        )
    return docs


# 줄 단위로 찾아서 쉼표로 나눔
def parse_concepts(doc: Document) -> list[str]:
    for line in doc.page_content.splitlines():
        line = line.strip()
        if line.startswith(CONCEPTS_PREFIX):
            return [
                c.strip()
                for c in line.removeprefix(CONCEPTS_PREFIX).split(",")
                if c.strip()
            ]
    return []
