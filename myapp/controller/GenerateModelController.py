from flask import Blueprint,request
from flask import jsonify
import json
from service.GenerateModelService import GenerateModelService

GenerateModelController = Blueprint('GenerateModelController', __name__)


@GenerateModelController.route('/generatemodel/accept/<ModelName>',methods=['GET'])
def accept(ModelName: str):

    generateModelService = GenerateModelService()
    
    return jsonify(generateModelService.generatemodel())