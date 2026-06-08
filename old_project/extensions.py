from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from authlib.integrations.base_client import OAuthError
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from typing import AsyncGenerator
from sqlalchemy import event
import time
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, CollectorRegistry, generate_latest, multiprocess

load_dotenv()

# Initialize FastAPI
app = FastAPI()

# CORS Configuration (similar to Flask-CORS)
# origins = [f"http://127.0.0.1:{port}" for port in range(5500,5520)]
# origins.extend([f"http://localhost:{port}" for port in range(5500,5520)])
# origins.append("http://localhost:3000")
# origins.append("http://159.198.77.60")
# origins.append("http://cu-portal.com")
# origins.append("https://cu-portal.com")
app.add_middleware(
    CORSMiddleware,
    # # allow_origins=[os.environ.get("FRONTEND_URL")],  # Adjust in production!
    # allow_origins=[],  # Adjust in production!
    # allow_origin_regex='.*',
    # allow_credentials=True,
    # allow_methods=["*"],
    # allow_headers=["*"],
)

# Session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get('SECRET_KEY')
)
# Fernet encryption
fernet = Fernet((os.environ.get('FERNET_KEY')).encode())

# # Database setup (async SQLAlchemy)
# DATABASE_URL = "sqlite+aiosqlite:///./instance/students_portal.db"  # Async SQLite

# Database setup (async PostgreSQL)
# Get PostgreSQL connection details from environment variables
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "students_portal")

# Create PostgreSQL async connection URL
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass

# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# OAuth Setup (Google)
config = Config('.env')  # read config from .env file
oauth = OAuth(config)
google = oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    authorize_params={
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
    },
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/drive.file '
                 # 'https://www.googleapis.com/auth/drive.metadata https://www.googleapis.com/auth/docs '
                 # 'https://www.googleapis.com/auth/drive'
    }
)

# Prometheus Instrumentator
registry = CollectorRegistry()
prom_dir = os.environ.get('PROMETHEUS_MULTIPROC_DIR')

if prom_dir and os.path.isdir(prom_dir):
    multiprocess.MultiProcessCollector(registry, path=prom_dir)
    # Initialize instrumentator with the shared registry
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_instrument_requests_inprogress=True,
        inprogress_name="fastapi_requests_in_progress",
        inprogress_labels=True,
    )

    # Use the shared registry instead of the default one
    instrumentator.instrument(app)
else:
    pass


# 3. Manually create the /metrics endpoint to handle the multiprocess registry
@app.get("/metrics")
def metrics():
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

# Define the metrics
DB_QUERY_LATENCY = Histogram("db_query_duration_seconds", "Time spent on DB queries")
DB_QUERY_COUNT = Counter("db_query_total", "Total number of DB queries")

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.perf_counter() - context._query_start_time
    DB_QUERY_LATENCY.observe(total)
    DB_QUERY_COUNT.inc()

# Timezone setup
cairo_tz = ZoneInfo('Africa/Cairo')
utc_tz = ZoneInfo('UTC')

# Configurations
access_token_expire_time = 30  # minutes
refresh_token_expire_time = 30  # days
google_token_expire_time = 60  # minutes
user_token_expire_time = 60  # minutes
stored_state_expire_time = 10 * 365  # days

def get_hours_diff():
    """
    Calculates the difference in hours between Egypt time and UTC.
    :return: The difference in hours.
    """
    egypt_time = datetime.now(cairo_tz)
    utc_time = datetime.now(timezone.utc)
    diff = egypt_time - utc_time
    return diff.total_seconds() // 3600

def convert_to_utc(dt):
    """
    Converts a datetime/date object from Egypt timezone to UTC timezone.
    :param dt: The datetime/date object in Egypt timezone to convert.
    :return: The converted datetime object in UTC timezone.
    """
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=cairo_tz)
    
    return dt.astimezone(utc_tz)

def convert_from_utc(dt):
    """
    Converts a datetime/date object from UTC timezone to Egypt timezone.
    :param dt: The datetime/date object in UTC timezone to convert.
    :return: The converted datetime object in Egypt timezone.
    """    
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=utc_tz)
    
    return dt.astimezone(cairo_tz)