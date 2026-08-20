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
from api.routes.announcementRoutes import (
    create_announcement_user_router,
    create_announcement_admin_router,
)
from api.routes.subjectRoutes import (
    create_subject_admin_router,
    create_subject_user_router,
)
from api.routes.notificationRoutes import create_notification_user_router
from api.routes.materialRoutes import (
    create_material_user_router,
    create_material_admin_router,
)
from api.routes.messageRoutes import (
    create_message_public_router,
    create_message_admin_router,
)
from api.routes.yearRoutes import create_year_admin_router
from api.routes.departmentRoutes import create_department_admin_router
from api.routes.facultyRoutes import create_faculty_admin_router
from api.controllers.userController import UserController
from api.controllers.roleController import RoleController
from api.controllers.examController import ExamController
from api.controllers.facultyController import FacultyController
from api.controllers.messageController import MessageController
from api.controllers.materialController import MaterialController
from api.controllers.subjectController import SubjectController
from api.controllers.announcementController import AnnouncementController
from api.controllers.taskController import TaskController
from api.controllers.notificationController import NotificationController
from api.controllers.yearController import YearController
from api.controllers.departmentController import DepartmentController
from api.middlewares.authMiddleware import AuthMiddleware
from api.middlewares.validationMiddleware import ValidationMiddleware
from api.middlewares.requestLimitMiddleware import RequestLimitMiddleware
from business.contextVars.sessionContext import session_context
from business.services.userService import UserService
from business.services.roleService import RoleService
from business.services.taskService import TaskService
from business.services.subjectService import SubjectService
from business.services.announcementService import AnnouncementService
from business.services.notificationService import NotificationService
from business.services.materialService import MaterialService
from business.services.messageService import MessageService
from business.services.facultyService import FacultyService
from business.services.yearService import YearService
from business.services.departmentService import DepartmentService
from business.services.requestLimitService import RequestLimitService
from business.services.helperService import HelperService
from business.services.examService import ExamService
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
from core.entities.requestLimit import RequestLimit
from core.entities.subject import Subject
from core.entities.userSubjectLink import UserSubjectLink
from core.entities.announcement import Announcement
from core.entities.task import Task
from core.entities.subject import Subject
from core.entities.year import Year
from core.entities.department import Department
from core.entities.userNotification import UserNotification
from core.entities.notification import Notification
from core.entities.message import Message
from core.entities.faculty import Faculty
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
    request_limit_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=RequestLimit,
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

    # --- 4. Services ---
    helper_service = providers.Factory(
        HelperService,
        notification_repository=notification_repository,
        user_notification_repository=user_notification_repository,
        user_repository=user_repository,
        role_repository=role_repository,
        faculty_repository=faculty_repository,
        department_repository=department_repository,
        year_repository=year_repository,
        subject_repository=subject_repository,
    )
    logger = providers.Factory(
        BaseLogger, repository=log_repository, helper_service=helper_service
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
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
    material_service = providers.Factory(
        MaterialService,
        material_repository=material_repository,
        subject_repository=subject_repository,
        user_repository=user_repository,
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

    request_limit_service = providers.Factory(
        RequestLimitService,
        request_limit_repository=request_limit_repository,
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
    notification_service = providers.Factory(
        NotificationService,
        user_notification_repository=user_notification_repository,
        notification_repository=notification_repository,
        logger=logger,
        helper_service=helper_service,
    )
    subject_service = providers.Factory(
        SubjectService,
        subject_repository=subject_repository,
        user_subject_link_repository=user_subject_link_repository,
        year_repository=year_repository,
        logger=logger,
        helper_service=helper_service,
    )

    # --- 5. Middlewares ---
    auth_middleware = providers.Factory(
        AuthMiddleware,
        user_service=user_service,
        role_service=None,  # Until Created
        logger=logger,
    )

    request_limit_middleware = providers.Factory(
        RequestLimitMiddleware,
        request_limit_service=request_limit_service,
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
    notification_controller = providers.Factory(
        NotificationController, notification_service=notification_service, logger=logger
    )

    material_controller = providers.Factory(
        MaterialController, material_service=material_service, logger=logger
    )

    message_controller = providers.Factory(
        MessageController, message_service=message_service, logger=logger
    )

    faculty_controller = providers.Factory(
        FacultyController, faculty_service=faculty_service, logger=logger
    )

    year_controller = providers.Factory(
        YearController, year_service=year_service, logger=logger
    )

    department_controller = providers.Factory(
        DepartmentController, department_service=department_service, logger=logger
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

    role_controller = providers.Factory(
        RoleController, role_service=role_service, logger=logger
    )

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

    year_admin_routes = providers.Factory(
        create_year_admin_router,
        controller_provider=year_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    department_admin_routes = providers.Factory(
        create_department_admin_router,
        controller_provider=department_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    notification_user_routes = providers.Factory(
        create_notification_user_router,
        controller_provider=notification_controller.provider,
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

    material_admin_routes = providers.Factory(
        create_material_admin_router,
        controller_provider=material_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
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
        validation_middleware_provider=validation_middleware.provider,
    )

    faculty_admin_routes = providers.Factory(
        create_faculty_admin_router,
        controller_provider=faculty_controller.provider,
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
