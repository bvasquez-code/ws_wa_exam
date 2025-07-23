from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db

class PerformanceRepository:
    @staticmethod
    def get_global_avg_points(student_id: str) -> float:
        query = text("""
            SELECT (SUM(if(SolvedCorrectly=1,1,0)) / COUNT(1))*100 as avg_points
            FROM data_exam_results
            WHERE StudentID = :student_id
        """)
        with db.engine.connect() as connection:
            result = connection.execute(query, {"student_id": student_id}).mappings().fetchone()
        return result["avg_points"] if result and result["avg_points"] is not None else 0

    @staticmethod
    def get_topic_avg_points(student_id: str):
        query = text("""
            SELECT TopicID, (SUM(if(SolvedCorrectly=1,1,0)) / COUNT(1))*100 as avg_points
            FROM data_exam_results
            WHERE StudentID = :student_id
            GROUP BY TopicID
        """)
        with db.engine.connect() as connection:
            result = connection.execute(query, {"student_id": student_id}).mappings().all()
        return result
