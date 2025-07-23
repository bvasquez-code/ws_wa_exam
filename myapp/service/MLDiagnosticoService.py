# myapp/service/MLDiagnosticoService.py

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from myapp.model.entity.DataExamExercisesEntity import db
from myapp.repository.PerformanceRepository import PerformanceRepository

class MLDiagnosticoService:
    def __init__(self, model_path=r"F:\proyectos\python\ws_wa_exam\model\diagnostic_model.pkl"):
        self.model_path = model_path
        self.model = None
        # Si el modelo ya existe, lo cargamos; si no, se entrenará desde cero.
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print("Modelo diagnóstico cargado desde:", self.model_path)

    def train_model(self):
        """
        Entrena el Modelo de Diagnóstico utilizando datos de la tabla 'data_exam_results'.
        Se asume que la tabla cuenta con las columnas:
          - PointsObtained
          - NumberAttempt
          - SolvedCorrectly
        El modelo se guarda en la ruta especificada.
        """
        # Consulta para extraer datos relevantes de la tabla.
        query = """
            SELECT PointsObtained, NumberAttempt, SolvedCorrectly 
            FROM data_exam_results 
            WHERE NumberAttempt IS NOT NULL
        """
        df = pd.read_sql(query, con=db.engine)

        if df.empty:
            return {"message": "No se encontraron datos para entrenar el modelo diagnóstico."}

        # Definir las características (X) y la etiqueta (y)
        X = df[['PointsObtained', 'NumberAttempt']]
        y = df['SolvedCorrectly']

        # Dividir los datos en conjuntos de entrenamiento y prueba
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Entrenar el modelo diagnóstico (ejemplo con RandomForestClassifier)
        diagnostic_model = RandomForestClassifier()
        diagnostic_model.fit(X_train, y_train)

        # Guardar el modelo entrenado en la ruta especificada
        joblib.dump(diagnostic_model, self.model_path)
        self.model = diagnostic_model

        # Calcular la precisión del modelo en el conjunto de prueba
        accuracy = diagnostic_model.score(X_test, y_test)

        return {
            "message": "Modelo diagnóstico entrenado correctamente.",
            "accuracy": accuracy,
            "model_path": self.model_path
        }
    
    def analyze_student_performance(self, student_id: str) -> dict:
        """
        Analiza el desempeño del alumno de forma dinámica utilizando los datos de desempeño por tópico.
        
        Procedimiento:
          1. Se consulta la información de desempeño por tópico a partir de PerformanceRepository.
             Esto obtiene, para cada TopicID en los resultados de exámenes del alumno,
             el promedio de PointsObtained.
          2. Para cada tópico se evalúa:
             - Si el promedio es menor a 50, se considera que el alumno tiene un desempeño "débil" en ese tópico.
             - Si el promedio es igual o superior a 80, se considera una fortaleza.
             - Los promedios intermedios se pueden tratar como "medios" y, en este ejemplo, no se incluyen en ninguna lista.
          3. Se retornan tres elementos:
             - weak_topics: Lista de TopicIDs donde el alumno presenta bajo desempeño.
             - strengths: Lista de TopicIDs donde el desempeño es alto.
             - detailed: Información detallada por tópico (TopicID y promedio obtenido).
        """
        topic_rows = PerformanceRepository.get_topic_avg_points(student_id)
        weak_topics = []
        strengths = []
        detailed = []

        for row in topic_rows:
            topic_id = row["TopicID"]
            avg_points = row["avg_points"]
            detailed.append({
                "TopicID": topic_id,
                "avg_points": avg_points
            })
            if avg_points < 50:
                weak_topics.append(topic_id)
            elif avg_points >= 80:
                strengths.append(topic_id)
            # Los promedios entre 50 y 80 se consideran intermedios y se omiten en esta clasificación

        return {
            "student_id": student_id,
            "weak_topics": weak_topics,
            "strengths": strengths,
            "detailed": detailed
        }
