# myapp/repository/ExamResultsRepository.py

from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db

class ExamResultsRepository:
    @staticmethod
    def insert_exam_result(result: dict):
        """
        Inserta un registro en la tabla data_exam_results.
        Se espera que result sea un diccionario con las siguientes claves:
          - StudentID
          - ExamID
          - TopicID
          - ExerciseID
          - SolvedCorrectly (0 o 1)
          - PointsObtained
          - CreationUser
          - NumberAttempt (opcional)
        """
        insert_sql = text("""
            INSERT INTO data_exam_results 
            (StudentID, ExamID, TopicID, ExerciseID, SolvedCorrectly, PointsObtained, CreationUser, NumberAttempt)
            VALUES (:StudentID, :ExamID, :TopicID, :ExerciseID, :SolvedCorrectly, :PointsObtained, :CreationUser, :NumberAttempt)
        """)
        # Se inicia una transacción con begin(), que se commitea automáticamente al finalizar
        with db.engine.begin() as connection:
            connection.execute(insert_sql, result)

    @staticmethod
    def insert_multiple_exam_results(results: list):
        """
        Inserta múltiples registros en la tabla data_exam_results.
        results: lista de diccionarios, cada uno con la estructura requerida.
        """
        for result in results:
            ExamResultsRepository.insert_exam_result(result)
