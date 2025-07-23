from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db

class StudentTopicPerformanceRepository:
    @staticmethod
    def upsert_performance(student_id, topic_id, avg_points, classification):
        query = text("""
            INSERT INTO student_topic_performance (StudentID, TopicID, AveragePoints, PerformanceClassification)
            VALUES (:student_id, :topic_id, :avg_points, :classification)
            ON DUPLICATE KEY UPDATE
                AveragePoints = :avg_points,
                PerformanceClassification = :classification
        """)
        # Usamos begin() para iniciar una transacción que se commiteará automáticamente
        with db.engine.begin() as connection:
            connection.execute(query, {
                "student_id": student_id,
                "topic_id": topic_id,
                "avg_points": avg_points,
                "classification": classification
            })
