from werkzeug.exceptions import HTTPException

from app.utils.responses import error_response


class ApiError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400, details=None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            status=error.status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(_error):
        return error_response(
            error_code="NOT_FOUND",
            message="요청한 경로를 찾을 수 없습니다.",
            status=404,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if isinstance(error, HTTPException):
            return error_response(
                error_code=error.name.upper().replace(" ", "_"),
                message=error.description,
                status=error.code or 500,
            )

        if app.config.get("TESTING"):
            raise error

        return error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다.",
            status=500,
        )
