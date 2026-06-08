# from app import app, templates, Request, async_session, updated_roles, Select, User, Role, or_, is_logged_in_web, is_not_logged_in_web, is_ready_web, is_authorized_web, has_valid_id_web, has_registered_subjects, has_registered_subjects_web
# @app.get('/create_profile')
# async def create_profile(request: Request):
#     """
#     This route is used to render the create_profile page.
#     It will RedirectResponse to the create_profile page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'create_profile.html'
#         , {'request': request})

# @app.get('/')
# async def main(request: Request):
#     """
#     This route is used to render the index page.
#     It will RedirectResponse to the index page of the frontend.
#     """
#     await updated_roles()
#     async with async_session() as session:
#         # deleted = await session.execute(Delete(User).where(User.id == 1))  # Clear the user with id 1 for testing
#         user = (await session.execute(Select(User).where(or_(User.id == 1, User.id == 2)))).scalars().all()
#         role = (await session.execute(Select(Role).where(Role.name == 'admin'))).scalar_one_or_none()
#         for u in user:
#             if u and role:
#                 u.role = role
#         await session.commit()
#     return templates.TemplateResponse(
#         'index.html'
#         , {'request': request})

# @app.get('/login')
# async def login(request: Request):
#     """
#     This route is used to render the login page.
#     It will RedirectResponse to the login page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login.html'
#         , {'request': request})

# @app.get('/login_success')
# async def login_success(request: Request):
#     """
#     This route is used to render the login_success page.
#     It will RedirectResponse to the login_success page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login_success.html'
#         , {'request': request})

# @app.get('/privacy_policy')
# async def privacy_policy(request: Request):
#     """
#     This route is used to render the privacy_policy page.
#     It will RedirectResponse to the privacy_policy page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'privacy_policy.html'
#         , {'request': request})

# @app.get('/terms_of_service')
# async def terms_of_service(request: Request):
#     """
#     This route is used to render the terms_of_service page.
#     It will RedirectResponse to the terms_of_service page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'terms_of_service.html'
#         , {'request': request})

# @app.get('/verify_email')
# async def verify_email(request: Request):
#     """
#     This route is used to render the verify_email page.
#     It will RedirectResponse to the verify_email page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'verify_email.html'
#         , {'request': request})

# @app.get('/admin/announcements')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @is_authorized_web(['View Announcements'])
# async def admin_announcements(request: Request):
#     """
#     This route is used to render the admin_announcements page.
#     It will RedirectResponse to the admin_announcements page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/announcements.html'
#         , {'request': request})

# @app.get('/admin/announcement_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# @is_authorized_web(['View Announcements'])
# async def admin_announcement_details(request: Request):
#     """
#     This route is used to render the admin_announcement_details page.
#     It will RedirectResponse to the admin_announcement_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/announcement_details.html'
#         , {'request': request})

# @app.get('/admin/courses')
# @is_logged_in_web
# @is_authorized_web(['View Courses'])
# async def admin_courses(request: Request):
#     """
#     This route is used to render the admin_courses page.
#     It will RedirectResponse to the admin_courses page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/courses.html'
#         , {'request': request})

# @app.get('/admin/course_details')
# @is_logged_in_web
# @has_valid_id_web
# async def admin_course_details(request: Request):
#     """
#     This route is used to render the admin_course_details page.
#     It will RedirectResponse to the admin_course_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/course_details.html'
#         , {'request': request})

# @app.get('/admin/course_maps')
# @is_logged_in_web
# @is_authorized_web(['View Course Maps'])
# async def admin_course_maps(request: Request):
#     """
#     This route is used to render the admin_course_maps page.
#     It will RedirectResponse to the admin_course_maps page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/course_maps.html'
#         , {'request': request})

# @app.get('/admin/course_map_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Course Maps'])
# async def admin_course_map_details(request: Request):
#     """
#     This route is used to render the admin_course_map_details page.
#     It will RedirectResponse to the admin_course_map_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/course_map_details.html'
#         , {'request': request})

# @app.get('/admin/create_announcement')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def admin_create_announcement(request: Request):
#     """
#     This route is used to render the admin_create_announcement page.
#     It will RedirectResponse to the admin_create_announcement page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/create_announcement.html'
#         , {'request': request})

# @app.get('/admin/create_course')
# @is_logged_in_web
# @is_authorized_web(['Add Courses'])
# async def admin_create_course(request: Request):
#     """
#     This route is used to render the admin_create_course page.
#     It will RedirectResponse to the admin_create_course page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/create_course.html'
#         , {'request': request})

# @app.get('/admin/create_event')
# @is_logged_in_web
# @is_authorized_web(['Add Events'])
# async def admin_create_event(request: Request):
#     """
#     This route is used to render the admin_create_event page.
#     It will RedirectResponse to the admin_create_event page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/create_event.html'
#         , {'request': request})

# @app.get('/admin/create_exam')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @is_authorized_web(['Add Exams'])
# async def admin_create_exam(request: Request):
#     """
#     This route is used to render the admin_create_exam page.
#     It will RedirectResponse to the admin_create_exam page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/create_exam.html'
#         , {'request': request})

# @app.get('/admin/create_task')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @is_authorized_web(['Add Tasks'])
# async def admin_create_task(request: Request):
#     """
#     This route is used to render the admin_create_task page.
#     It will RedirectResponse to the admin_create_task page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/create_task.html'
#         , {'request': request})

# @app.get('/admin/departments')
# @is_logged_in_web
# @is_authorized_web(['View Departments'])
# async def admin_departments(request: Request):
#     """
#     This route is used to render the admin_departments page.
#     It will RedirectResponse to the admin_departments page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/departments.html'
#         , {'request': request})

# @app.get('/admin/department_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Departments'])
# async def admin_department_details(request: Request):
#     """
#     This route is used to render the admin_department_details page.
#     It will RedirectResponse to the admin_department_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/department_details.html'
#         , {'request': request})

# @app.get('/admin/edit_announcement')
# @is_logged_in_web
# @has_registered_subjects_web
# @has_valid_id_web
# async def admin_edit_announcement(request: Request):
#     """
#     This route is used to render the admin_edit_announcement page.
#     It will RedirectResponse to the admin_edit_announcement page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/edit_announcement.html'
#         , {'request': request})

# @app.get('/admin/edit_course')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['Edit Courses'])
# async def admin_edit_course(request: Request):
#     """
#     This route is used to render the admin_edit_course page.
#     It will RedirectResponse to the admin_edit_course page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/edit_course.html'
#         , {'request': request})

# @app.get('/admin/edit_exam')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# @is_authorized_web(['Edit Exams'])
# async def admin_edit_exam(request: Request):
#     """
#     This route is used to render the admin_edit_exam page.
#     It will RedirectResponse to the admin_edit_exam page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/edit_exam.html'
#         , {'request': request})

# @app.get('/admin/edit_task')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# async def admin_edit_task(request: Request):
#     """
#     This route is used to render the admin_edit_task page.
#     It will RedirectResponse to the admin_edit_task page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/edit_task.html'
#         , {'request': request})

# @app.get('/admin/event_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Events'])
# async def admin_event_details(request: Request):
#     """
#     This route is used to render the admin_event_details page.
#     It will RedirectResponse to the admin_event_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/event_details.html'
#         , {'request': request})

# @app.get('/admin/exams')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @is_authorized_web(['View Exams'])
# async def admin_exams(request: Request):
#     """
#     This route is used to render the admin_exams page.
#     It will RedirectResponse to the admin_exams page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/exams.html'
#         , {'request': request})

# @app.get('/admin/exam_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# @is_authorized_web(['View Exams'])
# async def admin_exam_details(request: Request):
#     """
#     This route is used to render the admin_exam_details page.
#     It will RedirectResponse to the admin_exam_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/exam_details.html'
#         , {'request': request})

# @app.get('/admin/faculties')
# @is_logged_in_web
# @is_authorized_web(['View Faculties'])
# async def admin_faculties(request: Request):
#     """
#     This route is used to render the admin_faculties page.
#     It will RedirectResponse to the admin_faculties page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/faculties.html'
#         , {'request': request})

# @app.get('/admin/grades')
# @is_logged_in_web
# @has_registered_subjects_web
# @is_authorized_web(['View Grades'])
# async def admin_grades(request: Request):
#     """
#     This route is used to render the admin_grades page.
#     It will RedirectResponse to the admin_grades page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/grades.html'
#         , {'request': request})

# @app.get('/admin')
# @is_logged_in_web
# @is_authorized_web(['View Admin Panel'])
# async def admin_main(request: Request):
#     """
#     This route is used to render the admin_index page.
#     It will RedirectResponse to the admin_index page of the frontend.
#     """
#     await updated_roles()
#     async with async_session() as session:
#         # deleted = await session.execute(Delete(User).where(User.id == 1))  # Clear the user with id 1 for testing
#         user = (await session.execute(Select(User).where(or_(User.id == 1, User.id == 2)))).scalars().all()
#         role = (await session.execute(Select(Role).where(Role.name == 'admin'))).scalar_one_or_none()
#         for u in user:
#             if u and role:
#                 u.role = role
#         await session.commit()
#     return templates.TemplateResponse(
#         'admin/index.html'
#         , {'request': request})

# @app.get('/admin/logs')
# @is_logged_in_web
# @is_authorized_web(['View Logs'])
# async def admin_logs(request: Request):
#     """
#     This route is used to render the admin_logs page.
#     It will RedirectResponse to the admin_logs page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/logs.html'
#         , {'request': request})

# @app.get('/admin/log_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Logs'])
# async def admin_log_details(request: Request):
#     """
#     This route is used to render the admin_log_details page.
#     It will RedirectResponse to the admin_log_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/log_details.html'
#         , {'request': request})

# @app.get('/admin/materials')
# @is_logged_in_web
# @has_registered_subjects_web
# @is_authorized_web(['View Materials'])
# async def admin_materials(request: Request):
#     """
#     This route is used to render the admin_materials page.
#     It will RedirectResponse to the admin_materials page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/materials.html'
#         , {'request': request})

# @app.get('/admin/pending_users')
# @is_logged_in_web
# @is_authorized_web(['View Users'])
# async def admin_pending_users(request: Request):
#     """
#     This route is used to render the admin_pending_users page.
#     It will RedirectResponse to the admin_pending_users page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/pending_users.html'
#         , {'request': request})

# @app.get('/admin/roles')
# @is_logged_in_web
# @is_authorized_web(['View Roles'])
# async def admin_roles(request: Request):
#     """
#     This route is used to render the admin_roles page.
#     It will RedirectResponse to the admin_roles page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/roles.html'
#         , {'request': request})

# @app.get('/admin/role_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Roles'])
# async def admin_role_details(request: Request):
#     """
#     This route is used to render the admin_role_details page.
#     It will RedirectResponse to the admin_role_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/role_details.html'
#         , {'request': request})

# @app.get('/admin/tasks')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @is_authorized_web(['View Tasks'])
# async def admin_tasks(request: Request):
#     """
#     This route is used to render the admin_tasks page.
#     It will RedirectResponse to the admin_tasks page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/tasks.html'
#         , {'request': request})

# @app.get('/admin/task_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# @is_authorized_web(['View Tasks'])
# async def admin_task_details(request: Request):
#     """
#     This route is used to render the admin_task_details page.
#     It will RedirectResponse to the admin_task_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/task_details.html'
#         , {'request': request})

# @app.get('/admin/test')
# @is_logged_in_web
# async def admin_test(request: Request):
#     """
#     This route is used to render the admin_test page.
#     It will RedirectResponse to the admin_test page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/test.html'
#         , {'request': request})

# @app.get('/admin/users')
# @is_logged_in_web
# @is_authorized_web(['View Users'])
# async def admin_users(request: Request):
#     """
#     This route is used to render the admin_users page.
#     It will RedirectResponse to the admin_users page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/users.html'
#         , {'request': request})

# @app.get('/admin/user_details')
# @is_logged_in_web
# @has_valid_id_web
# @is_authorized_web(['View Users'])
# async def admin_user_details(request: Request):
#     """
#     This route is used to render the admin_user_details page.
#     It will RedirectResponse to the admin_user_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/user_details.html'
#         , {'request': request})

# @app.get('/admin/years')
# @is_logged_in_web
# @is_authorized_web(['View Years'])
# async def admin_years(request: Request):
#     """
#     This route is used to render the admin_years page.
#     It will RedirectResponse to the admin_years page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'admin/years.html'
#         , {'request': request})

# @app.get('/user/academic_settings')
# @is_logged_in_web
# async def user_academic_settings(request: Request):
#     """
#     This route is used to render the user_academic_settings page.
#     It will RedirectResponse to the user_academic_settings page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/academic_settings.html'
#         , {'request': request})

# @app.get('/user/announcements')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def user_announcements(request: Request):
#     """
#     This route is used to render the user_announcements page.
#     It will RedirectResponse to the user_announcements page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/announcements.html'
#         , {'request': request})

# @app.get('/user/announcement_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# async def user_announcement_details(request: Request):
#     """
#     This route is used to render the user_announcement_details page.
#     It will RedirectResponse to the user_announcement_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/announcement_details.html'
#         , {'request': request})

# @app.get('/user/calendar')
# @is_logged_in_web
# @is_ready_web
# async def user_calendar(request: Request):
#     """
#     This route is used to render the user_calendar page.
#     It will RedirectResponse to the user_calendar page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/calendar.html'
#         , {'request': request})

# @app.get('/user/courses')
# @is_logged_in_web
# @is_ready_web
# async def user_courses(request: Request):
#     """
#     This route is used to render the user_courses page.
#     It will RedirectResponse to the user_courses page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/courses.html'
#         , {'request': request})

# @app.get('/user/course_details')
# @is_logged_in_web
# @is_ready_web
# @has_valid_id_web
# async def user_course_details(request: Request):
#     """
#     This route is used to render the user_course_details page.
#     It will RedirectResponse to the user_course_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/course_details.html'
#         , {'request': request})

# @app.get('/user/course_map')
# @is_logged_in_web
# @is_ready_web
# async def user_course_map(request: Request):
#     """
#     This route is used to render the user_course_map page.
#     It will RedirectResponse to the user_course_map page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/course_map.html'
#         , {'request': request})

# @app.get('/user/enrolled_courses')
# @is_logged_in_web
# @is_ready_web
# async def user_enrolled_courses(request: Request):
#     """
#     This route is used to render the user_enrolled_courses page.
#     It will RedirectResponse to the user_enrolled_courses page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/enrolled_courses.html'
#         , {'request': request})

# @app.get('/user/exams')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def user_exams(request: Request):
#     """
#     This route is used to render the user_exams page.
#     It will RedirectResponse to the user_exams page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/exams.html'
#         , {'request': request})

# @app.get('/user/exam_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# async def user_exam_details(request: Request):
#     """
#     This route is used to render the user_exam_details page.
#     It will RedirectResponse to the user_exam_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/exam_details.html'
#         , {'request': request})

# @app.get('/user/grades')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def user_grades(request: Request):
#     """
#     This route is used to render the user_grades page.
#     It will RedirectResponse to the user_grades page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/grades.html'
#         , {'request': request})

# @app.get('/user')
# @is_logged_in_web
# async def user_main(request: Request):
#     """
#     This route is used to render the user_index page.
#     It will RedirectResponse to the user_index page of the frontend.
#     """
#     await updated_roles()
#     async with async_session() as session:
#         # deleted = await session.execute(Delete(User).where(User.id == 1))  # Clear the user with id 1 for testing
#         user = (await session.execute(Select(User).where(or_(User.id == 1, User.id == 2)))).scalars().all()
#         role = (await session.execute(Select(Role).where(Role.name == 'admin'))).scalar_one_or_none()
#         for u in user:
#             if u and role:
#                 u.role = role
#         await session.commit()
#     return templates.TemplateResponse(
#         'user/index.html'
#         , {'request': request})

# @app.get('/user/lecture_media')
# @is_logged_in_web
# @is_ready_web
# async def user_lecture_media(request: Request):
#     """
#     This route is used to render the user_lecture_media page.
#     It will RedirectResponse to the user_lecture_media page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/lecture_media.html'
#         , {'request': request})

# @app.get('/user/materials')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def user_materials(request: Request):
#     """
#     This route is used to render the user_materials page.
#     It will RedirectResponse to the user_materials page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/materials.html'
#         , {'request': request})

# @app.get('/user/notification')
# @is_logged_in_web
# @is_ready_web
# async def user_notification(request: Request):
#     """
#     This route is used to render the user_notification page.
#     It will RedirectResponse to the user_notification page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/notification.html'
#         , {'request': request})

# @app.get('/user/profile_settings')
# @is_logged_in_web
# async def user_profile_settings(request: Request):
#     """
#     This route is used to render the user_profile_settings page.
#     It will RedirectResponse to the user_profile_settings page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/profile_settings.html'
#         , {'request': request})

# @app.get('/user/registered_courses')
# @is_logged_in_web
# @is_ready_web
# async def user_registered_courses(request: Request):
#     """
#     This route is used to render the user_registered_courses page.
#     It will RedirectResponse to the user_registered_courses page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/registered_courses.html'
#         , {'request': request})

# @app.get('/user/tasks')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# async def user_tasks(request: Request):
#     """
#     This route is used to render the user_tasks page.
#     It will RedirectResponse to the user_tasks page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/tasks.html'
#         , {'request': request})

# @app.get('/user/task_details')
# @is_logged_in_web
# @is_ready_web
# @has_registered_subjects_web
# @has_valid_id_web
# async def user_task_details(request: Request):
#     """
#     This route is used to render the user_task_details page.
#     It will RedirectResponse to the user_task_details page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'user/task_details.html'
#         , {'request': request})

