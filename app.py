from flask import Flask
from flask_cors import CORS
from myapp.config.Config import Config
from myapp.model.entity.DataExamExercisesEntity import db
from myapp.controller.DataExamExercisesController import DataExamExercisesController
from myapp.controller.DiagnosticModelController import DiagnosticModelController
# from myapp.controller.GenerateModelController import GenerateModelController
from myapp.controller.GeneracionRankingController import GeneracionRankingController
from myapp.controller.RetroalimentacionReclasificacionController import RetroalimentacionReclasificacionController
from myapp.controller.ExamSubmissionController import ExamSubmissionController

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Inicializamos SQLAlchemy con la aplicación
    db.init_app(app)
    
    with app.app_context():
        # En producción se recomienda utilizar migraciones en lugar de create_all()
        db.create_all()
    
    # Instanciamos y registramos el blueprint del DataExamExercisesController
    dataExamExercisesController = DataExamExercisesController()
    app.register_blueprint(dataExamExercisesController.blueprint)

    diagnosticModelController = DiagnosticModelController()
    app.register_blueprint(diagnosticModelController.blueprint)

    generacionRankingController = GeneracionRankingController()
    app.register_blueprint(generacionRankingController.blueprint)

    retroalimentacionReclasificacionController = RetroalimentacionReclasificacionController()
    app.register_blueprint(retroalimentacionReclasificacionController.blueprint)

    examSubmissionController = ExamSubmissionController()
    app.register_blueprint(examSubmissionController.blueprint)
    
    # Registramos también el blueprint del GenerateModelController
    # app.register_blueprint(GenerateModelController)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=4000)
