from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 폴더(.env 파일이 있는 곳)를 기준 위치로 잡는다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # DTO의 model_config와 동일하게, 클래스 변수 model_config에 설정을 적는다.
    model_config = SettingsConfigDict(
        # .env 파일의 위치와 인코딩
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        # 이 클래스에 없는 환경 변수는 무시한다
        extra="ignore",
    )

    # OpenAI API 키
    openai_api_key: SecretStr | None = None

    # 사용할 모델
    openai_model: str = "gpt-6-luna"

    # 추론 정도
    openai_reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh"
    ] = "none"

    # 출력 토큰 상한 : 상한을 넘으면 응답이 중간에 끊긴다. 0보다 커야 한다.
    openai_max_output_tokens: int = Field(default=1000, gt=0)

    # OpenAI의 응답을 기다리는 최대 시간(초). 0보다 커야 한다.
    openai_timeout_seconds: float = Field(default=30.0, gt=0)

    # 가짜 LLM : true면 키가 있어도 OpenAI를 호출하지 않는다. 비용 없이 시험하거나 성능을 잴 때 사용한다.
    fake_llm: bool = False

    # 가짜 LLM이 응답하기 전에 기다리는 시간(초). 실제 LLM의 응답 시간을 흉내 낸다. 0 이상이어야 한다.
    fake_llm_delay_seconds: float = Field(default=3.0, ge=0)

    # 실험용 : def 핸들러를 실행할 스레드의 수. None이면 FastAPI의 기본값(40개)을 그대로 사용한다.
    # 1로 줄이면 def 핸들러가 한 번에 하나씩만 실행되는 것을 눈으로 확인할 수 있다(routers/ai_router.py의 실험 2).
    thread_pool_size: int | None = Field(default=None, ge=1)

    feedback_max_reviews: int = Field(default=2, ge=1)
    question_max_regenerations: int = Field(default=2, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
