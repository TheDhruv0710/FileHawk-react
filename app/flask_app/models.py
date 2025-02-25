from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(100), unique=True, nullable=False)
    schedule = db.Column(db.String(50), nullable=False)  # Cron expression
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    server_key = db.Column(db.String(50), nullable=False)
    retries = db.Column(db.Integer, default=3)
    retry_delay = db.Column(db.Integer, default=60)  # Seconds
    timeout = db.Column(db.Integer, default=120)
    dependency_server_key = db.Column(db.String(50), nullable=True)
    command = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='WAITING')

    def __repr__(self):
        return f"<Schedule {self.task_id}>"


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(100))
    action = db.Column(db.String(255))
    details = db.Column(db.Text)