import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Ensure `src` is importable as the top-level package root in serverless runtimes.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from api.di.container import Container
from api.routes.customRoute import CustomRoute
from business.contextVars.sessionContext import session_context


def create_app() -> FastAPI:
    app = FastAPI(title="CU - Portal", version="1.0.0")
    container = Container()
    app.state.container = container
    app.router.route_class = CustomRoute

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Create one DB session per request and store it in ContextVar.
        await container.request_limit_middleware.provider().throttle(request)
        session = container.session_factory()()
        session_token = session_context.set(session)
        try:
            response = await call_next(request)
            return response
        finally:
            session_context.reset(session_token)
            await session.close()

    # We resolve the router here at startup.
    # Because we are now using `Depends()` inside `create_user_router`,
    # the providers will correctly wait to resolve until a request comes in.
    main_user_routes = container.main_user_routes()
    main_admin_routes = container.main_admin_routes()
    auth_routes = container.auth_routes()
    user_user_routes = container.user_user_routes()
    user_admin_routes = container.user_admin_routes()
    message_public_routes = container.message_public_routes()
    message_admin_routes = container.message_admin_routes()
    faculty_admin_routes = container.faculty_admin_routes()
    main_user_routes.include_router(user_user_routes)
    main_admin_routes.include_router(user_admin_routes)
    main_admin_routes.include_router(message_admin_routes)
    main_admin_routes.include_router(faculty_admin_routes)
    app.include_router(main_user_routes)
    app.include_router(main_admin_routes)
    app.include_router(auth_routes)
    app.include_router(message_public_routes)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
