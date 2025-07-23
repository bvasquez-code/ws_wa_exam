from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db

class DataStudentsRepository:
    @staticmethod
    def update_global_classification(student_id: str, classification: str):
        query = text("""
            UPDATE data_students 
            SET PerformanceClassification = :classification 
            WHERE StudentID = :student_id
        """)
        with db.engine.begin() as connection:
            connection.execute(query, {"classification": classification, "student_id": student_id})
