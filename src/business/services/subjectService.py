from sqlalchemy import func,and_,or_
from core.iServices.iSubjectService import ISubjectService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.user import User
from core.entities.subject import Subject
from core.entities.faculty import Faculty
from core.entities.department import Department
from core.entities.year import Year
from core.entities.userSubjectLink import UserSubjectLink
from core.dtos.baseDtos import BaseResponseDto

class SubjectService(ISubjectService):
    def __init__(
        self,
        subject_repository: IBaseRepository[Subject],
        faculty_repository: IBaseRepository[Faculty],
        department_repository: IBaseRepository[Department],
        year_repository: IBaseRepository[Year],
        user_subject_link_repository: IBaseRepository[UserSubjectLink],
        user_repository:IBaseRepository[User],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.subject_repository = subject_repository
        self.faculty_repository = faculty_repository
        self.department_repository = department_repository
        self.user_subject_link_repository = user_subject_link_repository
        self.year_repository = year_repository
        self.user_repository=user_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.subject_repository.begin_transaction()

    async def commit_transaction(self):
        await self.subject_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.subject_repository.rollback_transaction()

    # CRUD Functions
    async def create(self, data):
        try:
          if not data:
            await self.logger.log(
                action="Create",
                entity="Subject",
                level="warning",
                code=400,
                message="No Data Provided for Creating Course.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=400,
                data=None,
                message="Empty Request was sent. Please provide data correctly.",
            )
           
          faculty_response = await self.faculty_repository.find_one(
              Faculty.id == int(data.faculty_id)
          )
          if not faculty_response.success:
              return BaseResponseDto(
                  success=False,
                  code=faculty_response.code,
                  data=None,
                  message=faculty_response.message,
              )
          faculty = faculty_response.data
          if not faculty:
              await self.logger.log(
                  action="Create",
                  entity="Subject",
                  level="warning",
                  code=404,
                  message="Faculty not found for subject creation",
                  details={"faculty_id": data.faculty_id},
                  source="SubjectService",
              )
              return BaseResponseDto(
                  success=False,
                  code=404,
                  data=None,
                  message="Faculty not found",
              )
        
          department_response = await self.department_repository.find_one(
              Department.id == int(data.department_id)
          )
          if not department_response.success:
              return BaseResponseDto(
                  success=False,
                  code=department_response.code,
                  data=None,
                  message=department_response.message,
              )
          department = department_response.data
          if not department:
              await self.logger.log(
                  action="Create",
                  entity="Subject",
                  level="warning",
                  code=404,
                  message="Department not found for subject creation",
                  details={"department_id": data.department_id},
                  source="SubjectService",
              )
              return BaseResponseDto(
                  success=False,
                  code=404,
                  data=None,
                  message="Department not found",
              )
        
                              
          if department.faculty_id != faculty.id:
              await self.logger.log(
                  action="Create",
                  entity="Subject",
                  level="warning",
                  code=400,
                  message="Department Does Not Belong to the Specified Faculty for Course Creation.",
                  details={"department_id": data.department_id, "faculty_id": data.faculty_id},
                  source="SubjectService",
              )
              return BaseResponseDto(
                  success=False,
                  code=400,
                  data=None,
                  message="Department does not belong to the specified faculty",
              )
          
          year_response = await self.year_repository.find_one(
              Year.id == int(data.year_id)
          )
          if not year_response.success:
              return BaseResponseDto(
                  success=False,
                  code=year_response.code,
                  data=None,
                  message=year_response.message,
              )
          year = year_response.data
          if not year:
              await self.logger.log(
                  action="Create",
                  entity="Subject",
                  level="warning",
                  code=404,
                  message="Year not found for subject creation",
                  details={"year_id": data.year_id},
                  source="SubjectService",
              )
              return BaseResponseDto(
                  success=False,
                  code=404,
                  data=None,
                  message="Year not found",
              )
        
          existing_subject_response = await self.subject_repository.find_one(and_(
                Subject.faculty_id == int(data.faculty_id),
                Subject.department_id == int(data.department_id),
                Subject.year_id == int(data.year_id),
                func.lower(Subject.code) == data.code.lower(),))              
            
          if not existing_subject_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=existing_subject_response.code,
                        data=None,
                        message=existing_subject_response.message,
                    )         
                    
                    
          if existing_subject_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Subject with this code Already Exists in the Specified Faculty, Department and Year.",
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Subject with this code already exists in the specified criteria",
                )          

          data.faculty_id = faculty.id
          data.department_id = department.id
          data.year_id = year.id
            
                        
          
          create_response = await self.subject_repository.create(data)
          if not create_response.success:
              return BaseResponseDto(
                  success=False,
                  code=create_response.code,
                  data=None,
                  message=create_response.message,
              )
          
          await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="info",
                    code=201,
                    message="Subject Created Successfully.",
                    details={"subject_id": create_response.data.id, "code": data.code},
                    source="SubjectService",
                )
          return BaseResponseDto(success=True, code=201, data=create_response.data,
          message="Subject created successfully")
                  
        except Exception as e:
         await self.logger.log(
          action="Create",
          entity="Subject",
          level="error",
          code=500,
          message="An Error Occurred while Creating Subject.",
          details={"error": str(e)},
          source="SubjectService",)
         
         return BaseResponseDto(success=False, code=500, 
          message="An error occurred while creating Subject")


    async def find_one(
            self, data=None, includes=None, selects=None, is_and=False,
            starts_with=True, is_exact=True, order_by=None, descending=False,
        ):
            try:
                predicate = self.helper_service.generate_dynamic_predicate(
                    Subject, data, ["name", "code"], is_and, starts_with, is_exact
                )
                dynamic_includes = self.helper_service.generate_dynamic_includes(Subject, includes)
                dynamic_selects = self.helper_service.generate_dynamic_selects("Subject", selects)
                dynamic_order_by = self.helper_service.generate_dynamic_order_by("Subject", order_by)
                result = await self.subject_repository.find_one(
                    predicate, dynamic_includes, dynamic_selects, dynamic_order_by, descending
                )
                if not result.success:
                    return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)
                return BaseResponseDto(success=True, data=result.data)
            except Exception as ex:
                await self.logger.log(
                    action="FindOne", entity="Subject", level="error", code=500,
                    message="An error occurred while finding subject",
                    details={"error": str(ex)}, source="SubjectService",
                )
                return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while finding subject")


    async def find(
        self, data=None, includes=None, selects=None, is_and=False,
        starts_with=True, is_exact=True, order_by=None, descending=False, page=1, limit=50,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Subject, data, ["name", "code"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(Subject, includes)
            dynamic_selects = self.helper_service.generate_dynamic_selects("Subject", selects)
            dynamic_order_by = self.helper_service.generate_dynamic_order_by("Subject", order_by)
            result = await self.subject_repository.find(
                predicate, dynamic_includes, dynamic_selects, dynamic_order_by, descending, page, limit
            )
            if not result.success:
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Find", entity="Subject", level="error", code=500,
                message="An error occurred while finding subjects",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while finding subjects")

    async def update(self, subject_id: int, data: Subject) -> BaseResponseDto:
        try:
            existing_response = await self.subject_repository.find_one(Subject.id == subject_id)

            if not existing_response.success:
                return BaseResponseDto(success=False, code=existing_response.code, data=None, message=existing_response.message)
            subject = existing_response.data

            if not subject:
                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Subject not found for update", details={"subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(success=False,
                 code=404, data=None, message="Subject not found")

            faculty_response = await self.faculty_repository.find_one(Faculty.id == data.faculty_id)
            if not faculty_response.success:
                return BaseResponseDto(success=False, code=faculty_response.code, data=None, message=faculty_response.message)
            
            faculty = faculty_response.data
            if not faculty:
                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Faculty Not Found for Subject Update.", details={'faculty_id': data.faculty_id},
                    source="SubjectService",
                )


                return BaseResponseDto(success=False, code=404, data=None, message="Faculty not found")

            department_response = await self.department_repository.find_one(Department.id == data.department_id)
            if not department_response.success:
                return BaseResponseDto(success=False, code=department_response.code, data=None, message=department_response.message)
            department = department_response.data

            if not department:
                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Department Not Found for Subject Update.", 
                    details={'department_id': data.department_id},
                    source="SubjectService",
                )

                return BaseResponseDto(success=False, code=404, data=None, message="Department not found")

            if department.faculty_id != faculty.id:
                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Department Does Not Belong to the Specified Faculty for Subject Update.", 
                    details={{'department_id': data.department_id, 'faculty_id': data.faculty_id}},
                    source="SubjectService",
                )
                
                return BaseResponseDto(success=False, code=400, data=None, message="Department does not belong to the specified faculty")

            year_response = await self.year_repository.find_one(Year.id == data.year_id)
            if not year_response.success:
                return BaseResponseDto(success=False, code=year_response.code, data=None, message=year_response.message)
            year = year_response.data
            if not year:

                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Year Not Found for Subject Update.", 
                    details={'year_id': data.year_id},
                    source="SubjectService",
                )

                return BaseResponseDto(success=False, code=404, data=None, message="Year not found")

            duplicate_response = await self.subject_repository.find_one(
                and_(
                    Subject.faculty_id == faculty.id,
                    Subject.department_id == department.id,
                    Subject.year_id == year.id,
                    func.lower(Subject.code) == data.code.lower(),
                )
            )
            if not duplicate_response.success:
                return BaseResponseDto(success=False, code=duplicate_response.code, data=None, message=duplicate_response.message)
            
            duplicate = duplicate_response.data
            if duplicate and duplicate.id != subject.id:

                await self.logger.log(
                    action="Update",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Subject with this code Already Exists in the Specified Faculty, Department and Year for Subject Update", 
                    source="SubjectService",
                )
               
                return BaseResponseDto(success=False, code=400, data=None, message="Subject with this code already exists in the specified criteria")

            subject.name = data.name
            subject.code = data.code
            subject.faculty_id = faculty.id
            subject.department_id = department.id
            subject.year_id = year.id
            subject.credits = data.credits
            subject.details["description"] = data.details.get("description") if data.details else None
            subject.details["max_students"] = data.details.get("max_students") if data.details else None

            update_response = await self.subject_repository.update(subject)
            if not update_response.success:
                return BaseResponseDto(success=False, code=update_response.code, data=None, message=update_response.message)

            await self.logger.log(
                action="Update", entity="Subject", level="info", code=200,
                message="Subject updated successfully.",
                details={"subject_id": subject.id}, source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=update_response.data, message="Subject updated successfully")
        except Exception as ex:
            await self.logger.log(
                action="Update", entity="Subject", level="error", code=500,
                message="An error occurred while updating subject",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while updating subject")

    async def delete(self, subject_id: int) -> BaseResponseDto:
        try:
            existing_response = await self.subject_repository.find_one(
                Subject.id == subject_id, ["users"]
            )
            if not existing_response.success:
                return BaseResponseDto(success=False, code=existing_response.code, data=None, message=existing_response.message)
            subject = existing_response.data
            if not subject:
                await self.logger.log(
                    action="Delete",
                    entity="Subject", 
                    level="warning", 
                    code=404,
                    message="Subject not found for deletion", details={"subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(success=False, code=404, data=None, message="Subject not found")

           
            if subject.users and len(subject.users) > 0:
                await self.logger.log(
                    action="Delete", entity="Subject", level="warning", code=400,
                    message="Subject cannot be deleted because it has users associated with it.",
                    details={"subject_id": subject_id, "users_count": len(subject.users)},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None,
                    message="Subject cannot be deleted because it has users associated with it",
                )

            delete_response = await self.subject_repository.delete(subject)
            if not delete_response.success:
                return BaseResponseDto(success=False, code=delete_response.code, data=None, message=delete_response.message)

            await self.logger.log(
                action="Delete", entity="Subject", level="info", code=200,
                message="Subject deleted successfully.", details={"subject_id": subject_id},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=True, message="Subject deleted successfully")
        except Exception as ex:
            await self.logger.log(
                action="Delete", entity="Subject", level="error", code=500,
                message="An error occurred while deleting subject",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while deleting subject")
        
    async def search(
        self,
        user,
        query: str | None = None,
        faculty_id: int | None = None,
        department_id: int | None = None,
        year_id: int | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> BaseResponseDto:
        try:
            if faculty_id:
                faculty_response = await self.faculty_repository.find_one(Faculty.id == faculty_id)
                if not faculty_response.success:
                    return BaseResponseDto(success=False, code=faculty_response.code, data=None, message=faculty_response.message)
                if not faculty_response.data:
                    await self.logger.log(
                        action="Search", entity="Subject", level="warning", code=404,
                        message="Faculty not found for subject search",
                        details={"faculty_id": faculty_id}, source="SubjectService",
                    )
                    return BaseResponseDto(success=False, code=404, data=None, message="Faculty not found")

            if department_id:
                department_response = await self.department_repository.find_one(Department.id == department_id)
                if not department_response.success:
                    return BaseResponseDto(success=False, code=department_response.code, data=None, message=department_response.message)
                department = department_response.data
                if not department:
                    await self.logger.log(
                        action="Search", entity="Subject", level="warning", code=404,
                        message="Department not found for subject search",
                        details={"department_id": department_id}, source="SubjectService",
                    )
                    return BaseResponseDto(success=False, code=404, data=None, message="Department not found")
                if not faculty_id:
                    await self.logger.log(
                        action="Search", entity="Subject", level="warning", code=400,
                        message="Faculty ID must be provided when department ID is given for subject search.",
                        details={"department_id": department_id}, source="SubjectService",
                    )
                    return BaseResponseDto(success=False, code=400, data=None, message="Faculty must be provided when department is given")
                if department.faculty_id != faculty_id:
                    await self.logger.log(
                        action="Search", entity="Subject", level="warning", code=400,
                        message="Department does not belong to the specified faculty for subject search.",
                        details={"department_id": department_id, "faculty_id": faculty_id},
                        source="SubjectService",
                    )
                    return BaseResponseDto(success=False, code=400, data=None, message="Department does not belong to the specified faculty")

            if year_id:
                year_response = await self.year_repository.find_one(Year.id == year_id)
                if not year_response.success:
                    return BaseResponseDto(success=False, code=year_response.code, data=None, message=year_response.message)
                if not year_response.data:
                    await self.logger.log(
                        action="Search", entity="Subject", level="warning", code=404,
                        message="Year not found for subject search",
                        details={"year_id": year_id}, source="SubjectService",
                    )
                    return BaseResponseDto(success=False, code=404, data=None, message="Year not found")

            conditions = []
            # Role-based scoping: non-top-level users only see subjects they're enrolled in
            if user.role.level != 1:
                enrolled_response = await self.user_subject_link_repository.find(
                    UserSubjectLink.user_id == user.id
                )
                if not enrolled_response.success:
                    return BaseResponseDto(success=False, code=enrolled_response.code, data=None, message=enrolled_response.message)
                enrolled_subject_ids = [link.subject_id for link in enrolled_response.data]
                if not enrolled_subject_ids:
                    return BaseResponseDto(success=True, code=200, data=[], message="Subjects search completed successfully")
                conditions.append(Subject.id.in_(enrolled_subject_ids))

            if faculty_id:
                conditions.append(Subject.faculty_id == faculty_id)
            if department_id:
                conditions.append(Subject.department_id == department_id)
            if year_id:
                conditions.append(Subject.year_id == year_id)
            if query:
                conditions.append(
                    or_(
                        func.lower(Subject.name).startswith(query.strip().lower()),
                        func.lower(Subject.code).startswith(query.strip().lower()),
                    )
                )

            predicate = and_(*conditions) if conditions else None
            order_by = self.helper_service.generate_dynamic_order_by("Subject", ["name"])

            result = await self.subject_repository.find(
                predicate, order_by=order_by, page=page, limit=limit
            )
            if not result.success:
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)

            await self.logger.log(
                action="Search", entity="Subject", level="info", code=200,
                message="Subjects search completed successfully.",
                details={"query": query, "subjects_count": len(result.data)},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=result.data, message="Subjects search completed successfully")
        except Exception as ex:
            await self.logger.log(
                action="Search", entity="Subject", level="error", code=500,
                message="An error occurred while searching subjects",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while searching subjects") 

    async def register(self, user_id: int, subject_id: int) -> BaseResponseDto:
        try:
            user_response = await self.user_repository.find_one(User.id == user_id)
            if not user_response.success:
                return BaseResponseDto(success=False, code=user_response.code, data=None, message=user_response.message)
            user = user_response.data
            if not user:
                return BaseResponseDto(success=False, code=404, data=None, message="User not found")

            subject_response = await self.subject_repository.find_one(
                Subject.id == subject_id, ["department", "year", "faculty"]
            )
            if not subject_response.success:
                return BaseResponseDto(success=False, code=subject_response.code, data=None, message=subject_response.message)
            subject = subject_response.data
            if not subject:
                await self.logger.log(
                    action="Register",
                    entity="Subject", 
                    level="warning", 
                    code=400,
                    message="Subject Not Found for Registration.",
                    details={"subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(success=False, code=404, data=None, message="Subject not found")

            if (
                subject.faculty_id != user.faculty_id
                or subject.department_id != user.department_id
                or subject.year_id != user.year_id
            ):
                await self.logger.log(
                    action="Register", entity="Subject", level="warning", code=400,
                    message="User Tried to Register to a Subject Not Belonging to His Academic Data.",
                    details={"user_id": user_id, "subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None,
                    message="You can only register to courses belonging to your academic data",
                )

            existing_response = await self.user_subject_link_repository.find_one(
                and_(UserSubjectLink.user_id == user_id, UserSubjectLink.subject_id == subject_id)
            )
            if not existing_response.success:
                return BaseResponseDto(success=False, code=existing_response.code, data=None, message=existing_response.message)
            if existing_response.data:
                await self.logger.log(
                    action="Register",
                    entity="Subject", 
                    level="warning", 
                    code=400,
                    message="User Tried to Register to a Course He is Already Registered In.",
                    details={"subject_id": subject_id},
                    source="SubjectService",
                )

                return BaseResponseDto(success=False, 
                code=400, data=None, message="You are already registered in this course")

            link = UserSubjectLink(user_id=user_id, subject_id=subject_id)
            create_response = await self.user_subject_link_repository.create(link)
            if not create_response.success:
                return BaseResponseDto(success=False, code=create_response.code, data=None, message=create_response.message)

            await self.logger.log(
                action="Register", entity="Subject", level="info", code=200,
                message="User registered for subject successfully.",
                details={"user_id": user_id, "subject_id": subject_id},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=subject, message="Registered to course successfully")
        except Exception as ex:
            await self.logger.log(
                action="Register", entity="Subject", level="error", code=500,
                message="An error occurred while registering for subject",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while registering for subject")

    async def unregister(self, user_id: int, subject_id: int) -> BaseResponseDto:
        try:
            existing_response = await self.user_subject_link_repository.find_one(
                and_(UserSubjectLink.user_id == user_id, UserSubjectLink.subject_id == subject_id)
            )
            if not existing_response.success:
                return BaseResponseDto(success=False, code=existing_response.code, data=None, message=existing_response.message)
            link = existing_response.data
            if not link:
                await self.logger.log(
                action="Unregister", 
                entity="Subject", 
                level="warning", 
                code=404,
                message="User Tried to Unregister from a Course He is Not Registered In.",
                details={"user_id": user_id, "subject_id": subject_id},
                source="SubjectService",
            )
                return BaseResponseDto(success=False, code=404, data=None, message="You are not registered for this course")

            delete_response = await self.user_subject_link_repository.delete(link)
            if not delete_response.success:
                return BaseResponseDto(success=False, code=delete_response.code, data=None, message=delete_response.message)

            await self.logger.log(
                action="Unregister", entity="Subject", level="info", code=200,
                message="User unregistered from subject successfully.",
                details={"user_id": user_id, "subject_id": subject_id},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=link.subject, message="Unregistered successfully")
        except Exception as ex:
            await self.logger.log(
                action="Unregister", entity="Subject", level="error", code=500,
                message="An error occurred while unregistering from subject",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while unregistering from subject")

    async def get_enrolled(self, user_id: int) -> BaseResponseDto:
        try:
            result = await self.user_subject_link_repository.find(
                UserSubjectLink.user_id == user_id, ["subject.department", "subject.year", "subject.faculty"]
            )
            if not result.success:
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)
            subjects = [link.subject for link in result.data]
            await self.logger.log(
                action="Get", 
                entity="Subject", 
                level="info", 
                code=200,
                message="User Enrolled Courses Retrieved Successfully.",
                details={"user_id": user_id},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=subjects, message="Enrolled courses retrieved successfully")
        except Exception as ex:
            await self.logger.log(
                action="GetEnrolled", entity="Subject", level="error", code=500,
                message="An error occurred while getting enrolled courses",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while getting enrolled courses")

    async def get_available(self, user_id: int, query: str | None = None) -> BaseResponseDto:
        try:
            user_response = await self.user_repository.find_one(User.id == user_id)
            if not user_response.success:
                return BaseResponseDto(success=False, code=user_response.code, data=None, message=user_response.message)
            user = user_response.data
            if not user:
                return BaseResponseDto(success=False, code=404, data=None, message="User not found")

            enrolled_response = await self.user_subject_link_repository.find(
                UserSubjectLink.user_id == user_id
            )
            if not enrolled_response.success:
                return BaseResponseDto(success=False, code=enrolled_response.code, data=None, message=enrolled_response.message)
            enrolled_subject_ids = [link.subject_id for link in enrolled_response.data]

            conditions = [
                Subject.faculty_id == user.faculty_id,
                Subject.department_id == user.department_id,
                Subject.year_id == user.year_id,
            ]
            if enrolled_subject_ids:
                conditions.append(Subject.id.notin_(enrolled_subject_ids))
            if query:
                conditions.append(
                    or_(
                        func.lower(Subject.name).startswith(query.strip().lower()),
                        func.lower(Subject.code).startswith(query.strip().lower()),
                    )
                )
            predicate = and_(*conditions)

            subjects_response = await self.subject_repository.find(
                predicate, includes=["department", "year", "faculty"], order_by=["name"]
            )
            if not subjects_response.success:
                return BaseResponseDto(success=False, code=subjects_response.code, data=None, message=subjects_response.message)

            await self.logger.log(
                action="GetAvailable", entity="Subject", level="info", code=200,
                message="Available courses for user retrieved successfully.",
                details={"user_id": user_id}, source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=subjects_response.data, message="Available courses retrieved successfully")
        except Exception as ex:
            await self.logger.log(
                action="GetAvailable", entity="Subject", level="error", code=500,
                message="An error occurred while getting available courses",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while getting available courses")  
        
    async def search_registered(
        self, user_id: int, query: str | None = None, page: int = 1, limit: int = 50,
    ) -> BaseResponseDto:
        try:
            conditions = [UserSubjectLink.user_id == user_id]
            if query:
                conditions.append(
                    or_(
                        func.lower(Subject.name).startswith(query.strip().lower()),
                        func.lower(Subject.code).startswith(query.strip().lower()),
                    )
                )

            result = await self.user_subject_link_repository.find(
                and_(*conditions), ["subject"], order_by=["subject.name"], page=page, limit=limit
            )
            if not result.success:
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)

            subjects = [link.subject for link in result.data]
            await self.logger.log(
                action="Search", entity="Subject", level="info", code=200,
                message="Registered courses search completed successfully.",
                details={"query": query, "subjects_count": len(subjects)},
                source="SubjectService",
            )
            return BaseResponseDto(success=True, code=200, data=subjects, message="Registered courses search completed successfully")
        except Exception as ex:
            await self.logger.log(
                action="Search", entity="Subject", level="error", code=500,
                message="An error occurred while searching registered courses",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while searching registered courses")

    async def get_enrolled_one(self, user_id: int, subject_id: int) -> BaseResponseDto:
        try:
            link_response = await self.user_subject_link_repository.find_one(
                and_(UserSubjectLink.user_id == user_id, UserSubjectLink.subject_id == subject_id),
                ["subject.department", "subject.year", "subject.faculty"],
            )
            if not link_response.success:
                return BaseResponseDto(success=False, code=link_response.code, data=None, message=link_response.message)
            link = link_response.data
            if not link:
                await self.logger.log(
                    action="GetEnrolledOne", entity="Subject", level="warning", code=404,
                    message="Enrolled course not found for user.",
                    details={"subject_id": subject_id}, source="SubjectService",
                )
                return BaseResponseDto(success=False, code=404, data=None, message="Enrolled course not found")
            await self.logger.log(
                    action="GetEnrolledOne", entity="Subject", level="info", code=200,
                    message="User Enrolled Course Retrieved Successfully.",
                    details={"user_id": user_id}, source="SubjectService",
                )
            return BaseResponseDto(success=True, code=200, data=link.subject, message="Enrolled course retrieved successfully")
        except Exception as ex:
            await self.logger.log(
                action="GetEnrolledOne", entity="Subject", level="error", code=500,
                message="An error occurred while getting enrolled course",
                details={"error": str(ex)}, source="SubjectService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while retrieving enrolled course")