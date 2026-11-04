from app.domain.answer import Answer


def init_answers() -> list[Answer]:
    return [
        Answer(0, "둘리", "FastAPI의 장점은 무엇인가요?", "빠르고 쉽습니다", 1),
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
