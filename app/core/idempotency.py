import time
import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from app.core.logging import logger


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl_seconds = ttl_seconds
        # key -> {"job_id": str, "request_hash": str, "created_at": float, "response": dict}
        self._store: Dict[str, Dict[str, Any]] = {}

    def _cleanup_expired(self):
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if now - v["created_at"] > self.ttl_seconds]
        for k in expired_keys:
            del self._store[k]

    def compute_hash(self, payload: Any) -> str:
        if isinstance(payload, bytes):
            return hashlib.sha256(payload).hexdigest()
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        self._cleanup_expired()
        return self._store.get(key)

    def set(self, key: str, job_id: str, request_hash: str, response_data: Dict[str, Any]) -> None:
        self._cleanup_expired()
        self._store[key] = {
            "job_id": job_id,
            "request_hash": request_hash,
            "created_at": time.time(),
            "response": response_data,
        }
        logger.info(f"Stored idempotency record for key: {key} -> job: {job_id}")

    def update_response(self, key: str, response_data: Dict[str, Any]) -> None:
        if key in self._store:
            self._store[key]["response"] = response_data


idempotency_store = IdempotencyStore()
