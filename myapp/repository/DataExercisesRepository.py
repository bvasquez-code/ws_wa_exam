from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db
import sys

class DataExercisesRepository:
    @staticmethod
    def update_exercise_points():
        """
        Actualiza el campo Points en data_exercises usando los datos de data_exam_results.
        Calcula la utilidad:
            utility = (1 - SolvedCorrectly) / (NumberAttempt + 1)
        y la escala a 0-100.
        """
        update_sql = text("""
            UPDATE data_exercises e
            JOIN (
                SELECT ExerciseID,
                       AVG((1 - SolvedCorrectly) / (NumberAttempt + 1)) AS avg_utility
                FROM data_exam_results
                GROUP BY ExerciseID
            ) r ON e.ExerciseID = r.ExerciseID
            SET e.Points = ROUND(r.avg_utility * 100)
        """)
        # Usamos un contexto transaccional para ejecutar y commitear la actualización
        with db.engine.begin() as connection:
            connection.execute(update_sql)
            # No es necesario llamar a commit(), se realiza automáticamente al salir del bloque

    @staticmethod
    def get_exercises_by_topics(topic_names: list):
        """
        Obtiene ejercicios para los tópicos especificados.
        Se espera que topic_names sea una lista de nombres de tópicos.
        """
        topics_str = "', '".join(map(str, topic_names))
        query = text(f"""
            SELECT e.ExerciseID, e.ExerciseCod, e.TopicID, e.Level, e.Points, t.Name as topic_name
            FROM data_exercises e
            JOIN data_topics t ON e.TopicID = t.TopicID
            WHERE t.TopicID IN ('{topics_str}')
        """)
        # Usamos un contexto de conexión para ejecutar la consulta
        with db.engine.connect() as connection:
            result = connection.execute(query)
            return result.fetchall()
