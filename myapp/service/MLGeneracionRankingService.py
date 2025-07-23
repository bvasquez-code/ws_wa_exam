# myapp/service/MLGeneracionRankingService.py

import os
import joblib
import pandas as pd
import numpy as np
import random
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from myapp.repository.DataExercisesRepository import DataExercisesRepository
from myapp.repository.DataTopicsRepository import DataTopicsRepository
from myapp.repository.ExamRepository import ExamRepository
from myapp.repository.DataStudentExamHistoryRepository import DataStudentExamHistoryRepository
from sqlalchemy import text
from myapp.model.entity.DataExamExercisesEntity import db


class MLGeneracionRankingService:
    def __init__(self, model_path=r"F:\proyectos\python\ws_wa_exam\model\generation_ranking_model.pkl"):
        self.model_path = model_path
        self.model = None
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print("Modelo de generación y ranking cargado desde:", self.model_path)
    
    def train_model(self):
        """
        Actualiza los Points en data_exercises y entrena un modelo de regresión.
        Las features son: Points, Level y NumberAttempt; target: utility = (1 - SolvedCorrectly) / (NumberAttempt + 1).
        """
        # Actualizar Points usando DataExercisesRepository
        DataExercisesRepository.update_exercise_points()
        
        query = """
            SELECT r.SolvedCorrectly, r.NumberAttempt, e.Points, e.Level
            FROM data_exam_results r
            JOIN data_exercises e ON r.ExerciseID = e.ExerciseID
            WHERE r.NumberAttempt IS NOT NULL
        """
        df = pd.read_sql(query, con=db.engine)
        if df.empty:
            return {"message": "No se encontraron datos para entrenar el modelo de generación y ranking."}

        df['utility'] = (1 - df['SolvedCorrectly']) / (df['NumberAttempt'] + 1)
        X = df[['Points', 'Level', 'NumberAttempt']]
        y = df['utility']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(random_state=42)
        model.fit(X_train, y_train)
        joblib.dump(model, self.model_path)
        self.model = model
        r2_score = model.score(X_test, y_test)
        return {
            "message": "Modelo de generación y ranking entrenado correctamente.",
            "r2_score": r2_score,
            "model_path": self.model_path
        }
    
    def generate_exam(self, student_id: str, weak_topics: list):
        """
        Genera un examen personalizado usando ejercicios de data_exercises para los tópicos débiles.
        Construye el vector de características [Points, Level, NumberAttempt=0] para cada ejercicio,
        predice la utilidad y rankea los ejercicios.
        """
        # Obtener ejercicios usando DataExercisesRepository
        exercises = DataExercisesRepository.get_exercises_by_topics(weak_topics)
        if not exercises:
            return {"message": "No se encontraron ejercicios para los temas débiles proporcionados."}
        
        # Convertir el resultado a DataFrame
        df_exercises = pd.DataFrame(exercises, columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"])
        features = df_exercises[['Points', 'Level']].copy()
        features['NumberAttempt'] = 0
        X_candidates = features[['Points', 'Level', 'NumberAttempt']]
        
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                return {"message": "Modelo de generación y ranking no encontrado. Entrénalo primero."}

        df_exercises['predicted_utility'] = self.model.predict(X_candidates)
        df_ranked = df_exercises.sort_values(by='predicted_utility', ascending=False)
        exam = {
            "exam_id": f"EXAM-RANK-{student_id}",
            "student_id": student_id,
            "exercises": df_ranked.to_dict(orient='records')
        }
        return exam


    def generate_exercises_by_topics(self, student_id: str, topics: list, limit: int, total_points: float) -> dict:
        """
        Genera un examen personalizado para el alumno basado en los ejercicios disponibles
        para los topics indicados, limitando el número de ejercicios a 'limit'. Además, registra
        el examen en data_exams y sus ejercicios en data_exam_exercises.
        
        Parámetros:
          - student_id: ID del alumno.
          - topics: Lista de nombres de topics.
          - limit: Número máximo de ejercicios a incluir.
          - total_points: Valor total del examen.
        
        Procedimiento:
          1. Se consultan los ejercicios para los topics.
          2. Se construye el vector de características [Points, Level, NumberAttempt=0] para cada ejercicio.
          3. Se predice la utilidad y se ordenan los ejercicios.
          4. Se limita el número de ejercicios a 'limit'.
          5. Se genera un nuevo ExamID de forma incremental.
          6. Se registra el examen en data_exams y cada ejercicio en data_exam_exercises, asignando a cada ejercicio 
             un puntaje calculado como total_points/limit.
        """
        # 1. Obtener ejercicios para los topics indicados
        exercises = DataExercisesRepository.get_exercises_by_topics(topics)
        if not exercises:
            return {"message": "No se encontraron ejercicios para los topics proporcionados."}
        
        # 2. Convertir el resultado a DataFrame y construir el vector de características
        df_exercises = pd.DataFrame(exercises, columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"])
        features = df_exercises[['Points', 'Level']].copy()
        features['NumberAttempt'] = 0  # Asumimos que el alumno aún no ha intentado estos ejercicios.
        X_candidates = features[['Points', 'Level', 'NumberAttempt']]
        
        # 3. Cargar el modelo de ranking si no está cargado
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                return {"message": "Modelo de generación y ranking no encontrado. Entrénalo primero."}
        
        # 4. Predecir la utilidad y ordenar los ejercicios
        df_exercises['predicted_utility'] = self.model.predict(X_candidates)
        df_ranked = df_exercises.sort_values(by='predicted_utility', ascending=False).head(limit)
        exam_exercises = df_ranked.to_dict(orient='records')
        
        # 5. Generar un nuevo ExamID
        exam_id = ExamRepository.generate_exam_id()
        
        # 6. Registrar el examen en data_exams
        exam_data = {
            "ExamID": exam_id,
            "ExamName": f"Examen personalizado para {student_id}",
            "Description": "Examen generado automáticamente basado en los topics proporcionados.",
            "Subject": "Personalizado",
            "DurationMinutes": 60,  # Valor por defecto, ajustar según necesidad.
            "CreationUser": "system"
        }
        ExamRepository.insert_exam(exam_data)

        # 7. Registrar el intento en data_student_exam_history como el primer intento (utilizando el Repository)
        DataStudentExamHistoryRepository.insert_exam_attempt(student_id, exam_id, attempt_number=1, is_completed=0)
        
        # 8. Calcular el puntaje por ejercicio
        points_per_exercise = total_points / limit
        
        # 9. Registrar cada ejercicio en data_exam_exercises.
        def level_to_difficulty(level):
            if level == 1:
                return "Easy"
            elif level == 2:
                return "Medium"
            else:
                return "Hard"
        
        exam_exercises_data = []
        for ex in exam_exercises:
            exam_exercises_data.append({
                "ExamID": exam_id,
                "ExerciseID": ex["ExerciseID"],
                "TopicID": ex["TopicID"],
                "DifficultyLevel": level_to_difficulty(ex["Level"]),
                "Points": points_per_exercise,
                "CreationUser": "system"
            })
        ExamRepository.insert_exam_exercises(exam_exercises_data)
        
        return {
            "ExamID": exam_id,
            "StudentID": student_id,
            "results": exam_exercises
        }

    def generate_entry_exam(self, student_id: str) -> dict:
        """
        Genera examen de entrada para alumno nuevo:
        5 preguntas por curso, temas distintos, basado en predicted_utility.
        """
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                raise Exception("Modelo de generación y ranking no encontrado. Entrénalo primero.")

        courses = DataTopicsRepository.get_all_courses()
        selected = []
        for course in courses:
            topic_ids = DataTopicsRepository.get_topic_ids_by_course(course)
            sampled = random.sample(topic_ids, min(5, len(topic_ids)))
            for tid in sampled:
                exs = DataExercisesRepository.get_exercises_by_topics([tid])
                if not exs:
                    continue
                df = pd.DataFrame(exs, columns=["ExerciseID","ExerciseCod","TopicID","Level","Points","topic_name"])
                df['NumberAttempt'] = 0
                df['predicted_utility'] = self.model.predict(df[['Points','Level','NumberAttempt']])
                top = df.sort_values('predicted_utility', ascending=False).iloc[0]
                selected.append({
                    "ExerciseCod": top["ExerciseCod"],
                    "ExerciseID": int(top["ExerciseID"]),
                    "Level": int(top["Level"]),
                    "Points": float(top["Points"]),
                    "TopicID": int(top["TopicID"]),
                    "predicted_utility": float(top["predicted_utility"]),
                    "topic_name": top["topic_name"]
                })
        if not selected:
            return {"message": "No se encontraron ejercicios para generar examen de entrada."}
        exam_id = ExamRepository.generate_exam_id()
        ExamRepository.insert_exam({
            "ExamID": exam_id,
            "ExamName": f"Examen de entrada {student_id}",
            "Description": "Diagnóstico inicial",
            "Subject": "Diagnóstico",
            "DurationMinutes": 60,
            "CreationUser": "system"
        })
        ExamRepository.insert_exam_exercises([
            {"ExamID":exam_id,"ExerciseID":it["ExerciseID"],"TopicID":it["TopicID"],"DifficultyLevel":"Medium","Points":it["Points"],"CreationUser":"system"}
            for it in selected
        ])
        DataStudentExamHistoryRepository.insert_exam_attempt(student_id, exam_id, 1, 0)
        return {
            "ExamID": exam_id, 
            "StudentID": student_id, 
            "results": selected
            }