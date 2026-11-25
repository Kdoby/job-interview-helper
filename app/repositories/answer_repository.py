from app.domain.answer import Answer


def init_answers() -> list[Answer]:
    return [
        Answer(0, "둘리", "FastAPI의 장점은 무엇인가요?", "빠르고 쉽습니다", 1),
        # 루브릭 있음 (RAG)
        Answer(
            0,
            "또치",
            "게시글 목록을 조회할 때 댓글 때문에 쿼리가 100번 넘게 나갑니다. 원인과 해결 방법은 무엇인가요?",
            "댓글이 지연 로딩이라 게시글마다 댓글에 접근할 때 조회 쿼리가 하나씩 더 나갑니다. join fetch로 한 번에 조회하거나, batch size를 설정해 IN 절로 묶어서 조회하면 쿼리 수를 줄일 수 있습니다.",
            3,
        ),
        Answer(
            0,
            "도우너",
            "JPA N+1 문제는 어떻게 해결하나요?",
            "연관관계를 즉시 로딩(EAGER)으로 바꾸면 조인으로 한 번에 가져오기 때문에 해결됩니다.",
            4,
        ),
        Answer(
            0,
            "희동이",
            "지연 로딩에서 LazyInitializationException은 왜 발생하나요?",
            "지연 로딩은 연관 엔티티 자리에 프록시 객체를 넣어 두고 처음 접근할 때 DB를 조회합니다. 그런데 트랜잭션이 끝나 영속성 컨텍스트가 닫힌 뒤에 프록시에 접근하면 초기화할 수 없어서 예외가 발생합니다.",
            3,
        ),
        Answer(
            0,
            "고길동",
            "FastAPI 핸들러 안에서 time.sleep을 쓰면 왜 다른 요청까지 느려질 수 있나요?",
            "async def 핸들러는 이벤트 루프에서 직접 실행되므로 블로킹 호출을 하면 루프가 멈춰 다른 요청도 모두 기다립니다. def로 선언하면 스레드 풀의 작업 스레드에서 실행되어 이벤트 루프를 막지 않습니다.",
            4,
        ),
        Answer(
            0,
            "마이콜",
            "MySQL의 트랜잭션 격리 수준을 설명해 주세요.",
            "READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE이 있고 뒤로 갈수록 정합성이 높고 동시성이 낮습니다. 커밋 전 값을 읽는 것이 Dirty Read, 같은 행의 값이 달라지는 것이 Non-Repeatable Read, 범위 조회의 행이 달라지는 것이 Phantom Read입니다. InnoDB 기본값은 REPEATABLE READ이고, MVCC로 undo 로그의 스냅샷을 읽어 잠금 없이 조회합니다.",
            5,
        ),
        Answer(
            0,
            "둘리",
            "MySQL의 트랜잭션 격리 수준을 설명해 주세요.",
            "잘 모르겠습니다.",
            1,
        ),
        Answer(
            0,
            "또치",
            "@Transactional의 전파 속성 REQUIRED와 REQUIRES_NEW의 차이는 무엇인가요?",
            "REQUIRED는 기본값으로 진행 중인 트랜잭션이 있으면 참여하고 없으면 새로 시작합니다. REQUIRES_NEW는 기존 트랜잭션을 보류하고 항상 새 트랜잭션을 시작합니다. REQUIRED로 참여한 내부에서 예외가 나도 외부에서 catch하면 외부는 정상 커밋됩니다.",
            4,
        ),
        # 루브릭 없음 (기존 피드백 그래프)
        Answer(
            0,
            "도우너",
            "Spring AOP는 어떻게 동작하나요?",
            "프록시 객체가 메서드 호출을 가로채서 트랜잭션이나 로깅 같은 부가 기능을 실행한 뒤 실제 객체의 메서드를 호출합니다.",
            3,
        ),
        Answer(
            0,
            "희동이",
            "HTTP와 HTTPS의 차이는 무엇인가요?",
            "HTTPS는 TLS로 통신 내용을 암호화하고 인증서로 서버를 확인합니다.",
            2,
        ),
        Answer(
            0,
            "고길동",
            "낙관적 락과 비관적 락의 차이는 무엇인가요?",
            "낙관적 락은 버전 컬럼으로 커밋할 때 충돌을 확인하고, 비관적 락은 SELECT FOR UPDATE로 먼저 행을 잠가 다른 트랜잭션의 수정을 막습니다.",
            3,
        ),
    ]


class AnswerRepository:
    def __init__(self):

        self._answers: dict[int, Answer] = {}
        self._next_id = 1

        for answer in init_answers():
            self.save(answer)

    # 전체 답변 조회
    def find_all(self) -> list[Answer]:

        return list(self._answers.values())

    # 단일 답변 조회
    def find_by_id(self, answer_id: int) -> Answer:

        return self._answers.get(answer_id)

    # 답변 저장
    def save(self, answer: Answer) -> Answer:

        # 신규 답변인 경우, 번호를 붙이고 다음 번호를 하나 올림
        if answer.answer_id == 0:
            answer.answer_id = self._next_id
            self._next_id += 1

        self._answers[answer.answer_id] = answer

        return answer
