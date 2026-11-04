from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI

from app.clients.llm_client import FakeLlmClient, OpenAiLlmClient
from app.core.config import get_settings
from app.core.exceptions import register_exception_handler
from app.routers import answer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. 설정을 가져온다.
    settings = get_settings()

    # 1. 서버 시작 : 모든 요청이 함께 사용할 LLM 클라이언트를 만들어 app.state에 저장한다.
    if settings.fake_llm or settings.openai_api_key is None:
        print(
            f"[lifespan] 가짜 LLM 클라이언트를 사용한다 (FAKE_LLM={settings.fake_llm}, "
            f"키 있음={settings.openai_api_key is not None}, 응답까지 {settings.fake_llm_delay_seconds}초)"
        )
        app.state.llm_client = FakeLlmClient(settings)
    # 1-2. 키가 있으면 실제 OpenAI 클라이언트를 만든다.
    else:
        print(
            f"[lifespan] OpenAI 클라이언트를 사용한다 (model={settings.openai_model})"
        )
        app.state.llm_client = OpenAiLlmClient(settings)

    # 2. 실험용 : 설정에 THREAD_POOL_SIZE가 있으면 def 핸들러를 실행하는 스레드 풀의 크기를 바꾼다.
    if settings.thread_pool_size is not None:
        anyio.to_thread.current_default_thread_limiter().total_tokens = (
            settings.thread_pool_size
        )
        print(f"[lifespan] 스레드 풀 크기 : {settings.thread_pool_size}개")

    # 3. yield : 서버는 이 지점에서 멈춰 있는 동안 요청을 받는다.
    yield

    # 4. 서버 종료 : OpenAI 서버와의 연결을 닫는다. close()가 async def라서 await가 필요하다.
    await app.state.llm_client.close()


# 1. 앱 객체 생성
app = FastAPI(title="모의 면접 헬퍼 서버", version="1.0.0", lifespan=lifespan)

# 2. 예외 처리기 등록
register_exception_handler(app)

# 3. 라우터 등록
app.include_router(answer_router.router)
