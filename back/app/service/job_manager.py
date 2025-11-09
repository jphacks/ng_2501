import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class JobRecord:
    status: JobStatus
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = field(default=None)


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = JobRecord(status=JobStatus.QUEUED)
        return job_id

    def mark_running(self, job_id: str):
        self._update_job(job_id, status=JobStatus.RUNNING)

    def mark_succeeded(self, job_id: str, message: Optional[str], result: Optional[Dict[str, Any]]):
        self._update_job(job_id, status=JobStatus.SUCCEEDED, message=message, result=result)

    def mark_failed(self, job_id: str, message: Optional[str], result: Optional[Dict[str, Any]] = None):
        self._update_job(job_id, status=JobStatus.FAILED, message=message, result=result)

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return JobRecord(status=job.status, message=job.message, result=job.result.copy() if job.result else None)

    def as_response(self, job_id: str) -> Optional[Dict[str, Any]]:
        record = self.get_job(job_id)
        if not record:
            return None
        payload: Dict[str, Any] = {
            "job_id": job_id,
            "status": record.status,
            "message": record.message,
        }
        if record.result:
            payload.update(record.result)
        return payload

    def _update_job(
        self,
        job_id: str,
        *,
        status: Optional[JobStatus] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ):
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            if status:
                record.status = status
            if message is not None:
                record.message = message
            if result is not None:
                record.result = result


job_manager = JobManager()
