# def is_logged_in(f):
#     @wraps(f)
#     async def decorated_function(request:Request, *args, **kwargs):
#         try:
#             token = request.cookies.get('access_token')
#             refresh_token = request.cookies.get('refresh_token')
#             if not token:
#                 if not refresh_token:
#                     await log(request, 401,'warning','No Access Token Nor Refresh Token Found in The Request Cookies.',{"cookies": request.cookies})
#                     raise ValueError("No Login Session Found. Please log in to access this resource.")
#                 # If refresh token is present, we can assume the user is logged in but needs to refresh
#                 try:
#                     await log(request, 401,'warning','Expired Access Token Found With Valid Refresh Token.',{"cookies":
#                                                                                                   request.cookies},
#                         jwt.decode(refresh_token, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithms=["HS256"]).get('id'))
#                 except Exception as e:
#                     await log(request, 401,'warning','Invalid Refresh Token Found.',{"cookies": request.cookies}, str(e))
#                 raise jwt.ExpiredSignatureError("Token has expired. Please request a refresh request using the refresh token.")
#             data = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"])
#             if not data:
#                 await log(request, 401,'warning','Invalid Access Token Found.',{"cookies": request.cookies})
#                 raise jwt.InvalidTokenError("Invalid Login Session. Please log in to access this resource.")
#             async with async_session() as session:
#                 user = await session.execute(select(User).where(User.id == data.get('id')))
#                 if not user:
#                     await log(request, 401,'warning','User Not Found.',{"cookies": request.cookies, "user_id": data.get('id')})
#                     raise ValueError("User not found. Please log in to access this resource.")
#                 if not user.google_refresh_token:
#                     await log(request, 401,'warning','User Not Logged in With Google.',{"cookies": request.cookies, "user_id": data.get('id')})
#                     raise ValueError("Please log in with Google to Proceed.")
#                 kwargs['current_user'] = user
#         except jwt.ExpiredSignatureError as e:
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=401)
#             return finalize_request(response)
#         except jwt.InvalidTokenError as e:
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=401)
#             return finalize_request(response)
#         except ValueError as e:
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=401)
#             return finalize_request(response)
#         except Exception as e:
#             await log(request, 500,'error','An Error Occurred While Validating Login Session.',{"cookies": request.cookies, "error": str(e)})
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=500)
#             return finalize_request(response)
#         return await f(*args, **kwargs)
#     return decorated_function
# def is_not_logged_in(f):
#     @wraps(f)
#     async def decorated_function(request:Request,*args, **kwargs):
#         try:
#             token = request.cookies.get('access_token')
#             refresh_token = request.cookies.get('refresh_token')
#             if token or refresh_token:
#                 payload = jwt.decode(token, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithms=["HS256"]) if token\
#                     else jwt.decode(refresh_token, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithms=["HS256"])
#                 if payload and payload.get('id'):
#                     async with async_session() as session:
#                         user = await session.execute(select(User).where(User.id == payload.get('id')))
#                         if user:
#                             await log(request, 401,'warning','User Already Logged In Tries to access Route Requires No Login Session.',
#                                 {"cookies": request.cookies}, user.id)
#                             raise ValueError("You are already logged in. Please log out to access this resource.")
#         except ValueError as e:
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=401)
#             return finalize_request(response)
#         except Exception as e:
#             await log(request, 500,'error','An Error Occurred While Validating No Login Session.',{"cookies": request.cookies, "error": str(e)})
#             response = JSONResponse(content={
#                 "status": "error",
#                 "message": str(e)
#             }, status_code=500)
#             return finalize_request(response)
#         return await f(*args, **kwargs)
#     return decorated_function
#
# def is_authorized(required_roles):
#     """ Decorator Factory to check if the user has the required roles. """
#     def decorator(f):
#         @wraps(f)
#         async def decorated_function(request:Request,*args, **kwargs):
#             required_roles = kwargs.get('required_roles')
#             user = kwargs.get('current_user')
#             if not user:
#                 await log(request, 401,'warning','UnAuthenticated Request Attempted.',{"cookies": request.cookies, "required_roles":
#                     required_roles})
#                 response = JSONResponse(content={
#                     "status": "error",
#                     "message": "You are not logged in. Please log in to access this resource."
#                 }, status_code=401)
#                 return finalize_request(response)
#             async with async_session() as session:
#                 result = await session.execute(select(Role).where(Role.id == user.role_id))
#                 roles = result.scalar_one_or_none().exact_roles if result else []
#                 matched_roles = [role for role in roles if role.name in required_roles]
#                 if len(matched_roles) != len(required_roles):
#                     await log(request, 403,'warning','Unauthorized Request Attempted.',{"cookies": request.cookies, "required_roles":
#                         required_roles, "user_roles": [role.name for role in roles]}, user.id)
#                     response = JSONResponse({
#                         "status": "error",
#                         "message": "You are not authorized to access this resource."
#                     }, 403)
#                     return finalize_request(response)
#             return await f(*args, **kwargs)
#         return decorated_function
#     return decorator
#
# def rate_limit(f):
#     @wraps(f)
#     async def decorated_function(request:Request,*args, **kwargs):
#         try:
#             ip = request.client.host
#             if not ip:
#                 await log(request, 400,'warning','Invalid Request. No IP Address Found.',{"request": request})
#                 raise ValueError("Invalid Request. Please try again later.")
#             async with async_session() as session:
#                 time_threshold = datetime.now() - timedelta(minutes=1)
#                 count_query = select(func.count()).where(
#                     RequestLimit.ip == ip,
#                     RequestLimit.created_at >= time_threshold
#                 )
#                 requests_last_minute = (await session.execute(count_query)).scalar_one()
#                 threshold = os.environ.get('REQUEST_LIMIT_THRESHOLD')
#                 if requests_last_minute >= int(threshold):
#                     await log(request, 429,'warning','Rate Limit Exceeded.',{"requests_last_minute": requests_last_minute, "cookies": request.cookies})
#                     session.add(RequestLimit(
#                         ip=ip,
#                         route=request.url.path,
#                         status=False,
#                     ))
#                     await session.commit()
#                     response = JSONResponse({
#                         "status": "error",
#                         "message": "Please wait a minute before making another request."
#                     }, 429)
#                     return finalize_request(response)
#                 new_request = RequestLimit(
#                     ip=ip,
#                     route=request.url.path,
#                 )
#                 session.add(new_request)
#                 await session.commit()
#         except ValueError as e:
#             response = JSONResponse({
#                 "status": "error",
#                 "message": str(e)
#             }, 400)
#             return finalize_request(response)
#         except Exception as e:
#             await log(request, 500,'error','An Error Occurred While Validating Rate Limit.',{"request": request, "error": str(e)})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": str(e)
#             }, 500)
#             return finalize_request(response)
#         return await f(*args, **kwargs)
#     return decorated_function
#
#
#
# tication routes
# @auth.get('/refresh')
# @is_not_logged_in
# @rate_limit
# async def refresh(request: Request):
#     refresh_token = request.cookies.get('refresh_token')
#     if not refresh_token:
#         await log(request, 400, 'warning', 'No Refresh Token Found in The Request Cookies.', {"cookies": request.cookies})
#         return {
#             "status": "error",
#             "message": "You are not logged in. Please log in again."
#         }, 400
#     try:
#         decoded_data = jwt.decode(refresh_token, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithms=["HS256"])
#         if not decoded_data:
#             await log(request, 401, 'warning', 'Invalid Refresh Token Found.', {"cookies": request.cookies})
#             raise jwt.InvalidTokenError("You are not logged in. Please log in again.")
#         user_id = decoded_data.get('id')
#         if not user_id:
#             await log(request, 401, 'warning', 'No User ID Found in the Refresh Token.', {"cookies": request.cookies})
#             raise jwt.InvalidTokenError("You are not logged in. Please log in again.")
#         async with async_session() as session:
#             user = await session.execute(Select(User).where(User.id == user_id)).scalar_one_or_none()
#             if not user:
#                 await log(request, 404, 'warning', 'User Not Found.', {"cookies": request.cookies, "user_id": user_id})
#                 response = JSONResponse(
#                     {
#                         "status": "error",
#                         "message": "User not found"
#                     }, 404
#                 )
#                 return finalize_request(response)
#             expire_date = datetime.fromisoformat(decoded_data.get('expire_date'))
#             payload = {
#                 "id": user.id,
#                 "expire_date": (datetime.now() + timedelta(minutes=access_token_expire_time)).isoformat()
#             }
#             access_token = jwt.encode(payload, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm="HS256")
#             if (expire_date - datetime.now()).days < 7:  # If the refresh token is about to expire in less than 7 days
#                 await log(request, 200, 'info', 'Refreshing Refresh Token for User.', {}, user.id)
#                 refresh_payload = {
#                     "id": user.id,
#                     "expire_date": (datetime.now() + timedelta(days=refresh_token_expire_time)).isoformat()
#                 }
#                 refresh_token = jwt.encode(refresh_payload, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithm="HS256")
#             refresh_expire_date = datetime.fromisoformat(jwt.decode(refresh_token, os.environ.get('REFRESH_TOKEN_SECRET_KEY'),
#                                                        algorithms=[
#                 "HS256"]).get('expire_date'))
#             await log(request, 200, 'info', 'Successfully refreshed tokens for user.', {}, user.id)
#             response = JSONResponse(
#                 {
#                     "status": "success",
#                     "message": "Token refreshed successfully",
#                 }, 200
#             )
#             response.set_cookie(
#                 key='access_token',  # Cookie name
#                 value=access_token,  # JWT or session token
#                 httponly=True,  # Prevent JavaScript access
#                 secure=True,  # Only send over HTTPS
#                 samesite='lax',  # Or 'Strict' for better security
#                 max_age=int(timedelta(minutes=access_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#                 path='/',  # Accessible across all paths
#             )
#             response.set_cookie(
#                 key='refresh_token',  # Cookie name
#                 value=refresh_token,  # JWT or session token
#                 httponly=True,  # Prevent JavaScript access
#                 secure=True,  # Only send over HTTPS
#                 samesite='lax',  # Or 'Strict' for better security
#                 max_age=int((refresh_expire_date - datetime.now()).total_seconds()),  # 1 hour expiration (in seconds)
#                 path='/',  # Accessible across all paths
#             )
#             return finalize_request(response)
#     except jwt.ExpiredSignatureError as e:
#         response = JSONResponse({
#             "status": "error",
#             "message": str(e)
#         }, 407)
#         return finalize_request(response)
#     except jwt.InvalidTokenError as e:
#         response = JSONResponse({
#             "status": "error",
#             "message": str(e)
#         }, 401)
#         return finalize_request(response)
#     except Exception as e:
#         await log(request, 500, 'error', 'An error occurred while refreshing tokens.', {"error": str(e), "cookies": request.cookies})
#         response = JSONResponse({
#             "status": "error",
#             "message": str(e)
#         }, 500)
#         return finalize_request(response)
#
# @auth.post('/signup')
# @is_not_logged_in
# @rate_limit
# async def signup(request: Request):
#     data = await request.form()
#     if not data:
#         await log(request, 400, 'warning', 'No Data Provided for SignUp.', {"request": request})
#         response = JSONResponse({
#             "status": "error",
#             "message": "No data provided"
#         }, 400)
#         return finalize_request(response)
#     name = data.get('name').strip()
#     email = data.get('email').strip().lower()
#     phone = data.get('phone').strip()
#     national_id = data.get('national_id').strip()
#     gender = data.get('gender').strip()
#     agreed = data.get('agreed')
#     if agreed != "on":
#         await log(request, 400, 'warning', 'User did not agree to the terms and conditions.', {"data": data, "request": request})
#         response = JSONResponse({
#             "status": "error",
#             "message": "You must agree to the terms and conditions to sign up"
#         }, 400)
#         return finalize_request(response)
#     manages = {}
#     details = {}
#     google_details_token = request.cookies.get('google_details_token')
#     if not google_details_token:
#         await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {"cookies": request.cookies,
#                                                                                "data": data, "request": request})
#         response = JSONResponse({
#             "status": "error",
#             "message": "You Must Authorize Google Account to Proceed."
#         }, 400)
#         return finalize_request(response)
#     async with async_session() as session:
#         google_details_token = await session.execute(Select(Token).where(Token.token == google_details_token,
#                                                                     Token.expire_at > datetime.now())).scalar_one_or_none()
#         if not google_details_token or not google_details_token.details:
#             await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {"cookies": request.cookies,
#                                                                                    "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "You Must Authorize Google Account to Proceed."
#             }, 400)
#             return finalize_request(response)
#         google_details_token = google_details_token.details
#         if not name or not email or not phone or not national_id or not gender or gender == 'gender':
#             await log(request, 400, 'warning', 'Missing Required Fields for SignUp.', {"data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "Please make sure to fill all the required fields"
#             }, 400)
#             return finalize_request(response)
#         if await session.execute(Select(User).where(User.email == email)).scalar_one_or_none():
#             await log(request, 400, 'warning', 'User Tried to SignUp with Email Already Existing.', {"email": email, "data": data,
#                                                                                     "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "Email already exists"
#             }, 400)
#             return finalize_request(response)
#         if await session.execute(Select(User).where(User.national_id == national_id)).scalar_one_or_none():
#             await log(request, 400, 'warning', 'User Tried to SignUp with National ID Already Existing.', {"national_id": national_id,
#                                                                                               "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "A user with this national ID already exists"
#             }, 400)
#             return finalize_request(response)
#         if await session.execute(Select(User).where(User.phone == phone)).scalar_one_or_none():
#             await log(request, 400, 'warning', 'User Tried to SignUp with Phone Number Already Existing.', {"phone": phone,
#                                                                                               "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "A user with this phone number already exists"
#             }, 400)
#             return finalize_request(response)
#         try:
#             email_info = validate_email(email, check_deliverability=True)
#         except EmailNotValidError as e:
#             await log(request, 400, 'warning', 'Invalid Email Address Provided for SignUp.', {"email": email, "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": str(e)
#             }, 400)
#             return finalize_request(response)
#         domain = email_info.domain
#         url = None
#         allowed_domains = ['cu.edu.eg', 'stud.cu.edu.eg']
#         if domain not in allowed_domains:
#             url = data.get('url', None).strip() if data.get('url') else None
#             # file = request.files.get('file')
#             # if not file:
#             #     return {
#             #         "status": "error",
#             #         "message": "You must upload your approval img to signup or Use your university email ("
#             #                    "eng-st.cu.edu.eg) instead."
#             #     }, 400
#             # if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
#             #     return {
#             #         "status": "error",
#             #         "message": "File must be an image (png, jpg, jpeg, webp)"
#             #     }, 400
#             # filename = secure_filename(file.filename)
#             # # check file size
#             # if file.content_length > 10 * 1024 * 1024:  # 10 MB limit
#             #     return {
#             #         "status": "error",
#             #         "message": "File size exceeds the limit of 10 MB"
#             #     }, 400
#             # try:
#             #     file.save(os.path.join(os.environ.get('UPLOAD_FOLDER'), filename))
#             # except Exception as e:
#             #     return {
#             #         "status": "error",
#             #         "message": f"Failed to save file: {str(e)}"
#             #     }, 500
#             # url = f"{os.environ.get('UPLOAD_PREFIX')}/{filename}"
#         if url is None and domain not in allowed_domains:
#             await log(request, 400, 'warning', 'User Did not use University email and did not provide approval image for SignUp.',
#                       {"email": email,
#                                                                                            "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "You must Upload Your Approval Image or Use Your University Email (stud.cu.edu.eg) to "
#                            "SignUp."
#             }, 400)
#             return finalize_request(response)
#         status = (url is None)
#         google_user_details = jwt.decode(
#             google_details_token,
#             os.environ.get('GOOGLE_TOKEN_SECRET_KEY'),
#             algorithms=["HS256"]
#         )
#         if not google_user_details:
#             await log(request, 400, 'warning', 'UnAuthorized User With Google Tried to SignUp.', {"cookies": request.cookies,
#                                                                                    "data": data, "request": request})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "You Must Authorize Google Account to Proceed."
#             }, 400)
#             return finalize_request(response)
#         google_user_details = google_user_details.get('google_user_details')
#         token = generate_unique_token(40)
#         payload = {
#             "user" : {
#             "name": name,
#             "email": email,
#             "phone": phone,
#             "national_id": national_id,
#             "gender": gender,
#             "role": 'user',
#             "manages": manages,
#             "details": details,
#             "status": status,
#             "google_id": google_user_details.get('google_id'),
#             "google_name": google_user_details.get('google_name'),
#             "google_email": google_user_details.get('google_email'),
#             "google_avatar": google_user_details.get('google_avatar'),
#             "google_refresh_token": google_user_details.get('google_refresh_token')
#         }
#         }
#         if not status:
#             payload['pending_user'] = {
#                 "url": url
#             }
#         token_user = jwt.encode(payload, os.environ.get('USER_TOKEN_SECRET_KEY'), algorithm="HS256")
#         token_db = Token(
#             token=token,
#             details=token_user,
#             is_valid=True,
#             expire_at=datetime.now() + timedelta(minutes=user_token_expire_time),
#             type=1  # 1 for User signup token
#         )
#         session.add(token_db)
#         await session.commit()
#         await send_email(request, email, 'verify_email', {
#             'name': name,
#             'link': str(request.url_for("verify_email", token=token , _external=True)).replace('http://', 'https://')
#         })
#         response = JSONResponse({
#             "status": "success",
#             "message": "Successfully Created Your Profile. Please Check Your Email to Verify Your Account."
#         }, 201)
#         await log(request, 201, 'info', 'User Signed Up Successfully.', {"data": data, "user":payload.get('user')})
#         return finalize_request(response)
#
# @auth.get('/logout')
# @is_logged_in
# @rate_limit
# async def logout(request: Request,current_user):
#     """
#     This route is used to log out the user.
#     It will clear the session and cookies.
#     """
#     response = JSONResponse(RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=You have "
#                                       f"logged out successfully."))
#     response.set_cookie('access_token', '', expires=0, httponly=True, secure=True, samesite='lax', path='/')
#     response.set_cookie('refresh_token', '', expires=0, httponly=True, secure=True, samesite='lax', path='/')
#     response.set_cookie('google_details_token', '', expires=0, httponly=True, secure=True, samesite='lax', path='/')
#     await log(request, 200, 'info', 'User logged out successfully.', {}, current_user.id)
#     return finalize_request(response)
#
# @app.get('/verify-email')
# @is_not_logged_in
# @rate_limit
# async def verify_email(request: Request):
#     token = request.query_params.get('token')
#     if not token:
#         await log(request, 400, 'warning', 'No Token Provided for Email Verification.', {"request": request})
#         response = JSONResponse(RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
#                                           f"Request. Please try to SignUp Again."))
#         return finalize_request(response)
#     async with async_session() as session:
#         token_db = await session.execute(Select(Token).where(Token.token == token, Token.expire_at > datetime.now(
#
#         ))).scalar_one_or_none()
#         if not token_db or not token_db.details:
#             await log(request, 400, 'warning', 'Invalid or Expired Token Provided for Email Verification.', {"token": token,
#                                                                                                "request": request})
#             response = JSONResponse(RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
#                                               f"Request. Please Try to SignUp Again."))
#             return finalize_request(response)
#         payload = jwt.decode(token_db.details, os.environ.get('USER_TOKEN_SECRET_KEY'), algorithms=["HS256"])
#         user = payload.get('user')
#         if not user:
#             await log(request, 400, 'warning', 'Invalid User Data in Token Provided for Email Verification.', {"token": token,
#                                                                                                  "request": request})
#             response = JSONResponse(RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Invalid "
#                                               f"Request. Please Try to SignUp Again."))
#             return finalize_request(response)
#         user_db = User(
#             name=user.get('name'),
#             email=user.get('email'),
#             phone=user.get('phone'),
#             national_id=user.get('national_id'),
#             gender=user.get('gender'),
#             role=Role.query.filter_by(name=user.get('role')).scalar_one_or_none(),
#             manages=user.get('manages'),
#             details=user.get('details'),
#             status=user.get('status'),
#             google_id=user.get('google_id'),
#             google_name=user.get('google_name'),
#             google_email=user.get('google_email'),
#             google_avatar=user.get('google_avatar'),
#             google_refresh_token=user.get('google_refresh_token'),
#             ips = [request.client.host]  # Store the IP address of the user
#         )
#         pending_user = payload.get('pending_user')
#         pending_user_db = PendingUser(
#             url=pending_user.get('url') if pending_user else None,
#         )
#         session.add(user_db)
#         await session.commit()
#         user = await session.execute(Select(User).where(User.email == user_db.email)).scalar_one_or_none()
#         if pending_user:
#             pending_user_db.user = user
#             session.add(pending_user_db)
#             await session.commit()
#         token_db.expire_at = datetime.now() - timedelta(minutes=1)  # Invalidate the token
#         await session.commit()
#         access_token = jwt.encode({
#             "id": user.id,
#             "expire_date": (datetime.now() + timedelta(minutes=access_token_expire_time)).isoformat()
#         }, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm="HS256")
#         refresh_token = jwt.encode({
#             "id": user.id,
#             "expire_date": (datetime.now() + timedelta(days=refresh_token_expire_time)).isoformat()
#         }, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithm="HS256")
#         response = JSONResponse(
#             RedirectResponse(
#                 f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=Your Account Has Been Verified "
#                 f"Successfully.")
#         )
#         response.set_cookie(
#             key='access_token',  # Cookie name
#             value=access_token,  # JWT or session token
#             httponly=True,  # Prevent JavaScript access
#             secure=True,  # Only send over HTTPS
#             samesite='lax',  # Or 'Strict' for better security
#             max_age=int(timedelta(minutes=access_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#             path='/',  # Accessible across all paths
#         )
#         response.set_cookie(
#             key='refresh_token',  # Cookie name
#             value=refresh_token,  # JWT or session token
#             httponly=True,  # Prevent JavaScript access
#             secure=True,  # Only send over HTTPS
#             samesite='lax',  # Or 'Strict' for better security
#             max_age=int(timedelta(days=refresh_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#             path='/',  # Accessible across all paths
#         )
#         await log(request, 200, 'info', 'User Email Verified and Created Account Successfully.', {}, user.id)
#         return finalize_request(response)
#
# @auth.get('/get-google-stored-token')
# @is_not_logged_in
# @rate_limit
# async def get_google_stored_token(request: Request):
#     """
#     This route is used to get stored google access token from the session.
#     It is used to check if the user is already logged in.
#     """
#     google_details_token = request.cookies.get('google_details_token')
#     if not google_details_token:
#         await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {"cookies": request.cookies})
#         response = JSONResponse({
#             "status": "error",
#             "message": "You Must Authorize Google Account to Proceed."
#         }, 401)
#         return finalize_request(response)
#     async with async_session() as session:
#         token = await session.execute(Select(Token).where(Token.token == google_details_token,
#                                                         Token.expire_at > datetime.now())).scalar_one_or_none()
#         google_details = jwt.decode(token.details, os.environ.get('GOOGLE_TOKEN_SECRET_KEY'), algorithms=["HS256"])
#         if not token or not google_details or not google_details.get('google_user_details'):
#             await log(request, 401, 'warning', 'UnAuthorized User Tried to Get Google Access Token.', {"cookies": request.cookies})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "You Must Authorize Google Account to Proceed."
#             }, 401)
#             return finalize_request(response)
#         google_details = google_details.get('google_user_details')
#         user = await session.execute(Select(User).where(User.google_id == google_details.get('google_id'))).scalar_one_or_none()
#         if not user:
#             await log(request, 404, 'warning', 'User Not Found Tried to Get Google Access Token.', {"google_id": google_details.get(
#                 'google_id'), "google_name": google_details.get('google_name'),"google_email": google_details.get(
#                 'google_email'),"cookies": request.cookies})
#             response = JSONResponse({
#                 "status": "error",
#                 "message": "User not found"
#             }, 404)
#             return finalize_request(response)
#         try:
#             new_token = google.authorize_access_token(
#                 refresh_token=decrypt_data(google_details.get('google_refresh_token')),
#                 grant_type='refresh_token'
#             )
#             # Extract the new access token
#             access_token = new_token['access_token']
#         except Exception as e:
#             await log(request, 500, 'error', 'An Error Occurred while Retrieving Google Access Token.', {"error": str(e), "cookies":
#                 request.cookies}, user.id)
#             response = JSONResponse({
#                 "status": "error",
#                 "message": str(e)
#             }, 500)
#             return finalize_request(response)
#         response = JSONResponse({
#             "status": "success",
#             "message": "Google access token retrieved successfully",
#             "data": {
#                 "access_token": access_token,
#                 "expire_at": new_token['expires_in'],  # seconds until expiration
#             }
#         })
#         await log(request, 200, 'info', 'Google Access Token Retrieved Successfully.', {"google_id": user.google_id, "google_name":
#             user.google_name, "google_email": user.google_email},
#             user.id)
#         return finalize_request(response)
#
# @auth.get('/get-google-access-token')
# @is_logged_in
# @rate_limit
# async def get_google_access_token(request: Request, current_user):
#     """
#     This route is used to get the Google access token for the user.
#     It is used to access Google Drive and other Google services.
#     """
#     try:
#         new_token = google.authorize_access_token(
#             refresh_token=decrypt_data(current_user.google_refresh_token),
#             grant_type='refresh_token'
#         )
#         # Extract the new access token
#         access_token = new_token['access_token']
#         async with async_session() as session:
#             if 'refresh_token' in new_token:
#                 current_user.google_refresh_token = encrypt_data(new_token['refresh_token'])
#                 await session.commit()
#             response = JSONResponse(
#                 {
#                     "status": "success",
#                     "message": "Google access token retrieved successfully",
#                     "data": {
#                         "access_token": access_token,
#                         "expire_at": new_token['expires_in'],  # seconds until expiration
#                     }
#                 }, 200
#             )
#             await log(request, 200, 'info', 'Google Access Token Retrieved Successfully.', {"google_id": current_user.google_id,
#                                                                           "google_name": current_user.google_name,
#                                                                           "google_email": current_user.google_email},
#                 current_user.id)
#             return finalize_request(response)
#     except Exception as e:
#         await log(request, 500, 'error', 'An Error Occurred while Retrieving Google Access Token.', {"error": str(e), "cookies":
#             request.cookies}, current_user.id)
#         response = JSONResponse(
#             {
#                 "status": "error",
#                 "message": str(e)
#             }, 500
#         )
#         return finalize_request(response)
#
# # User routes
# @user_prefix.get('/get-user-data')
# @is_logged_in
# @rate_limit
# async def get_user_data(request: Request, current_user):
#     await log(request, 200, 'info', 'User Data Retrieved Successfully.', {}, current_user.id)
#     response = JSONResponse({
#         "status": "success",
#         "message": "User data retrieved successfully",
#         "data": current_user.to_dict()
#     }, 200)
#     return finalize_request(response)
#
# @app.get('/login-with-google')
# @is_not_logged_in
# @rate_limit
# async def login_with_google(request: Request):
#     redirect_response_url = str(request.url_for('google_authentication_redirect_response', _external=True))
#     redirect_response_url = redirect_response_url.replace('http://', 'https://')  # Ensure the RedirectResponse URI is secure
#     google_client = oauth.create_client('google')
#     await log(request, 200, 'info', 'Redirecting user to Google for authentication.', {"redirect_response_url": redirect_response_url})
#     return google_client.authorize_RedirectResponse(redirect_response_url)
#
# @app.get('/google-authentication-RedirectResponse')
# @is_not_logged_in
# @rate_limit
# async def google_authentication_redirect_response(request: Request):
#     requested_scopes = [
#         'openid',
#         'https://www.googleapis.com/auth/userinfo.email',
#         'https://www.googleapis.com/auth/userinfo.profile',
#         'https://www.googleapis.com/auth/drive',
#         'https://www.googleapis.com/auth/drive.file',
#         'https://www.googleapis.com/auth/drive.metadata'
#     ]
#     token = oauth.google.authorize_access_token()
#     granted_scopes = token.get('scope')
#     un_granted_scopes = [scope for scope in requested_scopes if scope not in granted_scopes]
#     if len(un_granted_scopes) > 0:
#         await log(request, 403, 'warning', 'Google did not grant the requested scopes.',{"un_granted_scopes": un_granted_scopes, "granted_scopes": granted_scopes})
#         un_granted_scopes_short = ', '.join(scope.replace('https://www.googleapis.com/auth/','') for scope in (
#                 un_granted_scopes))
#         response = JSONResponse(RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=Google did not grant the "
#                         f"following scopes: {un_granted_scopes_short}"))
#         return finalize_request(response)
#     user = token['userinfo']
#     google_user_details = {
#         'google_id': user.get('sub'),
#         'google_name': user.get('name'),
#         'google_email': user.get('email'),
#         'google_avatar': user.get('picture'),
#         'google_refresh_token': encrypt_data(token.get('refresh_token'))
#     }
#     async with async_session() as session:
#         user = await session.execute(Select(User).where(User.google_id == google_user_details.get(
#             'google_id'))).scalar_one_or_none()
#         if user:
#             user.ips.append(request.client.host)  if request.client.host not in user.ips else None
#             if len(user.ips) > 3:
#                 await log(request, 403, 'warning', 'User Tried To Associate More Than 3 IPs to His Account.', {"ips": user.ips},
#                     user.id)
#                 response = JSONResponse(
#                     RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?error=true&message=You Can't Associate More than 3 "
#                              f"Devices with Your Account. Please logout from one of your devices and try again.")
#                 )
#                 return finalize_request(response)
#             user.google_refresh_token = google_user_details.get('google_refresh_token')
#             user.google_name = google_user_details.get('google_name')
#             user.google_avatar = google_user_details.get('google_avatar')
#             await session.commit()
#             token = jwt.encode({
#                 "id": user.id,
#                 "expire_date": (datetime.now() + timedelta(minutes=access_token_expire_time)).isoformat()
#             }, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm="HS256")
#             refresh_token = jwt.encode({
#                 "id": user.id,
#                 "expire_date": (datetime.now() + timedelta(days=refresh_token_expire_time)).isoformat()
#             }, os.environ.get('REFRESH_TOKEN_SECRET_KEY'), algorithm="HS256")
#             response = JSONResponse(
#                 RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login?success=true&message=Successfully logged in")
#             )
#             response.set_cookie(
#                 key='access_token',  # Cookie name
#                 value=token,  # JWT or session token
#                 httponly=True,  # Prevent JavaScript access
#                 secure=True,  # Only send over HTTPS
#                 samesite='lax',  # Or 'Strict' for better security
#                 max_age=int(timedelta(minutes=access_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#                 path='/',  # Accessible across all paths
#             )
#             response.set_cookie(
#                 key='refresh_token',  # Cookie name
#                 value=refresh_token,  # JWT or session token
#                 httponly=True,  # Prevent JavaScript access
#                 secure=True,  # Only send over HTTPS
#                 samesite='lax',  # Or 'Strict' for better security
#                 max_age=int(timedelta(days=refresh_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#                 path='/',  # Accessible across all paths
#             )
#             await log(request, 200, 'info', 'User logged in successfully using Google.', {"google_id": user.google_id}, user.id)
#             return finalize_request(response)
#         new_safe_token = generate_unique_token(40)
#         new_safe_token_db = Token(
#             token=new_safe_token,
#             details=jwt.encode({
#                 'google_user_details': google_user_details,
#                 'expire_date': (datetime.now() + timedelta(minutes=google_token_expire_time)).isoformat()
#             }, os.environ.get('GOOGLE_TOKEN_SECRET_KEY'), algorithm="HS256"),
#             is_valid=True,
#             expire_at=datetime.now() + timedelta(minutes=google_token_expire_time),
#             type=0  # 0 for Google login token
#         )
#         session.add(new_safe_token_db)
#         await session.commit()
#         response = JSONResponse(
#             RedirectResponse(f"{os.environ.get("FRONTEND_URL")}/login_success")
#         )
#         response.set_cookie(
#             key='google_details_token',  # Cookie name
#             value=new_safe_token,  # JWT or session token
#             httponly=True,  # Prevent JavaScript access
#             secure=True,  # Only send over HTTPS
#             samesite='lax',  # Or 'Strict' for better security
#             max_age=int(timedelta(minutes=google_token_expire_time).total_seconds()),  # 1 hour expiration (in seconds)
#             path='/',  # Accessible across all paths
#         )
#         await log(request, 200, 'info', 'User Authenticated Google Successfully.', {"google_id": google_user_details.get('google_id')})
#         return finalize_request(response)
