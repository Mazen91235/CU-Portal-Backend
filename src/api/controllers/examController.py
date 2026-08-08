from fastapi import Request
from core.iControllers.iExamController import IExamController
from core.iServices.iExamService import IExamService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# DTOs
from core.dtos.examDtos import ExamResponseDto, ExamCreateDto, ExamUpdateDto, ExamSearchDto
from core.models.queryModel import QueryModel


class ExamController(IExamController):
    def __init__(self, exam_service: IExamService, logger: IBaseLogger):
        self.exam_service = exam_service
        self.logger = logger

    # Admin Controllers
    async def create_exam(self, request: Request):
        try:
            payload = await request.json()
            data = Generator.generate(ExamCreateDto, payload)
            
            result = await self.exam_service.create_exam(data)
            
            if result.success and result.data:
                result.data = Mapper.map(result.data, ExamResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Add", "Exam", "error", 500, "Error in controller creating exam", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while creating the exam.")

    async def update_exam(self, request: Request, exam_id: int):
        try:
            payload = await request.json()
            data = Generator.generate(ExamUpdateDto, payload)
            
            result = await self.exam_service.update_exam(exam_id, data)
            
            if result.success and result.data:
                result.data = Mapper.map(result.data, ExamResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Edit", "Exam", "error", 500, "Error in controller updating exam", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while updating the exam.")

    async def delete_exam(self, request: Request, exam_id: int):
        try:
            result = await self.exam_service.delete_exam(exam_id)
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Delete", "Exam", "error", 500, "Error in controller deleting exam", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while deleting the exam.")

    async def get_exams_admin(self, request: Request):
        try:
            query_str = request.query_params.get("query", "{}")
            query_model = Parser.parse_query(query_str, QueryModel[ExamSearchDto])
            
            result = await self.exam_service.get_exams_admin(query_model)
            
            if result.success and result.data:
                result.data = Mapper.map_list(result.data, ExamResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data,
                next=True if result.data and len(result.data) > (query_model.limit or 50) else False
            )
        except Exception as e:
            await self.logger.log("Get", "Exams", "error", 500, "Error in controller getting admin exams", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while fetching exams.")

    async def get_exam_admin(self, request: Request, exam_id: int):
        try:
            result = await self.exam_service.get_exam_admin(exam_id)
            if result.success and result.data:
                result.data = Mapper.map(result.data, ExamResponseDto, to_dict=True)
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Get", "Exam", "error", 500, "Error in controller getting admin exam", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while fetching the exam.")

    # User Controllers
    async def get_exams_user(self, request: Request):
        try:
            query_str = request.query_params.get("query", "{}")
            query_model = Parser.parse_query(query_str, QueryModel[ExamSearchDto])
            
            result = await self.exam_service.get_exams_user(query_model)
            
            if result.success and result.data:
                result.data = Mapper.map_list(result.data, ExamResponseDto, to_dict=True)
                
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data,
                next=True if result.data and len(result.data) > (query_model.limit or 50) else False
            )
        except Exception as e:
            await self.logger.log("Get", "Exams", "error", 500, "Error in controller getting user exams", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while fetching your exams.")

    async def get_exam_user(self, request: Request, exam_id: int):
        try:
            result = await self.exam_service.get_exam_user(exam_id)
            if result.success and result.data:
                result.data = Mapper.map(result.data, ExamResponseDto, to_dict=True)
            return ResponseHandler.generate_response(
                success=result.success, code=result.code, message=result.message, data=result.data
            )
        except Exception as e:
            await self.logger.log("Get", "Exam", "error", 500, "Error in controller getting user exam", "ExamController", {"error": str(e)})
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while fetching the exam.")