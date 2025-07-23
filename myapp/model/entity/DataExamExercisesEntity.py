# myapp/model/entity/DataExamExercisesEntity.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DataExamExercisesEntity(db.Model):
    __tablename__ = 'data_exam_exercises'
    
    ExamID = db.Column(db.String(10), primary_key=True, nullable=False, comment='Identifier for the exam')
    ExerciseID = db.Column(db.Integer, primary_key=True, nullable=False, comment='Identifier for the exercise')
    TopicID = db.Column(db.Integer, nullable=False, comment='Identifier for the topic the exercise belongs to')
    DifficultyLevel = db.Column(db.String(10), nullable=False, comment='Difficulty level of the exercise (e.g., Easy, Medium, Hard)')
    Points = db.Column(db.Integer, nullable=False, comment='Points assigned to this exercise')
    CreationUser = db.Column(db.String(16), nullable=False, comment='User who created the record')
    CreationDate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='Creation date')
    ModifyUser = db.Column(db.String(16), nullable=True, comment='User who last modified the record')
    ModifyDate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='Last modification date')
    Status = db.Column(db.CHAR(1), nullable=False, default='A', comment='Record status (A: Active, I: Inactive)')
    
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
