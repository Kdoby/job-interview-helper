from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AnswerNotFoundError(Exception):
    def __init__(self, answer_id: int):
        super().__init__(f"해당 답변이 존재하지 않습니다. answer_id={answer_id}")
        self.answer_id = answer_id


class AiRequestError(Exception):
    pass


def register_exception_handler(app: FastAPI) -> None:

    @app.exception_handler(AnswerNotFoundError)
    def handle_answer_not_found(request: Request, e: AnswerNotFoundError):

        return JSONResponse(
            status_code=404,
            content={
                "code": "ERROR_CODE_00001",
                "description": "조회 실패",
                "detail": str(e),
            },
        )

    # OpenAI 호출이 실패하면 502 Bad Gateway로 응답한다.
    # 502는 "우리 서버가 호출한 다른 서버가 실패했다"는 뜻이다. 우리 서버의 잘못(500)과 구분한다.
    @app.exception_handler(AiRequestError)
    def handle_ai_request_error(request: Request, e: AiRequestError):
        return JSONResponse(
            status_code=502,
            content={
                "code": "ERROR_CODE_00011",
                "description": "AI 응답 실패",
                "detail": str(e),
            },
        )
