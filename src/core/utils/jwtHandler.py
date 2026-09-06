import jwt
from core.dtos.baseDtos import BaseResponseDto


class JWTHandler:
    @staticmethod
    def encode_jwt(
        payload: dict, secret_key: str | None, algorithm: str
    ) -> BaseResponseDto[str]:
        try:
            if not secret_key:
                return BaseResponseDto(
                    success=False,
                    data=None,
                    message="An Error Occurred, please try again later",
                    error="Secret key is not provided",
                )
            token = jwt.encode(payload, secret_key, algorithm=algorithm)
            return BaseResponseDto(success=True, data=token)
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                data=None,
                message="An Error Occurred, please try again later",
                error=repr(ex),
            )

    @staticmethod
    def decode_jwt(
        token: str | None, secret_key: str | None, algorithms: list[str]
    ) -> BaseResponseDto[dict]:
        try:
            if not token:
                return BaseResponseDto(
                    success=False,
                    data=None,
                    message="Token is not provided",
                    error="Token is not provided",
                )
            if not secret_key:
                return BaseResponseDto(
                    success=False,
                    data=None,
                    message="An Error Occurred, please try again later",
                    error="Secret key is not provided",
                )
            payload = jwt.decode(token, secret_key, algorithms=algorithms)
            return BaseResponseDto(success=True, data=payload)
        except jwt.ExpiredSignatureError:
            return BaseResponseDto(
                success=False,
                data=None,
                message="Token has expired",
                error="Token has expired",
            )
        except jwt.InvalidTokenError:
            return BaseResponseDto(
                success=False, data=None, message="Invalid token", error="Invalid token"
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                data=None,
                message="An Error Occurred, please try again later",
                error=repr(ex),
            )
