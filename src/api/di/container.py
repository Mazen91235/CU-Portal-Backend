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
from api.routes.messageRoutes import (
    create_message_router,
    create_message_admin_router,
)
from api.routes.facultyRoutes import create_faculty_admin_router
from api.routes.eventOrganizerRoutes import create_event_organizer_admin_router, create_event_organizer_user_router
from api.controllers.userController import UserController
from api.controllers.facultyController import FacultyController
from api.controllers.messageController import MessageController
from api.controllers.eventOrganizerController import EventOrganizerController
from api.middlewares.authMiddleware import AuthMiddleware
from api.middlewares.validationMiddleware import ValidationMiddleware
from api.middlewares.requestLimitMiddleware import RequestLimitMiddleware
from business.contextVars.sessionContext import session_context
from business.services.userService import UserService
from business.services.messageService import MessageService
from business.services.facultyService import FacultyService
from business.services.eventOrganizerService import EventOrganizerService
from business.services.requestLimitService import RequestLimitService
from business.services.helperService import HelperService
from business.loggers.baseLogger import BaseLogger
from infrastructure.repositories.baseRepository import BaseRepository
from core.entities.log import Log
from core.entities.user import User
from core.entities.pendingUser import PendingUser
from core.entities.role import Role
from core.entities.token import Token
from core.entities.requestLimit import RequestLimit
from core.entities.message import Message
from core.entities.faculty import Faculty
from core.entities.eventOrganizer import EventOrganizer
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
    pending_user_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=PendingUser,
        session_factory=session_factory,
    )
    role_repository = providers.Factory(
        BaseRepository, session=db_session, model=Role, session_factory=session_factory
    )
    request_limit_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=RequestLimit,
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
    event_organizer_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=EventOrganizer,
        session_factory=session_factory,
    )

    # --- 4. Services ---
    helper_service = providers.Factory(HelperService)
    logger = providers.Factory(
        BaseLogger, repository=log_repository, helper_service=helper_service
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        token_repository=token_repository,
        role_repository=role_repository,
        pending_repository=pending_user_repository,
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

    request_limit_service = providers.Factory(
        RequestLimitService,
        request_limit_repository=request_limit_repository,
        logger=logger,
        helper_service=helper_service,
    )

    # --- 5. Middlewares ---
    auth_middleware = providers.Factory(
        AuthMiddleware,
        user_service=user_service,
        token_service=None,  # Until Created
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

    message_controller = providers.Factory(
        MessageController, message_service=message_service, logger=logger
    )
    
    faculty_controller = providers.Factory(
        FacultyController, faculty_service=faculty_service, logger=logger
    )

    event_organizer_controller = providers.Factory(
        EventOrganizerController, 
        event_organizer_service=event_organizer_service, 
        logger=logger
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

    message_public_routes = providers.Factory(
        create_message_router,
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

    event_organizer_user_routes = providers.Factory(
        create_event_organizer_user_router,
        controller_provider=event_organizer_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    event_organizer_admin_routes = providers.Factory(
        create_event_organizer_admin_router,
        controller_provider=event_organizer_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
