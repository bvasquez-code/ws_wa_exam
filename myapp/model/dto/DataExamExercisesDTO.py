# myapp/model/dto/DataExamExercisesDTO.py

from myapp.model.entity.DataExamExercisesEntity import DataExamExercisesEntity

class DataExamExercisesDTO:
    def __init__(self, exam_id, exercise_id, topic_id, difficulty_level, points, creation_user, creation_date, modify_user, modify_date, status):
        self.ExamID = exam_id
        self.ExerciseID = exercise_id
        self.TopicID = topic_id
        self.DifficultyLevel = difficulty_level
        self.Points = points
        self.CreationUser = creation_user
        self.CreationDate = creation_date
        self.ModifyUser = modify_user
        self.ModifyDate = modify_date
        self.Status = status

    @classmethod
    def from_entity(cls, entity: DataExamExercisesEntity):
        return cls(
            exam_id=entity.ExamID,
            exercise_id=entity.ExerciseID,
            topic_id=entity.TopicID,
            difficulty_level=entity.DifficultyLevel,
            points=entity.Points,
            creation_user=entity.CreationUser,
            creation_date=entity.CreationDate,
            modify_user=entity.ModifyUser,
            modify_date=entity.ModifyDate,
            status=entity.Status
        )
    
    def to_dict(self):
        return {
            'ExamID': self.ExamID,
            'ExerciseID': self.ExerciseID,
            'TopicID': self.TopicID,
            'DifficultyLevel': self.DifficultyLevel,
            'Points': self.Points,
            'CreationUser': self.CreationUser,
            'CreationDate': self.CreationDate.isoformat() if self.CreationDate else None,
            'ModifyUser': self.ModifyUser,
            'ModifyDate': self.ModifyDate.isoformat() if self.ModifyDate else None,
            'Status': self.Status
        }
