# myapp/controller/RetroalimentacionReclasificacionController.py

from flask import Blueprint, jsonify
from myapp.service.MLRetroalimentacionReclasificacionService import MLRetroalimentacionReclasificacionService

class RetroalimentacionReclasificacionController:
    def __init__(self):
        self.blueprint = Blueprint('RetroalimentacionReclasificacionController', __name__, url_prefix='/reclassify_student')
        self.service = MLRetroalimentacionReclasificacionService()
        self.register_routes()
    
    def register_routes(self):
        @self.blueprint.route('/global/<student_id>', methods=['POST'])
        def reclassify_global(student_id):
            """
            Endpoint para recalcular y actualizar la clasificación global del alumno.
            """
            result = self.service.reclassify_student(student_id)
            return jsonify(result)
        
        @self.blueprint.route('/topics/<student_id>', methods=['POST'])
        def reclassify_topics(student_id):
            """
            Endpoint para recalcular y actualizar la clasificación del desempeño del alumno por tópico.
            """
            result = self.service.reclassify_student_topics(student_id)
            return jsonify(result)
