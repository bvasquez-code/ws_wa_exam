from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db

class DataStudentExamHistoryRepository:
    @staticmethod
    def insert_exam_attempt(student_id: str, exam_id: str, attempt_number: int, is_completed: int):
        """
        Registra un intento de examen para un alumno.
        
        Parámetros:
          - student_id: Identificador del alumno.
          - exam_id: Identificador del examen.
          - attempt_number: Número secuencial del intento para ese alumno.
          - is_completed: Flag (0 en curso, 1 culminado).
        """
        insert_sql = text("""
            INSERT INTO data_student_exam_history 
            (StudentID, ExamID, AttemptNumber, IsCompleted, StartDate)
            VALUES (:student_id, :exam_id, :attempt_number, :is_completed, NOW())
        """)
        with db.engine.begin() as connection:
            connection.execute(insert_sql, {
                "student_id": student_id,
                "exam_id": exam_id,
                "attempt_number": attempt_number,
                "is_completed": is_completed
            })

    @staticmethod
    def mark_attempt_completed(history_id: int):
        """
        Marca un intento de examen como completado y registra la fecha de finalización.

        Parámetros:
          - history_id: Identificador único del registro en data_student_exam_history.
        """
        update_sql = text(
            """
            UPDATE data_student_exam_history
            SET IsCompleted = 1,
                FinishDate = NOW()
            WHERE HistoryID = :history_id
            """
        )
        with db.engine.begin() as connection:
            connection.execute(update_sql, {"history_id": history_id})
