from fastapi import APIRouter
from api.routes.customRoute import CustomRoute


def create_main_user_router():
    router = APIRouter(prefix="/user", tags=[], route_class=CustomRoute)
    return router


def create_main_admin_router():
    router = APIRouter(prefix="/admin", tags=[], route_class=CustomRoute)
    return router
