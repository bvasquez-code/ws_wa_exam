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
    def __init__(self, model_path : str = None):
        if model_path:
            self.model_path = model_path
        else:
            # __file__ -> .../myapp/service/MLGeneracionRankingService.py
            svc_dir = os.path.dirname(os.path.abspath(__file__))
            # Sube dos niveles para llegar a la raíz del proyecto (/app)
            project_root = os.path.dirname(os.path.dirname(svc_dir))
            # Apunta al modelo dentro de model/
            self.model_path = os.path.join(project_root, 'model', 'generation_ranking_model.pkl')

        self.model = None

        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print("Modelo de generación y ranking cargado desde:", self.model_path)
        else:
            raise FileNotFoundError(f"No se encontró el modelo en: {self.model_path}")
    
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

    def _ensure_model_loaded(self):
        """
        Carga el modelo en memoria si aún no está cargado.
        Lanza excepción si no existe el archivo del modelo.
        """
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print("Modelo de generación y ranking cargado desde:", self.model_path)
            else:
                raise Exception("Modelo de generación y ranking no encontrado. Entrénalo primero.")

    @staticmethod
    def _compute_course_quotas(courses, total_questions: int = 20) -> dict:
        """
        Calcula cuántas preguntas le corresponden a cada curso,
        con las siguientes reglas:

        - Máximo total_questions (20) preguntas en el examen.
        - Si hay más de total_questions cursos, se seleccionan aleatoriamente
          total_questions cursos y a cada uno se le asigna 1 pregunta.
        - Si hay 1 curso: se le asignan hasta total_questions preguntas.
        - Si hay entre 2 y total_questions cursos:
            base = total_questions // num_courses
            remainder = total_questions % num_courses
            A los primeros 'remainder' cursos se les asigna base + 1,
            al resto base. La suma total es exactamente total_questions.
        """
        if not courses:
            return {}

        # Si hay más cursos que preguntas máximas, limitar a un subset aleatorio
        if len(courses) > total_questions:
            courses = random.sample(courses, total_questions)

        num_courses = len(courses)
        quotas = {}

        if num_courses == 1:
            # Un solo curso: hasta total_questions preguntas
            quotas[courses[0]] = total_questions
            return quotas

        # Para 2 <= num_courses <= total_questions
        base = total_questions // num_courses
        remainder = total_questions % num_courses

        for idx, course in enumerate(courses):
            if idx < remainder:
                quotas[course] = base + 1
            else:
                quotas[course] = base

        return quotas

    @staticmethod
    def _recalculate_points_for_exam(selected: list, total_points: int = 20) -> None:
        """
        Recalcula los puntos de cada pregunta de forma que:
        - Todos sean enteros.
        - La suma total sea total_points (20).
        Modifica la lista 'selected' in-place, asignando la clave "Points".
        """
        n = len(selected)
        if n == 0:
            return

        base = total_points // n
        remainder = total_points % n

        # Asignar base + 1 a las primeras 'remainder' preguntas,
        # y base al resto.
        for idx, item in enumerate(selected):
            if idx < remainder:
                item["Points"] = base + 1
            else:
                item["Points"] = base

    def generate_entry_exam(self, student_id: str) -> dict:
        """
        Genera examen de entrada para alumno nuevo:
        - Máximo 20 preguntas en total.
        - Distribución de preguntas por curso según número de cursos:
            * 1 curso  -> hasta 20 preguntas de ese curso.
            * 2..20    -> se reparten exactamente 20 preguntas entre los cursos.
            * >20      -> se eligen aleatoriamente 20 cursos, 1 pregunta por curso.
        - Dentro de cada curso:
            * Se eligen temas aleatorios según la cuota de preguntas.
            * Por cada tema, se selecciona el ejercicio con mayor predicted_utility.
        - Los puntos se recalculan para que el examen completo valga 20 puntos.
        """
        # 1) Asegurar modelo en memoria
        self._ensure_model_loaded()

        # 2) Obtener cursos y calcular cuotas de preguntas por curso
        courses = DataTopicsRepository.get_all_courses()
        quotas = self._compute_course_quotas(courses, total_questions=20)

        if not quotas:
            return {"message": "No hay cursos configurados para generar examen de entrada."}

        selected = []

        # 3) Para cada curso, seleccionar preguntas según la cuota
        for course, quota in quotas.items():
            if quota <= 0:
                continue

            topic_ids = DataTopicsRepository.get_topic_ids_by_course(course)
            if not topic_ids:
                continue

            # Elegir hasta 'quota' temas aleatorios de este curso
            num_topics = min(quota, len(topic_ids))
            sampled_topics = random.sample(topic_ids, num_topics)

            for tid in sampled_topics:
                exs = DataExercisesRepository.get_exercises_by_topics([tid])
                if not exs:
                    continue

                # Se asume que exs es una lista de tuplas o dicts compatibles con estas columnas
                df = pd.DataFrame(
                    exs,
                    columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"]
                )

                # NumberAttempt = 0 para examen de entrada
                df["NumberAttempt"] = 0

                # Predecir utilidad del ejercicio según el modelo
                # (se usan los puntos originales, nivel y número de intentos = 0)
                df["predicted_utility"] = self.model.predict(
                    df[["Points", "Level", "NumberAttempt"]]
                )

                # Elegir el ejercicio con mayor predicted_utility
                top = df.sort_values("predicted_utility", ascending=False).iloc[0]

                selected.append({
                    "ExerciseCod": top["ExerciseCod"],
                    "ExerciseID": int(top["ExerciseID"]),
                    "Level": int(top["Level"]),
                    # Points se recalcularán luego, pero guardamos el original por si se requiere
                    "Points": float(top["Points"]),
                    "TopicID": int(top["TopicID"]),
                    "predicted_utility": float(top["predicted_utility"]),
                    "topic_name": top["topic_name"]
                })

        # Si no se seleccionó ningún ejercicio
        if not selected:
            return {"message": "No se encontraron ejercicios para generar examen de entrada."}

        # 4) Chocolatear (mezclar aleatoriamente las preguntas)
        random.shuffle(selected)

        # 5) Recalcular los puntos para que el examen valga 20 en total
        self._recalculate_points_for_exam(selected, total_points=20)

        # 6) Crear examen en BD
        exam_id = ExamRepository.generate_exam_id()
        ExamRepository.insert_exam({
            "ExamID": exam_id,
            "ExamName": f"Examen de entrada {student_id}",
            "Description": "Diagnóstico inicial",
            "Subject": "Diagnóstico",
            "DurationMinutes": 60,
            "CreationUser": "system"
        })

        # 7) Insertar ejercicios del examen con los puntos ya recalculados
        ExamRepository.insert_exam_exercises([
            {
                "ExamID": exam_id,
                "ExerciseID": it["ExerciseID"],
                "TopicID": it["TopicID"],
                "DifficultyLevel": "Medium",
                "Points": it["Points"],       # puntos ajustados para sumar 20
                "CreationUser": "system"
            }
            for it in selected
        ])

        # 8) Registrar intento inicial del alumno
        DataStudentExamHistoryRepository.insert_exam_attempt(student_id, exam_id, 1, 0)

        # 9) Respuesta
        return {
            "ExamID": exam_id,
            "StudentID": student_id,
            "results": selected
        }