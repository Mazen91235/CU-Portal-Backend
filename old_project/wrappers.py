from functools import wraps
from certifi import where
from fastapi.responses import JSONResponse
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from starlette.responses import RedirectResponse
from models import (Faculty, Year, ExactRole, Role, User, RequestLimit, Department, PendingUser, Roadmap, Subject,
                    Material, Grade, Task, Announcement, Log, UserSubjectLink)
from extensions import async_session, cairo_tz, utc_tz, refresh_token_expire_time, os, load_dotenv
from fastapi import Request
from settings import finalize_request, log
from sqlalchemy import Select
from sqlalchemy import func
import asyncio
load_dotenv()
# utils/crawler_detection.py
def is_crawler(request: Request) -> bool:
    user_agent = request.headers.get('user-agent', '')
    if not user_agent:
        return False

    user_agent_lower = user_agent.lower()
    crawler_keywords = [
        'facebookexternalhit', 'facebookcatalog', 'twitterbot',
        'linkedinbot', 'whatsapp', 'telegrambot', 'discordbot',
        'googlebot', 'bingbot', 'slackbot', 'applebot',
        'baiduspider', 'yandexbot', 'duckduckbot', 'pinterest',
        'slack-imgproxy', 'skypeuripreview', 'mastodon', 'redditbot',
        'iframely', 'embedly', 'bufferbot', 'quora link preview',
        'discordbot', 'telegrambot', 'vkshare', 'w3c_validator'
    ]
    return any(keyword in user_agent_lower for keyword in crawler_keywords)

def is_logged_in(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            authentication_type = os.environ.get("AUTHENTICATION")
            query = Select(User)
            user_id = None
            if authentication_type == "cookies":
                token = request.cookies.get("refresh_token_backend", None) if request.cookies else None
                if not token:
                    await log(request, "Check Logged In API", "User", 407,'warning','Expired Refresh Token Found.')
                    raise jwt.ExpiredSignatureError("Session has expired. Please log in to access this resource.")
                query = query.where(User.refresh_token == token, User.refresh_expire_at > datetime.now(utc_tz))
            else:
                token = request.headers.get("Authorization", "").split(' ')[1] if request.headers.get("Authorization") else None
                if not token:
                    await log(request, "Check Logged In API", "User", 407,'warning','Expired Access Token Found.')
                    raise jwt.ExpiredSignatureError("Token has expired. Please request a refresh request using the refresh token.")
                data = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"])
                if not data:
                    await log(request, "Check Logged In API", "User", 401,'warning','Invalid Access Token Found.')
                    raise jwt.InvalidTokenError("Invalid Login Session. Please log in to access this resource.")
                if datetime.fromisoformat(data.get('expire_date')) < datetime.now(cairo_tz):
                    await log(request, "Check Logged In API", "User", 407,'warning','Expired Access Token Found.',{"user_id": data.get('id')})
                    raise jwt.ExpiredSignatureError("Token has expired. Please request a refresh request using the refresh token.")
                user_id = data.get('id')
                query = query.where(User.id == user_id)
            async with async_session() as session:
                user = (await session.execute(query.options(
                    selectinload(User.year),
                    # selectinload(User.department).selectinload(Department.faculty),
                    selectinload(User.department),
                    # selectinload(User.role).selectinload(Role.exact_roles),
                    # selectinload(User.role).selectinload(Role.users),
                    selectinload(User.role),
                    selectinload(User.faculty),
                    selectinload(User.subjects),
                    # selectinload(User.pending_user).selectinload(PendingUser.user),
                    selectinload(User.pending_user),
                    selectinload(User.notifications)))).scalar_one_or_none()
                if not user:
                    await log(request, "Check Logged In API", "User", 401,'warning','User Not Found.',{"user_id": user_id})
                    raise ValueError("User not found. Please log in to access this resource.")
                if not user.refresh_token or not user.refresh_expire_at or user.refresh_expire_at <= datetime.now(utc_tz):
                    await log(request, "Check Logged In API", "User", 407,'warning','Expired Refresh Token Found.',{"user_id": user_id})
                    raise jwt.ExpiredSignatureError("Session has expired. Please log in to access this resource.")
                if not user.google_refresh_token:
                    await log(request, "Check Logged In API", "User", 401,'warning','User Not Logged in With Google.',{"user_id": user_id})
                    raise ValueError("Please log in with Google to Proceed.")
                if user.refresh_expire_at - datetime.now(utc_tz) < timedelta(days=7):
                    asyncio.create_task(refresh_session(request, user.id))
                # ip = request.client.host
                # if ip and not ip in user.ips:
                #     await log(request, "Check Logged In API", "User", 401,'warning','User is trying to access from an IP not in his devices list.',
                #               {"user_id": user.id, "ip": ip, "ips": user.ips}, user.id)
                #     raise ValueError("This Device is not in your devices list. Please log in from a recognized device.")
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
            await log(request, "Check Logged In API", "User", 500,'error','An Error Occurred While Validating Login Session.',{"error": str(e), "user_id": user_id})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

async def refresh_session(request: Request, user_id):
    async with async_session() as session:
        user = (await session.execute(Select(User).where(User.id == user_id))).scalar_one_or_none()
        if user:
            user.refresh_expire_at = datetime.now(utc_tz) + timedelta(days=refresh_token_expire_time)
            await session.commit()
            await log(request, "Refresh Session", "User", 200,'info','User Session Refreshed Successfully.',{"user_id": user.id})
            return True
        await log(request, "Refresh Session", "User", 404,'warning','User Not Found for Session Refresh.',{"user_id": user_id})
        return False

def is_not_logged_in(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            authentication_type = os.environ.get("AUTHENTICATION")
            query = Select(User)
            if authentication_type == "cookies":
                token = request.cookies.get("refresh_token_backend", None) if request.cookies else None
                query = query.where(User.refresh_token == token, User.refresh_expire_at > datetime.now(utc_tz))
            else:
                token = request.headers.get("Authorization", "").split(' ')[1] if request.headers.get("Authorization") else None
                payload = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"]) if token else None
                query = query.where(User.id == payload.get('id')) if payload else query.where(False)
            async with async_session() as session:
                user = (await session.execute(query)).scalar_one_or_none()
                # ip = request.client.host
                if user:
                    await log(request, "Check Not Logged In API", "User", 401,'warning','User Already Logged In Tries to access Route Requires '
                                                        'No Login Session.', {}, user.id)
                    raise ValueError("You are already logged in. Please log out to access this resource.")
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 401)
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            pass
        except jwt.InvalidTokenError as e:
            pass
        except Exception as e:
            await log(request, "Check Not Logged In API", "User", 500,'error','An Error Occurred While Validating No Login Session.',{"error": str(e)})
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
                await log(request, "Check Ready API", "User", 401,'warning','UnAuthenticated Request Attempted.',{})
                response = JSONResponse({
                    "status": "error",
                    "message": "You are not logged in. Please log in to access this resource."
                }, 401)
                return finalize_request(response)
            if not user.faculty or not user.department or not user.year or not user.type or user.type == '':
                await log(request, "Check Ready API", "User", 403,'warning','User Not Ready to Use the System.',{"user_id": user.id})
                raise ValueError("Please complete your profile to proceed.")
            if not user.status: # User is not verified yet
                await log(request, "Check Ready API", "User", 403,'warning','User Not Verified Yet.',{"user_id": user.id})
                raise ValueError("Your account is not verified yet. Please wait for an admin to verify your account.")
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 403)
            return finalize_request(response)
        except Exception as e:
            await log(request, "Check Ready API", "User", 500,'error','An Error Occurred While Validating User is Ready or Not.',{"error": str(e)})
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
                    await log(request, "Check Authorized API", "User", 401,'warning','UnAuthenticated Request Attempted.',{"required_roles":
                        required_roles})
                    response = JSONResponse({
                        "status": "error",
                        "message": "You are not logged in. Please log in to access this resource."
                    }, 401)
                    return finalize_request(response)
                early_access_required = False
                if "Is Early Access Member" in required_roles:
                    early_access_required = True
                    required_roles.remove("Is Early Access Member")
                async with async_session() as session:
                    result = (await session.execute(Select(Role).where(Role.id == user.role_id).options(selectinload(
                        Role.exact_roles)))).scalar_one_or_none()
                    roles = result.exact_roles if result else []
                    matched_roles = [role for role in roles if role.name in required_roles]
                    if len(matched_roles) != len(required_roles):
                        await log(request, "Check Authorized API", "User", 403,'warning','Unauthorized Request Attempted.',{"required_roles":
                            required_roles, "user_roles": [role.name for role in roles]}, user.id)
                        response = JSONResponse({
                            "status": "error",
                            "message": "You are not authorized to access this resource."
                        }, 403)
                        return finalize_request(response)
                if early_access_required and not user.is_early_access:
                    await log(request, "Check Authorized API", "User", 403,'warning','Unauthorized Request Attempted. User is not Early Access Member.',{"required_roles":
                        required_roles}, user.id)
                    response = JSONResponse({
                        "status": "error",
                        "message": "You are not authorized to access this resource."
                    }, 403)
                    return finalize_request(response)
                return await f(request, *args, **kwargs)
            except Exception as e:
                await log(request, "Check Authorized API", "User", 500,'error','An Error Occurred While Validating User Authorization.',{"error": str(e),
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
            is_testing = os.environ.get("TESTING", "false").lower() == "true"
            if not ip:
                await log(request, "Check RateLimit API", "User", 400,'warning','Invalid Request. No IP Address Found.',{})
                raise ValueError("Invalid Request. Please try again later.")
            if is_testing:
                return await f(request, *args, **kwargs)
            async with async_session() as session:
                time_threshold = datetime.now(cairo_tz) - timedelta(minutes=1)
                count_query = Select(func.count()).where(
                    RequestLimit.ip == ip,
                    RequestLimit.created_at >= time_threshold
                )
                requests_last_minute = (await session.execute(count_query)).scalar_one()
                threshold = os.environ.get('REQUEST_LIMIT_THRESHOLD')
                asyncio.create_task(rate_limit_async(request, ip, request.url.path, requests_last_minute, int(threshold)))
                if requests_last_minute >= int(threshold):
                    response = JSONResponse({
                        "status": "error",
                        "message": "Please wait a minute before making another request."
                    }, 429)
                    return finalize_request(response)
        except ValueError as e:
            response = JSONResponse({
                "status": "error",
                "message": str(e)
            }, 400)
            return finalize_request(response)
        except Exception as e:
            await log(request, "Check RateLimit API", "User", 500,'error','An Error Occurred While Validating Rate Limit.',{"error": str(e)})
            response = JSONResponse({
                "status": "error",
                "message": "An Error Occurred. Please try again later."
            }, 500)
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

async def rate_limit_async(request: Request, ip, route, requests_last_minute, threshold):
    try:
        current_user = request.state.current_user if hasattr(request.state, 'current_user') else None
        async with async_session() as session:
            user_id = current_user.id if current_user else None
            if requests_last_minute >= threshold:
                await log(request, "Check RateLimit API", "User", 429,'warning','Rate Limit Exceeded.',{"requests_last_minute": requests_last_minute, })
                session.add(RequestLimit(
                    ip=ip,
                    route=route,
                    status=False,
                    user_id=user_id
                ))
                await session.commit()
                return True
            new_request = RequestLimit(
                ip=ip,
                route=route,
                status=True,
                user_id=user_id
            )
            session.add(new_request)
            await session.commit()
            return True
    except ValueError as e:
        await log(request, "Check RateLimit API", "User", 400,'warning','Invalid Request. No IP Address Found.',{"error": str(e)})
        return False
    except Exception as e:
        await log(request, "Check RateLimit API", "User", 500,'error','An Error Occurred While Validating Rate Limit.',{"error": str(e)})
        return False

def has_cookies(required_cookies):
    """ Decorator Factory to check if the request has the required cookies. """
    def decorator(f):
        @wraps(f)
        async def decorated_function(request:Request,*args, **kwargs):
            try:
                cookies = request.cookies if request.cookies else {}
                missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
                if missing_cookies:
                    await log(request, "Check Cookies API", "User", 400,'warning','Missing Required Cookies.',{"missing_cookies": missing_cookies})
                    response = JSONResponse({
                        "status": "error",
                        "message": f"Invalid Request."
                    }, 400)
                    return finalize_request(response)
                return await f(request, *args, **kwargs)
            except Exception as e:
                await log(request, "Check Cookies API", "User", 500,'error','An Error Occurred While Validating Required Cookies.',{"error": str(e),
                    "required_cookies": required_cookies})
                response = JSONResponse({
                    "status": "error",
                    "message": "An Error Occurred. Please try again later."
                }, 500)
                return finalize_request(response)
        return decorated_function
    return decorator

def has_registered_subjects(f):
    @wraps(f)
    async def decorated_function(request:Request,*args, **kwargs):
        # try:
        #     user = request.state.current_user if hasattr(request.state, 'current_user') else None
        #     if not user:
        #         await log(request, "Check Registered Subjects API", "User", 401,'warning','UnAuthenticated Request Attempted.',{})
        #         response = JSONResponse({
        #             "status": "error",
        #             "message": "You are not logged in. Please log in to access this resource."
        #         }, 401)
        #         return finalize_request(response)
        #     async with async_session() as session:
        #         user_entity = (await session.execute(Select(User).where(User.id == user.id).options(
        #             selectinload(User.subjects)))).scalar_one_or_none()
        #         if not user_entity:
        #             await log(request, "Check Registered Subjects API", "User", 401,'warning','User Not Found.',{"user_id": user.id})
        #             raise ValueError("User not found. Please log in to access this resource.")
        #         if not user_entity.subjects or len(user_entity.subjects) == 0:
        #             await log(request, "Check Registered Subjects API", "User", 403,'warning','User Has No Registered Subjects.',{"user_id": user.id})
        #             raise ValueError("You have no registered subjects. Please register subjects to proceed.")
        # except ValueError as e:
        #     response = JSONResponse({
        #         "status": "error",
        #         "message": str(e)
        #     }, 403)
        #     return finalize_request(response)
        # except Exception as e:
        #     await log(request, "Check Registered Subjects API", "User", 500,'error','An Error Occurred While Validating User Registered Subjects.',{"error": str(e)})
        #     response = JSONResponse({
        #         "status": "error",
        #         "message": "An Error Occurred. Please try again later."
        #     }, 500)
        #     return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

# Web Decorators

def is_logged_in_web(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            if is_crawler(request):
                return await f(request, *args, **kwargs)
            authentication_type = os.environ.get("AUTHENTICATION")
            if authentication_type == "cookies":
                token = request.cookies.get("refresh_token_backend", None) if request.cookies else None
            else:
                token = request.cookies.get("refresh_token", None) if request.cookies else None
            if not token:
                await log(request, "Check Logged In Web", "User", 407,'warning','Expired Refresh Token Found.')
                raise ValueError("Session has expired. Please log in to access this resource.")
            async with async_session() as session:
                user = (await session.execute(Select(User).where(User.refresh_token == token,
                                                                 User.refresh_expire_at > datetime.now(cairo_tz)).options(
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
                    await log(request, "Check Logged In Web", "User", 401,'warning','User Not Found.',
                              {"user_refresh_token": token})
                    raise ValueError("User not found. Please log in to access this resource.")
                if not user.refresh_token or not user.refresh_expire_at or user.refresh_expire_at.replace(tzinfo=cairo_tz) < datetime.now(cairo_tz):
                    await log(request, "Check Logged In Web", "User", 407,'warning','Expired Refresh Token Found.',{"user_id": user.id})
                    raise ValueError("Session has expired. Please log in to access this resource.")
                if not user.google_refresh_token:
                    await log(request, "Check Logged In Web", "User", 401,'warning','User Not Logged in With '
                                                                                    'Google.',{"user_refresh_token": token})
                    raise ValueError("Please log in with Google to Proceed.")
                # ip = request.client.host
                # if ip and not ip in user.ips:
                #     await log(request, "Check Logged In Web", "User", 401, 'warning', 'User is trying to access from an IP not in his devices list.',
                #               {"user_id": user.id, "ip": ip, "ips": user.ips}, user.id)
                #     raise ValueError("This Device is not in your devices list. Please log in from a recognized device.")
                # kwargs['current_user'] = user
                request.state.current_user = user
        except ValueError as e:
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
            response.set_cookie(
                key="error",
                value=str(e),
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        except Exception as e:
            await log(request, "Check Logged In Web", "User", 500,'error','An Error Occurred While Validating Login Session.',{"error": str(e)})
            response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
            response.set_cookie(
                key="error",
                value="An Error Occurred. Please try again later.",
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_not_logged_in_web(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            if is_crawler(request):
                return await f(request, *args, **kwargs)
            authentication_type = os.environ.get("AUTHENTICATION")
            if authentication_type == "cookies":
                token = request.cookies.get("refresh_token_backend", None) if request.cookies else None
            else:
                token = request.cookies.get("refresh_token", None) if request.cookies else None
            if token:
                async with async_session() as session:
                    user = (await session.execute(Select(User).where(User.refresh_token == token,
                    User.refresh_expire_at > datetime.now(cairo_tz)))).scalar_one_or_none()
                if user:
                    await log(request, "Check Not Logged In Web", "User", 401,'warning','User Already Logged In Tries to access Route Requires '
                                                     'No Login Session.', {}, user.id)
                    raise ValueError("You are already logged in. Please log out to access this resource.")
        except ValueError as e:
            response = RedirectResponse(
                request.headers.get("referer") or
                request.headers.get("referrer") or
                request.query_params.get("next") or
                request.query_params.get("redirect") or
                f"{os.environ.get('FRONTEND_URL')}/user")
            response.set_cookie(
                key="error",
                value=str(e),
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            pass
        except jwt.InvalidTokenError as e:
            pass
        except Exception as e:
            await log(request, "Check Not Logged In Web", "User", 500,'error','An Error Occurred While Validating No Login Session.',{"error": str(e)})
            response = RedirectResponse(
                request.headers.get("referer") or
                request.headers.get("referrer") or
                request.query_params.get("next") or
                request.query_params.get("redirect") or
                f"{os.environ.get('FRONTEND_URL')}/user")
            response.set_cookie(
                key="error",
                value="An Error Occurred. Please try again later.",
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_ready_web(f):
    @wraps(f)
    async def decorated_function(request:Request, *args, **kwargs):
        try:
            if is_crawler(request):
                return await f(request, *args, **kwargs)
            user = request.state.current_user if hasattr(request.state, 'current_user') else None
            if not user:
                await log(request, "Check Ready Web", "User", 401,'warning','UnAuthenticated Request Attempted.',{})
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
                response.set_cookie(
                    key="error",
                    value="You are not logged in. Please log in to access this resource.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
            async with async_session() as session:
                user_entity = (await session.execute(Select(User).where(User.id == user.id).options(
                    selectinload(User.year),
                    selectinload(User.department),
                    selectinload(User.faculty),
                    selectinload(User.subjects)))).scalar_one_or_none()
                if not user_entity:
                    await log(request, "Check Ready Web", "User", 401,'warning','User Not Found.',{"user_id": user.id})
                    raise ValueError("User not found. Please log in to access this resource.")
                if not user_entity.faculty or not user_entity.department or not user_entity.year or not user_entity.type or user_entity.type == '':
                    await log(request, "Check Ready Web", "User", 403,'warning','User Not Ready to Use the System.',{"user_id": user.id})
                    raise ValueError("Please complete your profile to proceed.")
                if not user_entity.status: # User is not verified yet
                    await log(request, "Check Ready Web", "User", 403,'warning','User Not Verified Yet.',{"user_id": user.id})
                    raise ValueError("Your account is not verified yet. Please wait for an admin to verify your account.")
        except ValueError as e:
            if "verified" not in str(e).lower():
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/user/academic_settings")
                response.set_cookie(
                    key="error",
                    value=str(e),
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the profile_settings page only
                )
                return finalize_request(response)
            else:
                response = RedirectResponse(
                    request.headers.get("referer") or
                    request.headers.get("referrer") or
                    request.query_params.get("next") or
                    request.query_params.get("redirect") or
                    f"{os.environ.get('FRONTEND_URL')}/user")
                response.set_cookie(
                    key="error",
                    value=str(e),
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
        except Exception as e:
            await log(request, "Check Ready Web", "User", 500,'error','An Error Occurred While Validating User is Ready or Not.',{"error": str(e)})
            response = RedirectResponse(
                request.headers.get("referer") or
                request.headers.get("referrer") or
                request.query_params.get("next") or
                request.query_params.get("redirect") or
                f"{os.environ.get('FRONTEND_URL')}/user")
            response.set_cookie(
                key="error",
                value="An Error Occurred. Please try again later.",
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def is_authorized_web(required_roles):
    """ Decorator Factory to check if the user has the required roles. """
    def decorator(f):
        @wraps(f)
        async def decorated_function(request:Request,*args, **kwargs):
            try:
                if is_crawler(request):
                    return await f(request, *args, **kwargs)
                user = request.state.current_user if hasattr(request.state, 'current_user') else None
                if not user:
                    await log(request, "Check Authorized Web", "User", 401,'warning','UnAuthenticated Request Attempted.',{"required_roles":
                        required_roles})
                    response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
                    response.set_cookie(
                        key="error",
                        value="You are not logged in. Please log in to access this resource.",
                        httponly=False,
                        secure=True,
                        samesite='lax',
                        path="/"  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
                early_access_required = False
                if "Is Early Access Member" in required_roles:
                    early_access_required = True
                    required_roles.remove("Is Early Access Member")
                async with async_session() as session:
                    result = (await session.execute(Select(Role).where(Role.id == user.role_id).options(selectinload(
                        Role.exact_roles)))).scalar_one_or_none()
                    roles = result.exact_roles if result else []
                    matched_roles = [role for role in roles if role.name in required_roles]
                    if len(matched_roles) != len(required_roles):
                        await log(request, "Check Authorized Web", "User", 403,'warning','Unauthorized Request Attempted.',{"required_roles":
                            required_roles, "user_roles": [role.name for role in roles]}, user.id)
                        response = RedirectResponse(
                            request.headers.get("referer") or
                            request.headers.get("referrer") or
                            request.query_params.get("next") or
                            request.query_params.get("redirect") or
                            f"{os.environ.get('FRONTEND_URL')}/user")
                        response.set_cookie(
                            key="error",
                            value="You are not authorized to access this resource.",
                            httponly=False,
                            secure=True,
                            samesite='lax',
                            path="/" # Cookie is valid for the entire site
                        )
                        return finalize_request(response)
                if early_access_required and not user.is_early_access:
                    await log(request, "Check Authorized Web", "User", 403,'warning','Unauthorized Request Attempted. User is not Early Access Member.',{"required_roles":
                        required_roles}, user.id)
                    response = RedirectResponse(
                        request.headers.get("referer") or
                        request.headers.get("referrer") or
                        request.query_params.get("next") or
                        request.query_params.get("redirect") or
                        f"{os.environ.get('FRONTEND_URL')}/user")
                    response.set_cookie(
                        key="error",
                        value="You are not authorized to access this resource.",
                        httponly=False,
                        secure=True,
                        samesite='lax',
                        path="/"  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
                return await f(request, *args, **kwargs)
            except Exception as e:
                await log(request, "Check Authorized Web", "User", 500,'error','An Error Occurred While Validating User Authorization.',{"error": str(e),
                    "required_roles": required_roles})
                response = RedirectResponse(
                    request.headers.get("referer") or
                    request.headers.get("referrer") or
                    request.query_params.get("next") or
                    request.query_params.get("redirect") or
                    f"{os.environ.get('FRONTEND_URL')}/user")
                response.set_cookie(
                    key="error",
                    value="An Error Occurred. Please try again later.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
        return decorated_function
    return decorator

def has_cookies_web(required_cookies):
    """ Decorator Factory to check if the user has the required cookies. """
    def decorator(f):
        @wraps(f)
        async def decorated_function(request:Request,*args, **kwargs):
            try:
                if is_crawler(request):
                    return await f(request, *args, **kwargs)
                cookies = request.cookies if request.cookies else {}
                missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
                if missing_cookies:
                    await log(request, "Check Has Cookies Web", "User", 400,'warning','Missing Required Cookies.',{"missing_cookies":
                        missing_cookies})
                    response = RedirectResponse(
                        request.headers.get("referer") or
                        request.headers.get("referrer") or
                        request.query_params.get("next") or
                        request.query_params.get("redirect") or
                        f"{os.environ.get('FRONTEND_URL')}/user")
                    response.set_cookie(
                        key="error",
                        value=f"Invalid Request.",
                        httponly=False,
                        secure=True,
                        samesite='lax',
                        path="/"  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
                return await f(request, *args, **kwargs)
            except Exception as e:
                await log(request, "Check Has Cookies Web", "User", 500,'error','An Error Occurred While Validating Required Cookies.',{"error": str(e),
                    "required_cookies": required_cookies})
                response = RedirectResponse(
                    request.headers.get("referer") or
                    request.headers.get("referrer") or
                    request.query_params.get("next") or
                    request.query_params.get("redirect") or
                    f"{os.environ.get('FRONTEND_URL')}/user")
                response.set_cookie(
                    key="error",
                    value="An Error Occurred. Please try again later.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
        return decorated_function
    return decorator

def has_valid_id_web(f):
    @wraps(f)
    async def decorated_function(request:Request,*args, **kwargs):
        try:
            if is_crawler(request):
                return await f(request, *args, **kwargs)
            request_path = request.url.path
            user = request.state.current_user if hasattr(request.state, 'current_user') else None
            if not user:
                await log(request, "Check Valid ID Web", "User", 401,'warning','UnAuthenticated Request Attempted.',{})
                response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
                response.set_cookie(
                    key="error",
                    value="You are not logged in. Please log in to access this resource.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
            if "edit" not in request_path and "details" not in request_path:
                return await f(request, *args, **kwargs)
            id = request.query_params.get('id')
            if not id or not str(id).isdigit() or int(id) < 1:
                await log(request, "Check Valid ID Web", "User", 400,'warning','Invalid ID Provided.',{"id": id})
                response = RedirectResponse(
                    request.headers.get("referer") or
                    request.headers.get("referrer") or
                    request.query_params.get("next") or
                    request.query_params.get("redirect") or
                    f"{os.environ.get('FRONTEND_URL')}/user")
                response.set_cookie(
                    key="error",
                    value="Invalid Request.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
            query = None
            redirect_url = f"{os.environ.get('FRONTEND_URL')}/user" if request_path.startswith("/user") else f"{os.environ.get('FRONTEND_URL')}/admin"
            if "/faculty" in request_path:
                query = Select(Faculty).where(Faculty.id == int(id))
                entity = "Faculty"
                redirect_url += "/faculties"
            elif "/department" in request_path:
                query = Select(Department).where(Department.id == int(id))
                entity = "Department"
                redirect_url += "/departments"
            elif "/year" in request_path:
                query = Select(Year).where(Year.id == int(id))
                entity = "Year"
                redirect_url += "/years"
            elif "/course_map" in request_path:
                query = Select(Roadmap).where(Roadmap.id == int(id), Roadmap.type == 2)
                entity = "Course Map"
                redirect_url += "/course_maps"
            elif "/user" in request_path:
                query = Select(User).where(User.id == int(id))
                entity = "User"
                redirect_url += "/users"
            elif "/role" in request_path:
                query = Select(Role).where(Role.id == int(id))
                entity = "Role"
                redirect_url += "/roles"
            elif "/course" in request_path:
                query = Select(Subject).where(Subject.id == int(id))
                entity = "Course"
                if redirect_url.endswith("/user"):
                    query = query.join(UserSubjectLink).where(UserSubjectLink.user_id == user.id,
                                                              UserSubjectLink.subject_id == int(id))
                redirect_url += "/courses"
            elif "/material" in request_path:
                query = Select(Material).where(Material.id == int(id))
                entity = "Material"
                redirect_url += "/materials"
            elif "/grade" in request_path:
                query = Select(Grade).where(Grade.id == int(id))
                entity = "Grade"
                redirect_url += "/grades"
            elif "/task" in request_path:
                query = Select(Task).where(Task.id == int(id), Task.type != "exam")
                entity = "Task"
                redirect_url += "/tasks"
            elif "/exam" in request_path:
                query = Select(Task).where(Task.id == int(id), Task.type == "exam")
                entity = "Exam"
                redirect_url += "/exams"
            elif "/announcement" in request_path:
                query = Select(Announcement).where(Announcement.id == int(id))
                entity = "Announcement"
                redirect_url += "/announcements"
            elif "/log" in request_path:
                query = Select(Log).where(Log.id == int(id))
                entity = "Log"
                redirect_url += "/logs"
            else:
                await log(request, "Check Valid ID Web", "User", 400,'warning','Invalid Request to Validate ID.',{"path": request_path})
                response = RedirectResponse(
                    request.headers.get("referer") or
                    request.headers.get("referrer") or
                    request.query_params.get("next") or
                    request.query_params.get("redirect") or
                    f"{os.environ.get('FRONTEND_URL')}/user")
                response.set_cookie(
                    key="error",
                    value="Invalid Request.",
                    httponly=False,
                    secure=True,
                    samesite='lax',
                    path="/"  # Cookie is valid for the entire site
                )
                return finalize_request(response)
            async with async_session() as session:
                result = (await session.execute(query)).scalar_one_or_none()
                if not result:
                    await log(request, "Check Valid ID Web", "User", 404,'warning','Entity Not Found with Provided ID.',{"entity": entity, "id": id})
                    response = RedirectResponse(redirect_url)
                    response.set_cookie(
                        key="error",
                        value=f"{entity} not found.",
                        httponly=False,
                        secure=True,
                        samesite='lax',
                        path="/"  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
        except Exception as e:
            await log(request, "Check Valid ID Web", "User", 500,'error','An Error Occurred While Validating ID.',{"error": str(e)})
            response = RedirectResponse(
                request.headers.get("referer") or
                request.headers.get("referrer") or
                request.query_params.get("next") or
                request.query_params.get("redirect") or
                f"{os.environ.get('FRONTEND_URL')}/user")
            response.set_cookie(
                key="error",
                value="An Error Occurred. Please try again later.",
                httponly=False,
                secure=True,
                samesite='lax',
                path="/"  # Cookie is valid for the entire site
            )
            return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function

def has_registered_subjects_web(f):
    @wraps(f)
    async def decorated_function(request:Request,*args, **kwargs):
        # try:
        #     if is_crawler(request):
        #         return await f(request, *args, **kwargs)
        #     user = request.state.current_user if hasattr(request.state, 'current_user') else None
        #     if not user:
        #         await log(request, "Check Registered Subjects Web", "User", 401,'warning','UnAuthenticated Request Attempted.',{})
        #         response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
        #         response.set_cookie(
        #             key="error",
        #             value="You are not logged in. Please log in to access this resource.",
        #             httponly=False,
        #             secure=True,
        #             samesite='lax',
        #             path="/"  # Cookie is valid for the entire site
        #         )
        #         return finalize_request(response)
        #     async with async_session() as session:
        #         user_entity = (await session.execute(Select(User).where(User.id == user.id).options(
        #             selectinload(User.subjects)))).scalar_one_or_none()
        #         if not user_entity:
        #             await log(request, "Check Registered Subjects Web", "User", 401,'warning','User Not Found.',{"user_id": user.id})
        #             raise ValueError("User not found. Please log in to access this resource.")
        #         if not user_entity.subjects or len(user_entity.subjects) == 0:
        #             await log(request, "Check Registered Subjects Web", "User", 403,'warning','User Has No Registered Subjects.',{"user_id": user.id})
        #             raise ValueError("You have no registered subjects. Please register subjects to proceed.")
        # except ValueError as e:
        #     response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/user/academic_settings")
        #     response.set_cookie(
        #         key="error",
        #         value=str(e),
        #         httponly=False,
        #         secure=True,
        #         samesite='lax',
        #         path="/"  # Cookie is valid for the profile_settings page only
        #     )
        #     return finalize_request(response)
        # except Exception as e:
        #     await log(request, "Check Registered Subjects Web", "User", 500,'error','An Error Occurred While Validating User Registered Subjects.',{"error": str(e)})
        #     response = RedirectResponse(
        #         request.headers.get("referer") or
        #         request.headers.get("referrer") or
        #         request.query_params.get("next") or
        #         request.query_params.get("redirect") or
        #         f"{os.environ.get('FRONTEND_URL')}/user")
        #     response.set_cookie(
        #         key="error",
        #         value="An Error Occurred. Please try again later.",
        #         httponly=False,
        #         secure=True,
        #         samesite='lax',
        #         path="/"  # Cookie is valid for the entire site
        #     )
        #     return finalize_request(response)
        return await f(request, *args, **kwargs)
    return decorated_function