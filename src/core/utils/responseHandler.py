from fastapi.responses import JSONResponse, RedirectResponse


class ResponseHandler:
    @staticmethod
    def generate_response(
        success: bool, code: int | None, message: str | None = None, data=None, **kwargs
    ):
        return JSONResponse(
            status_code=code or (200 if success else 500),
            content={
                "success": success,
                "message": message,
                "data": data,
                **kwargs,
            },
        )

    @staticmethod
    def generate_redirect_response(redirect_url: str):
        return RedirectResponse(redirect_url)
