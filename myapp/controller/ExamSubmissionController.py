# myapp/controller/ExamSubmissionController.py

from flask import Blueprint, jsonify, request
from myapp.service.MLGeneracionRankingService import MLGeneracionRankingService
from myapp.service.MLExamSubmissionService import MLExamSubmissionService
from myapp.model.dto.ResponseWsDto import ResponseWsDto

class ExamSubmissionController:
    def __init__(self):
        self.blueprint = Blueprint('ExamSubmissionController', __name__, url_prefix='/exam')
        self.ranking_service = MLGeneracionRankingService()
        self.submission_service = MLExamSubmissionService()
        self.register_routes()
    
    def register_routes(self):
        @self.blueprint.route('/generate_exercises', methods=['POST'])
        def generate_exercises():
            """
            Endpoint para generar y registrar un examen personalizado.
            Se espera un JSON con:
              - student_id: identificador del alumno
              - topics: lista de nombres de topics
              - limit: número máximo de ejercicios
            """
            data = request.get_json()
            student_id = data.get("student_id")
            topics = data.get("topics", [])
            limit = data.get("limit", 10)
            total_points = data.get("total_points", 0)
            result = self.ranking_service.generate_exercises_by_topics(student_id, topics, limit, total_points)
            response = ResponseWsDto().ok_response(result)
            return jsonify(response.__dict__)
        
        @self.blueprint.route('/submit', methods=['POST'])
        def submit_exam():
            """
            Endpoint para enviar el examen resuelto y almacenar los resultados.
            Se espera un JSON con:
              - StudentID
              - ExamID
              - HistoryID
              - results: lista de registros (cada uno con TopicID, ExerciseID, SolvedCorrectly, PointsObtained, CreationUser, y opcionalmente NumberAttempt)
            """
            exam_data = request.get_json()
            result = self.submission_service.submit_exam(exam_data)
            response = ResponseWsDto().ok_response(result)
            return jsonify(response.__dict__)

        @self.blueprint.route('/generate_entry_exam', methods=['POST'])
        def generate_entry_exam():
            """
            Genera el examen de entrada para un alumno completamente nuevo.
            Se espera un JSON con:
              - student_id: identificador del alumno
            """
            data = request.get_json()
            student_id = data.get("student_id")
            try:
                exam = self.ranking_service.generate_entry_exam(student_id)
                response = ResponseWsDto().ok_response(exam)
            except Exception as ex:
                response = ResponseWsDto().error_response(ex)
            return jsonify(response.__dict__)