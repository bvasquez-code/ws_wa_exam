from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db
import sys

class DataTopicsRepository:
    @staticmethod
    def get_all_courses() -> list[str]:
        sql = text("SELECT DISTINCT Course FROM data_topics where Status = 'A'")
        with db.engine.connect() as conn:
            return [row["Course"] for row in conn.execute(sql).mappings().all()]

    @staticmethod
    def get_topic_ids_by_course(course: str) -> list[int]:
        sql = text("SELECT TopicID FROM data_topics WHERE Course = :course and Status = 'A'")
        with db.engine.connect() as conn:
            return [row["TopicID"] for row in conn.execute(sql, {"course": course}).mappings().all()]

    @staticmethod
    def get_active_topic_ids() -> list[int]:
        sql = text("SELECT TopicID FROM data_topics WHERE Status = 'A'")
        with db.engine.connect() as conn:
            return [row["TopicID"] for row in conn.execute(sql).mappings().all()]
