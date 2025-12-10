# myapp/service/MLDiagnosticoService.py

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from myapp.model.entity.DataExamExercisesEntity import db
from myapp.repository.PerformanceRepository import PerformanceRepository

class MLDiagnosticoService:
    """
    Modelo de Diagnóstico:
    - Entrena un clasificador a nivel (StudentID, TopicID) usando el historial de data_exam_results.
    - Para cada par (alumno, tema) calcula:
        * avg_points     -> promedio de PointsObtained
        * correct_rate   -> promedio de SolvedCorrectly
        * attempts       -> cantidad de ejercicios resueltos en el tema
      y genera una etiqueta de nivel:
        0 = débil, 1 = medio, 2 = fuerte (según umbrales de avg_points).
    - Luego, para un alumno específico, estima el nivel de cada tema y clasifica
      en weak_topics, strengths e información detallada.
    """

    def __init__(self, model_path: str = None):
        if model_path:
            self.model_path = model_path
        else:
            # __file__ -> .../myapp/service/MLDiagnosticoService.py
            svc_dir = os.path.dirname(os.path.abspath(__file__))
            # Sube dos niveles para llegar a la raíz del proyecto (/app)
            project_root = os.path.dirname(os.path.dirname(svc_dir))
            # Apunta al modelo dentro de model/
            self.model_path = os.path.join(project_root, 'model', 'diagnostic_model.pkl')

        self.model = None

        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print("Modelo diagnóstico cargado desde:", self.model_path)
        else:
            # No lanzamos error aquí para permitir entrenar el modelo desde cero
            print(f"No se encontró el modelo diagnóstico en: {self.model_path}. Será necesario entrenarlo.")

    @staticmethod
    def _label_from_avg_points(avg_points: float) -> int:
        """
        Genera la etiqueta de nivel de dominio en función del promedio de puntos.
        0 = débil, 1 = medio, 2 = fuerte.
        """
        if avg_points < 50:
            return 0  # débil
        elif avg_points >= 80:
            return 2  # fuerte
        else:
            return 1  # medio

    def train_model(self, min_accuracy: float = 0.7) -> dict:
        """
        Entrena el Modelo de Diagnóstico utilizando datos agregados de 'data_exam_results'.

        Para cada (StudentID, TopicID) se calculan:
          - avg_points   = AVG(PointsObtained)
          - correct_rate = AVG(SolvedCorrectly)
          - attempts     = COUNT(*)

        La etiqueta (y) se define según avg_points:
          - < 50  -> 0 (débil)
          - 50-79 -> 1 (medio)
          - >= 80 -> 2 (fuerte)

        El modelo se guarda en la ruta especificada solo si alcanza al menos min_accuracy.
        """
        query = """
            SELECT 
                StudentID,
                TopicID,
                AVG(PointsObtained) AS avg_points,
                AVG(SolvedCorrectly) AS correct_rate,
                COUNT(*) AS attempts
            FROM data_exam_results
            WHERE NumberAttempt IS NOT NULL
              AND Status = 'A'
            GROUP BY StudentID, TopicID
        """
        df = pd.read_sql(query, con=db.engine)

        if df.empty:
            return {"message": "No se encontraron datos para entrenar el modelo diagnóstico.", "saved": False}

        # Generar etiqueta de nivel en función del avg_points
        df['label'] = df['avg_points'].apply(self._label_from_avg_points)

        # Features y etiqueta
        X = df[['avg_points', 'correct_rate', 'attempts']]
        y = df['label']

        # Separar en train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Entrenar clasificador
        diagnostic_model = RandomForestClassifier(
            class_weight="balanced",
            random_state=42
        )
        diagnostic_model.fit(X_train, y_train)

        # Evaluar accuracy
        accuracy = diagnostic_model.score(X_test, y_test)

        saved = False
        if accuracy >= min_accuracy:
            joblib.dump(diagnostic_model, self.model_path)
            self.model = diagnostic_model
            saved = True

        return {
            "message": "Entrenamiento del modelo diagnóstico finalizado.",
            "saved": saved,
            "accuracy": accuracy,
            "min_accuracy_required": min_accuracy,
            "model_path": self.model_path if saved else None
        }

    def analyze_student_performance(self, student_id: str) -> dict:
        """
        Analiza el desempeño del alumno utilizando el modelo diagnóstico.

        Procedimiento:
          1. Se consulta 'data_exam_results' para el alumno, agrupando por TopicID:
               - avg_points   = AVG(PointsObtained)
               - correct_rate = AVG(SolvedCorrectly)
               - attempts     = COUNT(*)
          2. Se construye el vector de características [avg_points, correct_rate, attempts]
             para cada TopicID.
          3. Si existe un modelo entrenado, se predice la etiqueta (0,1,2) por tópico:
               0 -> débil       -> se añade a weak_topics
               2 -> fuerte      -> se añade a strengths
               1 -> intermedio  -> solo queda en detailed
          4. Se retorna:
             - student_id
             - weak_topics
             - strengths
             - detailed: lista con { TopicID, avg_points, correct_rate, attempts, predicted_label }
        """
        # Asegurar que el modelo está cargado
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print("Modelo diagnóstico cargado desde:", self.model_path)
            else:
                return {"message": "Modelo diagnóstico no encontrado. Entrénalo primero."}

        # Consulta agregada por tópico para el alumno
        query = """
            SELECT 
                TopicID,
                AVG(PointsObtained) AS avg_points,
                AVG(SolvedCorrectly) AS correct_rate,
                COUNT(*) AS attempts
            FROM data_exam_results
            WHERE StudentID = %s
            AND NumberAttempt IS NOT NULL
            AND Status = 'A'
            GROUP BY TopicID
        """

        # OJO: aquí usamos params como lista, en el orden de los %s
        df = pd.read_sql(query, con=db.engine, params=[student_id])

        if df.empty:
            return {
                "student_id": student_id,
                "weak_topics": [],
                "strengths": [],
                "detailed": [],
                "message": "El alumno no tiene suficientes resultados para análisis."
            }

        # Features
        X = df[['avg_points', 'correct_rate', 'attempts']]

        # Predicciones
        predicted_labels = self.model.predict(X)

        weak_topics = []
        strengths = []
        detailed = []

        for idx, row in df.iterrows():
            topic_id = int(row["TopicID"])
            avg_points = float(row["avg_points"])
            correct_rate = float(row["correct_rate"])
            attempts = int(row["attempts"])
            label = int(predicted_labels[idx])  # 0, 1 o 2

            if label == 0:
                weak_topics.append(topic_id)
            elif label == 2:
                strengths.append(topic_id)

            detailed.append({
                "TopicID": topic_id,
                "avg_points": avg_points,
                "correct_rate": correct_rate,
                "attempts": attempts,
                "predicted_label": label  # 0 = débil, 1 = medio, 2 = fuerte
            })

        return {
            "student_id": student_id,
            "weak_topics": weak_topics,
            "strengths": strengths,
            "detailed": detailed
        }
