from fastapi import APIRouter
from customRoute import CustomRoute

def create_main_user_router():
    router = APIRouter(prefix="/user", tags=["Users"],route_class=CustomRoute)
    return router


def create_main_admin_router():
    router = APIRouter(prefix="/admin", tags=["Admin"],route_class=CustomRoute)
    return router
