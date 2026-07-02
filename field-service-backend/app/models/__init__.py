# Importing all models here ensures SQLAlchemy's mapper registry is fully
# populated before Alembic's autogenerate runs or the engine creates tables.
from app.models.photo import Photo
from app.models.sync_log import SyncLog
from app.models.task import Task
from app.models.task_report import TaskReport
from app.models.user import User

__all__ = ["User", "Task", "TaskReport", "Photo", "SyncLog"]
