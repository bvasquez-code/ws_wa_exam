# myapp/repository/DataExamExercisesRepository.py

from myapp.model.entity.DataExamExercisesEntity import DataExamExercisesEntity

class DataExamExercisesRepository:
    def __init__(self, db):
        self.db = db

    def find_by_exam_id(self, exam_id: str):
        # Consulta la tabla filtrando por ExamID.
        return DataExamExercisesEntity.query.filter_by(ExamID=exam_id).all()
