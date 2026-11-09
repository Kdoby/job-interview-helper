# interview-coach-server

면접 답변을 저장하고, 저장된 답변을 바탕으로 LLM이 면접관처럼 피드백을 주는 FastAPI 서버입니다.

- 지원자가 질문, 답변, 자신감(1~5)을 등록하면 AI 면접관이 **점수(0~100)와 피드백**을 돌려줍니다.
- 자신감이 낮으면 격려부터 시작하고, 자신감이 높으면 날카로운 **꼬리 질문**을 덧붙입니다.
- 연습할 질문이 없으면 AI에게 백엔드 기술 면접 질문을 받아 볼 수 있습니다.

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 언어 / 패키지 관리 | Python 3.14, uv |
| 웹 프레임워크 | FastAPI (`fastapi[standard]`) |
| 설정 | pydantic-settings |
| LLM | OpenAI Python SDK (Responses API, 구조화된 출력) |
| 저장소 | 메모리 딕셔너리 (서버를 끄면 데이터가 사라집니다) |

## 실행 방법

1. 의존성을 설치합니다.

   ```bash
   uv sync
   ```

2. `.env.example`을 복사해 `.env`를 만들고, `OPENAI_API_KEY`에 본인의 키를 넣습니다.

   ```bash
   cp .env.example .env
   ```

   키는 `.env` 대신 시스템 환경변수 `OPENAI_API_KEY`로 설정해도 됩니다.

3. 서버를 실행합니다.

   ```bash
   uv run fastapi dev
   ```

4. 브라우저에서 http://127.0.0.1:8000/docs 를 열어 API를 호출합니다.

### 키 없이 실행하기 (가짜 LLM)

`.env`에서 `OPENAI_API_KEY` 줄을 지우거나 `FAKE_LLM=true`로 설정하면, OpenAI를 호출하지 않는 가짜 LLM 클라이언트로 실행됩니다. 비용 없이 API 흐름만 확인할 때 사용합니다.

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 없음 | OpenAI API 키. 없으면 가짜 LLM으로 실행됩니다. |
| `OPENAI_MODEL` | `gpt-6-luna` | 사용할 모델 |
| `OPENAI_REASONING_EFFORT` | `none` | 추론 정도 (`none`, `minimal`, `low`, `medium`, `high`, `xhigh`) |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1000` | 출력 토큰 상한 |
| `OPENAI_TIMEOUT_SECONDS` | `30` | OpenAI 응답을 기다리는 최대 시간(초) |
| `FAKE_LLM` | `false` | `true`면 키가 있어도 가짜 LLM을 사용합니다. |
| `FAKE_LLM_DELAY_SECONDS` | `3` | 가짜 LLM이 응답하기 전에 기다리는 시간(초) |
| `THREAD_POOL_SIZE` | FastAPI 기본값 | (실험용) `def` 핸들러를 실행할 스레드 수 |

## API

| 메서드 | 경로 | 핸들러 | 설명 | 응답 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/answers` | `def` | 면접 답변 등록 | 201, 422 |
| `GET` | `/api/answers` | `def` | 전체 답변 목록 조회 | 200 |
| `GET` | `/api/answers/{answer_id}` | `def` | 답변 하나 조회 (피드백을 받았다면 함께 표시) | 200, 404 |
| `POST` | `/api/answers/{answer_id}/feedback` | `async def` | 저장된 답변으로 AI 피드백 생성 후 답변에 저장 | 200, 404, 502 |
| `POST` | `/api/questions` | `def` | AI가 백엔드 기술 면접 질문 생성 | 200, 502 |

### 답변 등록 `POST /api/answers`

```json
{
  "userName": "둘리",
  "question": "FastAPI의 async def는 언제 사용하나요?",
  "answer": "I/O 대기가 많은 작업을 처리할 때 사용합니다.",
  "confidence": 3
}
```

| 필드 | 규칙 |
| --- | --- |
| `userName` | 1~10자 |
| `question` | 빈 값 불가 |
| `answer` | 1~300자 |
| `confidence` | 1 이상 5 이하 정수 |

규칙에 맞지 않으면 422로 응답합니다.

### 답변 조회 `GET /api/answers/{answer_id}`

```json
{
  "answerId": 1,
  "userName": "둘리",
  "question": "FastAPI의 async def는 언제 사용하나요?",
  "answer": "I/O 대기가 많은 작업을 처리할 때 사용합니다.",
  "confidence": 3,
  "feedback": null,
  "score": null
}
```

피드백을 받기 전에는 `feedback`과 `score`가 `null`입니다.

### 피드백 생성 `POST /api/answers/{answer_id}/feedback`

```json
{
  "feedback": "I/O 대기라는 핵심은 잘 짚었습니다. 다만 이벤트 루프가 ...",
  "score": 72
}
```

- 자신감 1~2: 격려하는 문장으로 시작하고, 보완할 점을 부드럽게 제안합니다.
- 자신감 3: 잘한 점과 보완할 점을 균형 있게 짚습니다.
- 자신감 4~5: 빈틈을 날카롭게 짚고, 마지막에 `꼬리 질문:`을 덧붙입니다.

점수는 자신감과 관계없이 답변 내용만으로 매깁니다.

### 질문 생성 `POST /api/questions`

```json
{
  "question": "JPA에서 N+1 문제가 발생하는 원인과 해결 방법을 설명해 주세요."
}
```

받은 질문에 답한 뒤 `POST /api/answers`로 등록하면 피드백을 받을 수 있습니다.

### 에러 응답

```json
{
  "code": "ERROR_CODE_00001",
  "description": "조회 실패",
  "detail": "해당 답변이 존재하지 않습니다. answer_id=999"
}
```

| 상태 코드 | 코드 | 상황 |
| --- | --- | --- |
| 404 | `ERROR_CODE_00001` | 없는 답변을 조회하거나 피드백을 요청한 경우 |
| 502 | `ERROR_CODE_00011` | OpenAI 호출이 실패한 경우 (잘못된 키, 요청 한도 초과, 시간 초과, 연결 실패 등) |

## 프로젝트 구조

```text
app/
    main.py                  # lifespan(LLM 클라이언트 생성/종료), 예외 처리기, 라우터 등록
    dependencies.py          # 저장소, LLM 클라이언트, 서비스 의존성 함수
    core/
        config.py            # 환경 변수 설정 (pydantic-settings)
        exceptions.py        # AnswerNotFoundError(404), AiRequestError(502), 예외 처리기
        thread_log.py        # 핸들러가 실행되는 스레드 이름 출력
    domain/
        answer.py            # 면접 답변 엔티티
    repositories/
        answer_repository.py # 딕셔너리 저장소
    schemas/
        base.py              # camelCase 변환 기본 모델
        answer.py            # 답변 요청/응답 DTO, 피드백 응답 DTO
        question.py          # 질문 생성 응답 DTO
    clients/
        llm_client.py        # OpenAI 호출, 가짜 LLM 클라이언트
    services/
        answer_service.py    # 답변 등록, 조회
        feedback_service.py  # 프롬프트 생성, LLM 호출, 피드백 저장
        question_service.py  # 면접 질문 생성
    routers/
        answer_router.py     # 답변, 피드백 API
        question_router.py   # 질문 생성 API
```

의존 방향은 `router -> service -> repository/client`입니다. 라우터는 HTTP 요청과 응답만 다루고, 프롬프트 생성 같은 로직은 서비스에, OpenAI SDK 호출은 `llm_client.py`에만 둡니다.

## 설계 포인트

- **LLM 호출이 이벤트 루프를 막지 않습니다.** 피드백 API는 `async def`로 만들고 `AsyncOpenAI`를 `await`로 호출합니다. 호출하면 터미널에 `(스레드: MainThread)`가 출력되어 이벤트 루프에서 실행되는 것을 확인할 수 있습니다. 반면 `def`인 질문 생성 API는 `AnyIO worker thread`에서 실행됩니다.
- **LLM 클라이언트는 서버 전체에서 하나를 공유합니다.** lifespan에서 만들어 `app.state`에 저장하고, 서버가 종료될 때 연결을 닫습니다.
- **OpenAI 구조화된 출력으로 `score`와 `feedback`을 나눠 받습니다.** 응답 DTO(`AiFeedbackResponse`)를 그대로 출력 형식으로 넘깁니다.
- **지시문과 평가 데이터를 분리합니다.** 면접관 역할, 채점 규칙, 자신감별 말투는 `instructions`에, 질문과 답변은 `input`에 넣습니다. 지원자 답변에 섞인 지시를 따르지 않도록 지시문에 명시했습니다.
- **외부 서버의 실패는 502로 구분합니다.** OpenAI SDK의 예외를 `AiRequestError`로 바꿔, 우리 서버의 오류(500)와 구분해 응답합니다.
