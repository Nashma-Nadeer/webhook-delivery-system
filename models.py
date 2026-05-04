import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum
from database import Base
import enum

class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class WebhookTask(Base):
    __tablename__ = "webhook_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target_url = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
