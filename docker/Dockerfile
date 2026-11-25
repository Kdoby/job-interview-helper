# 1단계: 의존성 설치
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# 2단계: 실행 (파이썬 경로가 같도록 같은 버전과 배포판을 쓴다)
FROM python:3.14-slim-trixie
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 TZ=Asia/Seoul
RUN groupadd --system app && useradd --system --create-home --gid app app
WORKDIR /app
# 빈 볼륨은 이 폴더의 소유자를 이어받는다
RUN mkdir chroma_db && chown app:app chroma_db
COPY --from=build /app/.venv ./.venv
COPY app ./app
COPY scripts ./scripts
COPY data ./data
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]