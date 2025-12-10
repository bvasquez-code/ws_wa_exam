# myapp/service/MLGeneracionRankingService.py

import os
import joblib
import pandas as pd
import numpy as np
import random
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sqlalchemy import text

from myapp.repository.DataExercisesRepository import DataExercisesRepository
from myapp.repository.DataTopicsRepository import DataTopicsRepository
from myapp.repository.ExamRepository import ExamRepository
from myapp.repository.DataStudentExamHistoryRepository import DataStudentExamHistoryRepository
from myapp.model.entity.DataExamExercisesEntity import db
from myapp.service.MLDiagnosticoService import MLDiagnosticoService


class MLGeneracionRankingService:
    def __init__(self, model_path: str = None):
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
            # No lanzamos error aquí para permitir entrenar desde cero si se desea
            print(f"No se encontró el modelo de generación y ranking en: {self.model_path}. Será necesario entrenarlo.")

    # -------------------------------------------------------------------------
    # ENTRENAMIENTO DEL MODELO DE RANKING
    # -------------------------------------------------------------------------

    def train_model(self):
        """
        Actualiza los Points en data_exercises y entrena un modelo de regresión.
        Las features son: Points, Level y NumberAttempt; target:
            utility = (1 - SolvedCorrectly) / (NumberAttempt + 1).
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

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

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

    # -------------------------------------------------------------------------
    # UTILIDADES GENERALES
    # -------------------------------------------------------------------------

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

    @staticmethod
    def _get_student_history_count(student_id: str) -> int:
        """
        Retorna la cantidad de registros de historial del alumno en data_exam_results.
        """
        query = text("""
            SELECT COUNT(*) AS cnt
            FROM data_exam_results
            WHERE StudentID = :student_id
              AND Status = 'A'
        """)
        result = db.session.execute(query, {"student_id": student_id}).scalar()
        return int(result or 0)

    # -------------------------------------------------------------------------
    # SELECCIÓN DE EJERCICIOS (USANDO MODELO DE RANKING)
    # -------------------------------------------------------------------------

    def _select_exercises_for_course(self, course: str, quota: int) -> list:
        """
        Selecciona hasta 'quota' ejercicios para un curso dado.
        - Prioriza cubrir la mayor cantidad de temas posible (1 ejercicio por tema).
        - Si hay menos temas que quota, reutiliza temas escogiendo ejercicios adicionales,
          sin repetir el mismo ExerciseID.
        """
        if quota <= 0:
            return []

        topic_ids = DataTopicsRepository.get_topic_ids_by_course(course)
        if not topic_ids:
            return []

        # Aseguramos que el modelo de ranking está cargado
        self._ensure_model_loaded()

        # 1) Para cada tema, obtener lista de ejercicios ordenados por predicted_utility
        topic_exercises = {}  # { topic_id: [rows_ordenadas] }
        for tid in topic_ids:
            exs = DataExercisesRepository.get_exercises_by_topics([tid])
            if not exs:
                continue

            df = pd.DataFrame(
                exs,
                columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"]
            )
            df["NumberAttempt"] = 0
            df["predicted_utility"] = self.model.predict(
                df[["Points", "Level", "NumberAttempt"]]
            )

            df = df.sort_values("predicted_utility", ascending=False)
            topic_exercises[tid] = df.to_dict(orient="records")

        if not topic_exercises:
            return []

        selected_for_course = []

        # 2) Primera ronda: un ejercicio por tema (si hay más temas que quota, se limita)
        all_topic_ids = list(topic_exercises.keys())

        if len(all_topic_ids) > quota:
            all_topic_ids = random.sample(all_topic_ids, quota)

        for tid in all_topic_ids:
            if not topic_exercises[tid]:
                continue
            top = topic_exercises[tid].pop(0)
            selected_for_course.append({
                "ExerciseCod": top["ExerciseCod"],
                "ExerciseID": int(top["ExerciseID"]),
                "Level": int(top["Level"]),
                "Points": float(top["Points"]),  # se recalculará luego
                "TopicID": int(top["TopicID"]),
                "predicted_utility": float(top["predicted_utility"]),
                "topic_name": top["topic_name"]
            })
            if len(selected_for_course) >= quota:
                break

        # 3) Si aún faltan preguntas para llegar a quota, usar ejercicios restantes
        remaining_needed = quota - len(selected_for_course)
        if remaining_needed > 0:
            pool = []
            for _, rows in topic_exercises.items():
                pool.extend(rows)

            if pool:
                if len(pool) > remaining_needed:
                    pool = random.sample(pool, remaining_needed)

                for row in pool:
                    selected_for_course.append({
                        "ExerciseCod": row["ExerciseCod"],
                        "ExerciseID": int(row["ExerciseID"]),
                        "Level": int(row["Level"]),
                        "Points": float(row["Points"]),
                        "TopicID": int(row["TopicID"]),
                        "predicted_utility": float(row["predicted_utility"]),
                        "topic_name": row["topic_name"]
                    })

        return selected_for_course

    def _select_exercises_for_topics(self, topics: list, limit: int) -> list:
        """
        Selecciona hasta 'limit' ejercicios para una lista de topics dada,
        ordenados por predicted_utility.
        """
        if not topics or limit <= 0:
            return []

        self._ensure_model_loaded()

        exercises = DataExercisesRepository.get_exercises_by_topics(topics)
        if not exercises:
            return []

        df = pd.DataFrame(
            exercises,
            columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"]
        )
        df["NumberAttempt"] = 0
        df["predicted_utility"] = self.model.predict(
            df[["Points", "Level", "NumberAttempt"]]
        )

        df_ranked = df.sort_values("predicted_utility", ascending=False).head(limit)

        selected = []
        for _, row in df_ranked.iterrows():
            selected.append({
                "ExerciseCod": row["ExerciseCod"],
                "ExerciseID": int(row["ExerciseID"]),
                "Level": int(row["Level"]),
                "Points": float(row["Points"]),  # se recalculará luego
                "TopicID": int(row["TopicID"]),
                "predicted_utility": float(row["predicted_utility"]),
                "topic_name": row["topic_name"]
            })
        return selected

    def _persist_entry_exam(self, student_id: str, selected: list, description: str) -> dict:
        """
        Persiste en BD un examen de entrada de 20 puntos basado en la lista de ejercicios 'selected'.
        """
        if not selected:
            return {"message": "No se encontraron ejercicios para generar examen de entrada."}

        # Mezclar aleatoriamente
        random.shuffle(selected)

        # Recalcular puntos para que el examen valga 20
        self._recalculate_points_for_exam(selected, total_points=20)

        # Crear examen en BD
        exam_id = ExamRepository.generate_exam_id()
        ExamRepository.insert_exam({
            "ExamID": exam_id,
            "ExamName": f"Examen de entrada {student_id}",
            "Description": description,
            "Subject": "Diagnóstico",
            "DurationMinutes": 60,
            "CreationUser": "system"
        })

        # Insertar ejercicios
        ExamRepository.insert_exam_exercises([
            {
                "ExamID": exam_id,
                "ExerciseID": it["ExerciseID"],
                "TopicID": it["TopicID"],
                "DifficultyLevel": "Medium",
                "Points": it["Points"],
                "CreationUser": "system"
            }
            for it in selected
        ])

        # Registrar intento inicial
        DataStudentExamHistoryRepository.insert_exam_attempt(student_id, exam_id, 1, 0)

        return {
            "ExamID": exam_id,
            "StudentID": student_id,
            "results": selected
        }

    # -------------------------------------------------------------------------
    # EXÁMENES GENERALES (ya existentes)
    # -------------------------------------------------------------------------

    def generate_exam(self, student_id: str, weak_topics: list):
        """
        Genera un examen personalizado usando ejercicios de data_exercises para los tópicos débiles.
        Construye el vector de características [Points, Level, NumberAttempt=0] para cada ejercicio,
        predice la utilidad y rankea los ejercicios. (No persiste en BD).
        """
        exercises = DataExercisesRepository.get_exercises_by_topics(weak_topics)
        if not exercises:
            return {"message": "No se encontraron ejercicios para los temas débiles proporcionados."}

        df_exercises = pd.DataFrame(
            exercises,
            columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"]
        )
        features = df_exercises[['Points', 'Level']].copy()
        features['NumberAttempt'] = 0
        X_candidates = features[['Points', 'Level', 'NumberAttempt']]

        self._ensure_model_loaded()

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
        """
        exercises = DataExercisesRepository.get_exercises_by_topics(topics)
        if not exercises:
            return {"message": "No se encontraron ejercicios para los topics proporcionados."}

        df_exercises = pd.DataFrame(
            exercises,
            columns=["ExerciseID", "ExerciseCod", "TopicID", "Level", "Points", "topic_name"]
        )
        features = df_exercises[['Points', 'Level']].copy()
        features['NumberAttempt'] = 0
        X_candidates = features[['Points', 'Level', 'NumberAttempt']]

        self._ensure_model_loaded()

        df_exercises['predicted_utility'] = self.model.predict(X_candidates)
        df_ranked = df_exercises.sort_values(by='predicted_utility', ascending=False).head(limit)
        exam_exercises = df_ranked.to_dict(orient='records')

        exam_id = ExamRepository.generate_exam_id()

        exam_data = {
            "ExamID": exam_id,
            "ExamName": f"Examen personalizado para {student_id}",
            "Description": "Examen generado automáticamente basado en los topics proporcionados.",
            "Subject": "Personalizado",
            "DurationMinutes": 60,
            "CreationUser": "system"
        }
        ExamRepository.insert_exam(exam_data)

        DataStudentExamHistoryRepository.insert_exam_attempt(
            student_id, exam_id, attempt_number=1, is_completed=0
        )

        points_per_exercise = total_points / limit

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

    # -------------------------------------------------------------------------
    # EXAMEN DE ENTRADA (DOS CAMINOS)
    # -------------------------------------------------------------------------

    def _generate_entry_exam_initial(self, student_id: str) -> dict:
        """
        Camino 1: Alumno sin historial suficiente.
        Examen de entrada diagnóstico general (solo modelo de ranking).
        """
        courses = DataTopicsRepository.get_all_courses()
        quotas = self._compute_course_quotas(courses, total_questions=20)

        if not quotas:
            return {"message": "No hay cursos configurados para generar examen de entrada."}

        selected = []
        for course, quota in quotas.items():
            selected.extend(self._select_exercises_for_course(course, quota))

        return self._persist_entry_exam(student_id, selected, "Diagnóstico inicial")

    def _generate_entry_exam_personalized(self, student_id: str) -> dict:
        """
        Camino 2: Alumno con historial suficiente.
        Usa el modelo de diagnóstico para encontrar temas débiles y el modelo de ranking
        para seleccionar las mejores preguntas de esos temas.
        """
        diag_service = MLDiagnosticoService()
        diag_result = diag_service.analyze_student_performance(student_id)

        weak_topics = diag_result.get("weak_topics", []) or []

        # Si no hay débiles explícitos, usamos todos los temas del alumno como fallback
        if not weak_topics:
            detailed = diag_result.get("detailed", []) or []
            weak_topics = [row["TopicID"] for row in detailed]

        # Si aun así no hay topics, usamos el camino inicial como fallback
        if not weak_topics:
            return self._generate_entry_exam_initial(student_id)

        selected = self._select_exercises_for_topics(weak_topics, limit=20)

        return self._persist_entry_exam(
            student_id,
            selected,
            "Diagnóstico personalizado según desempeño"
        )

    def generate_entry_exam(self, student_id: str) -> dict:
        """
        Genera examen de entrada para un alumno:
        - Si el alumno NO tiene suficiente historial en data_exam_results:
            Camino 1 -> examen diagnóstico general (solo ranking).
        - Si el alumno YA tiene historial suficiente:
            Camino 2 -> diagnóstico por temas (MLDiagnosticoService) + ranking por ejercicios.
        En ambos casos:
            - Máximo 20 preguntas.
            - El examen vale 20 puntos en total.
        """
        # Aseguramos tener el modelo de ranking disponible
        self._ensure_model_loaded()

        MIN_HISTORY = 10  # puedes ajustar este umbral según lo que consideres "historial suficiente"
        history_count = self._get_student_history_count(student_id)

        if history_count < MIN_HISTORY:
            # Alumno "nuevo" -> examen diagnóstico general
            return self._generate_entry_exam_initial(student_id)
        else:
            # Alumno con historial -> examen basado en debilidades + ranking
            return self._generate_entry_exam_personalized(student_id)
