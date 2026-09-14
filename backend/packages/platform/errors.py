from fastapi.responses import JSONResponse


def result_response(status: int, code: int, message: str, data: object = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"code": code, "message": message, "data": data}
    )


def unauthorized_result() -> JSONResponse:
    return result_response(401, 401, "请先登录")
