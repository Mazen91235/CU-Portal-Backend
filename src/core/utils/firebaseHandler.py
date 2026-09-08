# app/core/firebase.py
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, messaging
from core.dtos.baseDtos import BaseResponseDto

load_dotenv()  # Load environment variables from .env file


class FirebaseHandler:
    @staticmethod
    def init_firebase():
        if not firebase_admin._apps:
            cert_dict = {
                "type": os.getenv("FIREBASE_TYPE"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY"),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv(
                    "FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
                ),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
                "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
            }

            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred)

    @staticmethod
    def send_notification(
        device_token: str,
        title: str,
        body: str,
        url: str | None = None,
        notification_id: int | None = None,
        icon: str | None = None,
    ) -> BaseResponseDto[str]:
        if not url or url.strip().startswith("/"):
            url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}{url or '/'}"
        if not icon or icon.strip().startswith("/"):
            icon = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}{icon or '/logo.png'}"
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                "url": url,
                "icon": icon,
                "notification_id": (
                    str(notification_id) if notification_id is not None else None
                ),
            },
            token=device_token,
            # Web push specific overrides
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(icon=icon),
                fcm_options=messaging.WebpushFCMOptions(
                    link=url,
                ),
            ),
        )

        try:
            response = messaging.send(message)
            return BaseResponseDto(
                success=True,
                code=200,
                data=response,
                message="Notification sent successfully",
            )
        except messaging.UnregisteredError:  # Token is invalid or user unsubscribed
            return BaseResponseDto(
                success=False,
                code=404,
                data=None,
                message="Device token is unregistered or invalid",
            )
        except Exception as e:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"Failed to send notification",
                error=repr(e),
            )
