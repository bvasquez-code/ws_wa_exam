# myapp/service/MLRetroalimentacionReclasificacionService.py

from myapp.repository.PerformanceRepository import PerformanceRepository
from myapp.repository.DataStudentsRepository import DataStudentsRepository
from myapp.repository.StudentTopicPerformanceRepository import StudentTopicPerformanceRepository

class MLRetroalimentacionReclasificacionService:
    def __init__(self):
        pass

    def reclassify_student(self, student_id: str) -> dict:
        """
        Recalcula el desempeño global del alumno basado en el promedio de PointsObtained
        de data_exam_results y actualiza data_students.
          - Promedio >= 80: "Alto"
          - Promedio entre 50 y 80: "Medio"
          - Promedio < 50: "Bajo"
        """
        avg_points = PerformanceRepository.get_global_avg_points(student_id)
        if avg_points >= 80:
            classification = "Alto"
        elif avg_points >= 50:
            classification = "Medio"
        else:
            classification = "Bajo"

        DataStudentsRepository.update_global_classification(student_id, classification)
        return {
            "student_id": student_id,
            "avg_points": avg_points,
            "global_classification": classification
        }

    def reclassify_student_topics(self, student_id: str) -> dict:
        """
        Recalcula el desempeño del alumno por cada tópico usando data_exam_results
        y actualiza student_topic_performance.
          - Promedio >= 80: "Alto"
          - Promedio entre 50 y 80: "Medio"
          - Promedio < 50: "Bajo"
        """
        topic_rows = PerformanceRepository.get_topic_avg_points(student_id)
        results = []
        for row in topic_rows:
            topic_id = row["TopicID"]
            avg_points = row["avg_points"]
            if avg_points >= 80:
                classification = "Alto"
            elif avg_points >= 50:
                classification = "Medio"
            else:
                classification = "Bajo"

            StudentTopicPerformanceRepository.upsert_performance(student_id, topic_id, avg_points, classification)
            results.append({
                "TopicID": topic_id,
                "AveragePoints": avg_points,
                "TopicClassification": classification
            })
        return {
            "student_id": student_id,
            "topics_classification": results
        }
