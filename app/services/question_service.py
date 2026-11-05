import random

from app.clients.llm_client import LlmClient
from app.schemas.question import AiQuestionResponse

TOPICS = [
    # Spring
    "Spring IoC와 DI",
    "Spring Bean 생명주기와 스코프",
    "Spring AOP와 프록시",
    "@Transactional 전파 속성",
    "Spring MVC 요청 처리 흐름",
    "필터와 인터셉터의 차이",
    "Spring Security 인증과 인가",
    "JWT와 세션 인증",
    "Spring Boot 자동 설정",
    "Spring의 전역 예외 처리",
    # JPA
    "JPA 영속성 컨텍스트",
    "JPA N+1 문제",
    "지연 로딩과 즉시 로딩",
    "JPA 낙관적 락과 비관적 락",
    # FastAPI / Python
    "FastAPI 의존성 주입",
    "FastAPI의 async와 이벤트 루프",
    "FastAPI에서 def와 async def의 차이",
    "FastAPI lifespan",
    "Pydantic 데이터 검증",
    "Python GIL",
    "Python 코루틴과 asyncio",
    "ASGI와 WSGI의 차이",
    # MySQL
    "MySQL 인덱스와 B+Tree",
    "복합 인덱스와 컬럼 순서",
    "커버링 인덱스",
    "EXPLAIN 실행 계획 분석",
    "MySQL 트랜잭션 격리 수준",
    "InnoDB MVCC",
    "MySQL 락과 데드락",
    "정규화와 반정규화",
    "슬로우 쿼리 튜닝",
    "페이지네이션 성능 최적화",
    "MySQL 복제와 읽기 분산",
    "샤딩과 파티셔닝",
    # 네트워크 / 웹
    "HTTP 메서드와 멱등성",
    "HTTP 상태 코드 설계",
    "HTTPS와 TLS 핸드셰이크",
    "TCP와 UDP의 차이",
    "REST API 설계",
    "CORS",
    "웹소켓과 SSE",
    "로드 밸런싱",
    # 운영체제 / 동시성
    "프로세스와 스레드의 차이",
    "스레드 풀 크기 설정",
    "동기와 비동기, 블로킹과 논블로킹",
    "경쟁 상태와 동시성 제어",
    "데드락의 조건과 해결",
    # 시스템 설계 / 인프라
    "캐시 전략과 캐시 무효화",
    "Redis 활용과 자료구조",
    "메시지 큐와 비동기 처리",
    "분산 트랜잭션과 사가 패턴",
    "분산 락",
    "API 속도 제한",
    "모놀리식과 MSA",
    "Docker 컨테이너와 이미지",
    "CI/CD와 무중단 배포",
    "로깅과 모니터링",
    # 보안 / 품질
    "SQL 인젝션과 XSS 방어",
    "비밀번호 해싱과 솔트",
    "단위 테스트와 통합 테스트",
    "SOLID 원칙",
]

INSTRUCTIONS = (
    "너는 IT 회사의 20년차 개발자이고 면접관으로 기술 면접에 참석할 예정이다. 면접 대상자들은 백엔드 개발 직군에 지원했다."
    "백엔드 기술에 관련한 면접 질문을 선정한다. Spring, FastAPI, MySQL에 관련한 지식이 주가 되어야 하며, 이외의 질문들도 "
    "예상치 못한 질문으로 괜찮다. 부연 설명 없이 질문 문장 하나만 출력한다."
)


class QuestionService:
    def __init__(self, llm_client: LlmClient):
        self.llm_client = llm_client

    def generate_question(self) -> AiQuestionResponse:

        topic = random.choice(TOPICS)
        prompt = f"'{topic}' 주제로 면접 질문을 1개 생성해줘."

        result = self.llm_client.ask(INSTRUCTIONS, prompt)

        return AiQuestionResponse(question=result)
