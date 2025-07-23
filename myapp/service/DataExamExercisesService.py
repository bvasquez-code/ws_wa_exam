# myapp/service/DataExamExercisesService.py

from myapp.repository.DataExamExercisesRepository import DataExamExercisesRepository
from myapp.model.dto.DataExamExercisesDTO import DataExamExercisesDTO

class DataExamExercisesService:
    def __init__(self, repository: DataExamExercisesRepository):
        self.repository = repository

    def find_data_exam_exercises_by_exam_id(self, exam_id: str):
        entities = self.repository.find_by_exam_id(exam_id)
        dtos = [DataExamExercisesDTO.from_entity(entity) for entity in entities]
        return dtos
