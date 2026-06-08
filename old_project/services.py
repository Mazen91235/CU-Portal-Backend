# from sqlalchemy.orm.attributes import set_committed_value
#
# from models import *
# from extensions import async_session
# class UserService(User):
#     async def create_user(self, name, email, phone, national_id, password, gender, url):
#         async with async_session() as session:
#             await session.begin()
#
#
#     @classmethod
#     def get_user_by_id(cls, user_id):
#         return cls.get_by_id(user_id)
#
#     async def update_user(self, id, name):
#         async with async_session() as session:
#             await session.begin()
#             user = await session.scalar(self.id == id)
#             if not user:
#                 return None
#             user.name = name
#             set_committed_value(user,"version",user.version+1)
#             await session.commit()
#         return user
#
#     @classmethod
#     def delete_user(cls, user_id):
#         user = cls.get_by_id(user_id)
#         if user:
#             user.delete()
#             return True
#         return False