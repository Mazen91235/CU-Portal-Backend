from contextvars import ContextVar
from core.entities.patient import Patient

# Define a context variable to hold the logged-in patient
patient_context: ContextVar[Patient] = ContextVar("patient_context")
