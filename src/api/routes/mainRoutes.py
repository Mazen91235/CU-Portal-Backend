from fastapi import APIRouter


def create_main_user_router():
    router = APIRouter(prefix="/user", tags=["Users"])
    return router


def create_main_admin_router():
    router = APIRouter(prefix="/admin", tags=["Admin"])
    return router
