from core.entities.announcement import Announcement
from core.entities.attachment import Attachment
from core.entities.department import Department
from core.entities.device import Device
from core.entities.event import Event
from core.entities.eventOrganizer import EventOrganizer
from core.entities.exactRole import ExactRole
from core.entities.faculty import Faculty
from core.entities.log import Log
from core.entities.material import Material
from core.entities.message import Message
from core.entities.note import Note
from core.entities.notification import Notification
from core.entities.pendingUser import PendingUser
from core.entities.release import Release
from core.entities.releaseItem import ReleaseItem
from core.entities.role import Role
from core.entities.roleLink import RoleLink
from core.entities.subject import Subject
from core.entities.task import Task
from core.entities.token import Token
from core.entities.user import User
from core.entities.userEvent import UserEvent
from core.entities.userNotification import UserNotification
from core.entities.userSubjectLink import UserSubjectLink
from core.entities.version import Version
from core.entities.week import Week
from core.entities.year import Year


class EntitiesHandler:
    ENTITIES = {
        "Announcement": Announcement,
        "Attachment": Attachment,
        "Department": Department,
        "Device": Device,
        "Event": Event,
        "EventOrganizer": EventOrganizer,
        "ExactRole": ExactRole,
        "Faculty": Faculty,
        "Log": Log,
        "Material": Material,
        "Message": Message,
        "Note": Note,
        "Notification": Notification,
        "PendingUser": PendingUser,
        "Release": Release,
        "ReleaseItem": ReleaseItem,
        "Role": Role,
        "RoleLink": RoleLink,
        "Subject": Subject,
        "Task": Task,
        "Token": Token,
        "User": User,
        "UserEvent": UserEvent,
        "UserNotification": UserNotification,
        "UserSubjectLink": UserSubjectLink,
        "Version": Version,
        "Week": Week,
        "Year": Year,
    }

    TABLES = {
        entity_name: entity.__tablename__ for entity_name, entity in ENTITIES.items()
    }

    @staticmethod
    def get_property(entity_name: str, property_name: str):
        entity = EntitiesHandler.ENTITIES.get(entity_name)
        if entity:
            return getattr(entity, property_name, None)
        return None
