# myapp/controller/DiagnosticModelController.py

from flask import Blueprint, jsonify
from myapp.service.MLDiagnosticoService import MLDiagnosticoService

class DiagnosticModelController:
    def __init__(self):
        # Creamos el blueprint con el nombre de la clase.
        self.blueprint = Blueprint('DiagnosticModelController', __name__, url_prefix='/train_diagnostic_model')
        self.ml_service = MLDiagnosticoService()
        self.register_routes()

    def register_routes(self):
        @self.blueprint.route('', methods=['POST'])
        def train_diagnostic_model():
            result = self.ml_service.train_model()
            return jsonify(result)
