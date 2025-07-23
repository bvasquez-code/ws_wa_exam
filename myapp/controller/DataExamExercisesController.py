# myapp/controller/DataExamExercisesController.py

from flask import Blueprint, jsonify
from myapp.service.DataExamExercisesService import DataExamExercisesService
from myapp.repository.DataExamExercisesRepository import DataExamExercisesRepository
from myapp.model.entity.DataExamExercisesEntity import db

class DataExamExercisesController:
    def __init__(self):
        # Creamos el blueprint con el nombre de la clase.
        self.blueprint = Blueprint('DataExamExercisesController', __name__, url_prefix='/get_data_exam_exercises_by_exam_id')
        repository = DataExamExercisesRepository(db)
        self.service = DataExamExercisesService(repository)
        self.register_routes()

    def register_routes(self):
        @self.blueprint.route('/<exam_id>', methods=['GET'])
        def get_data_exam_exercises_by_exam_id(exam_id):
            dtos = self.service.find_data_exam_exercises_by_exam_id(exam_id)
            return jsonify([dto.to_dict() for dto in dtos])
