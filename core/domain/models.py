from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Task(BaseModel):
    id: str
    name: str
    doc_path: str
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    branch_name: Optional[str] = None
    retries: int = 0

class Pipeline(BaseModel):
    project_name: str
    concurrency_limit: int = 3
    tasks: List[Task]
    
    def get_ready_tasks(self) -> List[Task]:
        """Returns tasks that have no incomplete dependencies."""
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        ready = []
        for task in self.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.READY):
                if all(dep in completed_ids for dep in task.dependencies):
                    ready.append(task)
        return ready