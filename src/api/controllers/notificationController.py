from fastapi import Request
from core.iControllers.iNotificationController import INotificationController
from core.iServices.iNotificationService import INotificationService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# DTOs
from core.dtos.userNotificationDtos import UserNotificationSearchDto, UserNotificationResponseDto
from core.models.queryModel import QueryModel


class NotificationController(INotificationController):
    def __init__(self, notification_service: INotificationService, logger: IBaseLogger):
        self.notification_service = notification_service
        self.logger = logger

    # User Controllers
    async def get_notifications_user(self, request: Request):
        try:
            query_str = request.query_params.get("query", "{}")
            query_model = Parser.parse_query(query_str, QueryModel[UserNotificationSearchDto])
            
            result = await self.notification_service.get_notifications_user(query_model)
            
            if result.success and result.data:
                # Map the list of UserNotification entities to their DTOs
                result.data = Mapper.map_list(result.data, UserNotificationResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, 
                code=result.code, 
                message=result.message, 
                data=result.data,
                next=True if result.data and len(result.data) == (query_model.limit or 50) else False
            )
            
        except Exception as e:
            await self.logger.log("Get", "Notification", "error", 500, "Error in controller getting user notifications", "NotificationController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while fetching your notifications.")

    async def mark_notification_as_seen(self, request: Request, notification_id: int):
        try:
            result = await self.notification_service.mark_notification_as_seen(notification_id)
            
            return ResponseHandler.generate_response(
                success=result.success, 
                code=result.code, 
                message=result.message, 
                data=result.data
            )
            
        except Exception as e:
            await self.logger.log("Mark", "Notification", "error", 500, "Error in controller marking notification as seen", "NotificationController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while marking the notification as seen.")