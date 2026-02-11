from __future__ import annotations

import os
from importlib import import_module
from typing import Any


broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

Celery: Any = getattr(import_module("celery"), "Celery")

celery_app = Celery("genesis_workers", broker=broker_url, backend=result_backend)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["backend.workers"])
