from core.entities.log import Log
from core.entities.logDetails import LogDetails
from core.entities.patient import Patient
from core.entities.patientUser import PatientUser
from core.entities.user import User


class EntitiesHandler:
    ENTITIES = {
        "Log": Log,
        "LogDetails": LogDetails,
        "Patient": Patient,
        "PatientUser": PatientUser,
        "User": User,
    }

    TABLES = {
        "Log": "logs",
        "LogDetails": "log_details",
        "Patient": "patients",
        "PatientUser": "patient_users",
        "User": "users",
    }

    @staticmethod
    def get_property(entity_name: str, property_name: str):
        entity = EntitiesHandler.ENTITIES.get(entity_name)
        if entity:
            return getattr(entity, property_name, None)
        return None
