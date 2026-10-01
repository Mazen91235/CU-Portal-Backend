import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dependency_injector import containers, providers

# Fix for ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.routes.mainRoutes import (
    create_main_user_router,
    create_main_admin_router,
)
from api.routes.authRoutes import create_auth_router
from api.routes.userRoutes import create_user_user_router, create_user_admin_router
from api.routes.roleRoutes import create_role_admin_router
from api.routes.examRoutes import create_exam_user_router, create_exam_admin_router
from api.routes.taskRoutes import create_task_user_router, create_task_admin_router
from api.routes.noteRoutes import create_note_user_router
from api.routes.announcementRoutes import (
    create_announcement_user_router,
    create_announcement_admin_router,
)
from api.routes.calendarRoutes import create_calendar_user_router
from api.routes.subjectRoutes import (
    create_subject_admin_router,
    create_subject_user_router,
)
from api.routes.notificationRoutes import (
    create_notification_public_router,
    create_notification_user_router,
)
from api.routes.logRoutes import create_log_admin_router
from api.routes.materialRoutes import (
    create_material_user_router,
    create_material_admin_router,
)
from api.routes.attachmentRoutes import create_attachment_public_router
from api.routes.fileRoutes import create_file_public_router
from api.routes.messageRoutes import (
    create_message_public_router,
    create_message_admin_router,
)
from api.routes.eventOrganizerRoutes import (
    create_event_organizer_user_router,
    create_event_organizer_admin_router,
)
from api.routes.releaseRoutes import (
    create_release_admin_router,
    create_release_user_router,
)
from api.routes.weekRoutes import (
    create_week_user_router,
    create_week_admin_router,
)
from api.routes.eventRoutes import (
    create_event_user_router,
    create_event_admin_router,
)
from api.routes.userCompletionRoutes import create_user_completion_user_router
from api.routes.yearRoutes import create_year_user_router, create_year_admin_router
from api.routes.departmentRoutes import (
    create_department_user_router,
    create_department_admin_router,
)
from api.routes.facultyRoutes import (
    create_faculty_user_router,
    create_faculty_admin_router,
)
from api.routes.systemRoutes import create_system_public_router
from api.middlewares.authMiddleware import AuthMiddleware
from api.middlewares.validationMiddleware import ValidationMiddleware
from api.middlewares.requestLimitMiddleware import RequestLimitMiddleware
from business.contextVars.sessionContext import session_context
from api.controllers.userController import UserController
from api.controllers.roleController import RoleController
from api.controllers.examController import ExamController
from api.controllers.facultyController import FacultyController
from api.controllers.fileController import FileController
from api.controllers.messageController import MessageController
from api.controllers.eventOrganizerController import EventOrganizerController
from api.controllers.logController import LogController
from api.controllers.materialController import MaterialController
from api.controllers.subjectController import SubjectController
from api.controllers.announcementController import AnnouncementController
from api.controllers.taskController import TaskController
from api.controllers.noteController import NoteController
from api.controllers.calendarController import CalendarController
from api.controllers.notificationController import NotificationController
from api.controllers.yearController import YearController
from api.controllers.departmentController import DepartmentController
from api.controllers.releaseController import ReleaseController
from api.controllers.weekController import WeekController
from api.controllers.eventController import EventController
from api.controllers.userCompletionController import UserCompletionController
from api.controllers.attachmentController import AttachmentController
from api.controllers.systemController import SystemController
from business.services.userService import UserService
from business.services.roleService import RoleService
from business.services.taskService import TaskService
from business.services.noteService import NoteService
from business.services.calendarService import CalendarService
from business.services.subjectService import SubjectService
from business.services.announcementService import AnnouncementService
from business.services.notificationService import NotificationService
from business.services.logService import LogService
from business.services.materialService import MaterialService
from business.services.messageService import MessageService
from business.services.facultyService import FacultyService
from business.services.eventOrganizerService import EventOrganizerService
from business.services.yearService import YearService
from business.services.departmentService import DepartmentService
from business.services.weekService import WeekService
from business.services.eventService import EventService
from business.services.userCompletionService import UserCompletionService
from business.services.examService import ExamService
from business.services.releaseService import ReleaseService
from business.services.attachmentService import AttachmentService
from business.services.helperService import HelperService
from business.loggers.baseLogger import BaseLogger
from infrastructure.repositories.baseRepository import BaseRepository
from core.entities.log import Log
from core.entities.user import User
from core.entities.role import Role
from core.entities.exactRole import ExactRole
from core.entities.material import Material
from core.entities.subject import Subject
from core.entities.pendingUser import PendingUser
from core.entities.token import Token
from core.entities.subject import Subject
from core.entities.userSubjectLink import UserSubjectLink
from core.entities.announcement import Announcement
from core.entities.task import Task
from core.entities.note import Note
from core.entities.subject import Subject
from core.entities.year import Year
from core.entities.department import Department
from core.entities.device import Device
from core.entities.userNotification import UserNotification
from core.entities.notification import Notification
from core.entities.message import Message
from core.entities.faculty import Faculty
from core.entities.release import Release
from core.entities.version import Version
from core.entities.releaseItem import ReleaseItem
from core.entities.eventOrganizer import EventOrganizer
from core.entities.week import Week
from core.entities.weekItem import WeekItem
from core.entities.event import Event
from core.entities.userEvent import UserEvent
from core.entities.userCompletion import UserCompletion
from core.entities.eventOrganizer import EventOrganizer
from core.entities.attachment import Attachment
from core.utils.databaseHandler import DatabaseHandler

DB_URL = DatabaseHandler.get_db_url()
ENGINE_OPTIONS = DatabaseHandler.get_engine_options(DB_URL)


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # --- 1. Infrastructure ---
    engine = providers.Singleton(
        create_async_engine,
        DB_URL,
        **ENGINE_OPTIONS,
    )

    session_factory = providers.Singleton(
        async_sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # --- 2. Request-Scoped Session Provider ---
    # Resolve the active request session from ContextVar to avoid global overrides.
    db_session = providers.Factory(lambda: session_context.get(None))

    # --- 3. Repositories ---
    log_repository = providers.Factory(
        BaseRepository, session=db_session, model=Log, session_factory=session_factory
    )
    token_repository = providers.Factory(
        BaseRepository, session=db_session, model=Token, session_factory=session_factory
    )
    user_repository = providers.Factory(
        BaseRepository, session=db_session, model=User, session_factory=session_factory
    )
    device_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Device,
        session_factory=session_factory,
    )
    role_repository = providers.Factory(
        BaseRepository, session=db_session, model=Role, session_factory=session_factory
    )
    exact_role_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=ExactRole,
        session_factory=session_factory,
    )
    material_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Material,
        session_factory=session_factory,
    )
    pending_user_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=PendingUser,
        session_factory=session_factory,
    )
    announcement_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Announcement,
        session_factory=session_factory,
    )
    task_repository = providers.Factory(
        BaseRepository, session=db_session, model=Task, session_factory=session_factory
    )
    note_repository = providers.Factory(
        BaseRepository, session=db_session, model=Note, session_factory=session_factory
    )
    subject_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Subject,
        session_factory=session_factory,
    )
    user_subject_link_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=UserSubjectLink,
        session_factory=session_factory,
    )
    year_repository = providers.Factory(
        BaseRepository, session=db_session, model=Year, session_factory=session_factory
    )
    department_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Department,
        session_factory=session_factory,
    )
    user_notification_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=UserNotification,
        session_factory=session_factory,
    )
    notification_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Notification,
        session_factory=session_factory,
    )
    message_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Message,
        session_factory=session_factory,
    )
    faculty_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Faculty,
        session_factory=session_factory,
    )
    week_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Week,
        session_factory=session_factory,
    )
    release_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Release,
        session_factory=session_factory,
    )
    version_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Version,
        session_factory=session_factory,
    )
    release_item_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=ReleaseItem,
        session_factory=session_factory,
    )
    event_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Event,
        session_factory=session_factory,
    )
    user_event_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=UserEvent,
        session_factory=session_factory,
    )
    user_completion_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=UserCompletion,
        session_factory=session_factory,
    )
    week_item_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=WeekItem,
        session_factory=session_factory,
    )
    event_organizer_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=EventOrganizer,
        session_factory=session_factory,
    )
    attachment_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Attachment,
        session_factory=session_factory,
    )

    # --- 4. Services ---
    helper_service = providers.Factory(
        HelperService,
        notification_repository=notification_repository,
        user_notification_repository=user_notification_repository,
        user_repository=user_repository,
        device_repository=device_repository,
        user_completion_repository=user_completion_repository,
        role_repository=role_repository,
        faculty_repository=faculty_repository,
        department_repository=department_repository,
        year_repository=year_repository,
        subject_repository=subject_repository,
        attachment_repository=attachment_repository,
        log_repository=log_repository,
        session_factory=session_factory,
    )
    logger = providers.Factory(
        BaseLogger, repository=log_repository, helper_service=helper_service
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        device_repository=device_repository,
        token_repository=token_repository,
        role_repository=role_repository,
        pending_user_repository=pending_user_repository,
        logger=logger,
        helper_service=helper_service,
    )
    role_service = providers.Factory(
        RoleService,
        role_repository=role_repository,
        exact_role_repository=exact_role_repository,
        logger=logger,
        helper_service=helper_service,
    )
    log_service = providers.Factory(
        LogService,
        log_repository=log_repository,
        logger=logger,
        helper_service=helper_service,
    )
    material_service = providers.Factory(
        MaterialService,
        material_repository=material_repository,
        subject_repository=subject_repository,
        user_repository=user_repository,
        week_repository=week_repository,
        logger=logger,
        helper_service=helper_service,
    )

    message_service = providers.Factory(
        MessageService,
        message_repository=message_repository,
        logger=logger,
        helper_service=helper_service,
    )

    faculty_service = providers.Factory(
        FacultyService,
        faculty_repository=faculty_repository,
        logger=logger,
        helper_service=helper_service,
    )

    event_organizer_service = providers.Factory(
        EventOrganizerService,
        event_organizer_repository=event_organizer_repository,
        logger=logger,
        helper_service=helper_service,
    )

    year_service = providers.Factory(
        YearService,
        year_repository=year_repository,
        logger=logger,
        helper_service=helper_service,
    )

    department_service = providers.Factory(
        DepartmentService,
        department_repository=department_repository,
        faculty_repository=faculty_repository,
        logger=logger,
        helper_service=helper_service,
    )

    week_service = providers.Factory(
        WeekService,
        week_repository=week_repository,
        logger=logger,
        helper_service=helper_service,
    )

    event_service = providers.Factory(
        EventService,
        event_repository=event_repository,
        user_event_repository=user_event_repository,
        event_organizer_repository=event_organizer_repository,
        logger=logger,
        helper_service=helper_service,
    )
    user_completion_service = providers.Factory(
        UserCompletionService,
        user_completion_repository=user_completion_repository,
        week_item_repository=week_item_repository,
        task_repository=task_repository,
        logger=logger,
        helper_service=helper_service,
    )

    announcement_service = providers.Factory(
        AnnouncementService,
        announcement_repository=announcement_repository,
        subject_repository=subject_repository,
        logger=logger,
        helper_service=helper_service,
    )
    task_service = providers.Factory(
        TaskService,
        task_repository=task_repository,
        subject_repository=subject_repository,
        logger=logger,
        helper_service=helper_service,
    )
    exam_service = providers.Factory(
        ExamService,
        task_repository=task_repository,
        subject_repository=subject_repository,
        logger=logger,
        helper_service=helper_service,
    )
    calendar_service = providers.Factory(
        CalendarService,
        task_repository=task_repository,
        announcement_repository=announcement_repository,
        logger=logger,
        helper_service=helper_service,
    )
    note_service = providers.Factory(
        NoteService,
        note_repository=note_repository,
        logger=logger,
        helper_service=helper_service,
    )
    notification_service = providers.Factory(
        NotificationService,
        user_notification_repository=user_notification_repository,
        notification_repository=notification_repository,
        task_repository=task_repository,
        event_repository=event_repository,
        logger=logger,
        helper_service=helper_service,
        session_factory=session_factory,
    )
    subject_service = providers.Factory(
        SubjectService,
        subject_repository=subject_repository,
        user_subject_link_repository=user_subject_link_repository,
        year_repository=year_repository,
        logger=logger,
        helper_service=helper_service,
    )
    release_service = providers.Factory(
        ReleaseService,
        release_repository=release_repository,
        version_repository=version_repository,
        release_item_repository=release_item_repository,
        logger=logger,
        helper_service=helper_service,
    )
    attachment_service = providers.Factory(
        AttachmentService,
        attachment_repository=attachment_repository,
        announcement_repository=announcement_repository,
        material_repository=material_repository,
        pending_user_repository=pending_user_repository,
        task_repository=task_repository,
        user_repository=user_repository,
        logger=logger,
        helper_service=helper_service,
        session_factory=session_factory,
    )

    # --- 5. Middlewares ---
    auth_middleware = providers.Factory(
        AuthMiddleware,
        user_service=user_service,
        token_repository=token_repository,
        log_repository=log_repository,
        logger=logger,
        session_factory=session_factory,
    )

    request_limit_middleware = providers.Factory(
        RequestLimitMiddleware,
        logger=logger,
        helper_service=helper_service,
    )

    validation_middleware = providers.Factory(
        ValidationMiddleware,
        logger=logger,
    )

    # --- 6. Controllers ---
    user_controller = providers.Factory(
        UserController, user_service=user_service, logger=logger
    )
    announcement_controller = providers.Factory(
        AnnouncementController,
        announcement_service=announcement_service,
        logger=logger,
    )
    task_controller = providers.Factory(
        TaskController, task_service=task_service, logger=logger
    )
    note_controller = providers.Factory(
        NoteController, note_service=note_service, logger=logger
    )
    calendar_controller = providers.Factory(
        CalendarController, calendar_service=calendar_service, logger=logger
    )
    notification_controller = providers.Factory(
        NotificationController, notification_service=notification_service, logger=logger
    )

    log_controller = providers.Factory(
        LogController, log_service=log_service, logger=logger
    )

    material_controller = providers.Factory(
        MaterialController, material_service=material_service, logger=logger
    )

    file_controller = providers.Factory(
        FileController, helper_service=helper_service, logger=logger
    )

    message_controller = providers.Factory(
        MessageController, message_service=message_service, logger=logger
    )

    faculty_controller = providers.Factory(
        FacultyController, faculty_service=faculty_service, logger=logger
    )

    event_organizer_controller = providers.Factory(
        EventOrganizerController,
        event_organizer_service=event_organizer_service,
        logger=logger,
    )

    year_controller = providers.Factory(
        YearController, year_service=year_service, logger=logger
    )

    department_controller = providers.Factory(
        DepartmentController, department_service=department_service, logger=logger
    )

    week_controller = providers.Factory(
        WeekController, week_service=week_service, logger=logger
    )

    event_controller = providers.Factory(
        EventController, event_service=event_service, logger=logger
    )

    user_completion_controller = providers.Factory(
        UserCompletionController,
        user_completion_service=user_completion_service,
        logger=logger,
    )

    subject_controller = providers.Factory(
        SubjectController,
        subject_service=subject_service,
        helper_service=helper_service,
        logger=logger,
    )

    exam_controller = providers.Factory(
        ExamController, exam_service=exam_service, logger=logger
    )

    release_controller = providers.Factory(
        ReleaseController, release_service=release_service, logger=logger
    )

    role_controller = providers.Factory(
        RoleController, role_service=role_service, logger=logger
    )

    attachment_controller = providers.Factory(
        AttachmentController, attachment_service=attachment_service, logger=logger
    )

    system_controller = providers.Factory(SystemController, logger=logger)

    # --- 7. Routes ---
    main_user_routes = providers.Factory(create_main_user_router)
    main_admin_routes = providers.Factory(create_main_admin_router)
    auth_routes = providers.Factory(
        create_auth_router,
        controller_provider=user_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    user_user_routes = providers.Factory(
        create_user_user_router,
        controller_provider=user_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    user_admin_routes = providers.Factory(
        create_user_admin_router,
        controller_provider=user_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    role_admin_routes = providers.Factory(
        create_role_admin_router,
        controller_provider=role_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    exam_user_routes = providers.Factory(
        create_exam_user_router,
        controller_provider=exam_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
    exam_admin_routes = providers.Factory(
        create_exam_admin_router,
        controller_provider=exam_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    year_user_routes = providers.Factory(
        create_year_user_router,
        controller_provider=year_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    year_admin_routes = providers.Factory(
        create_year_admin_router,
        controller_provider=year_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    department_user_routes = providers.Factory(
        create_department_user_router,
        controller_provider=department_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    department_admin_routes = providers.Factory(
        create_department_admin_router,
        controller_provider=department_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    notification_public_routes = providers.Factory(
        create_notification_public_router,
        controller_provider=notification_controller.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    notification_user_routes = providers.Factory(
        create_notification_user_router,
        controller_provider=notification_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
    )

    log_admin_routes = providers.Factory(
        create_log_admin_router,
        controller_provider=log_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    material_user_routes = providers.Factory(
        create_material_user_router,
        controller_provider=material_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    announcement_user_routes = providers.Factory(
        create_announcement_user_router,
        controller_provider=announcement_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
    announcement_admin_routes = providers.Factory(
        create_announcement_admin_router,
        controller_provider=announcement_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    task_user_routes = providers.Factory(
        create_task_user_router,
        controller_provider=task_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
    task_admin_routes = providers.Factory(
        create_task_admin_router,
        controller_provider=task_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    note_user_routes = providers.Factory(
        create_note_user_router,
        controller_provider=note_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
    calendar_user_routes = providers.Factory(
        create_calendar_user_router,
        controller_provider=calendar_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    material_admin_routes = providers.Factory(
        create_material_admin_router,
        controller_provider=material_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    attachment_public_routes = providers.Factory(
        create_attachment_public_router,
        controller_provider=attachment_controller.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    file_public_routes = providers.Factory(
        create_file_public_router, controller_provider=file_controller.provider
    )

    message_public_routes = providers.Factory(
        create_message_public_router,
        controller_provider=message_controller.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    message_admin_routes = providers.Factory(
        create_message_admin_router,
        controller_provider=message_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
    )

    faculty_user_routes = providers.Factory(
        create_faculty_user_router,
        controller_provider=faculty_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    faculty_admin_routes = providers.Factory(
        create_faculty_admin_router,
        controller_provider=faculty_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    event_organizer_user_routes = providers.Factory(
        create_event_organizer_user_router,
        controller_provider=event_organizer_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
    )

    event_organizer_admin_routes = providers.Factory(
        create_event_organizer_admin_router,
        controller_provider=event_organizer_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    release_user_routes = providers.Factory(
        create_release_user_router,
        controller_provider=release_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
    )

    release_admin_routes = providers.Factory(
        create_release_admin_router,
        controller_provider=release_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    subject_user_routes = providers.Factory(
        create_subject_user_router,
        controller_provider=subject_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    subject_admin_routes = providers.Factory(
        create_subject_admin_router,
        controller_provider=subject_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    week_user_routes = providers.Factory(
        create_week_user_router,
        controller_provider=week_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    week_admin_routes = providers.Factory(
        create_week_admin_router,
        controller_provider=week_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    event_user_routes = providers.Factory(
        create_event_user_router,
        controller_provider=event_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    user_completion_user_routes = providers.Factory(
        create_user_completion_user_router,
        controller_provider=user_completion_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
    )

    event_admin_routes = providers.Factory(
        create_event_admin_router,
        controller_provider=event_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    system_public_routes = providers.Factory(
        create_system_public_router,
        controller_provider=system_controller.provider,
    )
