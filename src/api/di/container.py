import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dependency_injector import containers, providers


# Fix for ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.middlewares.authMiddleware import AuthMiddleware
from api.middlewares.validationMiddleware import ValidationMiddleware
from api.controllers.userController import UserController
from api.controllers.patientController import PatientController
from api.controllers.patientUserController import PatientUserController
from api.routes.userRoutes import create_user_router
from api.routes.patientRoutes import create_patient_router
from api.routes.patientUserRoutes import create_patient_user_router
from business.loggers.baseLogger import BaseLogger
from business.services.helperService import HelperService
from business.services.aiService import AIService
from business.services.userService import UserService
from business.services.patientService import PatientService
from business.services.patientUserService import PatientUserService
from core.entities.log import Log
from core.entities.user import User
from core.entities.token import Token
from core.entities.patient import Patient
from core.entities.patientUser import PatientUser
from core.utils.databaseHandler import DatabaseHandler
from business.contextVars.sessionContext import session_context
from infrastructure.repositories.baseRepository import BaseRepository

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
    patient_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=Patient,
        session_factory=session_factory,
    )
    patient_user_repository = providers.Factory(
        BaseRepository,
        session=db_session,
        model=PatientUser,
        session_factory=session_factory,
    )

    # --- 4. Services ---
    helper_service = providers.Factory(HelperService)
    ai_service = providers.Singleton(AIService)  # Singleton for Single Object
    logger = providers.Factory(
        BaseLogger, repository=log_repository, helper_service=helper_service
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        patient_repository=patient_repository,
        token_repository=token_repository,
        logger=logger,
        helper_service=helper_service,
    )

    patient_service = providers.Factory(
        PatientService,
        patient_repository=patient_repository,
        logger=logger,
        helper_service=helper_service,
    )

    patient_user_service = providers.Factory(
        PatientUserService,
        patient_user_repository=patient_user_repository,
        logger=logger,
        helper_service=helper_service,
        ai_service=ai_service,
    )

    # --- 5. Middlewares & Controllers ---
    auth_middleware = providers.Factory(
        AuthMiddleware,
        user_repository=user_repository,
        patient_repository=patient_repository,
        token_repository=token_repository,
        logger=logger,
    )

    validation_middleware = providers.Factory(
        ValidationMiddleware,
        logger=logger,
    )

    user_controller = providers.Factory(
        UserController, user_service=user_service, logger=logger
    )

    patient_controller = providers.Factory(
        PatientController, patient_service=patient_service, logger=logger
    )

    patient_user_controller = providers.Factory(
        PatientUserController,
        patient_user_service=patient_user_service,
        helper_service=helper_service,
        ai_service=ai_service,
        logger=logger,
    )

    # --- 6. Routes ---
    user_routes = providers.Factory(
        create_user_router,
        controller_provider=user_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    patient_routes = providers.Factory(
        create_patient_router,
        controller_provider=patient_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )

    patient_user_routes = providers.Factory(
        create_patient_user_router,
        controller_provider=patient_user_controller.provider,
        auth_middleware_provider=auth_middleware.provider,
        validation_middleware_provider=validation_middleware.provider,
    )
