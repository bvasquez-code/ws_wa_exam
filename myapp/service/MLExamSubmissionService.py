# myapp/service/MLExamSubmissionService.py

from myapp.repository.ExamResultsRepository import ExamResultsRepository
from myapp.repository.DataStudentExamHistoryRepository import DataStudentExamHistoryRepository
from myapp.repository.ExamRepository import ExamRepository
from myapp.service.MLRetroalimentacionReclasificacionService import MLRetroalimentacionReclasificacionService

class MLExamSubmissionService:
    def __init__(self):
        self.exam_results_repo = ExamResultsRepository()
        self.reclasificacion_service = MLRetroalimentacionReclasificacionService()

    def submit_exam(self, exam_data: dict) -> dict:
        """
        Procesa el examen resuelto enviado.
        exam_data debe contener:
          - StudentID: Identificador del alumno.
          - ExamID: Identificador del examen.
          - results: lista de registros, cada uno con:
              * TopicID
              * ExerciseID
              * SolvedCorrectly (0 o 1)
              * CreationUser
              * NumberAttempt (opcional)
        El sistema calculará automáticamente PointsObtained:
          - Si SolvedCorrectly == 1, se asigna el valor del ejercicio (consultado en data_exam_exercises).
          - Si SolvedCorrectly == 0, se asigna 0.
        Luego, inserta los resultados en data_exam_results y actualiza las clasificaciones.
        Devuelve también la calificación total obtenida.
        """
        student_id = exam_data.get("StudentID")
        exam_id = exam_data.get("ExamID")
        results = exam_data.get("results", [])
        history_id = exam_data.get("HistoryID")
        
        # Importar el método para obtener puntos del ejercicio
        from myapp.repository.ExamRepository import ExamRepository
        
        processed_results = []
        for res in results:
            res.setdefault("StudentID", student_id)
            res.setdefault("ExamID", exam_id)
            res.setdefault("NumberAttempt", res.get("NumberAttempt", 1))
            solved = res.get("SolvedCorrectly", 0)
            if solved == 1:
                # Se obtiene el valor del ejercicio desde data_exam_exercises
                exercise_points = ExamRepository.get_exam_exercise_points(exam_id, res.get("ExerciseID"))
                res["PointsObtained"] = exercise_points
            else:
                res["PointsObtained"] = 0
            processed_results.append(res)
        
        # Insertar los resultados en data_exam_results
        ExamResultsRepository.insert_multiple_exam_results(processed_results)
        DataStudentExamHistoryRepository.mark_attempt_completed(history_id)
        
        # Actualizar reclasificación global y por tópicos
        global_reclass = self.reclasificacion_service.reclassify_student(student_id)
        topics_reclass = self.reclasificacion_service.reclassify_student_topics(student_id)
        
        # Calcular la calificación total del examen (suma de PointsObtained)
        total_score = sum(r["PointsObtained"] for r in processed_results)
        
        return {
            "message": "Examen enviado y resultados almacenados correctamente.",
            "total_score": total_score,
            "global_reclassification": global_reclass
        }
