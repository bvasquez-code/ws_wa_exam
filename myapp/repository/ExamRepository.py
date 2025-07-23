from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db
import random

class ExamRepository:
    @staticmethod
    def generate_exam_id() -> str:
        """
        Genera un ExamID de forma incremental.
        Realiza una consulta que obtiene el valor máximo de la parte numérica de ExamID de la tabla data_exams,
        incrementa ese valor en 1 y lo retorna con el prefijo "EX" formateado en 5 dígitos.
        """
        query = text("""
            SELECT MAX(CAST(SUBSTRING(ExamID, 3) AS UNSIGNED)) AS max_id
            FROM data_exams
        """)
        with db.engine.connect() as connection:
            result = connection.execute(query).mappings().fetchone()
        max_id = result["max_id"] if result and result["max_id"] is not None else 0
        next_id = max_id + 1
        return "EX" + "{:05d}".format(next_id)

    @staticmethod
    def insert_exam(exam_data: dict):
        """
        Inserta un registro en la tabla data_exams.
        Se espera exam_data con las claves:
          - ExamID, ExamName, Description, Subject, DurationMinutes, CreationUser
        """
        query = text("""
            INSERT INTO data_exams (ExamID, ExamName, Description, Subject, DurationMinutes, CreationUser)
            VALUES (:ExamID, :ExamName, :Description, :Subject, :DurationMinutes, :CreationUser)
        """)
        with db.engine.begin() as connection:
            connection.execute(query, exam_data)

    @staticmethod
    def insert_exam_exercises(exam_exercises: list):
        """
        Inserta múltiples registros en data_exam_exercises.
        Cada elemento de exam_exercises debe ser un diccionario con:
          - ExamID, ExerciseID, TopicID, DifficultyLevel, Points, CreationUser
        """
        query = text("""
            INSERT INTO data_exam_exercises (ExamID, ExerciseID, TopicID, DifficultyLevel, Points, CreationUser)
            VALUES (:ExamID, :ExerciseID, :TopicID, :DifficultyLevel, :Points, :CreationUser)
        """)
        with db.engine.begin() as connection:
            for exercise in exam_exercises:
                connection.execute(query, exercise)

    @staticmethod
    def get_exam_exercise_points(exam_id: str, exercise_id: int) -> float:
        query = text("""
            SELECT Points
            FROM data_exam_exercises
            WHERE ExamID = :exam_id AND ExerciseID = :exercise_id
        """)
        with db.engine.connect() as connection:
            result = connection.execute(query, {"exam_id": exam_id, "exercise_id": exercise_id}).mappings().fetchone()
        return result["Points"] if result and result["Points"] is not None else 0
