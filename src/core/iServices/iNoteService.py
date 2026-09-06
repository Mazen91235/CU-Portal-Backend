from core.iServices.bases.iCrudService import ICrudService
from core.entities.note import Note
from core.dtos.noteDtos import NoteSearchDto


class INoteService(ICrudService[Note, NoteSearchDto]):
    pass
