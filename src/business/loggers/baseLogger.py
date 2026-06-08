from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.iServices.iHelperService import IHelperService
from business.contextVars.requestContext import request_context
from core.utils.entitiesHandler import EntitiesHandler
from core.utils.timezoneHandler import TimezoneHandler


class BaseLogger(IBaseLogger):
    def __init__(self, repository: IBaseRepository, helper_service: IHelperService):
        self.repository = repository
        self.helper_service = helper_service

    async def log(
        self, action: str, entity: str, level: str, code: int, message: str, source: str
    ):
        try:
            ip_address_response = await self.helper_service.get_ip_address()
            ip_address = (
                ip_address_response.data if ip_address_response.success else None
            )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            logged_in_user_id = (
                logged_in_user_response.data.id
                if logged_in_user_response.success and logged_in_user_response.data
                else None
            )

            # When deleting the current user, the FK row may already be gone.
            if (
                entity.lower() == "user"
                and action.lower() == "delete"
                and level.lower() == "info"
            ):
                logged_in_user_id = None

            request = request_context.get(None)
            path = request.url.path if request else None

            await self.repository.execute_sql(
                f"INSERT INTO {EntitiesHandler.TABLES.get('Log')} (action, entity, level, code, message, source, path, ip, user_id, created_at, updated_at) VALUES (:action, :entity, :level, :code, :message, :source, :path, :ip, :user_id, :created_at, :updated_at)",
                {
                    "action": action,
                    "entity": entity,
                    "level": level,
                    "code": code,
                    "message": message,
                    "source": source,
                    "path": path,
                    "ip": ip_address,
                    "user_id": logged_in_user_id,
                    "created_at": TimezoneHandler.now("UTC"),
                    "updated_at": TimezoneHandler.now("UTC"),
                },
            )
        except Exception as ex:
            print(f"Failed to log message: {str(ex)}")
            return
