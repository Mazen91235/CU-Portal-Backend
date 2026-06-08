import os
import sys

# Ensure `src` is importable as the top-level package root in serverless runtimes.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.di.container import Container
from api.middlewares.requestMiddleware import RequestMiddleware
from business.contextVars.sessionContext import session_context
from core.utils.fileHandler import FileHandler


def create_app() -> FastAPI:
    app = FastAPI(title="AlZheimr API")
    container = Container()
    app.state.container = container
    # Static Content Serve on /uploads
    app.mount(
        "/uploads",
        StaticFiles(directory=FileHandler.Storage.UPLOAD_DIR),
        name="uploads",
    )

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Create one DB session per request and store it in ContextVar.
        session = container.session_factory()()
        session_token = session_context.set(session)
        try:
            response = await RequestMiddleware.handle(request, call_next)
            return response
        finally:
            session_context.reset(session_token)
            await session.close()

    # We resolve the router here at startup.
    # Because we are now using `Depends()` inside `create_user_router`,
    # the providers will correctly wait to resolve until a request comes in.
    user_routes = container.user_routes()
    patient_routes = container.patient_routes()
    patient_user_routes = container.patient_user_routes()
    patient_routes.include_router(patient_user_routes)
    app.include_router(user_routes)
    app.include_router(patient_routes)

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
