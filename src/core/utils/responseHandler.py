from fastapi.responses import JSONResponse


class ResponseHandler:
    @staticmethod
    def generate_response(
        success: bool, code: int, message: str = "", data=None, **kwargs
    ):
        return JSONResponse(
            status_code=code,
            content={
                "success": success,
                "message": message,
                "data": data,
                **kwargs,
            },
        )
