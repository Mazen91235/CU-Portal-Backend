import json
import math
import os
import jwt
from sqlalchemy import Select, Delete, func, or_
from sqlalchemy.orm import selectinload
import re
from models import *
from extensions import load_dotenv, oauth, google, async_session, cairo_tz
from wrappers import is_logged_in, is_not_logged_in, rate_limit, is_authorized, is_ready
from settings import (send_email, generate_unique_token, log,
                      encrypt_data, decrypt_data, finalize_request, get_user_if_exists, updated_roles)
from urllib.parse import urlparse, parse_qs
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from authlib.integrations.httpx_client import AsyncOAuth2Client
import uvicorn
# Load environment variables first
load_dotenv()
templates = Jinja2Templates(directory='templates')
# Configurations
access_token_expire_time = 30  # minutes
refresh_token_expire_time = 30  # days
google_token_expire_time = 60  # minutes
user_token_expire_time = 60  # minutes
stored_state_expire_time = 10 * 365  # days
# Configure Blueprints
v1 = APIRouter(prefix='/api/v1', tags=['v1'])
auth= APIRouter(prefix='/auth', tags=['auth'])
user_prefix = APIRouter(prefix='/user', tags=['user'])
admin_prefix = APIRouter(prefix='/admin', tags=['admin'])

# Helper functions
async def generate_refresh_token(user_id, request:Request = None):
    async with async_session() as session:
        await session.begin()
        try:
            user = (await session.execute(Select(User).where(User.id == user_id))).scalar_one_or_none()
            if not user:
                return None
            refresh_token = await generate_unique_token(40)
            user.refresh_token = refresh_token
            user.refresh_expire_at = datetime.now(cairo_tz) + timedelta(days=refresh_token_expire_time)
            await session.commit()
            return refresh_token
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while generating refresh token.', {'error': str(e)}, user_id)
            await session.rollback()
            return None

async def remove_file_from_drive(drive_url, user_refresh_token, request:Request = None):
    current_user = request.state.current_user if request and hasattr(request.state, 'current_user') else None
     # Ensure user is authenticated
    if not current_user:
        await log(request, 401, 'warning', 'Unauthorized user tried to delete file from Google Drive.', {})
        return False
    try:
        # Refresh access token
        async with AsyncOAuth2Client(
            client_id=os.environ['GOOGLE_CLIENT_ID'],
            client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
        ) as client:
            new_token = await client.refresh_token(
                url='https://oauth2.googleapis.com/token',
                refresh_token=decrypt_data(user_refresh_token)
            )

        access_token = new_token['access_token']

        url = urlparse(drive_url)
        url_params = parse_qs(url.query)
        file_id = url_params.get('id', [None])[0]

        if not file_id:
            await log(request, 400, 'warning', 'Could not extract file_id from the provided Google Drive URL.', {'drive_url': drive_url}, current_user.id)
            return False

        # Delete file
        async with AsyncOAuth2Client(
            token={'access_token': access_token, 'token_type': 'Bearer'}
        ) as client:
            response = await client.delete(
                f"https://www.googleapis.com/drive/v3/files/{file_id}"
            )

            if str(response.status_code)[0] == '2':
                await log(request, 200, 'info', 'File deleted from Google Drive successfully.', {'file_id': file_id}, current_user.id)
                return True
            else:
                body = await response.aread()
                decoded = json.loads(body.decode())
                if decoded and decoded.get('error') and decoded['error'].get('errors') and decoded['error']['errors'][0].get('reason') == 'notFound':
                    return True
                await log(request, 400, 'warning', 'Failed to delete file from Google Drive.', {'status_code': response.status_code, 'response': body.decode(), 'file_id': file_id}, current_user.id)
                return False

    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while deleting file from Google Drive.', {'error': str(e)}, current_user.id)
        return False

def format_size(bytes_str: str) -> str:
    if not bytes_str:
        return 'Unknown'
    size = int(bytes_str)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def verify_file_type(mimetype: str, type: str) -> bool:
    """
    Verifies if the given mimetype matches the expected file type.
    :param mimetype: File MIME type returned by Drive API
    :param type: Expected file category (image, pdf, doc, sheet, ppt, video, audio, text, archive, etc.)
    :return: True if matches, False otherwise
    """
    type = type.strip().lower()
    mimetype = mimetype.strip().lower()
    if type == 'image':
        return mimetype in [
            'image/png',
            'image/jpeg',   # covers .jpg and .jpeg
            'image/webp',
            'image/gif',
            'image/bmp',
            'image/svg+xml',
            'image/tiff',
            'image/heic'
        ]

    elif type == 'pdf':
        return mimetype == 'application/pdf'

    elif type in ['doc', 'docx', 'docs']:
        return mimetype in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.google-apps.document'
        ]

    elif type in ['sheet', 'xlsx', 'xls', 'excel']:
        return mimetype in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.google-apps.spreadsheet'
        ]

    elif type in ['ppt', 'pptx', 'presentation']:
        return mimetype in [
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.presentation'
        ]

    elif type == 'video':
        return mimetype in [
            'video/mp4',
            'video/mpeg',
            'video/quicktime',
            'video/x-msvideo',   # avi
            'video/x-ms-wmv',
            'video/webm',
            'video/ogg',
            'video/3gpp',
            'video/3gpp2'
        ]

    elif type == 'audio':
        return mimetype in [
            'audio/mpeg',   # mp3
            'audio/mp3',
            'audio/wav',
            'audio/ogg',
            'audio/aac',
            'audio/flac',
            'audio/webm',
            'audio/3gpp'
        ]

    elif type in ['text', 'json', 'xml', 'csv', 'html', 'css', 'js']:
        return mimetype in [
            'text/plain',
            'text/csv',
            'text/html',
            'text/css',
            'text/javascript',
            'application/json',   # Drive may return this for JSON files
            'application/xml'
        ]

    elif type in ['archive', 'compressed']:
        return mimetype in [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
            'application/gzip',
            'application/x-tar',
            'application/x-bzip2'
        ]

    # Google Drive special 'native' files
    elif type == 'gdrive':
        return mimetype in [
            'application/vnd.google-apps.folder',
            'application/vnd.google-apps.form',
            'application/vnd.google-apps.drawing',
            'application/vnd.google-apps.script',
            'application/vnd.google-apps.map',
            'application/vnd.google-apps.jam'
        ]

    else:
        return False

def get_file_type(mimetype: str) -> str:
    """
    Determines the general file type based on the MIME type.
    :param mimetype: File MIME type returned by Drive API
    :return: General file type (image, pdf, doc, sheet, ppt, video, audio, text, archive, gdrive, unknown)
    """
    mimetype = mimetype.strip().lower()
    if verify_file_type(mimetype, 'image'):
        return 'image'
    elif verify_file_type(mimetype, 'pdf'):
        return 'pdf'
    elif verify_file_type(mimetype, 'doc'):
        return 'doc'
    elif verify_file_type(mimetype, 'sheet'):
        return 'sheet'
    elif verify_file_type(mimetype, 'ppt'):
        return 'ppt'
    elif verify_file_type(mimetype, 'video'):
        return 'video'
    elif verify_file_type(mimetype, 'audio'):
        return 'audio'
    elif verify_file_type(mimetype, 'text'):
        return 'text'
    elif verify_file_type(mimetype, 'archive'):
        return 'archive'
    elif verify_file_type(mimetype, 'gdrive'):
        return 'gdrive'
    else:
        return 'unknown'

def is_allowed_file_type(mimetype: str, excluded_types: list) -> bool:
    """
    Checks if the given mimetype is not in the excluded types.
    :param mimetype: File MIME type returned by Drive API
    :param excluded_types: List of excluded file categories (image, pdf, doc, sheet, ppt, video, audio, text, archive, etc.)
    :return: True if not excluded, False otherwise
    """
    allowed_file_types = ['image', 'pdf', 'doc', 'sheet', 'ppt', 'video', 'audio', 'text', 'archive', 'gdrive']
    excluded_types = [type.strip().lower() for type in excluded_types]
    allowed_file_types = [type.strip().lower() for type in allowed_file_types if type.strip().lower() not in excluded_types]

    mimetype = mimetype.strip().lower()
    if mimetype not in allowed_file_types:
        return False
    return True

def get_file_data(drive_file: dict) -> dict:
    """
    Extracts and formats relevant file data from the Google Drive file metadata.
    :param drive_file: File metadata dictionary returned by Drive API
    :return: Formatted file data dictionary
    """
    if not drive_file or not isinstance(drive_file, dict):
        return {}

    file_id = drive_file.get('id')
    name = drive_file.get('name')
    mimeType = drive_file.get('mimeType')
    size = format_size(drive_file.get('size')) if drive_file.get('size') else 'Unknown'
    webContentLink = drive_file.get('webContentLink')
    webViewLink = drive_file.get('webViewLink')
    file_type = get_file_type(mimeType) if mimeType else 'unknown'
    if not webContentLink:
        webContentLink = f"https://drive.google.com/uc?id={file_id}&export=download"
    return {
        'id': file_id,
        'name': name,
        'mimeType': mimeType,
        'type': file_type,
        'size': size,
        'webContentLink': webContentLink,
        'webViewLink': webViewLink
    }

async def get_file_from_drive(drive_url, user_refresh_token, request:Request = None):
    current_user = request.state.current_user if request and hasattr(request.state, 'current_user') else None
    # Ensure user is authenticated
    if not current_user:
        await log(request, 401, 'warning', 'Unauthorized user tried to access file from Google Drive.', {})
        return None
    try:
        # Refresh access token
        async with AsyncOAuth2Client(
            client_id=os.environ['GOOGLE_CLIENT_ID'],
            client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
        ) as client:
            new_token = await client.refresh_token(
                url='https://oauth2.googleapis.com/token',
                refresh_token=decrypt_data(user_refresh_token)
            )

        access_token = new_token['access_token']

        url = urlparse(drive_url)
        url_params = parse_qs(url.query)
        file_id = url_params.get('id', [None])[0]

        if not file_id:
            await log(request, 400, 'warning', 'Could not extract file_id from the provided Google Drive URL.', {'drive_url': drive_url}, current_user.id)
            return None

        # Get file metadata
        async with AsyncOAuth2Client(
            token={'access_token': access_token, 'token_type': 'Bearer'}
        ) as client:
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={'fields': 'id, name, mimeType, size, webContentLink, webViewLink'}
            )

            if str(response.status_code)[0] == '2':
                body = await response.aread()
                decoded = json.loads(body.decode())
                await log(request, 200, 'info', 'File metadata retrieved from Google Drive successfully.', {'file_id': file_id}, current_user.id)
                return decoded
            else:
                body = await response.aread()
                decoded = json.loads(body.decode())
                if decoded and decoded.get('error') and decoded['error'].get('errors') and decoded['error']['errors'][0].get('reason') == 'notFound':
                    return None
                await log(request, 400, 'warning', 'Failed to get file metadata from Google Drive.', {'status_code': response.status_code, 'response': body.decode(), 'file_id': file_id}, current_user.id)
                return None

    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while retrieving file metadata from Google Drive.', {'error': str(e)}, current_user.id)
        return None

def is_int(value) -> bool:
    """
    Helper function to check if a value is an integer.
    """
    try:
        int(value)
        return True
    except ValueError:
        return False

def is_float(value) -> bool:
    """
    Helper function to check if a value is a float.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def is_sanitized(data) -> bool:
    """
    Checks if the given data is sanitized.

    Rules:
    - str: Must be either:
        1. A phone number starting with '+' followed by digits only (e.g. '+20151511'), OR
        2. Only letters (a-zA-Z), hyphen (-), underscore (_), and space.
    - dict: All keys and values must be sanitized recursively.
    - list: All elements must be sanitized recursively.
    - Other types: Considered safe (returns True).
    """
    if not data:
        return True
    if isinstance(data, str):
        # Phone number format: + followed by digits
        if re.fullmatch(r'\+\d+', data):
            return True
        # Allowed chars: letters, hyphen, underscore, space
        if re.fullmatch(r'[a-zA-Z0-9\-_ ]+', data):
            return True
        return False

    elif isinstance(data, dict):
        return all(is_sanitized(k) and is_sanitized(v) for k, v in data.items())

    elif isinstance(data, list):
        return all(is_sanitized(item) for item in data)

    return True

def is_drive_url(url: str) -> bool:
    """
    Validates if the provided URL is a valid Google Drive URL.
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match various Google Drive URL formats
    drive_url_pattern = re.compile(
        r'^(https?://)?(www\.)?(drive\.google\.com|docs\.google\.com|forms\.google\.com|slides\.google\.com|sheets\.google\.com|sites\.google\.com)/.*$'
    )

    return bool(drive_url_pattern.match(url.strip()))

def is_youtube_url(url: str) -> bool:
    """
    Validates if the provided URL is a valid YouTube URL.
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match various YouTube URL formats
    youtube_url_pattern = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.*$'
    )

    return bool(youtube_url_pattern.match(url.strip()))

def is_valid_url(url: str) -> bool:
    """
    Validates if the provided string is a well-formed URL (Public Url only).
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match well-formed URLs (excluding localhost, IP addresses, and port)
    url_pattern = re.compile(
        r'^(https?://)'  # http:// or https://
        r'(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})'  # Domain name only
        r'(/[A-Za-z0-9\-._~:/?#[\]@!$&\'()*+,;=]*)?$'  # Path and query string
    )

    return bool(url_pattern.match(url.strip()))

# Authentication routes
@auth.post('/refresh')
@rate_limit
@is_not_logged_in
async def refresh(request: Request):
    try:
        data = await request.json()
        if not data:
            await log(request, 400, 'warning', 'No Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'No data provided'
            }, 400)
            return finalize_request(response)
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        refresh_token = data.get('refresh_token' ,None) if data else None
        if not refresh_token:
            await log(request, 400, 'warning', 'No Refresh Token Found in The Request Cookies.', {})
            return {
                'status': 'error',
                'message': 'You are not logged in. Please log in again.'
            }, 400
    except json.JSONDecodeError as e:
        await log(request, 400, 'warning', 'Invalid JSON in Request Body.', {'error': str(e)})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid JSON. Please provide a valid JSON body.'
        }, 400)
        return finalize_request(response)
    try:
        async with async_session() as session:
            user = (await session.execute(Select(User).where(User.refresh_token == refresh_token,
                                                             User.refresh_expire_at > datetime.now(cairo_tz)
                                                             ))).scalar_one_or_none()
            if not user:
                await log(request, 404, 'warning', 'User Not Found.', { 'refresh_token': refresh_token})
                response = JSONResponse(
                    {
                        'status': 'error',
                        'message': 'User not found'
                    }, 404
                )
                return finalize_request(response)
            expire_date = user.refresh_expire_at.replace(tzinfo=cairo_tz)
            payload = {
                'id': user.id,
                'expire_date': (datetime.now(cairo_tz) + timedelta(minutes=access_token_expire_time)).isoformat()
            }
            access_token = jwt.encode(payload, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm='HS256')
            if (expire_date - datetime.now(cairo_tz)).days < 7:  # If the refresh token is about to expire in less than 7 days
                await log(request, 200, 'info', 'Refreshing Refresh Token for User.', {}, user.id)
                refresh_token = await generate_refresh_token(user.id)
                if not refresh_token:
                    await log(request, 500, 'error', 'An error occurred while generating refresh token for user.', {}, user.id)
                    response = JSONResponse(
                        {
                            'status': 'error',
                            'message': 'An error occurred while generating refresh token'
                        }, 500
                    )
                    return finalize_request(response)
                expire_date = user.refresh_expire_at
            await log(request, 200, 'info', 'Successfully refreshed tokens for user.', {}, user.id)
            response_payload = {
                'access_token': access_token,
                'access_expires_in': int(timedelta(minutes=access_token_expire_time).total_seconds()),  # seconds until expiration
                'refresh_token': refresh_token,
                'refresh_expires_in': int((expire_date - datetime.now(cairo_tz)).total_seconds()),  # seconds until expiration
            }
            response = JSONResponse(
                {
                    'status': 'success',
                    'message': 'Token refreshed successfully',
                    'data': response_payload
                }, 200
            )
            return finalize_request(response)
    except jwt.ExpiredSignatureError as e:
        response = JSONResponse({
            'status': 'error',
            'message': str(e)
        }, 407)
        return finalize_request(response)
    except jwt.InvalidTokenError as e:
        response = JSONResponse({
            'status': 'error',
            'message': str(e)
        }, 401)
        return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while refreshing tokens.', {'error': str(e)})
        response = JSONResponse({
            'status': 'error',
            'message': "An Error Occurred. Please Try Again Later."
        }, 500)
        return finalize_request(response)

@auth.post('/signup')
@rate_limit
@is_not_logged_in
async def signup(request: Request):
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for SignUp.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'No data provided'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    email = data.get('email').strip().lower()
    phone = data.get('phone').strip()
    national_id = data.get('national_id').strip()
    gender = data.get('gender').strip()
    agreed = data.get('agreed')
    if agreed != 'on':
        await log(request, 400, 'warning', 'User did not agree to the terms and conditions.', {'data': dict(data)})
        response = JSONResponse({
            'status': 'error',
            'message': 'You must agree to the terms and conditions to sign up'
        }, 400)
        return finalize_request(response)
    manages = {}
    details = {}
    google_details_token = data.get('google_details_token').strip()
    if not google_details_token:
        await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {
                                                                               'data': dict(data)})
        response = JSONResponse({
            'status': 'error',
            'message': 'You Must Authorize Google Account to Proceed.'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            google_details_token = (await session.execute(Select(Token).where(Token.token == google_details_token,
                                                                        Token.expire_at > datetime.now(cairo_tz)))).scalar_one_or_none()
            if not google_details_token or not google_details_token.details:
                await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {
                                                                                       'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You Must Authorize Google Account to Proceed.'
                }, 400)
                return finalize_request(response)
            google_details_token.expire_at = datetime.now(cairo_tz) + timedelta(minutes=-1) # Invalidate the token
            google_details_token = google_details_token.details
            if not name or not email or not phone or not national_id or not gender or gender == 'gender':
                await log(request, 400, 'warning', 'Missing Required Fields for SignUp.', {'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Please make sure to fill all the required fields'
                }, 400)
                return finalize_request(response)
            if (await session.execute(Select(User).where(User.email == email))).scalar_one_or_none():
                await log(request, 400, 'warning', 'User Tried to SignUp with Email Already Existing.', {'email': email, 'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Email already exists'
                }, 400)
                return finalize_request(response)
            if (await session.execute(Select(User).where(User.national_id == national_id))).scalar_one_or_none():
                await log(request, 400, 'warning', 'User Tried to SignUp with National ID Already Existing.', {'national_id': national_id,
                                                                                                  'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'A user with this national ID already exists'
                }, 400)
                return finalize_request(response)
            if (await session.execute(Select(User).where(User.phone == phone))).scalar_one_or_none():
                await log(request, 400, 'warning', 'User Tried to SignUp with Phone Number Already Existing.', {'phone': phone,
                                                                                                  'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'A user with this phone number already exists'
                }, 400)
                return finalize_request(response)
            try:
                email_info = validate_email(email, check_deliverability=True)
            except EmailNotValidError as e:
                await log(request, 400, 'warning', 'Invalid Email Address Provided for SignUp.', {'email': email, 'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': str(e)
                }, 400)
                return finalize_request(response)
            if len(national_id) != 14 or not national_id.isdigit():
                await log(request, 400, 'warning', 'Invalid National ID Provided for SignUp.', {'national_id': national_id,
                                                                                          'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'National ID must be exactly 14 digits'
                }, 400)
                return finalize_request(response)
            if len(phone) < 11:
                await log(request, 400, 'warning', 'Invalid Phone Number Provided for SignUp.', {'phone': phone,
                                                                                          'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Phone number must be at least 11 characters'
                }, 400)
                return finalize_request(response)
            if not phone.isdigit() and not (phone.startswith('+') and phone[1:].isdigit()):
                await log(request, 400, 'warning', 'Invalid Phone Number Provided for SignUp.', {'phone': phone,
                                                                                          'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Phone number must contain only digits and may start with a '+' for country code'
                }, 400)
                return finalize_request(response)
            domain = email_info.domain
            url = None
            allowed_domains = ['cu.edu.eg', 'stud.cu.edu.eg']
            if domain not in allowed_domains and not any(d for d in allowed_domains if d in domain):
                url = data.get('url', None).strip() if data.get('url') else None
                if not url:
                    await log(request, 400, 'warning', 'User Did not use University email and did not provide approval image for SignUp.',
                              {'email': email,
                                                                                                   'data': dict(data)})
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'You must Upload Your Approval Image or Use Your University Email (stud.cu.edu.eg) to '
                                   'SignUp.'
                    }, 400)
                    return finalize_request(response)
            status = (url is None)
            google_user_details = jwt.decode(
                google_details_token,
                os.environ.get('GOOGLE_TOKEN_SECRET_KEY'),
                algorithms=['HS256']
            )
            if not google_user_details:
                await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {
                                                                                       'data': dict(data)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You Must Authorize Google Account to Proceed.'
                }, 400)
                return finalize_request(response)
            google_user_details = google_user_details.get('google_user_details')
            if url:
                drive_file = await get_file_from_drive(url, google_user_details.get('google_refresh_token'), request)
                if not drive_file:
                    await log(request, 400, 'warning', 'Invalid Google Drive URL Provided for Approval Image.', {
                                                                                       'data': dict(data)})
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid Image Uploaded. Please try again.'
                    }, 400)
                    return finalize_request(response)
                if not verify_file_type(drive_file.get('mimeType', ''), 'image'):
                    await log(request, 400, 'warning', 'Non Image File Provided as Approval Image.', {
                                                                                       'data': dict(data),
                                                                                       'file_mimeType': drive_file.get('mimeType', '')})
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'The Uploaded File Must Be an Image. Please try again.'
                    }, 400)
                    return finalize_request(response)
                if drive_file.get('size') and int(drive_file.get('size')) > 10 * 1024 * 1024:
                    await log(request, 400, 'warning', 'Image Provided as Approval Image Exceeds Size Limit.', {
                                                                                       'data': dict(data),
                                                                                       'file_size': drive_file.get('size')})
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'The Uploaded Image Must Not Exceed 10MB in Size. Please try again.'
                    }, 400)
                    return finalize_request(response)
            token = await generate_unique_token(40)
            payload = {
                'user' : {
                'name': name,
                'email': email,
                'phone': phone,
                'national_id': national_id,
                'gender': gender,
                'role': 'user',
                'manages': manages,
                'details': details,
                'status': status,
                'google_id': google_user_details.get('google_id'),
                'google_name': google_user_details.get('google_name'),
                'google_email': google_user_details.get('google_email'),
                'google_avatar': google_user_details.get('google_avatar'),
                'google_refresh_token': google_user_details.get('google_refresh_token')
            }
            }
            if not status:
                payload['pending_user'] = {
                    'url': url
                }
            token_user = jwt.encode(payload, os.environ.get('USER_TOKEN_SECRET_KEY'), algorithm='HS256')
            token_db = Token(
                token=token,
                details=token_user,
                is_valid=True,
                expire_at=datetime.now(cairo_tz) + timedelta(minutes=user_token_expire_time),
                type=1  # 1 for User signup token
            )
            session.add(token_db)
            await session.commit()
            email_sent = await send_email(request, email, 'verify_email', {
                'name': name,
                'link': 'https://' + request.url.hostname + f"/verify-email?token={token}",
            })
            if email_sent.status_code != 200:
                await session.delete(token_db)
                await session.commit()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'An Error Occurred While Trying to SignUp Please Try Again Later.'
                }, 500)
                return finalize_request(response)
            response = JSONResponse({
                'status': 'success',
                'message': 'Successfully Created Your Profile. Please Check Your Email to Verify Your Account.'
            }, 201)
            await log(request, 201, 'info', 'User Signed Up Successfully.', {'data': dict(data), 'user':payload.get('user')})
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while signing up user.', {'error': str(e), 'data': dict(data)})
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An Error Occurred While Trying to SignUp Please Try Again Later.'
            }, 500)
            return finalize_request(response)

@auth.get('/logout')
@rate_limit
@is_logged_in
async def logout(request: Request):
    """
    This route is used to log out the user.
    It will clear the session and cookies.
    """
    async with async_session() as session:
        await session.begin()
        try:
            current_user = request.state.current_user
            current_user.refresh_token = None  # Clear the refresh token
            current_user.refresh_expire_at = datetime.now(cairo_tz) + timedelta(minutes=-1)
            await session.commit()
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=You have "
                                              f"logged out successfully.")
            await log(request, 200, 'info', 'User logged out successfully.', {}, current_user.id)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while logging out user.', {'error': str(e)}, current_user.id if current_user else None)
            await session.rollback()
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                              f"Logging You Out. Please Try Again Later.")
            return finalize_request(response)

@app.get('/verify-email')
@rate_limit
@is_not_logged_in
async def verify_email(request: Request):
    token = request.query_params.get('token')
    if not token:
        await log(request, 400, 'warning', 'No Token Provided for Email Verification.')
        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
                                          f"Request. Please try to SignUp Again.")
        return finalize_request(response)
    if not is_sanitized(token):
        await log(request, 400, 'warning', 'Un Sanitized Token Provided for Email Verification.', {'token': token})
        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
                                          f"Request. Please try to SignUp Again.")
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            token_db = (await session.execute(Select(Token).where(Token.token == token, Token.expire_at > datetime.now(
                cairo_tz)))).scalar_one_or_none()
            if not token_db or not token_db.details:
                await log(request, 400, 'warning', 'Invalid or Expired Token Provided for Email Verification.', {'token': token})
                await session.rollback()
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
                                                  f"Request. Please Try to SignUp Again.")
                return finalize_request(response)
            payload = jwt.decode(token_db.details, os.environ.get('USER_TOKEN_SECRET_KEY'), algorithms=['HS256'])
            user = payload.get('user')
            if not user:
                await log(request, 400, 'warning', 'Invalid User Data in Token Provided for Email Verification.', {'token': token})
                await session.rollback()
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
                                                  f"Request. Please Try to SignUp Again.")
                return finalize_request(response)
            user_db = User(
                name=user.get('name'),
                email=user.get('email'),
                phone=user.get('phone'),
                national_id=user.get('national_id'),
                gender=user.get('gender'),
                role=(await session.execute(Select(Role).where(Role.name == 'user'))).scalar_one_or_none(),
                manages=user.get('manages'),
                details=user.get('details'),
                status=user.get('status'),
                google_id=user.get('google_id'),
                google_name=user.get('google_name'),
                google_email=user.get('google_email'),
                google_avatar=user.get('google_avatar'),
                google_refresh_token=user.get('google_refresh_token'),
                ips = [request.client.host]  # Store the IP address of the user
            )
            pending_user = payload.get('pending_user')
            pending_user_db = PendingUser(
                url=pending_user.get('url') if pending_user else None,
            )
            session.add(user_db)
            if pending_user:
                pending_user_db.user = user_db
                session.add(pending_user_db)
            token_db.expire_at = datetime.now(cairo_tz) - timedelta(minutes=1)  # Invalidate the token
            await session.commit()
            refresh_token = await generate_refresh_token(user_db.id)
            if not refresh_token:
                await log(request, 500, 'error', 'An error occurred while generating refresh token for user.', {}, user_db.id)
                await session.delete(user_db)
                await session.commit()
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                                 f"Verifying Your Email. Please Try Again Later.")
                return finalize_request(response)
            access_token = jwt.encode({
                'id': user_db.id,
                'expire_date': (datetime.now(cairo_tz) + timedelta(minutes=access_token_expire_time)).isoformat()
            }, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm='HS256')
            response_payload = {
                'access_token': access_token,
                'access_expires_in': int(timedelta(minutes=access_token_expire_time).total_seconds()),  # seconds until expiration
                'refresh_token': refresh_token,
                'refresh_expires_in': int(timedelta(days=refresh_token_expire_time).total_seconds()),  # seconds until expiration
            }
            response = RedirectResponse(
                    f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=Your Account Has Been Verified "
                    f"Successfully&token="
                    f"{response_payload.get('access_token')}___{response_payload.get('access_expires_in')}___"
                    f"{response_payload.get('refresh_token')}___{response_payload.get('refresh_expires_in')}")
            await log(request, 200, 'info', 'User Email Verified and Created Account Successfully.', {}, user_db.id)
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(request, 400, 'warning', 'Expired Token Provided for Email Verification.', {'error': str(e), 'token': token})
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Session Expired. Please "
                                              f"Try to SignUp Again.")
            await session.rollback()
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(request, 400, 'warning', 'Invalid Token Provided for Email Verification.', {'error': str(e), 'token': token})
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid Token. Please "
                                              f"Try to SignUp Again.")
            await session.rollback()
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while verifying user email.', {'error': str(e)})
            await session.rollback()
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                              f"Verifying Your Email. Please Try Again Later.")
            return finalize_request(response)

@auth.post('/get-google-stored-token')
@rate_limit
@is_not_logged_in
async def get_google_stored_token(request: Request):
    """
    This route is used to get stored google access token from the session.
    It is used to check if the user is already logged in.
    """
    google_details_token = (await request.json()).get('google_details_token')
    oauth_state = request.headers.get('OAuth-State')
    if not oauth_state:
        await log(request, 400, 'warning', 'No OAuth State Provided in the Request Headers.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'MisMatched OAuth State. Please try again.'
        }, 400)
        return finalize_request(response)
    if not google_details_token:
        await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'You Must Authorize Google Account to Proceed.'
        }, 401)
        return finalize_request(response)
    if not is_sanitized(google_details_token) or not is_sanitized(oauth_state):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body or Headers.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            state_token = (await session.execute(Select(Token).where(Token.token == oauth_state, Token.expire_at >
                                                                     datetime.now(cairo_tz)))).scalar_one_or_none()
            if not state_token or not state_token.details:
                await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You Must Authorize Google Account to Proceed.'
                }, 401)
                return finalize_request(response)
            for key, value in state_token.details.get('session').items():
                request.session[key] = value
            for key, value in state_token.details.get('cookies').items():
                request.cookies[key] = value
            token = (await session.execute(Select(Token).where(Token.token == google_details_token,
                                                            Token.expire_at > datetime.now(cairo_tz)))).scalar_one_or_none()
            if not token or not token.details:
                await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You Must Authorize Google Account to Proceed.'
                }, 401)
                return finalize_request(response)
            google_details = jwt.decode(token.details, os.environ.get('GOOGLE_TOKEN_SECRET_KEY'), algorithms=['HS256'])
            if not google_details or not google_details.get('google_user_details'):
                await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You Must Authorize Google Account to Proceed.'
                }, 401)
                return finalize_request(response)
            google_details = google_details.get('google_user_details')
            try:
                # Extract the new access token
                async with AsyncOAuth2Client(
                    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                ) as client:
                    new_token = await client.refresh_token(
                        url='https://oauth2.googleapis.com/token',
                        refresh_token=decrypt_data(google_details.get('google_refresh_token'))
                    )
                access_token = new_token['access_token']
            except Exception as e:
                await log(request, 500, 'error', 'An Error Occurred while Retrieving Google Access Token.',
                          {'error': str(e)})
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': "An Error Occurred. Please try again later."
                }, 500)
                return finalize_request(response)
            response = JSONResponse({
                'status': 'success',
                'message': 'Google access token retrieved successfully',
                'data': {
                    'access_token': access_token,
                    'expires_in': new_token['expires_in'],  # seconds until expiration
                }
            })
            await session.commit()
            await log(request, 200, 'info', 'Google Access Token Retrieved Successfully.', {'google_id': google_details.get('google_id'), 'google_name': google_details.get('google_name'), 'google_email': google_details.get('google_email')})
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(request, 401, 'warning', 'Expired OAuth State Provided in the Request Headers.', {'error': str(e), 'oauth_state': oauth_state})
            response = JSONResponse({
                'status': 'error',
                'message': 'Session Expired. Please try again.'
            }, 401)
            await session.rollback()
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(request, 401, 'warning', 'Invalid OAuth State Provided in the Request Headers.', {'error': str(e), 'oauth_state': oauth_state})
            response = JSONResponse({
                'status': 'error',
                'message': 'MisMatched OAuth State. Please try again.'
            }, 401)
            await session.rollback()
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while getting google stored token.', {'error': str(e)})
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred. Please try again.'
            }, 500)
            return finalize_request(response)

@auth.get('/get-google-access-token')
@rate_limit
@is_logged_in
async def get_google_access_token(request: Request):
    """
    This route is used to get the Google access token for the user.
    It is used to access Google Drive and other Google services.
    """
    current_user = request.state.current_user
    try:
        async with AsyncOAuth2Client(
                client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        ) as client:
            new_token = await client.refresh_token(
                url='https://oauth2.googleapis.com/token',
                refresh_token=decrypt_data(current_user.google_refresh_token)
            )
        access_token = new_token['access_token']
        async with async_session() as session:
            if 'refresh_token' in new_token:
                current_user.google_refresh_token = encrypt_data(new_token['refresh_token'])
                await session.commit()
            response = JSONResponse(
                {
                    'status': 'success',
                    'message': 'Google access token retrieved successfully',
                    'data': {
                        'access_token': access_token,
                        'expires_in': new_token['expires_in'],  # seconds until expiration
                    }
                }, 200
            )
            await log(request, 200, 'info', 'Google Access Token Retrieved Successfully.', {'google_id': current_user.google_id,
                                                                          'google_name': current_user.google_name,
                                                                          'google_email': current_user.google_email},
                current_user.id)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Google Access Token.', {'error': str(
            e)}, current_user.id)
        response = JSONResponse(
            {
                'status': 'error',
                'message': "An Error Occurred. Please try again later."
            }, 500
        )
        return finalize_request(response)

@app.get('/login-with-google')
@rate_limit
@is_not_logged_in
async def login_with_google(request: Request):
    try:
        redirect_response_url = 'https://' + request.url.hostname + '/google-authentication-redirect'
        google_client = oauth.create_client('google')
        state = await generate_unique_token(40)
        nonce = await generate_unique_token(40)
        state_token = Token(
            token=state,
            details={
                'nonce': nonce,
            },
            is_valid=True,
            expire_at=datetime.now(cairo_tz) + timedelta(days=stored_state_expire_time),
            type=2  # 2 for Google OAuth state token
        )
        async with async_session() as session:
            session.add(state_token)
            await session.commit()
        await log(request, 200, 'info', 'Redirecting user to Google for authentication.', {'redirect_response_url': redirect_response_url})
        return await google_client.authorize_redirect(request, redirect_response_url, state=state, nonce=nonce)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while redirecting to Google for authentication.', {'error': str(e)})
        response = JSONResponse({
            'status': 'error',
            'message': "An error occurred. Please try again."
        }, 500)
        return finalize_request(response)

@app.get('/google-authentication-redirect')
@rate_limit
@is_not_logged_in
async def google_authentication_redirect_response(request: Request):
    try:
        requested_scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            # 'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            # 'https://www.googleapis.com/auth/drive.metadata'
        ]
        details = {'cookies': {k: v for k, v in request.cookies.items()},
                   'session': {k: v for k, v in request.session.items()}}
        oauth_state = request.query_params.get('state')
        async with async_session() as session:
            await session.begin()
            try:
                state_token = (await session.execute(Select(Token).where(Token.token == oauth_state, Token.expire_at >
                                                                         datetime.now(cairo_tz)))).scalar_one_or_none()
                if not state_token:
                    await log(request, 401, 'warning', 'UnAuthorized User Tried to Authenticate with Google.', {})
                    response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=You Must Authorize Google Account to Proceed.")
                    return finalize_request(response)
                details['nonce'] = state_token.details.get('nonce')
                state_token.details = details
                token = await oauth.google.authorize_access_token(request, nonce=state_token.details.get('nonce'))
                granted_scopes = token.get('scope')
                un_granted_scopes = [scope for scope in requested_scopes if scope not in granted_scopes]
                if len(un_granted_scopes) > 0:
                    await log(request, 403, 'warning', 'Google did not grant the requested scopes.',{'un_granted_scopes': un_granted_scopes, 'granted_scopes': granted_scopes})
                    await session.rollback()
                    un_granted_scopes_short = ', '.join(scope.replace('https://www.googleapis.com/auth/','') for scope in (
                            un_granted_scopes))
                    response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Google did not grant the "
                                    f"following scopes: {un_granted_scopes_short}")
                    return finalize_request(response)
                user = token['userinfo']
                google_user_details = {
                    'google_id': user.get('sub'),
                    'google_name': user.get('name'),
                    'google_email': user.get('email'),
                    'google_avatar': user.get('picture'),
                    'google_refresh_token': encrypt_data(token.get('refresh_token'))
                }
                user = (await session.execute(Select(User).where(User.google_id == google_user_details.get(
                    'google_id')))).scalar_one_or_none()
                if user:
                    user.ips.append(request.client.host)  if request.client.host not in user.ips else None
                    if len(user.ips) > 3:
                        await log(request, 403, 'warning', 'User Tried To Associate More Than 3 IPs to His Account.', {'ips': user.ips},
                            user.id)
                        await session.rollback()
                        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=You "
                                                    f"Can\'t Associate More than 3 "
                                     f"Devices with Your Account. Please logout from one of your devices and try again.")
                        return finalize_request(response)
                    user.google_refresh_token = google_user_details.get('google_refresh_token')
                    user.google_name = google_user_details.get('google_name')
                    user.google_avatar = google_user_details.get('google_avatar')
                    token = jwt.encode({
                        'id': user.id,
                        'expire_date': (datetime.now(cairo_tz) + timedelta(minutes=access_token_expire_time)).isoformat()
                    }, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm='HS256')
                    refresh_token = await generate_refresh_token(user.id)
                    if not refresh_token:
                        await log(request, 500, 'error', 'An error occurred while generating refresh token for user.', {}, user.id)
                        await session.rollback()
                        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                                     f"Logging In. Please Try Again Later.")
                        return finalize_request(response)
                    response_payload = {
                        'access_token': token,
                        'access_expires_in': int(timedelta(minutes=access_token_expire_time).total_seconds()),  # seconds until expiration
                        'refresh_token': refresh_token,
                        'refresh_expires_in': int(timedelta(days=refresh_token_expire_time).total_seconds()),  # seconds until expiration
                    }
                    response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=Successfully "
                                         f"logged&state={oauth_state}&token={response_payload.get('access_token')}___"
                                         f"{response_payload.get('access_expires_in')}___"
                                         f"{response_payload.get('refresh_token')}___{response_payload.get('refresh_expires_in')}")
                    await session.commit()
                    await log(request, 200, 'info', 'User logged in successfully using Google.', {'google_id': user.google_id}, user.id)
                    return finalize_request(response)
                new_safe_token = await generate_unique_token(40)
                new_safe_token_db = Token(
                    token=new_safe_token,
                    details=jwt.encode({
                        'google_user_details': google_user_details,
                        'expire_date': (datetime.now(cairo_tz) + timedelta(minutes=google_token_expire_time)).isoformat()
                    }, os.environ.get('GOOGLE_TOKEN_SECRET_KEY'), algorithm='HS256'),
                    is_valid=True,
                    expire_at=datetime.now(cairo_tz) + timedelta(minutes=google_token_expire_time),
                    type=0  # 0 for Google login token
                )
                session.add(new_safe_token_db)
                await session.commit()
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login_success?state={oauth_state}&token={new_safe_token}___{int(timedelta(minutes=google_token_expire_time).total_seconds())}")
                await log(request, 200, 'info', 'User Authenticated Google Successfully.', {'google_id': google_user_details.get('google_id')})
                return finalize_request(response)
            except Exception as e:
                await log(request, 500, 'error', 'An Error Occurred while Authenticating with Google.', {'error': str(e)})
                await session.rollback()
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                                  f"Logging In. Please Try Again Later.")
                return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Authenticating with Google.', {'error': str(e)})
        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=An Error Occurred While "
                                          f"Logging In. Please Try Again Later.")
        return finalize_request(response)

# User routes
@user_prefix.get('/get-user-data')
@rate_limit
@is_logged_in
async def get_user_data(request: Request):
    current_user = request.state.current_user
    await log(request, 200, 'info', 'User Data Retrieved Successfully.', {}, current_user.id)
    response = JSONResponse({
        'status': 'success',
        'message': 'User data retrieved successfully',
        'data': current_user.to_dict()
    }, 200)
    return finalize_request(response)

@user_prefix.get('/get-user-permissions')
@rate_limit
@is_logged_in
async def get_user_permissions(request: Request):
    """
    This route is used to get the permissions of the current user.
    It will return the permissions based on the user's role.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (await session.execute(Select(User).where(User.id == current_user.id).options(selectinload(
                User.role).selectinload(Role.exact_roles)))).scalar_one_or_none()
            if not user or not user.role:
                await log(request, 404, 'warning', 'User Not Found or User Role Not Assigned.', {'user_id': current_user.id})
                response = JSONResponse({
                    'status': 'error',
                    'message': 'User not found or user role not assigned'
                }, 404)
                return finalize_request(response)
            permissions = user.role.exact_roles if user.role else []
            await log(request, 200, 'info', 'User Permissions Retrieved Successfully.', {}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'User permissions retrieved successfully',
                'data': [permission.name for permission in permissions]
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while getting user permissions.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving user permissions'
        }, 500)
        return finalize_request(response)

@user_prefix.post('/user-has-permissions')
@rate_limit
@is_logged_in
async def user_has_permissions(request: Request):
    """
    This route is used to check if user has some permissions.
    It will return boolean based on the user's role.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (await session.execute(Select(User).where(User.id == current_user.id).options(selectinload(
                User.role).selectinload(Role.exact_roles)))).scalar_one_or_none()
            if not user or not user.role:
                await log(request, 404, 'warning', 'User Not Found or User Role Not Assigned.', {'user_id': current_user.id})
                response = JSONResponse({
                    'status': 'error',
                    'message': 'User not found or user role not assigned'
                }, 404)
                return finalize_request(response)
            permissions = user.role.exact_roles if user.role else []
            data = await request.json()
            if not is_sanitized(data):
                await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Invalid data provided'
                }, 400)
                return finalize_request(response)
            required_permissions = data.get('permissions', [])
            is_and = data.get('is_and', True)
            if not required_permissions:
                await log(request, 400, 'warning', 'No Permissions Provided for Checking.', {}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'No permissions provided'
                }, 400)
                return finalize_request(response)
            if is_and:
                has_permissions = all(permission in [p.name for p in permissions] for permission in required_permissions)
            else:
                has_permissions = any(permission in [p.name for p in permissions] for permission in required_permissions)
            if not has_permissions:
                await log(request, 403, 'warning', 'User Does Not Have Required Permissions.', {}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'User does not have the required permissions'
                }, 403)
                return finalize_request(response)
            await log(request, 200, 'info', 'User has Required Permissions.', {}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'User has the required permissions',
                'data': has_permissions
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while checking user permissions.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while checking user permissions'
        }, 500)
        return finalize_request(response)

@user_prefix.get('/change-google-account')
@rate_limit
@is_logged_in
async def change_google_account(request: Request):
    """
    This route is used to change the Google account associated with the user.
    :param request:
    :return:
    """
    # To be Done in V2
    response = JSONResponse({
        'status': 'error',
        'message': 'This feature is not available yet. Coming Soon!'
    }, 501)
    return finalize_request(response)

@user_prefix.patch('/update-user-data')
@rate_limit
@is_logged_in
async def update_user_data(request: Request):
    """
    This route is used to update the user data.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    avatar = current_user.details.get('avatar', current_user.google_avatar)
    existing_avatar_uploaded = current_user.details.get('avatar', None)
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating User Data.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', current_user.name).strip()
    url = data.get('url', avatar).strip()
    if not name or name == '':
        await log(request, 400, 'warning', 'No Name Provided for Updating User Data.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Name cannot be empty'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            user_existing = (await session.execute(Select(User).where(func.lower(User.name) == name.lower()))).scalar_one_or_none()
            if user_existing and user_existing.id != current_user.id:
                await log(request, 400, 'warning', 'User Tried to Update Name to Another Existing User Name.', {'name': name}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Name already exists'
                }, 400)
                return finalize_request(response)
            await session.refresh(current_user)
            if existing_avatar_uploaded:
                removed = await remove_file_from_drive(existing_avatar_uploaded, current_user.google_refresh_token, request)
                if not removed:
                    await log(request, 500, 'error', 'An Error Occurred While Removing Old Avatar from Google Drive.', {'old_avatar': existing_avatar_uploaded}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'An Error Occurred While Updating Your Avatar. Please Try Again Later.'
                    }, 500)
                    return finalize_request(response)
            current_user.name = name
            current_user.details['avatar'] = url
            await session.commit()
            await log(request, 200, 'info', 'User Data Updated Successfully.', {'updated_data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'User data updated successfully',
                'data': current_user.to_dict()
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while updating user data.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating user data'
            }, 500)
            return finalize_request(response)

@user_prefix.patch('/update-user-academic-data')
@rate_limit
@is_logged_in
async def update_user_academic_data(request: Request):
    """
    This route is used to update the user academic data.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    if current_user.faculty_id is not None or current_user.department_id is not None or current_user.year_id is not None or \
            current_user.type is not None and current_user.type != '':
        await log(request, 403, 'warning', 'User Tried to Update Academic Data Again.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'You have already set your academic data. You cannot change it again.'
        }, 403)
        return finalize_request(response)
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating User Academic Data.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    faculty_id = data.get('faculty_id', None)
    department_id = data.get('department_id', None)
    year_id = data.get('year_id', None)
    study_type = data.get('study_type', '').strip()
    if not faculty_id or faculty_id == '' or not department_id or department_id == '' or not year_id or year_id == '' or not study_type or study_type == '':
        await log(request, 400, 'warning', 'Incomplete Data Provided for Updating User Academic Data.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Faculty, Department, Year and Study Type are required'
        }, 400)
        return finalize_request(response)
    if study_type not in ['Mainstream', 'Credit']:
        await log(request, 400, 'warning', 'Invalid Study Type Provided for Updating User Academic Data.', {'study_type': study_type}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Study Type. It should be either \'Mainstream\' or \'Credit\''
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Updating User Academic Data.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return finalize_request(response)
            department = (await session.execute(Select(Department).where(Department.id == department_id))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Updating User Academic Data.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(request, 400, 'warning', 'Department Does Not Belong to the Given Faculty for Updating User Academic Data.', {'faculty_id': faculty_id, 'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department does not belong to the given faculty'
                }, 400)
                return finalize_request(response)
            year = (await session.execute(Select(Year).where(Year.id == year_id))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Updating User Academic Data.', {'year_id': year_id},
                          current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return finalize_request(response)
            await session.refresh(current_user)
            current_user.faculty = faculty
            current_user.department = department
            current_user.year = year
            current_user.type = study_type
            await session.commit()
            await log(request, 200, 'info', 'User Academic Data Updated Successfully.', {'updated_data': dict(data)},
                      current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'User academic data updated successfully',
                'data': current_user.to_dict()
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while updating user academic data.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating user academic data'
            }, 500)
            return finalize_request(response)

@user_prefix.get('/enrolled-courses')
@rate_limit
@is_logged_in
async def get_enrolled_courses(request: Request):
    """
    This route is used to get the courses the user is enrolled in.
    :param request:
    :return:
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            enrolled_courses = (await session.execute(Select(UserSubjectLink).where(UserSubjectLink.user_id == current_user.id).options(
                selectinload(UserSubjectLink.subject).selectinload(Subject.department),
                selectinload(UserSubjectLink.subject).selectinload(Subject.year),
                selectinload(UserSubjectLink.subject).selectinload(Subject.faculty)
            ).order_by(Subject.name))).scalars().all()
            courses = [course.user_to_dict() for course in enrolled_courses]
            await log(request, 200, 'info', 'User Enrolled Courses Retrieved Successfully.', {}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Enrolled courses retrieved successfully',
                'data': courses
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while getting enrolled courses.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving enrolled courses'
        }, 500)
        return finalize_request(response)

@user_prefix.get('/courses')
@rate_limit
@is_logged_in
async def get_available_courses(request: Request):
    """
    This route is used to get the courses available for the user to enroll in.
    :param request:
    :return:
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Params.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower()
        async with async_session() as session:
            query = Select(Subject).where(
                Subject.faculty_id == current_user.faculty_id,
                Subject.department_id == current_user.department_id,
                Subject.year_id == current_user.year_id)
            if query_search and query_search != '':
                query = query.where(or_(func.lower(Subject.name).startswith(query_search),
                                        func.lower(Subject.code).startswith(query_search)))
            available_courses = (await session.execute(query.options(
                selectinload(Subject.department),
                selectinload(Subject.year),
                selectinload(Subject.faculty)
            ).order_by(Subject.name))).scalars().all()
            courses = [course.user_to_dict() for course in available_courses]
            await log(request, 200, 'info', 'Available Courses for User Retrieved Successfully.', {}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Available courses retrieved successfully',
                'data': courses
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An error occurred while getting available courses.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving available courses'
        }, 500)
        return finalize_request(response)

@user_prefix.post('/register-course')
@rate_limit
@is_logged_in
async def register_course(request: Request):
    """
    This route is used to register the user to a course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Course Registration.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    course_id = data.get('course_id', None)
    if not course_id:
        await log(request, 400, 'warning', 'No Course ID Provided for Registration.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Course ID is required'
        }, 400)
        return finalize_request(response)
    if not is_int(course_id) or int(course_id) < 1:
        await log(request, 400, 'warning', 'Invalid Course ID Provided for Registration.', {'course_id': course_id}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Course ID provided'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (await session.execute(Select(Subject).where(Subject.id == course_id).options(
                selectinload(Subject.users),
                selectinload(Subject.department),
                selectinload(Subject.year),
                selectinload(Subject.faculty)
            ))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Course Not Found for Registration.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found'
                }, 404)
                return finalize_request(response)
            if subject.faculty_id != current_user.faculty_id or subject.department_id != current_user.department_id or subject.year_id != current_user.year_id:
                await log(request, 400, 'warning', 'User Tried to Register to a Course Not Belonging to His Academic Data.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You can only register to courses belonging to your academic data'
                }, 400)
                return finalize_request(response)
            if current_user in subject.users:
                await log(request, 400, 'warning', 'User Tried to Register to a Course He is Already Registered In.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are already registered in this course'
                }, 400)
                return finalize_request(response)
            subject.users.append(current_user)
            await session.commit()
            await log(request, 200, 'info', 'User Registered to Course Successfully.', {'course_id': course_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Registered to course successfully',
                'data': subject.user_to_dict()
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while registering to course.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while registering to course'
            }, 500)
            return finalize_request(response)

@user_prefix.post('/unregister-course')
@rate_limit
@is_logged_in
async def unregister_course(request: Request):
    """
    This route is used to unregister the user from a course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Course Registration.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    course_id = data.get('course_id', None)
    if not course_id:
        await log(request, 400, 'warning', 'No Course ID Provided for Registration.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Course ID is required'
        }, 400)
        return finalize_request(response)
    if not is_int(course_id) or int(course_id) < 1:
        await log(request, 400, 'warning', 'Invalid Course ID Provided for Registration.', {'course_id': course_id},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Course ID provided'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (await session.execute(Select(Subject).where(Subject.id == course_id).options(
                selectinload(Subject.users),
                selectinload(Subject.department),
                selectinload(Subject.year),
                selectinload(Subject.faculty)
            ))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Course Not Found for Unregistration.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found'
                }, 404)
                return finalize_request(response)
            if current_user not in subject.users:
                await log(request, 400, 'warning', 'User Tried to Unregister from a Course He is Not Registered In.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not registered in this course'
                }, 400)
                return finalize_request(response)
            subject.users.remove(current_user)
            await session.commit()
            await log(request, 200, 'info', 'User Unregistered from Course Successfully.', {'course_id': course_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Unregistered from course successfully',
                'data': subject.user_to_dict()
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An error occurred while unregistering from course.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while unregistering from course'
            }, 500)
            return finalize_request(response)

# Admin Routes
@admin_prefix.post('/faculties')
@rate_limit
@is_logged_in
@is_authorized(['Add Faculties'])
async def create_faculty(request: Request):
    """
    This route is used to create a new faculty.
    It will return the created faculty data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Faculty.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    if not name:
        await log(request, 400, 'warning', 'No Faculty Name Provided for Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Faculty name is required'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            existing_faculty = (await session.execute(Select(Faculty).where(func.lower(Faculty.name) ==
                                                                            name.lower()))).scalar_one_or_none()
            if existing_faculty:
                await log(request, 400, 'warning', 'Faculty Already Exists.', {'name': name}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty already exists'
                }, 400)
                return finalize_request(response)
            faculty = Faculty(name=name)
            session.add(faculty)
            await session.commit()
            await log(request, 201, 'info', 'Faculty Created Successfully.', {'name': name}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Faculty created successfully',
                'data': faculty.to_dict()
            }, 201)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Faculty.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating faculty'
            }, 500)
            return finalize_request(response)

@admin_prefix.patch('/faculties/{faculty_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Faculties'])
async def update_faculty(request: Request, faculty_id: int):
    """
    This route is used to update an existing faculty.
    It will return the updated faculty data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Faculty.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    if not name:
        await log(request, 400, 'warning', 'No Faculty Name Provided for Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Faculty name is required'
        }, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Update.', {'faculty_id': faculty_id, 'name': name},
                          current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return finalize_request(response)
            existing_faculty = (await session.execute(Select(Faculty).where(func.lower(Faculty.name) == name.lower(

            )))).scalar_one_or_none()
            if existing_faculty and existing_faculty.id != faculty_id:
                await log(request, 400, 'warning', 'Faculty Name Already Exists for Update.', {'name': name}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty with this Name already exists'
                }, 400)
                return finalize_request(response)
            faculty.name = name
            await session.commit()
            await log(request, 200, 'info', 'Faculty Updated Successfully.', {'faculty_id': faculty_id, 'name': name}, current_user.id)
            response =  JSONResponse({
                'status': 'success',
                'message': 'Faculty updated successfully',
                'data': faculty.to_dict()
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Faculty.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating faculty'
            }, 500)
            return finalize_request(response)

@admin_prefix.delete('/faculties/{faculty_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Faculties'])
async def delete_faculty(request: Request, faculty_id: int):
    """
    This route is used to delete an existing faculty.
    It will return a success message if the faculty is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id).options(
                selectinload(Faculty.users)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Deletion.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return finalize_request(response)
            if faculty.users and len(faculty.users) > 0:
                await log(request, 400, 'warning', 'Faculty Cannot Be Deleted Because It Has Users Associated with It.',
                          {'faculty_id': faculty_id, 'users_count': len(faculty.users)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty cannot be deleted because it has users associated with it'
                }, 400)
                return finalize_request(response)
            await session.delete(faculty)
            await session.commit()
            await log(request, 200, 'info', 'Faculty Deleted Successfully.', {'faculty_id': faculty_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Faculty deleted successfully'
            }, 200)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Faculty.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting faculty'
            }, 500)
            return finalize_request(response)

@admin_prefix.get('/faculties')
@rate_limit
@is_logged_in
@is_authorized(['View Faculties'])
async def get_faculties(request: Request):
    """
    This route is used to get all faculties.
    It will return a list of faculties.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip() if data else ''
        async with async_session() as session:
            faculties = (await session.execute(Select(Faculty).where(func.lower(Faculty.name).startswith(name.lower(

            ))).order_by(
                Faculty.name))).scalars().all()
            await log(request, 200, 'info', 'Faculties Retrieved Successfully.', {'faculties_count': len(faculties)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Faculties retrieved successfully',
                'data': [faculty.to_dict() for faculty in faculties]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Faculties.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving faculties'
        }, 500)
        return response

@admin_prefix.get('/faculties/{faculty_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Faculties'])
async def get_faculty(request: Request, faculty_id: int):
    """
    This route is used to get a single faculty by its ID.
    It will return the faculty data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found.', {'faculty_id': faculty_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Faculty Retrieved Successfully.', {'faculty_id': faculty_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Faculty retrieved successfully',
                'data': faculty.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Faculty.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving faculty'
        }, 500)
        return response

@admin_prefix.get('/search-faculties')
@rate_limit
@is_logged_in
@is_authorized(['View Faculties'])
async def search_faculties(request: Request):
    """
    This route is used to search faculties by name.
    It will return a list of faculties matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower() if data else ''
        async with async_session() as session:
            faculties = (await session.execute(Select(Faculty).where(func.lower(Faculty.name).startswith(query_search)).order_by(
                Faculty.name))).scalars().all()
            await log(request, 200, 'info', 'Faculties Search Completed Successfully.', {'query': query_search, 'faculties_count': len(faculties)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Faculties search completed successfully',
                'data': [faculty.min_to_dict() for faculty in faculties]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Faculties.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching faculties'
        }, 500)
        return response

@admin_prefix.post('/departments')
@rate_limit
@is_logged_in
@is_authorized(['Add Departments'])
async def create_department(request: Request):
    """
    This route is used to create a new department.
    It will return the created department data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Department.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    faculty_id = data.get('faculty_id')
    study_type = data.get('study_type', 'Mainstream').strip().title()  # Default to 'Mainstream' if not provided
    code = data.get('code', '').strip().upper() # Required Code Field
    if not name or not faculty_id or not study_type or not code:
        await log(request, 400, 'warning', 'No Department Name or Faculty ID or Study Type or Code Provided for Department Creation.', {},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Department name, Study Type, Code, faculty and code are required'
        }, 400)
        return response
    if study_type not in ['Mainstream', 'Credit', 'Both']:
        await log(request, 400, 'warning', 'Invalid Study Type Provided for Department Creation.', {'study_type': study_type}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid study type provided. Must be one of the options.'
        }, 400)
        return response
    permissions = json.loads((await get_user_permissions(request)).body)
    if permissions.get('status') != 'success':
        await log(request, 403, 'warning', 'User Does Not Have Required Permissions for Department Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': permissions.get('message')
        }, 403)
        return response
    can_access_all_faculties = False
    if permissions.get('data') and 'Access All Faculties' in permissions.get('data'):
        can_access_all_faculties = True
    async with async_session() as session:
        await session.begin()
        try:
            if faculty_id != current_user.faculty_id and can_access_all_faculties != True:
                await log(request, 403, 'warning', 'User Does Not Have Access to Change the Faculty for Department '
                                                   'Creation.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You do not have access to select faculty rather than your own'
                }, 403)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Department Creation.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            if study_type != 'Both':
                existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                      faculty.id,
                                                                                      func.lower(Department.study_type)
                                                                                      == study_type.lower(),
                                                             func.lower(Department.name) ==
                                                                                  name.lower()))).scalar_one_or_none()
            else:
                existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                      faculty.id,
                                                             func.lower(Department.name) ==
                                                                                  name.lower()))).scalar_one_or_none()
            if existing_department:
                await log(request, 400, 'warning', 'Department Already Exists with this type for this Faculty.',
                          {'name': name, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department already exists with this type for this faculty'
                }, 400)
                return response
            if study_type != 'Both':
                existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                      faculty.id,
                                                                                      func.lower(Department.study_type)
                                                                                      == study_type.lower(),
                                                             func.lower(Department.code) ==
                                                                                  code.lower()))).scalar_one_or_none()
            else:
                existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                      faculty.id,
                                                             func.lower(Department.code) ==
                                                                                  code.lower()))).scalar_one_or_none()
            if existing_department:
                await log(request, 400, 'warning', 'Department Code Already Exists with this type for this Faculty.',
                          {'code': code, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department with this Code already exists with this type for this faculty'
                }, 400)
                return response
            if study_type != 'Both':
                department = Department(
                    name=name,
                    faculty=faculty,
                    study_type=study_type,
                    code=code.strip().upper()
                )
                session.add(department)
            else:
                department = Department(
                    name=name,
                    faculty=faculty,
                    study_type='Mainstream',
                    code=code.strip().upper()
                )
                session.add(department)
                department = Department(
                    name=name,
                    faculty=faculty,
                    study_type='Credit',
                    code=code.strip().upper()
                )
                session.add(department)
            await session.commit()
            await log(request, 201, 'info', 'Department Created Successfully.', {'name': name, 'faculty_id': faculty_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Department created successfully',
                'data': department.to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Department.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating department'
            }, 500)
            return response

@admin_prefix.patch('/departments/{department_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Departments'])
async def update_department(request: Request, department_id: int):
    """
    This route is used to update an existing department.
    It will return the updated department data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Department.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    faculty_id = data.get('faculty_id')
    study_type = data.get('study_type', 'Mainstream').strip().title()  # Default to 'Mainstream' if not provided
    code = data.get('code', '').strip().upper()  # Required Code Field
    if not name or not faculty_id or not study_type or not code:
        await log(request, 400, 'warning', 'No Department Name or Faculty ID or Study Type or Code Provided for Department Update.', {},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Department name, Study Type, Code, faculty and code are required'
        }, 400)
        return response
    if study_type not in ['Mainstream', 'Credit']:
        await log(request, 400, 'warning', 'Invalid Study Type Provided for Department Update.', {'study_type': study_type}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid study type provided. Must be either \'Mainstream\' or \'Credit\'.'
        }, 400)
        return response
    permissions = json.loads((await get_user_permissions(request)).body)
    if permissions.get('status') != 'success':
        await log(request, 403, 'warning', 'User Does Not Have Required Permissions for Department Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': permissions.get('message')
        }, 403)
        return response
    can_access_all_faculties = False
    if permissions.get('data') and 'Access All Faculties' in permissions.get('data'):
        can_access_all_faculties = True
    async with async_session() as session:
        await session.begin()
        try:
            if faculty_id != current_user.faculty_id and can_access_all_faculties != True:
                await log(request, 403, 'warning', 'User Does Not Have Access to Change the Faculty for Department '
                                                   'Update.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You do not have access to select faculty rather than your own'
                }, 403)
                return response
            department = (await session.execute(Select(Department).where(Department.id == department_id))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Update.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                  department.faculty_id,
                                                                                  func.lower(Department.study_type) ==
                                                                                  study_type.lower(),func.lower(
                Department.name) == name.lower()))).scalar_one_or_none()
            if existing_department and existing_department.id != department_id:
                await log(request, 400, 'warning', 'Department Name Already Exists with this Type for this Faculty.',
                          {'name': name,
                                                                                                    'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department with this Name already exists with this type for this faculty'
                }, 400)
                return response
            existing_department = (await session.execute(Select(Department).where(Department.faculty_id ==
                                                                                  department.faculty_id,
                                                                                  func.lower(Department.study_type) ==
                                                                                  study_type.lower(),
                                                                                  func.lower(Department.code) == code.lower()))).scalar_one_or_none()
            if existing_department and existing_department.id != department_id:
                await log(request, 400, 'warning', 'Department Code Already Exists with this Type for this Faculty.',
                          {'code': code, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department with this Code already exists with this type for this faculty'
                }, 400)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Department Update.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department.name = name
            department.faculty = faculty
            department.study_type = study_type
            department.code = code
            await session.commit()
            await log(request, 200, 'info', 'Department Updated Successfully.', {'department_id': department_id, 'name': name, 'faculty_id': faculty_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Department updated successfully',
                'data': department.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Department.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating department'
            }, 500)
            return response

@admin_prefix.delete('/departments/{department_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Departments'])
async def delete_department(request: Request, department_id: int):
    """
    This route is used to delete an existing department.
    It will return a success message if the department is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            department = (await session.execute(Select(Department).where(Department.id == department_id).options(
                selectinload(Department.users)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Deletion.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            if department.users and len(department.users) > 0:
                await log(request, 400, 'warning', 'Department Cannot Be Deleted Because It Has Users Associated with It.',
                          {'department_id': department_id, 'users_count': len(department.users)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department cannot be deleted because it has users associated with it'
                }, 400)
                return response
            await session.delete(department)
            await session.commit()
            await log(request, 200, 'info', 'Department Deleted Successfully.', {'department_id': department_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Department deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Department.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting department'
            }, 500)
            return response

@admin_prefix.get('/departments')
@rate_limit
@is_logged_in
@is_authorized(['View Departments'])
async def get_departments(request: Request):
    """
    This route is used to get all departments.
    It will return a list of departments.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip() if data else ''
        faculty_id = data.get('faculty_id') if data else None
        study_type = data.get('study_type', '').strip().title() if data else None  # Default to '' if not provided
        if study_type != '' and study_type not in ['Mainstream', 'Credit']:
            await log(request, 400, 'warning', 'Invalid Study Type Provided for Department Retrieval.', {'study_type': study_type}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid study type provided. Must be either \'Mainstream\' or \'Credit\'.'
            }, 400)
            return response
        async with async_session() as session:
            query = Select(Department).options(selectinload(Department.faculty))
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for Department Retrieval.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
                query = query.where(Department.faculty_id == faculty_id)
            if study_type != '':
                query = query.where(Department.study_type == study_type)
            query = query.where(func.lower(Department.name).startswith(name.lower()))
            departments = (await session.execute(query.order_by(Department.name))).scalars().all()
            await log(request, 200, 'info', 'Departments Retrieved Successfully.', {'departments_count': len(departments)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Departments retrieved successfully',
                'data': [department.to_dict() for department in departments]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Departments.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving departments'
        }, 500)
        return response

@admin_prefix.get('/departments/{department_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Departments'])
async def get_department(request: Request, department_id: int):
    """
    This route is used to get a specific department by its ID.
    It will return the department data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            department = (await session.execute(Select(Department).where(Department.id == department_id).options(
                selectinload(Department.faculty),
            selectinload(Department.users),
            selectinload(Department.subjects),
            selectinload(Department.tasks),
            selectinload(Department.announcements),
            selectinload(Department.events)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Retrieval.', {'department_id': department_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            data = {
                'users': len(department.users),
                'subjects': len(department.subjects),
                'tasks': len([task for task in department.tasks if task.type.lower() != 'exam']),
                'exams': len([task for task in department.tasks if task.type.lower() == 'exam']),
                'announcements': len(department.announcements),
                'events': len(department.events),
            }
            await log(request, 200, 'info', 'Department Retrieved Successfully.', {'department_id': department_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Department retrieved successfully',
                'data': {
                    'department': department.to_dict(),
                    'summary': data
                }
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Department.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving department'
        }, 500)
        return response

@admin_prefix.get('/search-departments')
@rate_limit
@is_logged_in
@is_authorized(['View Departments'])
async def search_departments(request: Request):
    """
    This route is used to search departments by name.
    It will return a list of departments matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower() if data else ''
        faculty_id = data.get('faculty_id', None) if data else None
        study_type = data.get('study_type', '').strip().title() if data else None
        if study_type != '' and study_type not in ['Mainstream', 'Credit']:
            await log(request, 400, 'warning', 'Invalid Study Type Provided for Department Search.', {'study_type': study_type}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid study type provided. Must be either \'Mainstream\' or \'Credit\'.'
            }, 400)
            return response
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1):
            await log(request, 400, 'warning', 'Invalid Faculty ID Provided for Department Search.', {'faculty_id': faculty_id}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid Faculty ID provided'
            }, 400)
            return finalize_request(response)
        faculty = None
        async with async_session() as session:
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for Department Search.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
            query = Select(Department)
            if faculty:
                query = query.where(Department.faculty_id == faculty.id)
            if study_type != '':
                query = query.where(Department.study_type == study_type)
            if query_search != '':
                query = query.where(or_(
                    func.lower(Department.name).startswith(query_search),
                    func.lower(Department.code).startswith(query_search)
                ))
            departments = (await session.execute(query.order_by(Department.name))).scalars().all()
            await log(request, 200, 'info', 'Departments Search Completed Successfully.', {'query': query_search, 'departments_count': len(departments)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Departments search completed successfully',
                'data': [department.min_to_dict() for department in departments]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Departments.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching departments'
        }, 500)
        return response

@admin_prefix.post('/years')
@rate_limit
@is_logged_in
@is_authorized(['Add Years'])
async def create_year(request: Request):
    """
    This route is used to create a new academic year.
    It will return the created year data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Year.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    year = data.get('year').strip()
    if not year:
        await log(request, 400, 'warning', 'No Year Provided for Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Year is required'
        }, 400)
        return response
    if '-' in year or not is_int(year) or len(year) != 4:
        await log(request, 400, 'warning', 'Invalid Year Provided for Creation.', {'year': year}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Year must be a positive 4-digit number'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            existing_year = (await session.execute(Select(Year).where(Year.year == int(year)))).scalar_one_or_none()
            if existing_year:
                await log(request, 400, 'warning', 'Year Already Exists.', {'year': year}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year already exists'
                }, 400)
                return response
            year_added = Year(
                year=int(year)
            )
            session.add(year_added)
            await session.commit()
            await log(request, 201, 'info', 'Year Created Successfully.', {'year': year}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Year created successfully',
                'data': year_added.to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Year.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating year'
            }, 500)
            return response

@admin_prefix.patch('/years/{year_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Years'])
async def update_year(request: Request, year_id: int):
    """
    This route is used to update an existing academic year.
    It will return the updated year data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Year.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    year = data.get('year').strip()
    if not year:
        await log(request, 400, 'warning', 'No Year Provided for Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Year is required'
        }, 400)
        return response
    if '-' in year or not is_int(year) or len(year) != 4:
        await log(request, 400, 'warning', 'Invalid Year Provided for Update.', {'year': year}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Year must be a positive 4-digit number'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            year_obj = (await session.execute(Select(Year).where(Year.id == year_id))).scalar_one_or_none()
            if not year_obj:
                await log(request, 404, 'warning', 'Year Not Found for Update.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            existing_year = (await session.execute(Select(Year).where(Year.year == int(year)))).scalar_one_or_none()
            if existing_year and existing_year.id != year_id:
                await log(request, 400, 'warning', 'Year Already Exists for Update.', {'year': year}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year already exists'
                }, 400)
                return response
            year_obj.year = int(year)
            await session.commit()
            await log(request, 200, 'info', 'Year Updated Successfully.', {'year_id': year_id, 'year': year}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Year updated successfully',
                'data': year_obj.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Year.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating year'
            }, 500)
            return response

@admin_prefix.delete('/years/{year_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Years'])
async def delete_year(request: Request, year_id: int):
    """
    This route is used to delete an existing academic year.
    It will return a success message if the year is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            year = (await session.execute(Select(Year).where(Year.id == year_id).options(selectinload(Year.users)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Deletion.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            if year.users and len(year.users) > 0:
                await log(request, 400, 'warning', 'Year Cannot Be Deleted Because It Has Users Associated with It.',
                          {'year_id': year_id, 'users_count': len(year.users)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year cannot be deleted because it has users associated with it'
                }, 400)
                return response
            await session.delete(year)
            await session.commit()
            await log(request, 200, 'info', 'Year Deleted Successfully.', {'year_id': year_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Year deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Year.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting year'
            }, 500)
            return response

@admin_prefix.get('/years')
@rate_limit
@is_logged_in
@is_authorized(['View Years'])
async def get_years(request: Request):
    """
    This route is used to get all academic years.
    It will return a list of years.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        year = data.get('year', '').strip() if data else ''
        if year and (not is_int(year) or len(year) != 4):
            await log(request, 400, 'warning', 'Invalid Year Provided for Retrieval.', {'year': year}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Year must be a positive 4-digit number'
            }, 400)
            return response
        async with async_session() as session:
            query = Select(Year)
            if year:
                query = query.where(Year.year == int(year))
            years = (await session.execute(query.order_by(Year.year))).scalars().all()
            await log(request, 200, 'info', 'Years Retrieved Successfully.', {'years_count': len(years)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Years retrieved successfully',
                'data': [year.to_dict() for year in years]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Years.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving years'
        }, 500)
        return response

@admin_prefix.get('/years/{year_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Years'])
async def get_year(request: Request, year_id: int):
    """
    This route is used to get a specific academic year by its ID.
    It will return the year data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            year = (await session.execute(Select(Year).where(Year.id == year_id))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Retrieval.', {'year_id': year_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Year Retrieved Successfully.', {'year_id': year_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Year retrieved successfully',
                'data': year.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Year.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving year'
        }, 500)
        return response

@admin_prefix.get('/search-years')
@rate_limit
@is_logged_in
@is_authorized(['View Years'])
async def search_years(request: Request):
    """
    This route is used to search academic years by year.
    It will return a list of years matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip() if data else ''
        if query_search and (not is_int(query_search) or len(query_search) != 4):
            await log(request, 400, 'warning', 'Invalid Year Provided for Search.', {'query': query_search}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Year must be a positive 4-digit number'
            }, 400)
            return response
        async with async_session() as session:
            years = (await session.execute(Select(Year).where(Year.year == int(query_search)).order_by(
                Year.year))).scalars().all()
            await log(request, 200, 'info', 'Years Search Completed Successfully.', {'query': query_search, 'years_count': len(years)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Years search completed successfully',
                'data': [year.min_to_dict() for year in years]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Years.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching years'
        }, 500)
        return response

@admin_prefix.get('/get-users-data')
@rate_limit
@is_logged_in
@is_authorized(['View Users'])
async def get_users_data(request: Request):
    """
    This route is used to get users data.
    It will return a list of data.
    """
    try:
        current_user = request.state.current_user
        async with (async_session() as session):
            two_hours_ago = datetime.now(cairo_tz) - timedelta(hours=2)
            this_month_start = datetime.now(cairo_tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            users_count = await session.scalar(Select(func.count(User.id)))
            users_this_month = await session.scalar(Select(func.count(User.id)).where(
                User.created_at >= this_month_start))
            percentage_increase = (users_this_month / users_count) * 100 if users_count > 0 else 0
            active_now = await session.scalar(Select(func.count(func.distinct(RequestLimit.ip))).where(
                RequestLimit.created_at >= two_hours_ago))
            subc = Select(RequestLimit.ip, func.max(RequestLimit.created_at).label('max_created_at')).where(
                RequestLimit.created_at >= two_hours_ago
            ).group_by(RequestLimit.ip).subquery()
            last_five_ips_active = (await session.execute(Select(subc.c.ip).order_by(
                subc.c.max_created_at.desc()).limit(5))).scalars().all()
            last_five_users_active = []
            for ip in last_five_ips_active:
                user = (await session.execute(Select(User.details,User.google_avatar).where(User.ips.contains(
                    ip)))).scalar_one_or_none()
                if user:
                    avatar = user.get('details',{}).get('avatar', None) if user.get('details',{}).get('avatar',
                                                                                                      None) else user.get('google_avatar',{})
                    last_five_users_active.append(avatar)
            pending_users_count = await session.scalar(Select(func.count(PendingUser.id)))
            await log(request, 200, 'info', 'Users Data Retrieved Successfully.', {}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Users data retrieved successfully',
                'data': {
                    'users_count': users_count,
                    'users_this_month': users_this_month,
                    'percentage_increase': math.ceil(percentage_increase),
                    'active_now': active_now,
                    'pending_users_count': pending_users_count,
                    'last_five_users_active': last_five_users_active
                }
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Users Data.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving users data'
        }, 500)
        return response

@admin_prefix.get('/users')
@rate_limit
@is_logged_in
@is_authorized(['View Users'])
async def get_users(request: Request):
    """
    This route is used to get all users.
    It will return a list of users.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        if not data:
            data = {}
        search_query = data.get('query', '').strip().lower()
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        is_active = bool(data.get('is_active', True))
        page = int(data.get('page', 1)) if data.get('page', '1').isdigit() else 1
        limit = int(data.get('limit', 50)) if data.get('limit', '50').isdigit() else 50
        async with async_session() as session:
            query = Select(User).options(selectinload(User.role), selectinload(User.faculty),
                                         selectinload(User.department), selectinload(User.year), selectinload(
                    User.pending_user), selectinload(User.notifications))
            faculty = None
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for User Retrieval.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
                query = query.where(User.faculty_id == faculty_id)
            if department_id:
                department = (await session.execute(Select(Department).where(Department.id == department_id))).scalar_one_or_none()
                if not department:
                    await log(request, 404, 'warning', 'Department Not Found for User Retrieval.', {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department not found'
                    }, 404)
                    return response
                if not faculty:
                    await log(request, 400, 'warning', 'Faculty ID Must Be Provided with Department ID for User Retrieval.',
                                {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Can\'t choose department without faculty'
                    }, 400)
                    return response
                if department.faculty_id != int(faculty_id):
                    await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for User Retrieval.',
                                {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department does not belong to the specified faculty'
                    }, 400)
                    return response
                query = query.where(User.department_id == department_id)
            if year_id:
                year = (await session.execute(Select(Year).where(Year.id == year_id))).scalar_one_or_none()
                if not year:
                    await log(request, 404, 'warning', 'Year Not Found for User Retrieval.', {'year_id': year_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Year not found'
                    }, 404)
                    return response
                query = query.where(User.year_id == year_id)
            query = query.where(User.status == is_active)
            query.where(or_(
                func.lower(User.name).startswith(search_query),
                func.lower(User.email).startswith(search_query),
                func.lower(User.phone).startswith(search_query),
            ))
            users = (await session.execute(query.order_by(User.name).offset((page-1) * limit).limit(limit))).scalars().all()
            await log(request, 200, 'info', 'Users Retrieved Successfully.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Users retrieved successfully',
                'data': [user.to_dict() for user in users]
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Users.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving users'
        }, 500)
        return response

@admin_prefix.patch('/users/update')
@rate_limit
@is_logged_in
@is_authorized(['Manage Users'])
async def update_users(request: Request):
    """
    This route is used to update multiple users.
    It will return a success message if the users are updated successfully.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Users Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'No data provided'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    if isinstance(data, dict):
        data_to_update = data.get('data_to_update', []) # each contains {'id': user_id, 'approved': True/False, 'role_id':
        # role_id (optional)}
    elif isinstance(data, list):
        data_to_update = data
    else:
        await log(request, 400, 'warning', 'Invalid Data Format Provided for Users Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data format provided'
        }, 400)
        return response
    if not data_to_update or not isinstance(data_to_update, list):
        await log(request, 400, 'warning', 'No Users Data Provided for Users Update.', {'data': data}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty request was sent'
        }, 400)
        return response
    for record in data_to_update:
        if not record.get('id') or not is_int(record.get('id')) or 'approved' not in record or not record.get(
                'approved', True) in [True, False] or (record.get('role_id','1') and not is_int(
            record.get('role_id', '1'))) or (record.get('role_id','1') and int(record.get('role_id', '1')) < 1):
            await log(request, 400, 'warning', 'Invalid User Data Provided for Users Update.', {'record': record}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid request was sent'
            }, 400)
            return response
    async with async_session() as session:
        await session.begin()
        try:
            for record in data_to_update:
                user = (await session.execute(Select(User).where(User.id == int(record.get('id'))).options(selectinload(
                    User.role).selectinload(Role.exact_roles)))).scalar_one_or_none()
                if not user:
                    await log(request, 404, 'warning', 'User Not Found for Users Update.', {'user_id': record.get('id')}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': f"Invalid request was sent. Users sent contains not found users"
                    }, 404)
                    return response
                if user.id == current_user.id:
                    await log(request, 400, 'warning', 'User Cannot Update Their Own Account via This Endpoint.', {'user_id': user.id}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'You cannot update your own account using this method'
                    }, 400)
                    return response
                user_permissions = json.loads((await get_user_permissions(request)).body)
                permissions = user_permissions.get('data', [])
                updated_user_permissions = [permission.name for permission in user.role.exact_roles] if user.role and user.role.exact_roles else []
                missing_permissions = [permission for permission in updated_user_permissions if permission not in permissions]
                if missing_permissions and len(missing_permissions) > 0:
                    await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to Update the Specified User.',
                              {'user_id': user.id, 'missing_permissions': missing_permissions}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': f"You Cannot update a user having permissions you don\'t have."
                    }, 403)
                    return response
                if not bool(record.get('approved')) and user.status:
                    await log(request, 400, 'warning', 'Cannot Un Approve an Already Approved User.', {'user_id':
                                                                                                          user.id}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Cannot un approve an already approved user'
                    }, 400)
                    return response
                if not bool(record.get('approved')):
                    await session.delete(user)
                    # Send email to user notifying them of account deletion (V2)
                    continue
                user.status = True
                pending_user = (await session.execute(Select(PendingUser).where(PendingUser.user_id == user.id))).scalar_one_or_none()
                if pending_user:
                    await session.delete(pending_user)
                if record.get('role_id', None):
                    role = (await session.execute(Select(Role).where(Role.id == int(record.get(
                        'role_id'))).options(selectinload(Role.exact_roles)))).scalar_one_or_none()
                    if not role:
                        await log(request, 404, 'warning', 'Role Not Found for User Update.', {'role_id': record.get('role_id')}, current_user.id)
                        await session.rollback()
                        response = JSONResponse({
                            'status': 'error',
                            'message': f"Invalid request was sent. Roles sent contained roles not found"
                        }, 404)
                        return response
                    if 'Assign Roles' not in permissions:
                        await log(request, 403, 'warning', 'User Does Not Have Required Permissions to Assign Roles for User Update.', {}, current_user.id)
                        await session.rollback()
                        response = JSONResponse({
                            'status': 'error',
                            'message': 'You do not have permissions to assign roles'
                        }, 403)
                        return response
                    missing_permissions = [permission.name for permission in role.exact_roles if permission.name not in
                                                                                          permissions]
                    if missing_permissions and len(missing_permissions) > 0:
                        await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to Assign the Specified Role for User Update.',
                                  {'role_id': record.get('role_id'), 'missing_permissions': missing_permissions}, current_user.id)
                        await session.rollback()
                        response = JSONResponse({
                            'status': 'error',
                            'message': f"You Cannot assign a role having permissions you don\'t have."
                        }, 403)
                        return response
                    user.role = role
            await session.commit()
            await log(request, 200, 'info', 'Users Updated Successfully.', {'users_updated_count': len(data_to_update)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Users updated successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Users.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating users'
            }, 500)
            return response

@admin_prefix.get('/users/{user_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Users'])
async def get_user(request: Request, user_id: int):
    """
    This route is used to get a specific user by their ID.
    It will return the user data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (await session.execute(Select(User).where(User.id == user_id).options(
                selectinload(User.role).selectinload(Role.exact_roles),
                selectinload(User.faculty),
                selectinload(User.department),
                selectinload(User.year),
                selectinload(User.pending_user),
                selectinload(User.notifications),
            ))).scalar_one_or_none()
            if not user:
                await log(request, 404, 'warning', 'User Not Found for Retrieval.', {'user_id': user_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'User not found'
                }, 404)
                return response
            permissions = json.loads((await get_user_permissions(request)).body).get('data', [])
            user_permissions = [permission.name for permission in user.role.exact_roles] if user.role and user.role.exact_roles else []
            missing_permissions = [permission for permission in user_permissions if permission not in permissions]
            if missing_permissions and len(missing_permissions) > 0:
                await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to View the Specified User.',
                          {'user_id': user.id, 'missing_permissions': missing_permissions}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': f"You Cannot view a user having permissions you don\'t have."
                }, 403)
                return response
            user_dict = user.to_dict()
            exams_published = (await session.execute(Select(Task).where(Task.author_id == user.id, func.lower(Task.type) ==
                                                                       'exam').options(selectinload(Task.subject)).order_by(
                Task.deadline.desc(

            )).limit(
                3))).scalars().all()
            user_dict['exams_published'] = [exam.to_dict() for exam in exams_published]
            exams = (await session.execute(Select(Task).where(Task.faculty_id == user.faculty_id, Task.department_id == user.department_id,
                                                              Task.year_id == user.year_id, func.lower(Task.type) ==
                                                              'exam').options(selectinload(Task.subject)).order_by(Task.deadline.desc()).limit(3))).scalars().all()
            user_dict['exams'] = [exam.to_dict() for exam in exams]
            tasks_published = (await session.execute(Select(Task).where(Task.author_id == user.id, func.lower(Task.type) !=
                                                                       'exam').options(selectinload(Task.subject)).order_by(Task.deadline.desc()).limit(3))).scalars().all()
            user_dict['tasks_published'] = [task.to_dict() for task in tasks_published]
            tasks = (await session.execute(Select(Task).where(Task.faculty_id == user.faculty_id, Task.department_id == user.department_id,
                                                              Task.year_id == user.year_id, func.lower(Task.type) !=
                                                              'exam').options(selectinload(Task.subject)).order_by(Task.deadline.desc()).limit(3))).scalars().all()
            user_dict['tasks'] = [task.to_dict() for task in tasks]
            announcements_published = (await session.execute(Select(Announcement).where(Announcement.author_id == user.id).order_by(
                Announcement.created_at.desc()).limit(3))).scalars().all()
            user_dict['announcements_published'] = [announcement.to_dict() for announcement in announcements_published]
            materials_uploaded = (await session.execute(Select(Material).options(selectinload(Material.subject)).where(
                Material.author_id == user.id).order_by(
                Material.created_at.desc()).limit(3))).scalars().all()
            user_dict['materials_uploaded'] = [material.to_dict() for material in materials_uploaded]
            grades_uploaded = (await session.execute(Select(Grade).options(selectinload(Grade.subject)).where(
                Grade.author_id == user.id).order_by(
                Grade.created_at.desc()).limit(3))).scalars().all()
            user_dict['grades_uploaded'] = [grade.to_dict() for grade in grades_uploaded]
            subjects = (await session.execute(Select(Subject).where(Subject.department_id == user.department_id,
                                                                  Subject.year_id == user.year_id).order_by(
                Subject.name).limit(3))).scalars().all()
            user_dict['subjects'] = [subject.to_dict() for subject in subjects]
            logs = (await session.execute(Select(Log).where(Log.user_id == user.id).order_by(
                Log.created_at.desc()).limit(5))).scalars().all()
            user_dict['logs'] = [log_record.to_dict() for log_record in logs]
            await log(request, 200, 'info', 'User Retrieved Successfully.', {'user_id': user_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'User retrieved successfully',
                'data': user_dict
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving User.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving user'
        }, 500)
        return response

@admin_prefix.get('/search-users')
@rate_limit
@is_logged_in
@is_authorized(['View Users'])
async def search_users(request: Request):
    """
    This route is used to search users by name, email, or phone.
    It will return a list of users matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower()
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        is_active = bool(data.get('is_active', True))
        page = int(data.get('page', 1)) if data.get('page', '1').isdigit() else 1
        limit = int(data.get('limit', 50)) if data.get('limit', '50').isdigit() else 50
        if (faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1)) or (department_id and (not is_int(department_id) or int(department_id) < 1)) or (year_id and (not is_int(year_id) or int(year_id) < 1)):
            await log(request, 400, 'warning', 'Invalid Faculty/Department/Year ID Provided for User Search.', {'faculty_id': faculty_id, 'department_id': department_id, 'year_id': year_id}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid request was sent. Please provide Data correctly'
            }, 400)
            return finalize_request(response)
        async with async_session() as session:
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for User Search.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
            if department_id:
                department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
                if not department:
                    await log(request, 404, 'warning', 'Department Not Found for User Search.', {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department not found'
                    }, 404)
                    return response
                if not faculty_id:
                    await log(request, 400, 'warning', 'Faculty ID Must Be Provided with Department ID for User Search.',
                                {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Can\'t choose department without faculty'
                    }, 400)
                    return response
                if department.faculty_id != int(faculty_id):
                    await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for User Search.',
                                {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department does not belong to the specified faculty'
                    }, 400)
                    return response
            if year_id:
                year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
                if not year:
                    await log(request, 404, 'warning', 'Year Not Found for User Search.', {'year_id': year_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Year not found'
                    }, 404)
                    return response
            query = Select(User).where(User.status == is_active)
            if faculty_id:
                query = query.where(User.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(User.department_id == int(department_id))
            if year_id:
                query = query.where(User.year_id == int(year_id))
            if query_search != '':
                query = query.where(or_(
                    func.lower(User.name).startswith(query_search),
                    func.lower(User.email).startswith(query_search),
                    func.lower(User.phone).startswith(query_search),
                ))
            users = (await session.execute(query.order_by(User.name).offset((page-1) * limit).limit(limit))).scalars().all()
            await log(request, 200, 'info', 'Users Search Completed Successfully.', {'query': query_search, 'data': dict(data), 'users_count': len(users)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Users search completed successfully',
                'data': [user.min_to_dict() for user in users]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Users.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching users'
        }, 500)
        return response

@admin_prefix.get('/roles/count-permissions')
@rate_limit
@is_logged_in
@is_authorized(['View Roles'])
async def count_permissions(request: Request):
    """
    This route is used to count the total number of permissions.
    It will return the count of permissions.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            permissions_count = await session.scalar(Select(func.count(ExactRole.id)))
            await log(request, 200, 'info', 'Permissions Count Retrieved Successfully.', {'permissions_count': permissions_count}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Permissions count retrieved successfully',
                'data': permissions_count
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Counting Permissions.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while counting permissions'
        }, 500)
        return response

@admin_prefix.post('/roles')
@rate_limit
@is_logged_in
@is_authorized(['Add Roles'])
async def create_role(request: Request):
    """
    This route is used to create a new role.
    It will return the created role data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Role.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    if not name:
        await log(request, 400, 'warning', 'No Role Name Provided for Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Role name is required'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            existing_role = (await session.execute(Select(Role).where(func.lower(Role.name) == name.lower()))).scalar_one_or_none()
            if existing_role:
                await log(request, 400, 'warning', 'Role with this name Already Exists.', {'role_name': name},
                          current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role with this name already exists'
                }, 400)
                return response
            role = Role(
                name=name,
            )
            session.add(role)
            await session.commit()
            await log(request, 201, 'info', 'Role Created Successfully.', {'role_name': name}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Role created successfully',
                'data': role.min_to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Role.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating role'
            }, 500)
            return response

@admin_prefix.patch('/roles/{role_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Roles'])
async def update_role(request: Request, role_id: int):
    """
    This route is used to update an existing role.
    It will return the updated role data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Role.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    if not name:
        await log(request, 400, 'warning', 'No Role Name Provided for Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Role name is required'
        }, 400)
        return response
    permissions = data.get('permissions', [])  # list of permission names
    if not isinstance(permissions, list):
        await log(request, 400, 'warning', 'Invalid Permissions Format Provided for Role Update.', {'permissions': permissions}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid permissions provided'
        }, 400)
        return response
    current_user_permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    missing_permissions = [permission for permission in permissions if permission not in current_user_permissions]
    if missing_permissions and len(missing_permissions) > 0:
        await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to Assign the Specified Permissions for Role Update.',
                  {'missing_permissions': missing_permissions}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': f"You Cannot assign permissions you don\'t have."
        }, 403)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            role = (await session.execute(Select(Role).where(Role.id == role_id).options(selectinload(Role.exact_roles),
                                                                                         selectinload(Role.users)
                                                                                         ))).scalar_one_or_none()
            if not role:
                await log(request, 404, 'warning', 'Role Not Found for Update.', {'role_id': role_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role not found'
                }, 404)
                return response
            missing_permissions = [permission.name for permission in role.exact_roles if permission.name not in
                                   current_user_permissions]
            if missing_permissions and len(missing_permissions) > 0:
                await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to Update the Specified Role.',
                          {'role_id': role_id, 'missing_permissions': missing_permissions}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': f"You Cannot update a role having permissions you don\'t have."
                }, 403)
                return response
            existing_role = (await session.execute(Select(Role).where(func.lower(Role.name) == name.lower()))).scalar_one_or_none()
            if existing_role and existing_role.id != role_id:
                await log(request, 400, 'warning', 'Role with this name Already Exists for Update.', {'role_name': name}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role with this name already exists'
                }, 400)
                return response
            role.name = name
            for i in range(len(role.exact_roles)-1, -1, -1):
                if role.exact_roles[i].name not in permissions:
                    role.exact_roles.remove(role.exact_roles[i])
            for permission in permissions:
                exact_role = (await session.execute(Select(ExactRole).where(func.lower(ExactRole.name) == permission.lower()))).scalar_one_or_none()
                if not exact_role:
                    await log(request, 404, 'warning', 'Permission Not Found for Role Update.', {'permission': permission}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': f"Permission \'{permission}\' not found"
                    }, 404)
                    return response
                if exact_role not in role.exact_roles:
                    role.exact_roles.append(exact_role)
            await session.commit()
            await log(request, 200, 'info', 'Role Updated Successfully.', {'role_id': role_id, 'role_name': name}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Role updated successfully',
                'data': role.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Role.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating role'
            }, 500)
            return response

@admin_prefix.delete('/roles/{role_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Roles'])
async def delete_role(request: Request, role_id: int):
    """
    This route is used to delete an existing role.
    It will return a success message if the role is deleted successfully.
    """
    current_user = request.state.current_user
    current_user_permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    async with async_session() as session:
        await session.begin()
        try:
            role = (await session.execute(Select(Role).where(Role.id == role_id).options(selectinload(Role.users),
                                                                                         selectinload(Role.exact_roles)
                                                                                         ))).scalar_one_or_none()
            if not role:
                await log(request, 404, 'warning', 'Role Not Found for Deletion.', {'role_id': role_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role not found'
                }, 404)
                return response
            if role.users and len(role.users) > 0:
                await log(request, 400, 'warning', 'Role Cannot Be Deleted Because It Has Users Associated with It.',
                          {'role_id': role_id, 'users_count': len(role.users)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role cannot be deleted because it has users associated with it'
                }, 400)
                return response
            missing_permissions = [permission.name for permission in role.exact_roles if permission.name not in
                                   current_user_permissions]
            if missing_permissions and len(missing_permissions) > 0:
                await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to Delete the Specified Role.',
                          {'role_id': role_id, 'missing_permissions': missing_permissions}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': f"You Cannot delete a role having permissions you don\'t have."
                }, 403)
                return response
            role.exact_roles.clear()
            await session.flush()
            await session.delete(role)
            await session.commit()
            await log(request, 200, 'info', 'Role Deleted Successfully.', {'role_id': role_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Role deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Role.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting role'
            }, 500)
            return response

@admin_prefix.get('/roles')
@rate_limit
@is_logged_in
@is_authorized(['View Roles'])
async def get_roles(request: Request):
    """
    This route is used to get all roles.
    It will return a list of roles.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip().lower() if data else ''
        async with async_session() as session:
            query = Select(Role).options(selectinload(Role.exact_roles), selectinload(Role.users))
            query = query.where(Role.level >= current_user.role.level)
            if name:
                query = query.where(func.lower(Role.name).startswith(name))
            roles = (await session.execute(query.order_by(Role.name))).scalars().all()
            await log(request, 200, 'info', 'Roles Retrieved Successfully.', {'roles_count': len(roles)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Roles retrieved successfully',
                'data': [role.to_dict() for role in roles]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Roles.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving roles'
        }, 500)
        return response

@admin_prefix.get('/roles/{role_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Roles'])
async def get_role(request: Request, role_id: int):
    """
    This route is used to get a specific role by its ID.
    It will return the role data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            role = (await session.execute(Select(Role).where(Role.id == role_id).options(
                selectinload(Role.exact_roles),
                selectinload(Role.users)
            ))).scalar_one_or_none()
            if not role:
                await log(request, 404, 'warning', 'Role Not Found for Retrieval.', {'role_id': role_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Role not found'
                }, 404)
                return response
            permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
            missing_permissions = [permission.name for permission in role.exact_roles if permission.name not in permissions]
            if missing_permissions and len(missing_permissions) > 0:
                await log(request, 403, 'warning', 'User Does Not Have All Required Permissions to View the Specified Role.',
                          {'role_id': role_id, 'missing_permissions': missing_permissions}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': f"You Cannot view a role having permissions you don\'t have."
                }, 403)
                return response
            await log(request, 200, 'info', 'Role Retrieved Successfully.', {'role_id': role_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Role retrieved successfully',
                'data': {
                    'role': role.full_to_dict(),
                    'permissions': permissions,
                }
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Role.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving role'
        }, 500)
        return response

@admin_prefix.get('/search-roles')
@rate_limit
@is_logged_in
@is_authorized(['View Roles'])
async def search_roles(request: Request):
    """
    This route is used to search roles by name.
    It will return a list of roles matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower() if data else ''
        async with async_session() as session:
            roles = (await session.execute(Select(Role).where(Role.level >= current_user.role.level,
                                                              func.lower(Role.name).startswith(query_search)).order_by(
                Role.name))).scalars().all()
            await log(request, 200, 'info', 'Roles Search Completed Successfully.', {'query': query_search, 'roles_count': len(roles)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Roles search completed successfully',
                'data': [role.min_to_dict() for role in roles]
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Roles.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching roles'
        }, 500)
        return response

@admin_prefix.post('/courses')
@rate_limit
@is_logged_in
@is_authorized(['Add Courses'])
async def create_course(request: Request):
    """
    This route is used to create a new course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Course.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()
    description = data.get('description', '').strip()
    faculty_id = data.get('faculty_id', None)
    department_id = data.get('department_id', None)
    year_id = data.get('year_id', None)
    credits = data.get('credits', None)
    max_students = data.get('max_students', None)
    if not name or not code or not faculty_id or not department_id or not year_id or not credits:
        await log(request, 400, 'warning', 'Missing Required Fields for Course Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    if (not is_int(faculty_id) or int(faculty_id) < 1 or not is_int(department_id) or int(department_id) < 1 or not
    is_int(year_id) or int(year_id) < 1) or not is_int(credits) or int(credits) < 1 or (max_students and (not is_int(max_students) or int(max_students) < 1)):
        await log(request, 400, 'warning', 'Invalid Data Provided for Course Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Course Creation.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Course Creation.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            if department.faculty_id != faculty.id:
                await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for Course Creation.',
                          {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department does not belong to the specified faculty'
                }, 400)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Course Creation.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            existing_course = (await session.execute(Select(Subject).where(Subject.faculty_id == int(faculty_id),
                                                                  Subject.department_id == int(department_id),
                                                                  Subject.year_id == int(year_id),
                                                                  func.lower(Subject.code) == code.lower()))).scalar_one_or_none()
            if existing_course:
                await log(request, 400, 'warning', 'Course with this code Already Exists in the Specified Faculty, Department and Year.',
                          {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course with this code already exists in the specified criteria'
                }, 400)
                return response
            course = Subject(
                name=name,
                code=code,
                faculty_id=faculty.id,
                department_id=department.id,
                year_id=year.id,
                credits=int(credits),
                details={
                    'max_students': int(max_students) if max_students else None,
                    'description': description,
                },
            )
            session.add(course)
            await session.commit()
            await log(request, 201, 'info', 'Course Created Successfully.', {'course': course.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course created successfully',
                'data': course.to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Course.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating course'
            }, 500)
            return response

@admin_prefix.patch('/courses/{course_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Courses'])
async def update_course(request: Request, course_id: int):
    """
    This route is used to update an existing course.
    It will return the updated course data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Course.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()
    description = data.get('description', '').strip()
    faculty_id = data.get('faculty_id', None)
    department_id = data.get('department_id', None)
    year_id = data.get('year_id', None)
    credits = data.get('credits', None)
    max_students = data.get('max_students', None)
    if not name or not code or not faculty_id or not department_id or not year_id or not credits:
        await log(request, 400, 'warning', 'Missing Required Fields for Course Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    if (not is_int(faculty_id) or int(faculty_id) < 1 or not is_int(department_id) or int(department_id) < 1 or not
    is_int(year_id) or int(year_id) < 1) or not is_int(credits) or int(credits) < 1 or (max_students and (not is_int(max_students) or int(max_students) < 1)):
        await log(request, 400, 'warning', 'Invalid Data Provided for Course Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            course = (await session.execute(Select(Subject).where(Subject.id == course_id))).scalar_one_or_none()
            if not course:
                await log(request, 404, 'warning', 'Course Not Found for Update.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found'
                }, 404)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Course Update.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Course Update.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            if department.faculty_id != faculty.id:
                await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for Course Update.',
                          {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department does not belong to the specified faculty'
                }, 400)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Course Update.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            existing_course = (await session.execute(Select(Subject).where(Subject.faculty_id == int(faculty_id),
                                                                  Subject.department_id == int(department_id),
                                                                  Subject.year_id == int(year_id),
                                                                  func.lower(Subject.code) == code.lower()))).scalar_one_or_none()
            if existing_course and existing_course.id != course.id:
                await log(request, 400, 'warning', 'Course with this code Already Exists in the Specified Faculty, Department and Year for Course Update.',
                          {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course with this code already exists in the specified criteria'
                }, 400)
                return response
            course.name = name
            course.code = code
            course.faculty_id = faculty.id
            course.department_id = department.id
            course.year_id = year.id
            course.credits = int(credits)
            course.details['max_students'] = int(max_students) if max_students else None
            course.details['description'] = description
            await session.commit()
            await log(request, 200, 'info', 'Course Updated Successfully.', {'course': course.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course updated successfully',
                'data': course.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Course.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating course'
            }, 500)
            return response

@admin_prefix.delete('/courses/{course_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Courses'])
async def delete_course(request: Request, course_id: int):
    """
    This route is used to delete an existing course.
    It will return a success message if the course is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course = (await session.execute(Select(Subject).where(Subject.id == course_id).options(
                selectinload(Subject.users)))).scalar_one_or_none()
            if not course:
                await log(request, 404, 'warning', 'Course Not Found for Deletion.', {'course_id': course_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found'
                }, 404)
                return response
            if course.users and len(course.users) > 0:
                await log(request, 400, 'warning', 'Course Cannot Be Deleted Because It Has Users Associated with It.',
                          {'course_id': course_id, 'users_count': len(course.users)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course cannot be deleted because it has users associated with it'
                }, 400)
                return response
            await session.delete(course)
            await session.commit()
            await log(request, 200, 'info', 'Course Deleted Successfully.', {'course_id': course_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Course.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting course'
            }, 500)
            return response

@admin_prefix.get('/courses')
@rate_limit
@is_logged_in
@is_authorized(['View Courses'])
async def get_courses(request: Request):
    """
    This route is used to get all courses.
    It will return a list of courses.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower() if data else ''
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided for Course Retrieval.', {'data': dict(data)},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        async with async_session() as session:
            query = Select(Subject).options(selectinload(Subject.faculty), selectinload(Subject.department),
                                            selectinload(Subject.year), selectinload(Subject.users))
            if faculty_id:
                query = query.where(Subject.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Subject.department_id == int(department_id))
            if year_id:
                query = query.where(Subject.year_id == int(year_id))
            if query_search:
                query = query.where(or_(func.lower(Subject.name).startswith(query_search),
                                        func.lower(Subject.code).startswith(query_search)))
            courses = (await session.execute(query.order_by(Subject.name))).scalars().all()
            await log(request, 200, 'info', 'Courses Retrieved Successfully.', {'courses_count': len(courses)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Courses retrieved successfully',
                'data': [course.to_dict() for course in courses]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Courses.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving courses'
        }, 500)
        return response

@admin_prefix.get('/courses/{course_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Courses'])
async def get_course(request: Request, course_id: int):
    """
    This route is used to get a specific course by its ID.
    It will return the course data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course = (await session.execute(Select(Subject).where(Subject.id == course_id).options(
                selectinload(Subject.faculty),
                selectinload(Subject.department),
                selectinload(Subject.year),
                selectinload(Subject.users)
            ))).scalar_one_or_none()
            if not course:
                await log(request, 404, 'warning', 'Course Not Found for Retrieval.', {'course_id': course_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Course Retrieved Successfully.', {'course_id': course_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course retrieved successfully',
                'data': course.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Retrieving Course.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while retrieving course'
        }, 500)
        return response

@admin_prefix.get('/search-courses')
@rate_limit
@is_logged_in
@is_authorized(['View Courses'])
async def search_courses(request: Request):
    """
    This route is used to search courses by name or code.
    It will return a list of courses matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        query_search = data.get('query', '').strip().lower() if data else ''
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided for Course Search.', {'data': dict(data)},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        async with async_session() as session:
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for Course Search.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
            if department_id:
                department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
                if not department:
                    await log(request, 404, 'warning', 'Department Not Found for Course Search.', {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department not found'
                    }, 404)
                    return response
                if not faculty_id:
                    await log(request, 400, 'warning', 'Faculty ID Must Be Provided When Department ID is Given for Course Search.',
                                {'department_id': department_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty must be provided when department is given'
                    }, 400)
                    return response
                if department.faculty_id != int(faculty_id):
                    await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for Course Search.',
                              {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department does not belong to the specified faculty'
                    }, 400)
                    return response
            if year_id:
                year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
                if not year:
                    await log(request, 404, 'warning', 'Year Not Found for Course Search.', {'year_id': year_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Year not found'
                    }, 404)
                    return response
            query = Select(Subject)
            if faculty_id:
                query = query.where(Subject.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Subject.department_id == int(department_id))
            if year_id:
                query = query.where(Subject.year_id == int(year_id))
            if query_search:
                query = query.where(or_(func.lower(Subject.name).startswith(query_search),
                                        func.lower(Subject.code).startswith(query_search)))
            courses = (await session.execute(query.order_by(Subject.name))).scalars().all()
            await log(request, 200, 'info', 'Courses Search Completed Successfully.', {'query': query_search, 'courses_count': len(courses)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Courses search completed successfully',
                'data': [course.min_to_dict() for course in courses]
            }, 200)
            return finalize_request(response)
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Searching Courses.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while searching courses'
        }, 500)
        return response

@admin_prefix.post('/course-maps')
@rate_limit
@is_logged_in
@is_authorized(['Add Course Maps'])
async def create_course_map(request: Request):
    """
    This route is used to create a new course map.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Creating Course Map.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    faculty_id = data.get('faculty_id', None)
    department_id = data.get('department_id', None)
    year_id = data.get('year_id', None)
    years = data.get('years', None)
    terms = data.get('terms', None)
    if not faculty_id or not department_id or not year_id or not years or not terms:
        await log(request, 400, 'warning', 'Missing Required Fields for Course Map Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    if (not is_int(faculty_id) or int(faculty_id) < 1 or not is_int(department_id) or int(department_id) < 1 or not
    is_int(year_id) or int(year_id) < 1) or not is_int(years) or int(years) < 1 or not is_int(terms) or int(terms) < 1:
        await log(request, 400, 'warning', 'Invalid Data Provided for Course Map Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return response
    if int(years) < 4 or int(years) > 7 or int(terms) < 1 or int(terms) > 4:
        await log(request, 400, 'warning', 'Years or Terms Out of Allowed Range for Course Map Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Years must be between 4 and 7 and terms/year must be between 1 and 4'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Course Map Creation.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Course Map Creation.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            if department.faculty_id != faculty.id:
                await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for Course Map Creation.',
                          {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department does not belong to the specified faculty'
                }, 400)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Course Map Creation.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            existing_course_map = (await session.execute(Select(Roadmap).where(Roadmap.status == True,
                                                                    Roadmap.faculty_id ==int(faculty_id),
                                                                    Roadmap.department_id == int(department_id),
                                                                    Roadmap.year_id == int(year_id),
                                                                    Roadmap.type == 2))).scalar_one_or_none()
            if existing_course_map:
                await log(request, 400, 'warning', 'Course Map Already Exists in the Specified Faculty, Department and Year.',
                          {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map already exists in the specified criteria'
                }, 400)
                return response
            course_map = Roadmap(
                faculty=faculty,
                department=department,
                year=year,
                author=current_user,
                status=True,
                type=2,
                details={
                    'years': [f"Level {i+1}" for i in range(int(years))],
                    'terms': int(terms),
                },
            )
            session.add(course_map)
            await session.commit()
            await log(request, 201, 'info', 'Course Map Created Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course map created successfully',
                'data': course_map.to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating course map'
            }, 500)
            return response

@admin_prefix.patch('/course-maps/{course_map_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Course Maps'])
async def update_course_map(request: Request, course_map_id: int):
    """
    This route is used to update an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Course Map.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    faculty_id = data.get('faculty_id', None)
    department_id = data.get('department_id', None)
    year_id = data.get('year_id', None)
    years = data.get('years', None)
    terms = data.get('terms', None)
    if not faculty_id or not department_id or not year_id or not years or not terms:
        await log(request, 400, 'warning', 'Missing Required Fields for Course Map Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    if (not is_int(faculty_id) or int(faculty_id) < 1 or not is_int(department_id) or int(department_id) < 1 or not
    is_int(year_id) or int(year_id) < 1) or not is_int(years) or int(years) < 1 or not is_int(terms) or int(terms) < 1:
        await log(request, 400, 'warning', 'Invalid Data Provided for Course Map Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return response
    if int(years) < 4 or int(years) > 7 or int(terms) < 1 or int(terms) > 4:
        await log(request, 400, 'warning', 'Years or Terms Out of Allowed Range for Course Map Update.', {'data': dict(data)},
                    current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Years must be between 4 and 7 and terms/year must be between 1 and 4'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Update.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Course Map Update.', {'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department:
                await log(request, 404, 'warning', 'Department Not Found for Course Map Update.', {'department_id': department_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found'
                }, 404)
                return response
            if department.faculty_id != faculty.id:
                await log(request, 400, 'warning', 'Department Does Not Belong to the Specified Faculty for Course Map Update.',
                          {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department does not belong to the specified faculty'
                }, 400)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Course Map Update.', {'year_id': year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            existing_course_map = (await session.execute(Select(Roadmap).where(Roadmap.status == True,
                                                                    Roadmap.faculty_id ==int(faculty_id),
                                                                    Roadmap.department_id == int(department_id),
                                                                    Roadmap.year_id == int(year_id),
                                                                    Roadmap.type == 2))).scalar_one_or_none()
            if existing_course_map and existing_course_map.id != course_map.id:
                await log(request, 400, 'warning', 'Course Map Already Exists in the Specified Faculty, Department and Year for Course Map Update.',
                          {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map already exists in the specified criteria'
                }, 400)
                return response
            course_map.faculty = faculty
            course_map.department = department
            course_map.year = year
            course_map.details['years'] = [f"Level {i+1}" for i in range(int(years))]
            course_map.details['terms'] = int(terms)
            await session.commit()
            await log(request, 200, 'info', 'Course Map Updated Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course map updated successfully',
                'data': course_map.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating course map'
            }, 500)
            return response

@admin_prefix.patch('/course-maps/{course_map_id}/years')
@rate_limit
@is_logged_in
@is_authorized(['Edit Course Maps'])
async def update_course_map_years(request: Request, course_map_id: int):
    """
    This route is used to update the years of an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Course Map Years.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    year_index = data.get('year_index', None)
    year_name = data.get('year_name', '').strip()
    if not year_index or not year_name or year_name == '' or not is_int(year_index) or int(year_index) < 1:
        await log(request, 400, 'warning', 'Missing Required Fields for Course Map Years Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Request was sent. Please provide data correctly.'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Years Update.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            years = course_map.details.get('years', [])
            if int(year_index) > len(years):
                await log(request, 400, 'warning', 'Year Index Out of Range for Course Map Years Update.', {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year index out of range'
                }, 400)
                return response
            years[int(year_index)-1] = year_name
            course_map.details['years'] = years
            await session.commit()
            await log(request, 200, 'info', 'Course Map Years Updated Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course map years updated successfully',
                'data': course_map.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Course Map Years.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating course map years'
            }, 500)
            return response

@admin_prefix.post('/course-maps/{course_map_id}/courses')
@rate_limit
@is_logged_in
@is_authorized(['Edit Course Maps'])
async def add_course_to_course_map(request: Request, course_map_id: int):
    """
    This route is used to add a course to an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Adding Course to Course Map.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    subject_id = data.get('subject_id', None)
    year_index = data.get('year_index', None)
    term = data.get('term', None)
    rank = data.get('rank', None)
    if not subject_id or not year_index or not term or not rank or not is_int(subject_id) or int(subject_id) < 1 or not is_int(year_index) or int(year_index) < 1 or not is_int(term) or int(term) < 1 or not is_int(rank) or int(rank) < 1:
        await log(request, 400, 'warning', 'Missing or Invalid Required Fields for Adding Course to Course Map.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Request was sent. Please provide data correctly.'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id).options(
                selectinload(Roadmap.faculty),
                selectinload(Roadmap.department),
                selectinload(Roadmap.year),
                selectinload(Roadmap.author)
            ))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Adding Course.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            if int(year_index) > len(course_map.details.get('years', [])) or int(term) > course_map.details.get('terms', 0):
                await log(request, 400, 'warning', 'Year Index or Term Out of Range for Adding Course to Course Map.', {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year index or term out of range'
                }, 400)
                return response
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Subject Not Found for Adding to Course Map.', {'subject_id': subject_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found'
                }, 404)
                return response
            if subject.faculty_id != course_map.faculty_id or subject.department_id != course_map.department_id or subject.year_id != course_map.year_id:
                await log(request, 400, 'warning', 'Subject Does Not Belong to the Same Faculty, Department or Year as Course Map for Adding to Course Map.',
                          {'subject_id': subject_id, 'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject does not belong to the same criteria as course map'
                }, 400)
                return response
            courses = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.roadmap_id == course_map.id,
                                                                        RoadmapCourse.year == int(year_index),
                                                                        RoadmapCourse.term == int(term)))).scalars().all()
            if int(rank) > len(courses) + 1:
                await log(request, 400, 'warning', 'Rank Out of Allowed Range for Adding Course to Course Map.', {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Rank out of range'
                }, 400)
                return response
            for c in courses:
                if c.rank >= int(rank):
                    c.rank += 1
            course = RoadmapCourse(
                roadmap=course_map,
                subject=subject,
                year=int(year_index),
                term=int(term),
                rank=int(rank)
            )
            session.add(course)
            await session.commit()
            await log(request, 201, 'info', 'Course Added to Course Map Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course added to course map successfully',
                'data': course_map.to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Adding Course to Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while adding course to course map'
            }, 500)
            return response

@admin_prefix.patch('/course-maps/{course_map_id}/courses/{course_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Course Maps'])
async def update_course_in_course_map(request: Request, course_map_id: int, course_id: int):
    """
    This route is used to update a course in an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Updating Course in Course Map.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    year_index = data.get('year_index', None)
    term = data.get('term', None)
    rank = data.get('rank', None)
    if not year_index or not term or not rank or not is_int(year_index) or int(year_index) < 1 or not is_int(term) or int(term) < 1 or not is_int(rank) or int(rank) < 1:
        await log(request, 400, 'warning', 'Missing or Invalid Required Fields for Updating Course in Course Map.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid Request was sent. Please provide data correctly.'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id).options(
                selectinload(Roadmap.faculty),
                selectinload(Roadmap.department),
                selectinload(Roadmap.year),
                selectinload(Roadmap.author)
            ))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Updating Course.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            if int(year_index) > len(course_map.details.get('years', [])) or int(term) > course_map.details.get('terms', 0):
                await log(request, 400, 'warning', 'Year Index or Term Out of Range for Updating Course in Course Map.', {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year index or term out of range'
                }, 400)
                return response
            course = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.id == course_id))).scalar_one_or_none()
            if not course or course.roadmap_id != course_map.id:
                await log(request, 404, 'warning', 'Course Not Found in the Specified Course Map for Update.', {'course_id': course_id, 'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found in the specified course map'
                }, 404)
                return response
            courses = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.roadmap_id == course_map.id,
                                                                        RoadmapCourse.year == int(year_index),
                                                                        RoadmapCourse.term == int(term)))).scalars().all()
            courses_length = len(courses)
            if course in courses:
                courses_length -= 1
            if int(year_index) != course.year or int(term) != course.term:
                courses_length += 1
            if int(rank) > courses_length:
                await log(request, 400, 'warning', 'Rank Out of Allowed Range for Updating Course in Course Map.', {'data': dict(data)}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Rank out of range'
                }, 400)
                return response
            for c in courses:
                if c.id == course.id:
                    continue
                if c.rank >= int(rank):
                    c.rank += 1
            course.year = int(year_index)
            course.term = int(term)
            course.rank = int(rank)
            await session.commit()
            await log(request, 200, 'info', 'Course in Course Map Updated Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course in course map updated successfully',
                'data': course_map.min_to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Course in Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating course in course map'
            }, 500)
            return response

@admin_prefix.delete('/course-maps/{course_map_id}/courses/{course_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Course Maps'])
async def delete_course_from_course_map(request: Request, course_map_id: int, course_id: int):
    """
    This route is used to delete a course from an existing course map.
    It will return a success message if the course is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id).options(
                selectinload(Roadmap.faculty),
                selectinload(Roadmap.department),
                selectinload(Roadmap.year),
                selectinload(Roadmap.author)
            ))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Deleting Course.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            course = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.id == course_id))).scalar_one_or_none()
            if not course or course.roadmap_id != course_map.id:
                await log(request, 404, 'warning', 'Course Not Found in the Specified Course Map for Deletion.', {'course_id': course_id, 'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course not found in the specified course map'
                }, 404)
                return response
            rank = course.rank
            year = course.year
            term = course.term
            await session.delete(course)
            courses = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.roadmap_id == course_map.id,
                                                                        RoadmapCourse.year == year,
                                                                        RoadmapCourse.term == term))).scalars().all()
            for c in courses:
                if c.rank > rank:
                    c.rank -= 1
            await session.commit()
            await log(request, 200, 'info', 'Course Deleted from Course Map Successfully.', {'course_map': course_map.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course deleted from course map successfully',
                'data': course_map.to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Course from Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting course from course map'
            }, 500)
            return response

@admin_prefix.delete('/course-maps/{course_map_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Course Maps'])
async def delete_course_map(request: Request, course_map_id: int):
    """
    This route is used to delete an existing course map.
    It will return a success message if the course map is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found for Deletion.', {'course_map_id': course_map_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            await session.delete(course_map)
            await session.commit()
            await log(request, 200, 'info', 'Course Map Deleted Successfully.', {'course_map_id': course_map_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course map deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Course Map.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting course map'
            }, 500)
            return response

@admin_prefix.get('/course-maps')
@rate_limit
@is_logged_in
@is_authorized(['View Course Maps'])
async def get_course_maps(request: Request):
    """
    This route is used to get all course maps.
    It will return a list of course maps.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Parameters.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        if (faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1)) or (department_id and (not is_int(department_id) or int(department_id) < 1)) or (year_id and (not is_int(year_id) or int(year_id) < 1)):
            await log(request, 400, 'warning', 'Invalid Data Provided in The Request Query Parameters for Getting Course Maps.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        async with async_session() as session:
            query = Select(Roadmap).where(Roadmap.status == True, Roadmap.type == 2).options(
                selectinload(Roadmap.faculty),
                selectinload(Roadmap.department),
                selectinload(Roadmap.year),
                selectinload(Roadmap.author),
                selectinload(Roadmap.courses),
            )
            if faculty_id:
                query = query.where(Roadmap.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Roadmap.department_id == int(department_id))
            if year_id:
                query = query.where(Roadmap.year_id == int(year_id))
            course_maps = (await session.execute(query.order_by(Roadmap.id.desc()))).scalars().all()
            await log(request, 200, 'info', 'Course Maps Retrieved Successfully.', {'filters': dict(data), 'count': len(course_maps)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course maps retrieved successfully',
                'data': [{'roadmap': cm.to_dict(), 'courses_count': len(cm.courses)} for cm in course_maps]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Course Maps.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting course maps'
        }, 500)
        return response

@admin_prefix.get('/course-maps/{course_map_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Course Maps'])
async def get_course_map(request: Request, course_map_id: int):
    """
    This route is used to get a specific course map by its ID.
    It will return the course map data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course_map = (await session.execute(Select(Roadmap).where(Roadmap.id == course_map_id, Roadmap.status == True, Roadmap.type == 2).options(
                selectinload(Roadmap.faculty),
                selectinload(Roadmap.department),
                selectinload(Roadmap.year),
                selectinload(Roadmap.author)
            ))).scalar_one_or_none()
            if not course_map:
                await log(request, 404, 'warning', 'Course Map Not Found.', {'course_map_id': course_map_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Course map not found'
                }, 404)
                return response
            courses = (await session.execute(Select(RoadmapCourse).where(RoadmapCourse.roadmap_id == course_map.id).order_by(RoadmapCourse.year.asc(), RoadmapCourse.term.asc(), RoadmapCourse.rank.asc()).options(
                selectinload(RoadmapCourse.subject)
            ))).scalars().all()
            years = [[[] for term in range(course_map.details.get('terms', 0))] for _ in range(len(
                course_map.details.get('years', [])))]
            for course in courses:
                if 1 <= course.year <= len(years) and 1 <= course.term <= len(years[course.year - 1]):
                    if not years[course.year - 1][course.term - 1]:
                        years[course.year - 1][course.term - 1] = []
                    years[course.year - 1][course.term - 1].append(course.min_to_dict())
            await log(request, 200, 'info', 'Course Map Retrieved Successfully.', {'course_map': course_map.to_dict(), 'courses_count': len(courses)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Course map retrieved successfully',
                'data': {
                    'roadmap': course_map.to_dict(),
                    'courses': years,
                    'courses_count': len(courses)
                }
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Course Map.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting course map'
        }, 500)
        return response

@admin_prefix.post('/materials')
@rate_limit
@is_logged_in
@is_authorized(['Add Materials'])
async def create_material(request: Request):
    """
    This route is used to create a new material.
    It will return the created material data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Material Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    url = data.get('url', '').strip()
    type = data.get('type', '').strip().lower() # File or Folder or YouTube or Drive or External
    parent_id = data.get('parent_id', None) # Parent Folder ID
    subject_id = data.get('subject_id', None) # Subject ID
    # file_type = data.get('file_type', '').strip().lower() # pdf, docx, pptx, xlsx, txt, zip, rar, image, video,
    # audio, ...
    allowed_file_types = ['image', 'pdf', 'doc', 'sheet', 'ppt', 'video', 'audio', 'text', 'archive', 'gdrive']
    file = None
    if not type or type not in ['file', 'folder', 'youtube', 'drive', 'external']:
        await log(request, 400, 'warning', 'Invalid or Missing Material Type Provided for Material Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Material type must be one of the available types'
        }, 400)
        return response
    if parent_id and (not is_int(parent_id) or int(parent_id) < 1):
        await log(request, 400, 'warning', 'Invalid Parent ID Provided for Material Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid parent ID provided'
        }, 400)
        return response
    if not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(request, 400, 'warning', 'Invalid or Missing Subject ID Provided for Material Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid subject was provided.'
        }, 400)
        return response
    if type == 'folder':
        if not name or name == '':
            await log(request, 400, 'warning', 'Missing Required Fields for Folder Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Folder Name is required'
            }, 400)
            return response
    elif type in ['youtube', 'drive', 'external']:
        if not name or name == '' or not url or url == '':
            await log(request, 400, 'warning', 'Missing Required Fields for Link Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Name and URL are required'
            }, 400)
            return response
        if type == 'youtube' and not is_youtube_url(url):
            await log(request, 400, 'warning', 'Invalid YouTube URL Provided for Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid YouTube URL provided'
            }, 400)
            return response
        if type == 'drive' and not is_drive_url(url):
            await log(request, 400, 'warning', 'Invalid Google Drive URL Provided for Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid Google Drive URL provided'
            }, 400)
            return response
        if type == 'external' and not is_valid_url(url):
            await log(request, 400, 'warning', 'Invalid External URL Provided for Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid External URL provided'
            }, 400)
            return response
    else:
        if not url or url == '':
            await log(request, 400, 'warning', 'Missing Required Fields for File Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'File is required'
            }, 400)
            return response
        file = await get_file_from_drive(url, current_user.google_refresh_token, request)
        if not file:
            await log(request, 400, 'warning', 'Invalid File URL Provided for Material Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid File Provided.'
            }, 400)
            return response
        if get_file_type(file.get('mimeType')) not in allowed_file_types:
            await log(request, 400, 'warning', 'Unsupported File Type Provided for Material Creation.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
            }, 400)
            return response
    async with async_session() as session:
        await session.begin()
        try:
            if parent_id:
                parent = (await session.execute(Select(Material).where(Material.id == int(parent_id)))).scalar_one_or_none()
                if not parent or parent.type != 'folder':
                    await log(request, 404, 'warning', 'Parent Folder Not Found for Material Creation.', {'parent_id': parent_id}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Parent folder not found'
                    }, 404)
                    return response
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Subject Not Found for Material Creation.', {'subject_id': subject_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found'
                }, 404)
                return response
            material = Material(
                name=name if name and name != '' else file.get('name'),
                type=type,
                url=url if url and url != '' else None,
                subject=subject,
                author=current_user,
                parent=parent if parent_id else None,
                details={
                    'description': description if description and description != '' else None,
                        }
            )
            if file:
                material.details['file_data'] = get_file_data(file)
            session.add(material)
            await session.commit()
            await log(request, 201, 'info', 'Material Created Successfully.', {'material': material.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Material created successfully',
                'data': material.min_to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Material.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating material'
            }, 500)
            return response

@admin_prefix.patch('/materials/{material_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Materials'])
async def update_material(request: Request, material_id: int):
    """
    This route is used to update an existing material.
    It will return the updated material data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Material Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    url = data.get('url', '').strip()
    file = None
    to_be_removed = False
    async with async_session() as session:
        await session.begin()
        try:
            material = (await session.execute(Select(Material).where(Material.id == material_id).options(selectinload(Material.author)))).scalar_one_or_none()
            if not material:
                await log(request, 404, 'warning', 'Material Not Found for Update.', {'material_id': material_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Material not found'
                }, 404)
                return response
            if material.author_id != current_user.id and not 'Manage All Materials' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Material Update Attempt by Non-Author User.', {'material_id': material_id, 'author_id': material.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to update this material'
                }, 403)
                return response
            if name and name != '':
                material.name = name
            if description and description != '':
                material.details['description'] = description
            if material.type == 'file' and url and url != '' and url != material.url:
                file = await get_file_from_drive(url, current_user.google_refresh_token, request)
                if not file:
                    await log(request, 400, 'warning', 'Invalid File URL Provided for Material Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid File Provided.'
                    }, 400)
                    return response
                if get_file_type(file.get('mimeType')) not in ['image', 'pdf', 'doc', 'sheet', 'ppt', 'video', 'audio', 'text', 'archive', 'gdrive']:
                    await log(request, 400, 'warning', 'Unsupported File Type Provided for Material Update.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
                    }, 400)
                    return response
                to_be_removed = True
            if material.type in ['youtube', 'drive', 'external'] and url and url != '' and url != material.url:
                if material.type == 'youtube' and not is_youtube_url(url):
                    await log(request, 400, 'warning', 'Invalid YouTube URL Provided for Material Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid YouTube URL provided'
                    }, 400)
                    return response
                if material.type == 'drive' and not is_drive_url(url):
                    await log(request, 400, 'warning', 'Invalid Google Drive URL Provided for Material Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid Google Drive URL provided'
                    }, 400)
                    return response
                if material.type == 'external' and not is_valid_url(url):
                    await log(request, 400, 'warning', 'Invalid External URL Provided for Material Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid External URL provided'
                    }, 400)
                    return response
                material.url = url
            if to_be_removed:
                removed = await remove_file_from_drive(material.url, material.author.google_refresh_token, request)
                if not removed:
                    await log(request, 500, 'error', 'Failed to Remove Old File from Drive During Material Update.', {'material_id': material.id, 'old_url': material.url}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Failed to update material. Please try again later.'
                    }, 500)
                    return response
                material.url = url
                material.details['file_data'] = get_file_data(file)
            material.author = current_user  # Update the author to the user who made the update
            await session.commit()
            await log(request, 200, 'info', 'Material Updated Successfully.', {'material': material.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Material updated successfully',
                'data': material.min_to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Material.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating material'
            }, 500)
            return response

async def recursive_delete_materials(request: Request, material_id: int):
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            material = (await session.execute(Select(Material).where(Material.id == material_id).options(selectinload(Material.author)))).scalar_one_or_none()
            if not material:
                return True  # If material not found, consider it deleted
            if material.type == 'file':
                removed = await remove_file_from_drive(material.url, material.author.google_refresh_token, request)
                if not removed:
                    await log(request, 500, 'error', 'Failed to Remove File from Drive During Recursive Material Deletion.', {'material_id': material.id, 'url': material.url}, current_user.id)
                    return False
            if material.type == 'folder':
                # If folder, check if it has any children and delete them recursively
                children = (await session.execute(Select(Material).where(Material.parent_id == material.id))).scalars().all()
                for child in children:
                    deleted = await recursive_delete_materials(request, child.id)
                    if not deleted:
                        return False
            await session.delete(material)
            # await session.commit()
            return True
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred during Recursive Material Deletion.', {'error': str(e), 'material_id': material_id}, current_user.id)
        return False

@admin_prefix.delete('/materials/{material_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Materials'])
async def delete_material(request: Request, material_id: int):
    """
    This route is used to delete an existing material.
    It will return a success message if the material is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    async with async_session() as session:
        await session.begin()
        try:
            material = (await session.execute(Select(Material).where(Material.id == material_id).options(selectinload(Material.author)))).scalar_one_or_none()
            if not material:
                await log(request, 404, 'warning', 'Material Not Found for Deletion.', {'material_id': material_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Material not found'
                }, 404)
                return response
            if material.author_id != current_user.id and not 'Manage All Materials' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Material Deletion Attempt by Non-Author User.', {'material_id': material_id, 'author_id': material.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to delete this material'
                }, 403)
                return response
            removed = await recursive_delete_materials(request, material_id)
            if not removed:
                await log(request, 500, 'error', 'Failed to Recursively Delete Material and Its Contents.', {'material_id': material_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Failed to delete material. Please try again later.'
                }, 500)
                return response
            await session.commit()
            await log(request, 200, 'info', 'Material Deleted Successfully.', {'material_id': material_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Material deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Material.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting material'
            }, 500)
            return response

@admin_prefix.get('/materials')
@rate_limit
@is_logged_in
@is_authorized(['View Materials'])
async def get_materials(request: Request):
    """
    This route is used to get all materials.
    It will return a list of materials.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Parameters.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip().lower()
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        subject_id = data.get('subject_id', None)
        parent_id = data.get('parent_id', None)  # Parent Folder ID
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1) or subject_id and (not is_int(subject_id) or int(subject_id) < 1) or parent_id and (not is_int(parent_id) or int(parent_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided in The Request Query Parameters for Getting Materials.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        if not faculty_id or not department_id or not year_id or not subject_id:
            await log(request, 400, 'warning', 'Missing Required Query Parameters for Getting Materials.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Please make sure to fill all filters correctly'
            }, 400)
            return response
        async with async_session() as session:
            if parent_id:
                parent = (await session.execute(Select(Material).where(Material.id == int(parent_id)))).scalar_one_or_none()
                if not parent or parent.type != 'folder':
                    await log(request, 404, 'warning', 'Parent Folder Not Found for Getting Materials.', {'parent_id': parent_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Parent folder not found'
                    }, 404)
                    return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Getting Materials.', {'faculty_id': faculty_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department or department.faculty_id != faculty:
                await log(request, 404, 'warning', 'Department Not Found or Does Not Belong to Specified Faculty for Getting Materials.', {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found in the specified faculty'
                }, 404)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Getting Materials.', {'year_id': year_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to Specified Faculty, Department, or Year for Getting Materials.', {'subject_id': subject_id, 'faculty_id': faculty_id, 'department_id': department_id, 'year_id': year_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in the specified criteria'
                }, 404)
                return response
            query = Select(Material).where(Material.subject_id == subject.id, Material.parent_id == parent_id)
            query = query.where(func.lower(Material.name).startswith(name))
            materials = (await session.execute(query.order_by(Material.modified_at.desc()))).scalars().all()
            await log(request, 200, 'info', 'Materials Retrieved Successfully.', {'filters': dict(data), 'count': len(materials)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Materials retrieved successfully',
                'data': [m.min_to_dict() for m in materials]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Materials.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting materials'
        }, 500)
        return response

@admin_prefix.get('/materials/{material_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Materials'])
async def get_material(request: Request, material_id: int):
    """
    This route is used to get a specific material by its ID.
    It will return the material data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            material = (await session.execute(Select(Material).where(Material.id == material_id).options(
                selectinload(Material.author),
                selectinload(Material.subject),
                selectinload(Material.parent)
            ))).scalar_one_or_none()
            if not material:
                await log(request, 404, 'warning', 'Material Not Found.', {'material_id': material_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Material not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Material Retrieved Successfully.', {'material': material.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Material retrieved successfully',
                'data': material.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Material.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting material'
        }, 500)
        return response


@admin_prefix.post('/grades')
@rate_limit
@is_logged_in
@is_authorized(['Add Grades'])
async def create_grade(request: Request):
    """
    This route is used to create a new grade.
    It will return the created grade data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Grade Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    url = data.get('url', '').strip()
    type = data.get('type', '').strip().lower() # File or Folder or External
    parent_id = data.get('parent_id', None) # Parent Folder ID
    subject_id = data.get('subject_id', None) # Subject ID
    # file_type = data.get('file_type', '').strip().lower() # pdf, docx, pptx, xlsx, txt, zip, rar, image, video,
    # audio, ...
    allowed_file_types = ['image', 'pdf', 'doc', 'sheet', 'gdrive']
    file = None
    if not type or type not in ['file', 'folder', 'external']:
        await log(request, 400, 'warning', 'Invalid or Missing Grade Type Provided for Grade Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Grade type must be one of the available types'
        }, 400)
        return response
    if parent_id and (not is_int(parent_id) or int(parent_id) < 1):
        await log(request, 400, 'warning', 'Invalid Parent ID Provided for Grade Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid parent ID provided'
        }, 400)
        return response
    if not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(request, 400, 'warning', 'Invalid or Missing Subject ID Provided for Grade Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid subject was provided.'
        }, 400)
        return response
    if type == 'folder':
        if not name or name == '':
            await log(request, 400, 'warning', 'Missing Required Fields for Folder Grade Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Folder Name is required'
            }, 400)
            return response
    elif type in ['external']:
        if not name or name == '' or not url or url == '':
            await log(request, 400, 'warning', 'Missing Required Fields for Link Grade Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Name and URL are required'
            }, 400)
            return response
        if type == 'external' and not is_valid_url(url):
            await log(request, 400, 'warning', 'Invalid External URL Provided for Grade Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid URL provided'
            }, 400)
            return response
    else:
        if not url or url == '':
            await log(request, 400, 'warning', 'Missing Required Fields for File Grade Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'File is required'
            }, 400)
            return response
        file = await get_file_from_drive(url, current_user.google_refresh_token, request)
        if not file:
            await log(request, 400, 'warning', 'Invalid File URL Provided for Grade Creation.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid File Provided.'
            }, 400)
            return response
        if get_file_type(file.get('mimeType')) not in allowed_file_types:
            await log(request, 400, 'warning', 'Unsupported File Type Provided for Grade Creation.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
            }, 400)
            return response
    async with async_session() as session:
        await session.begin()
        try:
            if parent_id:
                parent = (await session.execute(Select(Grade).where(Grade.id == int(parent_id)))).scalar_one_or_none()
                if not parent or parent.type != 'folder':
                    await log(request, 404, 'warning', 'Parent Folder Not Found for Grade Creation.', {'parent_id': parent_id}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Parent folder not found'
                    }, 404)
                    return response
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Subject Not Found for Grade Creation.', {'subject_id': subject_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found'
                }, 404)
                return response
            grade = Grade(
                name=name if name and name != '' else file.get('name'),
                type=type,
                url=url if url and url != '' else None,
                subject=subject,
                author=current_user,
                parent=parent if parent_id else None,
                details={
                    'description': description if description and description != '' else None,
                        }
            )
            if file:
                grade.details['file_data'] = get_file_data(file)
            session.add(grade)
            await session.commit()
            await log(request, 201, 'info', 'Grade Created Successfully.', {'grade': grade.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Grade created successfully',
                'data': grade.min_to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Grade.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating grade'
            }, 500)
            return response

@admin_prefix.patch('/grades/{grade_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Grades'])
async def update_grade(request: Request, grade_id: int):
    """
    This route is used to update an existing grade.
    It will return the updated grade data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Grade Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    url = data.get('url', '').strip()
    file = None
    to_be_removed = False
    async with async_session() as session:
        await session.begin()
        try:
            grade = (await session.execute(Select(Grade).where(Grade.id == grade_id).options(selectinload(Grade.author)))).scalar_one_or_none()
            if not grade:
                await log(request, 404, 'warning', 'Grade Not Found for Update.', {'grade_id': grade_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Grade not found'
                }, 404)
                return response
            if grade.author_id != current_user.id and not 'Manage All Grades' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Grade Update Attempt by Non-Author User.', {'grade_id': grade_id, 'author_id': grade.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to update this grade'
                }, 403)
                return response
            if name and name != '':
                grade.name = name
            if description and description != '':
                grade.details['description'] = description
            if grade.type == 'file' and url and url != '' and url != grade.url:
                file = await get_file_from_drive(url, current_user.google_refresh_token, request)
                if not file:
                    await log(request, 400, 'warning', 'Invalid File URL Provided for Grade Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid File Provided.'
                    }, 400)
                    return response
                if get_file_type(file.get('mimeType')) not in ['image', 'pdf', 'doc', 'sheet', 'gdrive']:
                    await log(request, 400, 'warning', 'Unsupported File Type Provided for Grade Update.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
                    }, 400)
                    return response
                to_be_removed = True
            if grade.type in ['external'] and url and url != '' and url != grade.url:
                if grade.type == 'external' and not is_valid_url(url):
                    await log(request, 400, 'warning', 'Invalid External URL Provided for Grade Update.', {'data': dict(data)}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Invalid URL provided'
                    }, 400)
                    return response
                grade.url = url
            if to_be_removed:
                removed = await remove_file_from_drive(grade.url, grade.author.google_refresh_token, request)
                if not removed:
                    await log(request, 500, 'error', 'Failed to Remove Old File from Drive During Grade Update.',
                              {'grade_id': grade.id, 'old_url': grade.url}, current_user.id)
                    await session.rollback()
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Failed to update grade. Please try again later.'
                    }, 500)
                    return response
                grade.url = url
                grade.details['file_data'] = get_file_data(file)
            grade.author = current_user  # Update the author to the user who made the update
            await session.commit()
            await log(request, 200, 'info', 'Grade Updated Successfully.', {'grade': grade.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Grade updated successfully',
                'data': grade.min_to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Grade.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating grade'
            }, 500)
            return response

async def recursive_delete_grades(request: Request, grade_id: int):
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            grade = (await session.execute(Select(Grade).where(Grade.id == grade_id).options(selectinload(Grade.author)))).scalar_one_or_none()
            if not grade:
                return True  # If grade not found, consider it deleted
            if grade.type == 'file':
                removed = await remove_file_from_drive(grade.url, grade.author.google_refresh_token, request)
                if not removed:
                    await log(request, 500, 'error', 'Failed to Remove File from Drive During Recursive Grade Deletion.', {'grade_id': grade.id, 'url': grade.url}, current_user.id)
                    return False
            if grade.type == 'folder':
                # If folder, check if it has any children and delete them recursively
                children = (await session.execute(Select(Grade).where(Grade.parent_id == grade.id))).scalars().all()
                for child in children:
                    deleted = await recursive_delete_grades(request, child.id)
                    if not deleted:
                        return False
            await session.delete(grade)
            # await session.commit()
            return True
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred during Recursive Grade Deletion.', {'error': str(e), 'grade_id': grade_id}, current_user.id)
        return False

@admin_prefix.delete('/grades/{grade_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Grades'])
async def delete_grade(request: Request, grade_id: int):
    """
    This route is used to delete an existing grade.
    It will return a success message if the grade is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    async with async_session() as session:
        await session.begin()
        try:
            grade = (await session.execute(Select(Grade).where(Grade.id == grade_id).options(selectinload(Grade.author)))).scalar_one_or_none()
            if not grade:
                await log(request, 404, 'warning', 'Grade Not Found for Deletion.', {'grade_id': grade_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Grade not found'
                }, 404)
                return response
            if grade.author_id != current_user.id and not 'Manage All Grades' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Grade Deletion Attempt by Non-Author User.', {'grade_id': grade_id, 'author_id': grade.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to delete this grade'
                }, 403)
                return response
            removed = await recursive_delete_grades(request, grade_id)
            if not removed:
                await log(request, 500, 'error', 'Failed to Recursively Delete Grade and Its Contents.', {'grade_id': grade_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Failed to delete grade. Please try again later.'
                }, 500)
                return response
            await session.commit()
            await log(request, 200, 'info', 'Grade Deleted Successfully.', {'grade_id': grade_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Grade deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Grade.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting grade'
            }, 500)
            return response

@admin_prefix.get('/grades')
@rate_limit
@is_logged_in
@is_authorized(['View Grades'])
async def get_grades(request: Request):
    """
    This route is used to get all grades.
    It will return a list of grades.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Parameters.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip().lower()
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        subject_id = data.get('subject_id', None)
        parent_id = data.get('parent_id', None)  # Parent Folder ID
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1) or subject_id and (not is_int(subject_id) or int(subject_id) < 1) or parent_id and (not is_int(parent_id) or int(parent_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided in The Request Query Parameters for Getting Grades.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        if not faculty_id or not department_id or not year_id or not subject_id:
            await log(request, 400, 'warning', 'Missing Required Query Parameters for Getting Grades.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Please make sure to fill all filters correctly'
            }, 400)
            return response
        async with async_session() as session:
            if parent_id:
                parent = (await session.execute(Select(Grade).where(Grade.id == int(parent_id)))).scalar_one_or_none()
                if not parent or parent.type != 'folder':
                    await log(request, 404, 'warning', 'Parent Folder Not Found for Getting Grades.', {'parent_id': parent_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Parent folder not found'
                    }, 404)
                    return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
            if not faculty:
                await log(request, 404, 'warning', 'Faculty Not Found for Getting Grades.', {'faculty_id': faculty_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Faculty not found'
                }, 404)
                return response
            department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
            if not department or department.faculty_id != faculty:
                await log(request, 404, 'warning', 'Department Not Found or Does Not Belong to Specified Faculty for Getting Grades.', {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Department not found in the specified faculty'
                }, 404)
                return response
            year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
            if not year:
                await log(request, 404, 'warning', 'Year Not Found for Getting Grades.', {'year_id': year_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Year not found'
                }, 404)
                return response
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to Specified Faculty, Department, or Year for Getting Grades.', {'subject_id': subject_id, 'faculty_id': faculty_id, 'department_id': department_id, 'year_id': year_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in the specified criteria'
                }, 404)
                return response
            query = Select(Grade).where(Grade.subject_id == subject.id, Grade.parent_id == parent_id)
            query = query.where(func.lower(Grade.name).startswith(name))
            grades = (await session.execute(query.order_by(Grade.modified_at.desc()))).scalars().all()
            await log(request, 200, 'info', 'Grades Retrieved Successfully.', {'filters': dict(data), 'count': len(grades)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Grades retrieved successfully',
                'data': [g.min_to_dict() for g in grades]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Grades.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting grades'
        }, 500)
        return response

@admin_prefix.get('/grades/{grade_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Grades'])
async def get_grade(request: Request, grade_id: int):
    """
    This route is used to get a specific grade by its ID.
    It will return the grade data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            grade = (await session.execute(Select(Grade).where(Grade.id == grade_id).options(
                selectinload(Grade.author),
                selectinload(Grade.subject),
                selectinload(Grade.parent)
            ))).scalar_one_or_none()
            if not grade:
                await log(request, 404, 'warning', 'Grade Not Found.', {'grade_id': grade_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Grade not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Grade Retrieved Successfully.', {'grade': grade.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Grade retrieved successfully',
                'data': grade.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Grade.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting grade'
        }, 500)
        return response

@admin_prefix.post('/tasks')
@rate_limit
@is_logged_in
@is_authorized(['Add Tasks'])
@is_ready
async def create_task(request: Request):
    """
    This route is used to create a new task.
    It will return the created task data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Task Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    deadline = data.get('deadline', '').strip()
    subject_id = data.get('subject_id', None) # Subject ID
    urls = data.get('urls', [])  # List of Attached Files
    links = data.get('links', [])  # List of Attached Links
    if not title or title == '' or not deadline or deadline == '' or not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(request, 400, 'warning', 'Missing Required Fields for Task Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    try:
        deadline_date = datetime.fromisoformat(deadline).replace(microsecond=0,tzinfo=cairo_tz) if (deadline and deadline !=
                                                                                             '') else \
            None
        due_date = deadline_date.date()
    except ValueError:
        await log(request, 400, 'warning', 'Invalid Deadline Format Provided for Task Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid deadline format. Please provide a valid date.'
        }, 400)
        return response
    if deadline_date and deadline_date <= datetime.now(cairo_tz):
        await log(request, 400, 'warning', 'Past Deadline Provided for Task Creation.', {'data': dict(data)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Deadline must be a future date.'
        }, 400)
        return response
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(request, 400, 'warning', 'Invalid Data Type for URLs or Links Provided for Task Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided for files or links'
        }, 400)
        return response
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(request, 400, 'warning', 'Invalid File URL in URLs List Provided for Task Creation.', {'data': dict(data), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid File provided"
            }, 400)
            return response
        file = await get_file_from_drive(url, current_user.google_refresh_token, request)
        if not file:
            await log(request, 400, 'warning', 'Invalid File URL in URLs List Provided for Task Creation.', {'data': dict(data), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid File provided"
            }, 400)
            return response
        if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
            await log(request, 400, 'warning', 'Unsupported File Type in URLs List Provided for Task Creation.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
            }, 400)
            return response
        files.append(file)
    for link in links:
        if not is_valid_url(link):
            await log(request, 400, 'warning', 'Invalid Link URL in Links List Provided for Task Creation.', {'data': dict(data), 'invalid_link': link},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid Link provided"
            }, 400)
            return response
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == current_user.faculty_id))).scalar_one_or_none()
            department = (await session.execute(Select(Department).where(Department.id == current_user.department_id))).scalar_one_or_none()
            year = (await session.execute(Select(Year).where(Year.id == current_user.year_id))).scalar_one_or_none()
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to User\'s Faculty, Department, or Year for Task Creation.', {'subject_id': subject_id, 'faculty_id': current_user.faculty_id, 'department_id': current_user.department_id, 'year_id': current_user.year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in your criteria'
                }, 404)
                return response
            task = Task(
                name=title,
                urls=urls if urls and len(urls) > 0 else [],
                links=links if links and len(links) > 0 else [],
                type='task',
                year=year,
                faculty=faculty,
                department=department,
                details={
                    'description': description if description and description != '' else None,
                    'files_data': [get_file_data(f) for f in files] if files and len(files) > 0 else []
                },
                deadline=deadline_date,
                due_date=due_date,
                subject=subject,
                author=current_user,
            )
            session.add(task)
            await session.commit()
            await log(request, 201, 'info', 'Task Created Successfully.', {'task': task.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Task created successfully',
                'data': task.min_to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Task.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating task'
            }, 500)
            return response

@admin_prefix.patch('/tasks/{task_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Tasks'])
@is_ready
async def update_task(request: Request, task_id: int):
    """
    This route is used to update an existing task.
    It will return the updated task data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Task Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    deadline = data.get('deadline', '').strip()
    subject_id = data.get('subject_id', None) # Subject ID
    urls = data.get('urls', [])  # List of Attached Files
    links = data.get('links', [])  # List of Attached Links
    if not title or title == '' or not deadline or deadline == '' or not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(request, 400, 'warning', 'Missing Required Fields for Task Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    if deadline and deadline != '':
        try:
            deadline_date = datetime.fromisoformat(deadline).replace(microsecond=0,tzinfo=cairo_tz)
            due_date = deadline_date.date()
        except ValueError:
            await log(request, 400, 'warning', 'Invalid Deadline Format Provided for Task Update.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid deadline format. Please provide a valid date.'
            }, 400)
            return response
        if deadline_date <= datetime.now(cairo_tz):
            await log(request, 400, 'warning', 'Past Deadline Provided for Task Update.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Deadline must be a future date.'
            }, 400)
            return response
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(request, 400, 'warning', 'Invalid Data Type for URLs or Links Provided for Task Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided for files or links'
        }, 400)
        return response
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(request, 400, 'warning', 'Invalid File URL in URLs List Provided for Task Update.', {'data': dict(data), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid File provided"
            }, 400)
            return response
        file = await get_file_from_drive(url, current_user.google_refresh_token, request)
        if not file:
            await log(request, 400, 'warning', 'Invalid File URL in URLs List Provided for Task Update.', {'data': dict(data), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid File provided"
            }, 400)
            return response
        if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
            await log(request, 400, 'warning', 'Unsupported File Type in URLs List Provided for Task Update.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
            }, 400)
            return response
        files.append(file)
    for link in links:
        if not is_valid_url(link):
            await log(request, 400, 'warning', 'Invalid Link URL in Links List Provided for Task Update.', {'data': dict(data), 'invalid_link': link},
                      current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': f"Invalid Link provided"
            }, 400)
            return response
    async with async_session() as session:
        await session.begin()
        try:
            task = (await session.execute(Select(Task).where(Task.id == task_id).options(
                selectinload(Task.author),
                selectinload(Task.subject),
            ))).scalar_one_or_none()
            if not task or task.type == 'exam':
                await log(request, 404, 'warning', 'Task Not Found for Update.', {'task_id': task_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Task not found'
                }, 404)
                return response
            if task.author_id != current_user.id and not 'Manage All Tasks' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Task Update Attempt by Non-Author User.', {'task_id': task_id, 'author_id': task.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to update this task'
                }, 403)
                return response
            task.name = title
            task.deadline = deadline_date
            task.due_date = due_date
            if description and description != '':
                task.details['description'] = description
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Subject Not Found for Task Update.', {'subject_id': subject_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found'
                }, 404)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == current_user.faculty_id))).scalar_one_or_none()
            department = (await session.execute(Select(Department).where(Department.id == current_user.department_id))).scalar_one_or_none()
            year = (await session.execute(Select(Year).where(Year.id == current_user.year_id))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to User\'s Faculty, Department, or Year for Task Update.', {'subject_id': subject_id, 'faculty_id': current_user.faculty_id, 'department_id': current_user.department_id, 'year_id': current_user.year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in your criteria'
                }, 404)
                return response
            task.subject = subject
            task.urls = urls if urls and len(urls) > 0 else []
            task.links = links if links and len(links) > 0 else []
            if files and len(files) > 0:
                task.details['files_data'] = [get_file_data(f) for f in files]
            task.author = current_user  # Update the author to the user who made the update
            await session.commit()
            await log(request, 200, 'info', 'Task Updated Successfully.', {'task': task.min_to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Task updated successfully',
                'data': task.min_to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Task.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating task'
            }, 500)
            return response

@admin_prefix.delete('/tasks/{task_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Tasks'])
@is_ready
async def delete_task(request: Request, task_id: int):
    """
    This route is used to delete an existing task.
    It will return a success message if the task is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    async with async_session() as session:
        await session.begin()
        try:
            task = (await session.execute(Select(Task).where(Task.id == task_id))).scalar_one_or_none()
            if not task or task.type == 'exam':
                await log(request, 404, 'warning', 'Task Not Found for Deletion.', {'task_id': task_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Task not found'
                }, 404)
                return response
            if task.author_id != current_user.id and not 'Manage All Tasks' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Task Deletion Attempt by Non-Author User.', {'task_id': task_id, 'author_id': task.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to delete this task'
                }, 403)
                return response
            await session.delete(task)
            await session.commit()
            await log(request, 200, 'info', 'Task Deleted Successfully.', {'task_id': task_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Task deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Task.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting task'
            }, 500)
            return response

@admin_prefix.get('/tasks')
@rate_limit
@is_logged_in
@is_authorized(['View Tasks'])
@is_ready
async def get_tasks(request: Request):
    """
    This route is used to get all tasks.
    It will return a list of tasks.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Parameters.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip().lower()
        subject_id = data.get('subject_id', None) # Subject ID
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        start_date = data.get('start_date', '').strip()
        end_date = data.get('end_date', '').strip()
        start_date_obj = None
        end_date_obj = None
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
        if start_date and start_date != '':
            try:
                start_date_obj = datetime.fromisoformat(start_date).replace(microsecond=0,tzinfo=cairo_tz).date()
            except ValueError:
                await log(request, 400, 'warning', 'Invalid Start Date Format Provided for Getting Tasks.', {'data': dict(data)}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Invalid start date format. Please provide a valid date.'
                }, 400)
                return response
        if end_date and end_date!= '':
            try:
                end_date_obj = datetime.fromisoformat(end_date).replace(microsecond=0,tzinfo=cairo_tz).date()
            except ValueError:
                await log(request, 400, 'warning', 'Invalid End Date Format Provided for Getting Tasks.', {'data': dict(data)}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Invalid end date format. Please provide a valid date.'
                }, 400)
                return response
        if subject_id and (not is_int(subject_id) or int(subject_id) < 1) or faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided in The Request Query Parameters for Getting Tasks.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        if faculty_id and 'Access All Faculties' not in user_permissions or department_id and 'Access All Departments' not in user_permissions or year_id and 'Access All Years' not in user_permissions:
            await log(request, 403, 'warning', 'Unauthorized Access Attempt to Restricted Faculty, Department, or Year for Getting Tasks.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'You are not authorized to access the specified criteria'
            }, 403)
            return response
        async with async_session() as session:
            query = Select(Task).options(selectinload(Task.subject)).where(Task.type != 'exam')
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for Getting Tasks.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
                query = query.where(Task.faculty_id == faculty.id)
            if department_id:
                department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
                if not department or (faculty_id and department.faculty_id != faculty.id):
                    await log(request, 404, 'warning', 'Department Not Found or Does Not Belong to Specified Faculty for Getting Tasks.', {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department not found in the specified faculty'
                    }, 404)
                    return response
                query = query.where(Task.department_id == department.id)
            if year_id:
                year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
                if not year:
                    await log(request, 404, 'warning', 'Year Not Found for Getting Tasks.', {'year_id': year_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Year not found'
                    }, 404)
                    return response
                query = query.where(Task.year_id == year.id)
            if subject_id:
                subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
                if not subject:
                    await log(request, 404, 'warning', 'Subject Not Found for Getting Tasks.', {'subject_id': subject_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Subject not found'
                    }, 404)
                    return response
                query = query.where(Task.subject_id == subject.id)
            if start_date_obj:
                query = query.where(Task.due_date >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.due_date <= end_date_obj)
            if name and name != '':
                query = query.where(func.lower(Task.name).startswith(name))
            tasks = (await session.execute(query.order_by((Task.deadline >= func.now()).desc(), Task.deadline.asc()))).scalars().all()
            await log(request, 200, 'info', 'Tasks Retrieved Successfully.', {'filters': dict(data), 'count': len(tasks)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Tasks retrieved successfully',
                'data': [t.min_to_dict() for t in tasks]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Tasks.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting tasks'
        }, 500)
        return response

@admin_prefix.get('/tasks/{task_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Tasks'])
@is_ready
async def get_task(request: Request, task_id: int):
    """
    This route is used to get a specific task by its ID.
    It will return the task data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            task = (await session.execute(Select(Task).where(Task.id == task_id).options(
                selectinload(Task.author),
                selectinload(Task.subject),
                selectinload(Task.faculty),
                selectinload(Task.department),
                selectinload(Task.year),
            ))).scalar_one_or_none()
            if not task or task.type == 'exam':
                await log(request, 404, 'warning', 'Task Not Found.', {'task_id': task_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Task not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Task Retrieved Successfully.', {'task': task.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Task retrieved successfully',
                'data': task.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Task.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting task'
        }, 500)
        return response

@admin_prefix.post('/exams')
@rate_limit
@is_logged_in
@is_authorized(['Add Exams'])
@is_ready
async def create_exam(request: Request):
    """
    This route is used to create a new exam.
    It will return the created exam data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Exam Creation.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    instructions = data.get('instructions', '').strip()
    due_date = data.get('due_date', '').strip()
    start_time = data.get('start_time', '').strip()
    location = data.get('location', '').strip()
    duration = data.get('duration', '').strip()
    exam_type = data.get('exam_type', '').strip().title()
    exam_format = data.get('exam_format', '').strip()
    exam_weight = data.get('exam_weight', '').strip()
    subject_id = data.get('subject_id', None) # Subject ID
    if (not title or title == '' or not due_date or due_date == '' or not exam_type or exam_type == '' or not
    start_time or start_time == '' or
            not subject_id
        or not is_int(subject_id) or int(subject_id) < 1):
        await log(request, 400, 'warning', 'Missing Required Fields for Exam Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    try:
        due_date = datetime.fromisoformat(due_date).replace(tzinfo=cairo_tz).date() if (due_date and due_date != '') else None
        deadline_date = datetime.fromisoformat(f"{due_date}T{start_time}").replace(microsecond=0,tzinfo=cairo_tz) if (due_date and due_date != '' and start_time and start_time != '') else None
    except ValueError:
        await log(request, 400, 'warning', 'Invalid Deadline Format Provided for Exam Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid date format or start time format. Please provide a valid date and start time.'
        }, 400)
        return response
    if deadline_date and deadline_date <= datetime.now(cairo_tz):
        await log(request, 400, 'warning', 'Past Deadline Provided for Exam Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Exam Date must be a future date.'
        }, 400)
        return response
    if duration and (not is_float(duration) or float(duration) < 0):
        await log(request, 400, 'warning', 'Invalid Duration Provided for Exam Creation.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid duration provided'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == current_user.faculty_id))).scalar_one_or_none()
            department = (await session.execute(Select(Department).where(Department.id == current_user.department_id))).scalar_one_or_none()
            year = (await session.execute(Select(Year).where(Year.id == current_user.year_id))).scalar_one_or_none()
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to User\'s Faculty, Department, or Year for Exam Creation.', {'subject_id': subject_id, 'faculty_id': current_user.faculty_id, 'department_id': current_user.department_id, 'year_id': current_user.year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in your criteria'
                }, 404)
                return response
            exam = Task(
                name=title,
                type='exam',
                year=year,
                faculty=faculty,
                department=department,
                details={
                    'description': description if description and description != '' else None,
                    'instructions': instructions if instructions and instructions != '' else None,
                    'location': location if location and location != '' else None,
                    'exam_type': exam_type if exam_type and exam_type != '' else None,
                    'exam_format': exam_format if exam_format and exam_format != '' else None,
                    'exam_weight': exam_weight if exam_weight and exam_weight != '' else None,
                    'duration': float(duration) if duration and is_float(duration) and float(duration) > 0 else None,
                },
                deadline=deadline_date,
                due_date=due_date,
                subject=subject,
                author=current_user,
            )
            session.add(exam)
            await session.commit()
            await log(request, 201, 'info', 'Exam Created Successfully.', {'exam': exam.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Exam created successfully',
                'data': exam.min_to_dict()
            }, 201)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Creating Exam.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while creating exam'
            }, 500)
            return response

@admin_prefix.patch('/exams/{exam_id}')
@rate_limit
@is_logged_in
@is_authorized(['Edit Exams'])
@is_ready
async def update_exam(request: Request, exam_id: int):
    """
    This route is used to update an existing exam.
    It will return the updated exam data.
    """
    current_user = request.state.current_user
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Exam Update.', {}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Empty Request was sent. Please provide data correctly.'
        }, 400)
        return response
    if not is_sanitized(data):
        await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Body.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid data provided'
        }, 400)
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    instructions = data.get('instructions', '').strip()
    due_date = data.get('due_date', '').strip()
    start_time = data.get('start_time', '').strip()
    location = data.get('location', '').strip()
    duration = data.get('duration', '').strip()
    exam_type = data.get('exam_type', '').strip().title()
    exam_format = data.get('exam_format', '').strip()
    exam_weight = data.get('exam_weight', '').strip()
    subject_id = data.get('subject_id', None) # Subject ID
    if (not title or title == '' or not due_date or due_date == '' or not exam_type or exam_type == '' or not
    start_time or start_time == '' or
            not subject_id
        or not is_int(subject_id) or int(subject_id) < 1):
        await log(request, 400, 'warning', 'Missing Required Fields for Exam Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return response
    try:
        due_date = datetime.fromisoformat(due_date).replace(tzinfo=cairo_tz).date() if (due_date and due_date != '') else None
        deadline_date = datetime.fromisoformat(f"{due_date}T{start_time}").replace(microsecond=0,tzinfo=cairo_tz) if (due_date and due_date != '' and start_time and start_time != '') else None
    except ValueError:
        await log(request, 400, 'warning', 'Invalid Deadline Format Provided for Exam Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid date format or start time format. Please provide a valid date and start time.'
        }, 400)
        return response
    if deadline_date and deadline_date <= datetime.now(cairo_tz):
        await log(request, 400, 'warning', 'Past Deadline Provided for Exam Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Exam Date must be a future date.'
        }, 400)
        return response
    if duration and (not is_float(duration) or float(duration) < 0):
        await log(request, 400, 'warning', 'Invalid Duration Provided for Exam Update.', {'data': dict(data)},
                  current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'Invalid duration provided'
        }, 400)
        return response
    async with async_session() as session:
        await session.begin()
        try:
            exam = (await session.execute(Select(Task).where(Task.id == exam_id).options(
                selectinload(Task.author),
                selectinload(Task.subject),
            ))).scalar_one_or_none()
            if not exam or exam.type != 'exam':
                await log(request, 404, 'warning', 'Exam Not Found for Update.', {'exam_id': exam_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Exam not found'
                }, 404)
                return response
            if exam.author_id != current_user.id and not 'Manage All Exams' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Exam Update Attempt by Non-Author User.', {'exam_id': exam_id, 'author_id': exam.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to update this exam'
                }, 403)
                return response
            exam.name = title
            exam.deadline = deadline_date
            exam.due_date = due_date
            if description and description != '':
                exam.details['description'] = description
            if instructions and instructions != '':
                exam.details['instructions'] = instructions
            if location and location != '':
                exam.details['location'] = location
            if duration and is_float(duration) and float(duration) > 0:
                exam.details['duration'] = float(duration)
            if exam_format and exam_format != '':
                exam.details['exam_format'] = exam_format
            else:
                exam.details['exam_format'] = None
            if exam_weight and exam_weight != '':
                exam.details['exam_weight'] = exam_weight
            else:
                exam.details['exam_weight'] = None
            if exam_type and exam_type != '':
                exam.details['exam_type'] = exam_type
            else:
                exam.details['exam_type'] = None
            subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
            if not subject:
                await log(request, 404, 'warning', 'Subject Not Found for Exam Update.', {'subject_id': subject_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found'
                }, 404)
                return response
            faculty = (await session.execute(Select(Faculty).where(Faculty.id == current_user.faculty_id))).scalar_one_or_none()
            department = (await session.execute(Select(Department).where(Department.id == current_user.department_id))).scalar_one_or_none()
            year = (await session.execute(Select(Year).where(Year.id == current_user.year_id))).scalar_one_or_none()
            if not subject or subject.faculty_id != faculty or subject.department_id != department or subject.year_id != year:
                await log(request, 404, 'warning', 'Subject Not Found or Does Not Belong to User\'s Faculty, Department, or Year for Exam Update.', {'subject_id': subject_id, 'faculty_id': current_user.faculty_id, 'department_id': current_user.department_id, 'year_id': current_user.year_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Subject not found in your criteria'
                }, 404)
                return response
            exam.subject = subject
            exam.author = current_user  # Update the author to the user who made the update
            await session.commit()
            await log(request, 200, 'info', 'Exam Updated Successfully.', {'exam': exam.min_to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Exam updated successfully',
                'data': exam.min_to_dict()
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Updating Exam.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while updating exam'
            }, 500)
            return response

@admin_prefix.delete('/exams/{exam_id}')
@rate_limit
@is_logged_in
@is_authorized(['Delete Exams'])
@is_ready
async def delete_exam(request: Request, exam_id: int):
    """
    This route is used to delete an existing exam.
    It will return a success message if the exam is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
    async with async_session() as session:
        await session.begin()
        try:
            exam = (await session.execute(Select(Task).where(Task.id == exam_id))).scalar_one_or_none()
            if not exam or exam.type != 'exam':
                await log(request, 404, 'warning', 'Exam Not Found for Deletion.', {'exam_id': exam_id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Exam not found'
                }, 404)
                return response
            if exam.author_id != current_user.id and not 'Manage All Tasks' in permissions:
                await log(request, 403, 'warning', 'Unauthorized Exam Deletion Attempt by Non-Author User.', {'exam_id': exam_id, 'author_id': exam.author.id}, current_user.id)
                await session.rollback()
                response = JSONResponse({
                    'status': 'error',
                    'message': 'You are not authorized to delete this exam'
                }, 403)
                return response
            await session.delete(exam)
            await session.commit()
            await log(request, 200, 'info', 'Exam Deleted Successfully.', {'exam_id': exam_id}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Exam deleted successfully'
            }, 200)
            return response
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Deleting Exam.', {'error': str(e)}, current_user.id)
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while deleting exam'
            }, 500)
            return response

@admin_prefix.get('/exams')
@rate_limit
@is_logged_in
@is_authorized(['View Exams'])
@is_ready
async def get_exams(request: Request):
    """
    This route is used to get all exams.
    It will return a list of exams.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(request, 400, 'warning', 'Un Sanitized Data Provided in The Request Query Parameters.', {})
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return finalize_request(response)
        name = data.get('name', '').strip().lower()
        subject_id = data.get('subject_id', None) # Subject ID
        faculty_id = data.get('faculty_id', None)
        department_id = data.get('department_id', None)
        year_id = data.get('year_id', None)
        start_date = data.get('start_date', '').strip()
        end_date = data.get('end_date', '').strip()
        start_date_obj = None
        end_date_obj = None
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get('data', [])
        if start_date and start_date != '':
            try:
                start_date_obj = datetime.fromisoformat(start_date).replace(microsecond=0,tzinfo=cairo_tz).date()
            except ValueError:
                await log(request, 400, 'warning', 'Invalid Start Date Format Provided for Getting Exams.', {'data': dict(data)}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Invalid start date format. Please provide a valid date.'
                }, 400)
                return response
        if end_date and end_date!= '':
            try:
                end_date_obj = datetime.fromisoformat(end_date).replace(microsecond=0,tzinfo=cairo_tz).date()
            except ValueError:
                await log(request, 400, 'warning', 'Invalid End Date Format Provided for Getting Exams.', {'data': dict(data)}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Invalid end date format. Please provide a valid date.'
                }, 400)
                return response
        if subject_id and (not is_int(subject_id) or int(subject_id) < 1) or faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1) or department_id and (not is_int(department_id) or int(department_id) < 1) or year_id and (not is_int(year_id) or int(year_id) < 1):
            await log(request, 400, 'warning', 'Invalid Data Provided in The Request Query Parameters for Getting Exams.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            }, 400)
            return response
        if faculty_id and 'Access All Faculties' not in user_permissions or department_id and 'Access All Departments' not in user_permissions or year_id and 'Access All Years' not in user_permissions:
            await log(request, 403, 'warning', 'Unauthorized Access Attempt to Restricted Faculty, Department, or Year for Getting Exams.', {'data': dict(data)}, current_user.id)
            response = JSONResponse({
                'status': 'error',
                'message': 'You are not authorized to access the specified criteria'
            }, 403)
            return response
        async with async_session() as session:
            query = Select(Task).options(selectinload(Task.subject)).where(Task.type == 'exam')
            if faculty_id:
                faculty = (await session.execute(Select(Faculty).where(Faculty.id == int(faculty_id)))).scalar_one_or_none()
                if not faculty:
                    await log(request, 404, 'warning', 'Faculty Not Found for Getting Exams.', {'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Faculty not found'
                    }, 404)
                    return response
                query = query.where(Task.faculty_id == faculty.id)
            if department_id:
                department = (await session.execute(Select(Department).where(Department.id == int(department_id)))).scalar_one_or_none()
                if not department or (faculty_id and department.faculty_id != faculty.id):
                    await log(request, 404, 'warning', 'Department Not Found or Does Not Belong to Specified Faculty for Getting Exams.', {'department_id': department_id, 'faculty_id': faculty_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Department not found in the specified faculty'
                    }, 404)
                    return response
                query = query.where(Task.department_id == department.id)
            if year_id:
                year = (await session.execute(Select(Year).where(Year.id == int(year_id)))).scalar_one_or_none()
                if not year:
                    await log(request, 404, 'warning', 'Year Not Found for Getting Exams.', {'year_id': year_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Year not found'
                    }, 404)
                    return response
                query = query.where(Task.year_id == year.id)
            if subject_id:
                subject = (await session.execute(Select(Subject).where(Subject.id == int(subject_id)))).scalar_one_or_none()
                if not subject:
                    await log(request, 404, 'warning', 'Subject Not Found for Getting Exams.', {'subject_id': subject_id}, current_user.id)
                    response = JSONResponse({
                        'status': 'error',
                        'message': 'Subject not found'
                    }, 404)
                    return response
                query = query.where(Task.subject_id == subject.id)
            if start_date_obj:
                query = query.where(Task.due_date >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.due_date <= end_date_obj)
            if name and name != '':
                query = query.where(func.lower(Task.name).startswith(name))
            exams = (await session.execute(query.order_by((Task.deadline >= func.now()).desc(), Task.deadline.asc()))).scalars().all()
            await log(request, 200, 'info', 'Exams Retrieved Successfully.', {'filters': dict(data), 'count': len(exams)}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Exams retrieved successfully',
                'data': [e.min_to_dict() for e in exams]
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Exams.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting exams'
        }, 500)
        return response

@admin_prefix.get('/exams/{exam_id}')
@rate_limit
@is_logged_in
@is_authorized(['View Exams'])
@is_ready
async def get_exam(request: Request, exam_id: int):
    """
    This route is used to get a specific exam by its ID.
    It will return the exam data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            exam = (await session.execute(Select(Task).where(Task.id == exam_id).options(
                selectinload(Task.author),
                selectinload(Task.subject),
                selectinload(Task.faculty),
                selectinload(Task.department),
                selectinload(Task.year),
            ))).scalar_one_or_none()
            if not exam or exam.type != 'exam':
                await log(request, 404, 'warning', 'Exam Not Found.', {'exam_id': exam_id}, current_user.id)
                response = JSONResponse({
                    'status': 'error',
                    'message': 'Exam not found'
                }, 404)
                return response
            await log(request, 200, 'info', 'Exam Retrieved Successfully.', {'exam': exam.to_dict()}, current_user.id)
            response = JSONResponse({
                'status': 'success',
                'message': 'Exam retrieved successfully',
                'data': exam.to_dict()
            }, 200)
            return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Getting Exam.', {'error': str(e)}, current_user.id)
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while getting exam'
        }, 500)
        return response

# Public Routes
@v1.post('/contact-us')
@rate_limit
async def contact_us(request: Request):
    data = await request.form()
    if not data:
        await log(request, 400, 'warning', 'No Data Provided for Contact Us.', {})
        response = JSONResponse({
            'status': 'error',
            'message': 'No data provided'
        }, 400)
        return finalize_request(response)
    name = data.get('name').strip()
    email = data.get('email').strip().lower()
    phone = data.get('phone').strip()
    message = data.get('message').strip()
    if not name or not email or not phone or not message:
        await log(request, 400, 'warning', 'Missing Required Fields for Contact Us.', {'data': dict(data)})
        response = JSONResponse({
            'status': 'error',
            'message': 'Please make sure to fill all the required fields'
        }, 400)
        return finalize_request(response)
    message = Message(
        name=name,
        email=email,
        phone=phone,
        content=message,
    )
    async with async_session() as session:
        await session.begin()
        try:
            session.add(message)
            await session.commit()
            await log(request, 201, 'info', 'Contact Us message sent successfully.', {'data': dict(data)})
            response = JSONResponse({
                'status': 'success',
                'message': 'Your message has been sent successfully. We will get back to you soon.'
            }, 201)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500, 'error', 'An Error Occurred while Sending Contact Us message.', {'error': str(e)})
            await session.rollback()
            response = JSONResponse({
                'status': 'error',
                'message': 'An error occurred while sending your message. Please try again later.'
            }, 500)
            return finalize_request(response)

# # For Testing Sending Emails
# @app.get('/send-test-email')
# async def send_test_email(request: Request):
#     email = "mazenmohsen24@gmail.com"
#     name = "Mazen Mohsen"
#     email_sent = await send_email(request, email, 'verify_email', {
#         'name': name,
#         'link': 'https://cu-portal.com',
#     })
#     if email_sent.status_code != 200:
#         response = JSONResponse({
#             'status': 'error',
#             'message': 'An Error Occurred While Trying to Send Email Please Try Again Later.'
#         }, 500)
#         return finalize_request(response)
#     response = JSONResponse({
#         'status': 'success',
#         'message': 'Test email sent successfully'
#     }, 200)

# Views
# Coming from views.py
from views import *


# @app.get('/')
# async def main(request: Request):
#     await updated_roles()
#     async with async_session() as session:
#         # deleted = await session.execute(Delete(User).where(User.id == 1))  # Clear the user with id 1 for testing
#         user = (await session.execute(Select(User).where(or_(User.id == 1, User.id == 2)))).scalars().all()
#         role = (await session.execute(Select(Role).where(Role.name == 'admin'))).scalar_one_or_none()
#         for u in user:
#             if u and role:
#                 u.role = role
#         await session.commit()
#         # purposes
#     return templates.TemplateResponse(
#         'index.html'
#     , {'request': request})
# @app.get('/login')
# async def login(request: Request):
#     """
#     This route is used to render the login page.
#     It will RedirectResponse to the login page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login.html'
#     , {'request': request})
# @app.get('/login_success')
# async def login_success(request: Request):
#     """
#     This route is used to render the login success page.
#     It will RedirectResponse to the login success page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login_success.html',
#         {'request': request}
#     )
# @app.get('/createProfile')
# async def signup_page(request: Request):
#     """
#     This route is used to render the signup page.
#     It will RedirectResponse to the signup page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'createProfile.html',
#         {'request': request}
#     )
# @app.get('/dashboard')
# async def dashboard(request: Request):
#     """
#     This route is used to render the dashboard page.
#     It will RedirectResponse to the dashboard page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'dashboard.html',
#         {'request': request}
#     )
#
# @app.get('/faculties')
# async def faculties(request: Request):
#     """
#     This route is used to render the faculties page.
#     It will RedirectResponse to the faculties page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'faculties.html',
#         {'request': request}
#     )
#
# @app.get('/departments')
# async def departments(request: Request):
#     """
#     This route is used to render the departments page.
#     It will RedirectResponse to the departments page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'departments.html',
#         {'request': request}
#     )
#
# @app.get('/years')
# async def years(request: Request):
#     """
#     This route is used to render the years page.
#     It will RedirectResponse to the years page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'years.html',
#         {'request': request}
#     )

# @app.route(f"{os.environ.get('UPLOAD_PREFIX')}/<filename>')
# async def get_uploaded_file(request: Request, filename):
#     """Endpoint to serve uploaded files"""
#     if not filename:
#         await log(request, request, 400, 'warning', 'No filename provided for file download.', {})
#         response = JSONResponse({
#             'status': 'error',
#             'message': 'No filename provided'
#         }, 400)
#     await log(request, 200, 'info', 'Serving uploaded file.', {'filename': filename, 'url': request.url, 'path': request.path})
#     return send_from_directory(os.environ.get('UPLOAD_FOLDER'), filename)

@app.get('/get-template/{template_name}')
async def get_template(request: Request, template_name: str):
    """Endpoint to serve rendered templates"""
    try:
        return templates.TemplateResponse(
            f"components/{template_name}",
            {"request": request}
        )
        return response
    except Exception as e:
        await log(request, 500, 'error', 'An Error Occurred while Rendering Template.', {'error': str(e), 'template_name': template_name})
        response = JSONResponse({
            'status': 'error',
            'message': 'An error occurred while rendering the template. Please make sure the template exists.'
        }, 500)
        return response







# Register Blueprints with the Flask app
v1.include_router(auth)
v1.include_router(user_prefix)
v1.include_router(admin_prefix)
app.include_router(v1)

# Import remaining models after the route if needed
if __name__ == '__main__':
    # Explicitly push app context when running directly
    # uvicorn.run('app:app', host='0.0.0.0', port=3000, reload=True)
    uvicorn.run('app:app', host='0.0.0.0', port=3000)




# Old Wrappers
from functools import wraps
from fastapi.responses import JSONResponse
import jwt
from datetime import datetime, timedelta

from sqlalchemy.orm import selectinload

from models import ExactRole, Role, User, os, RequestLimit, Department, PendingUser
from extensions import async_session, cairo_tz
from fastapi import Request
from settings import finalize_request, log
from sqlalchemy import select
from sqlalchemy import func
def is_logged_in(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            token = request.headers.get('Authorization').split(' ')[1]
            if not token:
                await log(request, 407,'warning','Expired Access Token Found.')
                raise jwt.ExpiredSignatureError("Token has expired. Please request a refresh request using the refresh token.")
            data = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"])
            if not data:
                await log(request, 401,'warning','Invalid Access Token Found.')
                raise jwt.InvalidTokenError("Invalid Login Session. Please log in to access this resource.")
            if datetime.fromisoformat(data.get('expire_date')) < datetime.now(cairo_tz):
                await log(request, 407,'warning','Expired Access Token Found.',{"user_id": data.get('id')})
                raise jwt.ExpiredSignatureError("Token has expired. Please request a refresh request using the refresh token.")
            async with async_session() as session:
                user = (await session.execute(select(User).where(User.id == data.get('id')).options(
                    selectinload(User.year),
                    # selectinload(User.department).selectinload(Department.faculty),
                    selectinload(User.department),
                    # selectinload(User.role).selectinload(Role.exact_roles),
                    # selectinload(User.role).selectinload(Role.users),
                    selectinload(User.role),
                    selectinload(User.faculty),
                    # selectinload(User.pending_user).selectinload(PendingUser.user),
                    selectinload(User.pending_user),
                    selectinload(User.notifications)))).scalar_one_or_none()
                if not user:
                    await log(request, 401,'warning','User Not Found.',{"user_id": data.get('id')})
                    raise ValueError("User not found. Please log in to access this resource.")
                if not user.google_refresh_token:
                    await log(request, 401,'warning','User Not Logged in With Google.',{"user_id": data.get('id')})
                    raise ValueError("Please log in with Google to Proceed.")
                # kwargs['current_user'] = user
                request.state.current_user = user
        except jwt.ExpiredSignatureError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 407)
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 401)
            return finalize_request(response)
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 401)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500,'error','An Error Occurred While Validating Login Session.',{"error": str(e)})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_not_logged_in(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            token = request.headers.get('Authorization').split(' ')[1] if request.headers and request.headers.get(
                'Authorization', None) else None
            if token:
                payload = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"]) if token else None
                if payload and payload.get('id'):
                    async with async_session() as session:
                        user = (await session.execute(select(User).where(User.id == payload.get('id')))).scalar_one_or_none()
                        if user:
                            await log(request, 401,'warning','User Already Logged In Tries to access Route Requires '
                                                             'No Login Session.', {}, user.id)
                            raise ValueError("You are already logged in. Please log out to access this resource.")
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 401)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500,'error','An Error Occurred While Validating No Login Session.',{"error": str(e)})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_ready(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            user = request.state.current_user if hasattr(request.state, 'current_user') else None
            if not user:
                await log(request, 401,'warning','UnAuthenticated Request Attempted.',{})
                response = JSONResponse({
                    "status": "error",
                    "message": "You are not logged in. Please log in to access this resource."
                }, 401)
                return finalize_request(response)
            async with async_session() as session:
                user_entity = (await session.execute(select(User).where(User.id == user.id).options(
                    selectinload(User.year),
                    selectinload(User.department),
                    selectinload(User.faculty),
                    selectinload(User.subjects)))).scalar_one_or_none()
                if not user_entity:
                    await log(request, 401,'warning','User Not Found.',{"user_id": user.id})
                    raise ValueError("User not found. Please log in to access this resource.")
                if not user_entity.faculty or not user_entity.department or not user_entity.year or len(
                        user_entity.subjects) < 1:
                    await log(request, 403,'warning','User Not Ready to Use the System.',{"user_id": user.id})
                    raise ValueError("Please complete your profile to proceed.")
                if not user_entity.status: # User is not verified yet
                    await log(request, 403,'warning','User Not Verified Yet.',{"user_id": user.id})
                    raise ValueError("Your account is not verified yet. Please wait for an admin to verify your account.")
        except Exception as e:
            await log(request, 500,'error','An Error Occurred While Validating User is Ready or Not.',{"error": str(e)})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_authorized(required_roles):
    """ Decorator Factory to check if the user has the required roles. """
    def decorator(f):
        @wraps(f)
        async def decorated_function(request:Request,*args, **kwargs):
            try:
                user = request.state.current_user if hasattr(request.state, 'current_user') else None
                if not user:
                    await log(request, 401,'warning','UnAuthenticated Request Attempted.',{"required_roles":
                        required_roles})
                    response = JSONResponse({
                        "status": "error",
                        "message": "You are not logged in. Please log in to access this resource."
                    }, 401)
                    return finalize_request(response)
                async with async_session() as session:
                    result = (await session.execute(select(Role).where(Role.id == user.role_id).options(selectinload(
                        Role.exact_roles)))).scalar_one_or_none()
                    roles = result.exact_roles if result else []
                    matched_roles = [role for role in roles if role.name in required_roles]
                    if len(matched_roles) != len(required_roles):
                        await log(request, 403,'warning','Unauthorized Request Attempted.',{"required_roles":
                            required_roles, "user_roles": [role.name for role in roles]}, user.id)
                        response = JSONResponse({
                            "status": "error",
                            "message": "You are not authorized to access this resource."
                        }, 403)
                        return finalize_request(response)
                return await f(request, *args, **kwargs)
            except Exception as e:
                await log(request, 500,'error','An Error Occurred While Validating User Authorization.',{"error": str(e),
                    "required_roles": required_roles})
                response = JSONResponse({
                    "status": "error",
                    "message": "An Error Occurred. Please try again later."
                }, 500)
                return finalize_request(response)
        return decorated_function
    return decorator

def rate_limit(f):
    @wraps(f)
    async def decorated_function(request:Request,*args, **kwargs):
        try:
            ip = request.client.host
            if not ip:
                await log(request, 400,'warning','Invalid Request. No IP Address Found.',{})
                raise ValueError("Invalid Request. Please try again later.")
            async with async_session() as session:
                time_threshold = datetime.now(cairo_tz) - timedelta(minutes=1)
                count_query = select(func.count()).where(
                    RequestLimit.ip == ip,
                    RequestLimit.created_at >= time_threshold
                )
                requests_last_minute = (await session.execute(count_query)).scalar_one()
                threshold = os.environ.get('REQUEST_LIMIT_THRESHOLD')
                if requests_last_minute >= int(threshold):
                    await log(request, 429,'warning','Rate Limit Exceeded.',{"requests_last_minute": requests_last_minute, })
                    session.add(RequestLimit(
                        ip=ip,
                        route=request.url.path,
                        status=False,
                    ))
                    await session.commit()
                    response = JSONResponse({
                        "status": "error",
                        "message": "Please wait a minute before making another request."
                    }, 429)
                    return finalize_request(response)
                new_request = RequestLimit(
                    ip=ip,
                    route=request.url.path,
                )
                session.add(new_request)
                await session.commit()
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 400)
            return finalize_request(response)
        except Exception as e:
            await log(request, 500,'error','An Error Occurred While Validating Rate Limit.',{"error": str(e)})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function