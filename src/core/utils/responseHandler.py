import io
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel


class ResponseHandler:
    @staticmethod
    def generate_response(
        success: bool, code: int | None, message: str | None = None, data=None, **kwargs
    ):
        if isinstance(data, BaseModel):
            data = data.model_dump(mode="json")
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

    @staticmethod
    def generate_streaming_response(
        content: bytes, filename: str, content_type: str = "application/octet-stream"
    ):
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        stream = io.BytesIO(content)
        return StreamingResponse(stream, media_type=content_type, headers=headers)
