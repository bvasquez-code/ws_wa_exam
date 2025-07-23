# myapp/controller/GeneracionRankingController.py

from flask import Blueprint, jsonify
from myapp.service.MLGeneracionRankingService import MLGeneracionRankingService
from myapp.service.MLDiagnosticoService import MLDiagnosticoService  # Suponemos que ya tienes este servicio

class GeneracionRankingController:
    def __init__(self):
        self.blueprint = Blueprint('GeneracionRankingController', __name__, url_prefix='/generate_rank_exam')
        self.ranking_service = MLGeneracionRankingService()
        # Se usa el servicio de diagnóstico para obtener los temas débiles del alumno.
        self.diagnostic_service = MLDiagnosticoService()
        self.register_routes()
    
    def register_routes(self):
        @self.blueprint.route('generate_exam/<student_id>', methods=['GET'])
        def generate_rank_exam(student_id):
            # Primero se obtiene el rendimiento y weak_topics mediante el modelo diagnóstico.
            performance = self.diagnostic_service.analyze_student_performance(student_id)
            weak_topics = performance.get("weak_topics", [])
            if not weak_topics:
                return jsonify({"message": "No se identificaron temas débiles para el alumno."}), 404
            
            exam = self.ranking_service.generate_exam(student_id, weak_topics)
            return jsonify(exam)
        
        @self.blueprint.route('/train', methods=['POST'])
        def train_ranking_model():
            result = self.ranking_service.train_model()
            return jsonify(result)
