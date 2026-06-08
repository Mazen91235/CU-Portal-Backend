import math
from models import *
from extensions import async_session, cairo_tz, os, load_dotenv
from sqlalchemy import Select, Delete, func, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from settings import log
import asyncio
load_dotenv()
async def create_notifications():
    async with async_session() as session:
        await session.begin()
        count = 0
        try:
            tasks_threshold_date = datetime.now(cairo_tz) + timedelta(days=5)
            tasks = (await session.execute(Select(Task).where(Task.due_date <= tasks_threshold_date,
                                                              Task.due_date > datetime.now(cairo_tz)).options(selectinload(Task.subject).selectinload(Subject.users)).order_by((Task.deadline >= func.now()).desc(), Task.deadline.asc()))).scalars().all()
            for task in tasks:
                diff_days = math.ceil((task.due_date - datetime.now(cairo_tz)).total_seconds() / 86400)
                diff_string = f"{diff_days} days remaining" if diff_days > 1 else "1 day remaining"
                task_exam_string = "task" if task.type != "exam" else "exam"
                notification_string = f"{diff_string} on {task_exam_string} '{task.title}' for course '{task.subject.name}'"
                notification = Notification(
                    content=notification_string,
                    type="task" if task.type != "exam" else "exam",
                    parent_id=task.id,
                    url=f"{os.environ.get('FRONTEND_URL')}/user/tasks/{task.id}",
                    users=[]
                )
                session.add(notification)
                count += 1
                users = (await session.execute(Select(User).where(
                    User.faculty_id == task.faculty_id,
                    User.department_id == task.department_id,
                    User.year_id == task.year_id
                ))).scalars().all()
                for user in users:
                    if user in task.subject.users:
                        notification.users.append(user)
            await session.commit()
            await log(None, "Create", "Notifications", 201, 'info', 'Notifications Created Successfully.', {"count": count})
        except Exception as e:
            await log(None, "Create", "Notifications", 500, 'error', 'An Error Occurred While Creating Notifications.', {'error': e})
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(create_notifications())