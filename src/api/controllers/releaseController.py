from fastapi import Request
from core.iControllers.iReleaseController import IReleaseController
from core.iServices.iReleaseService import IReleaseService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

from core.dtos.releaseDtos import ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto, ReleaseResponseDto
from core.models.queryModel import QueryModel


class ReleaseController(IReleaseController):
    def __init__(self, release_service: IReleaseService, logger: IBaseLogger):
        self.release_service = release_service
        self.logger = logger

    async def create_release(self, request: Request):
        try:
            payload = await request.json()
            data = Generator.generate(ReleaseCreateDto, payload)
            
            result = await self.release_service.create_release(data)
            
            if result.success and result.data:
                result.data = Mapper.map(result.data, ReleaseResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Create", "Release", "error", 500, "Controller error", "ReleaseController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred.")

    async def update_release(self, request: Request, release_id: int):
        try:
            payload = await request.json()
            data = Generator.generate(ReleaseUpdateDto, payload)
            
            result = await self.release_service.update_release(release_id, data)
            
            if result.success and result.data:
                result.data = Mapper.map(result.data, ReleaseResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Update", "Release", "error", 500, "Controller error", "ReleaseController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred.")

    async def delete_release(self, request: Request, release_id: int):
        try:
            result = await self.release_service.delete_release(release_id)
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Delete", "Release", "error", 500, "Controller error", "ReleaseController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred.")

    async def get_releases(self, request: Request):
        try:
            query_str = request.query_params.get("query", "{}")
            query_model = Parser.parse_query(query_str, QueryModel[ReleaseSearchDto])
            
            result = await self.release_service.get_releases(query_model)
            
            if result.success and result.data:
                result.data = Mapper.map_list(result.data, ReleaseResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data,
                next=True if result.data and len(result.data) == (query_model.limit or 50) else False
            )
        except Exception as e:
            await self.logger.log("Get", "Releases", "error", 500, "Controller error", "ReleaseController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred.")

    async def get_release(self, request: Request, release_id: int):
        try:
            result = await self.release_service.get_release(release_id)
            if result.success and result.data:
                result.data = Mapper.map(result.data, ReleaseResponseDto, to_dict=True)
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Get", "Release", "error", 500, "Controller error", "ReleaseController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred.")