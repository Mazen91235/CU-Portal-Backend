import os
import sys
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Ensure `src` is importable as the top-level package root in serverless runtimes.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from api.di.container import Container
from api.routes.customRoute import CustomRoute
from business.contextVars.requestContext import request_context
from business.contextVars.sessionContext import session_context

# Imports for Model Rebuild and Open-API Schema Generation
from core.dtos.baseDtos import *
from core.dtos.announcementDtos import *
from core.dtos.attachmentDtos import *
from core.dtos.calendarDtos import *
from core.dtos.departmentDtos import *
from core.dtos.exactRoleDtos import *
from core.dtos.examDtos import *
from core.dtos.noteDtos import *
from core.dtos.eventDtos import *
from core.dtos.facultyDtos import *
from core.dtos.logDtos import *
from core.dtos.materialDtos import *
from core.dtos.messageDtos import *
from core.dtos.notificationDtos import *
from core.dtos.pendingUserDtos import *
from core.dtos.requestLimitDtos import *
from core.dtos.roleDtos import *
from core.dtos.subjectDtos import *
from core.dtos.taskDtos import *
from core.dtos.userDtos import *
from core.dtos.userNotificationDtos import *
from core.dtos.userSubjectLinkDtos import *
from core.dtos.weekDtos import *
from core.dtos.yearDtos import *
from core.entities.department import Department
from core.entities.faculty import Faculty
from core.entities.notification import Notification
from core.entities.subject import Subject
from core.entities.task import Task
from core.entities.announcement import Announcement
from core.entities.user import User
from core.entities.event import Event

load_dotenv()  # Load environment variables from .env file


def rebuild_response_dtos() -> None:
    dto_namespace = {
        name: value for name, value in globals().items() if name.endswith("Dto")
    }
    response_dtos = tuple(dto_namespace.values())
    dto_namespace.update(
        Department=Department,
        Faculty=Faculty,
        Subject=Subject,
        Task=Task,
        Announcement=Announcement,
        Notification=Notification,
        User=User,
        Event=Event,
    )
    for dto in response_dtos:
        dto.model_rebuild(_types_namespace=dto_namespace)


def create_app() -> FastAPI:
    rebuild_response_dtos()
    app = FastAPI(
        title="CU - Portal",
        version="1.0.0",
    )
    container = Container()
    app.state.container = container
    app.router.route_class = CustomRoute

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Create one DB session per request and store it in ContextVar.
        async with container.session_factory()() as session:
            session_token = session_context.set(session)
            request_token = request_context.set(request)
            try:
                response = await call_next(request)
                return response
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    await session.close()
                except Exception:
                    pass
                session_context.reset(session_token)
                request_context.reset(request_token)

    # We resolve the router here at startup.
    # Because we are now using `Depends()` inside `create_user_router`,
    # the providers will correctly wait to resolve until a request comes in.
    main_user_routes = container.main_user_routes()
    main_admin_routes = container.main_admin_routes()
    auth_routes = container.auth_routes()
    user_user_routes = container.user_user_routes()
    user_admin_routes = container.user_admin_routes()
    role_admin_routes = container.role_admin_routes()
    year_admin_routes = container.year_admin_routes()
    department_admin_routes = container.department_admin_routes()
    log_admin_routes = container.log_admin_routes()
    material_user_routes = container.material_user_routes()
    material_admin_routes = container.material_admin_routes()
    announcement_user_routes = container.announcement_user_routes()
    announcement_admin_routes = container.announcement_admin_routes()
    task_user_routes = container.task_user_routes()
    calendar_user_routes = container.calendar_user_routes()
    task_admin_routes = container.task_admin_routes()
    note_user_routes = container.note_user_routes()
    exam_user_routes = container.exam_user_routes()
    faculty_user_routes = container.faculty_user_routes()
    department_user_routes = container.department_user_routes()
    year_user_routes = container.year_user_routes()
    week_user_routes = container.week_user_routes()
    event_user_routes = container.event_user_routes()

    exam_admin_routes = container.exam_admin_routes()
    attachment_public_routes = container.attachment_public_routes()
    file_public_routes = container.file_public_routes()
    message_public_routes = container.message_public_routes()
    message_admin_routes = container.message_admin_routes()
    faculty_admin_routes = container.faculty_admin_routes()
    notification_user_routes = container.notification_user_routes()
    subject_user_routes = container.subject_user_routes()
    subject_admin_routes = container.subject_admin_routes()
    week_admin_routes = container.week_admin_routes()
    event_admin_routes = container.event_admin_routes()
    main_user_routes.include_router(user_user_routes)
    main_user_routes.include_router(material_user_routes)
    main_user_routes.include_router(notification_user_routes)
    main_user_routes.include_router(announcement_user_routes)
    main_user_routes.include_router(calendar_user_routes)
    main_user_routes.include_router(task_user_routes)
    main_user_routes.include_router(note_user_routes)
    main_user_routes.include_router(exam_user_routes)
    main_user_routes.include_router(subject_user_routes)
    main_user_routes.include_router(faculty_user_routes)
    main_user_routes.include_router(department_user_routes)
    main_user_routes.include_router(year_user_routes)
    main_user_routes.include_router(week_user_routes)
    main_user_routes.include_router(event_user_routes)
    main_admin_routes.include_router(user_admin_routes)
    main_admin_routes.include_router(role_admin_routes)
    main_admin_routes.include_router(faculty_admin_routes)
    main_admin_routes.include_router(department_admin_routes)
    main_admin_routes.include_router(year_admin_routes)
    main_admin_routes.include_router(announcement_admin_routes)
    main_admin_routes.include_router(task_admin_routes)
    main_admin_routes.include_router(exam_admin_routes)
    main_admin_routes.include_router(log_admin_routes)
    main_admin_routes.include_router(material_admin_routes)
    main_admin_routes.include_router(message_admin_routes)
    main_admin_routes.include_router(subject_admin_routes)
    main_admin_routes.include_router(week_admin_routes)
    main_admin_routes.include_router(event_admin_routes)
    app.include_router(main_user_routes)
    app.include_router(main_admin_routes)
    app.include_router(auth_routes)
    app.include_router(attachment_public_routes)
    app.include_router(file_public_routes)
    app.include_router(message_public_routes)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "https://cu-portal-dev.vercel.app",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", ""),
    )

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
