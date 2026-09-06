from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.noteDtos import NoteCreateDto, NoteUpdateDto, NoteSearchDto


class INoteController(ICrudController[NoteCreateDto, NoteUpdateDto, NoteSearchDto]):
    pass
