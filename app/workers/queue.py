import asyncio
from typing import Dict, Optional, List
from app.models.job import JobRecord
from app.core.logging import logger
from app.config import settings


class JobRepository:
    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    def save(self, job: JobRecord) -> None:
        self._jobs[job.job_id] = job

    def list_all(self) -> List[JobRecord]:
        return list(self._jobs.values())


job_repo = JobRepository()

_job_queue: Optional[asyncio.Queue] = None


def get_job_queue() -> asyncio.Queue:
    global _job_queue
    if _job_queue is None:
        _job_queue = asyncio.Queue()
    return _job_queue
