from typing import Generic, TypeVar

T = TypeVar("T")


class BaseResponseDto(Generic[T]):
    def __init__(
        self,
        success: bool,
        code: int = 200,
        message: str = "",
        error: str = "",
        data: T = None,
    ):
        self.success = success
        self.code = code
        self.message = message
        self.error = error
        self.data = data

    def to_dict(self):
        return {
            "success": self.success,
            "code": self.code,
            "message": self.message,
            "error": self.error,
            "data": self.data,
        }
