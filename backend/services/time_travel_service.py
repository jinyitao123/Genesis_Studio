from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING
from typing import TypedDict
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..config import load_settings
from ..ontology.deps import create_repository
from .backend_clients import TimeseriesBackendClient

if TYPE_CHECKING:
    from ..ontology.repository import Neo4jOntologyRepository


class TelemetryPoint(TypedDict):
    entity_id: str
    property_name: str
    value: float | int | str | bool
    tick: int
    timestamp: str


class PropertyHistoryPoint(TypedDict):
    timestamp: str
    value: float | int | str | bool
    tick: int


class TimeTravelService:
    service_name = "time-travel-service"
    RETENTION_RAW = 7
    RETENTION_DOWNSAMPLED = 90
    RETENTION_ARCHIVE = 365
    TELEMETRY_BUFFER_MS = 100
    
    def __init__(self) -> None:
        self._backend = TimeseriesBackendClient()
        self._telemetry_buffer: list[TelemetryPoint] = []
        self._buffer_lock = threading.Lock()
        self._running = False
        self._buffer_thread: threading.Thread | None = None
        self._start_buffer_flush()
    
    def _start_buffer_flush(self) -> None:
        if self._running:
            return
        self._running = True
        self._buffer_thread = threading.Thread(target=self._buffer_flush_loop, daemon=True)
        self._buffer_thread.start()
    
    def _buffer_flush_loop(self) -> None:
        import time
        while self._running:
            try:
                import asyncio
                asyncio.run(self._flush_buffer())
            except Exception:
                pass
            time.sleep(self.TELEMETRY_BUFFER_MS / 1000)
    
    async def _flush_buffer(self) -> None:
        with self._buffer_lock:
            if not self._telemetry_buffer:
                return
            points = self._telemetry_buffer.copy()
            self._telemetry_buffer.clear()
        if points and self._backend.is_configured():
            bulk_insert = getattr(self._backend, "bulk_insert_telemetry", None)
            if callable(bulk_insert):
                bulk_insert(points)
    
    def record_telemetry(
        self,
        entity_id: str,
        property_name: str,
        value: float | int | str | bool,
        tick: int,
        timestamp: str | None = None
    ) -> dict[str, object]:
        point: TelemetryPoint = {
            "entity_id": entity_id,
            "property_name": property_name,
            "value": value,
            "tick": tick,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        }
        with self._buffer_lock:
            self._telemetry_buffer.append(point)
        return {
            "service": self.service_name,
            "status": "buffered",
            "entity_id": entity_id,
            "property": property_name,
            "tick": tick,
            "buffer_size": len(self._telemetry_buffer),
        }
    
    def batch_record_telemetry(self, points: list[TelemetryPoint]) -> dict[str, object]:
        with self._buffer_lock:
            self._telemetry_buffer.extend(points)
        return {
            "service": self.service_name,
            "status": "recorded",
            "points_count": len(points),
            "total_buffered": len(self._telemetry_buffer),
        }
    
    def get_world_snapshot(self, tick: int) -> dict[str, object]:
        """Get a snapshot of the world at a specific tick.

        Args:
            tick: The simulation tick to snapshot

        Returns:
            World snapshot with entities, links, and properties
        """
        # Get entities and links at this tick from Neo4j
        settings = load_settings()
        repo = create_repository(settings)
        try:
            entities = repo.list_graph_nodes()
            links = repo.list_graph_edges()
        finally:
            repo.close()
        
        return {
            "snapshot_id": f"snap_{tick}_{int(datetime.now(timezone.utc).timestamp())}",
            "tick": tick,
            "entities": entities,
            "links": links,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def snapshot(self, entity_id: str, at_ts: str | None = None) -> dict[str, object]:
        """Alias for get_world_snapshot for API compatibility."""
        tick = 0  # Default to current tick
        if at_ts:
            # Parse timestamp and convert to tick
            try:
                dt = datetime.fromisoformat(at_ts.replace("Z", "+00:00"))
                tick = int(dt.timestamp())
            except ValueError:
                tick = 0
        return self.get_world_snapshot(tick)

    def get_property_history(
        self,
        entity_id: str,
        property_name: str,
        start_tick: int | None = None,
        end_tick: int | None = None
    ) -> dict[str, object]:
        if self._backend.is_configured():
            query_history = getattr(self._backend, "query_property_history", None)
            history = query_history(entity_id, property_name, start_tick, end_tick) if callable(query_history) else None
            if isinstance(history, list):
                return {
                    "service": self.service_name,
                    "entity_id": entity_id,
                    "property": property_name,
                    "data_points": len(history),
                    "history": history,
                }
        settings = load_settings()
        repo = create_repository(settings)
        try:
            events = repo.list_events()
        finally:
            repo.close()
        relevant = [
            e for e in events
            if e.source_id == entity_id and getattr(e, 'property_name', None) == property_name
            and (start_tick is None or int(getattr(e, "tick", 0)) >= start_tick)
            and (end_tick is None or int(getattr(e, "tick", 0)) <= end_tick)
        ]
        history = [
            {
                "timestamp": e.created_at,
                "value": getattr(e, "value", None),
                "tick": int(getattr(e, "tick", 0)),
            }
            for e in sorted(relevant, key=lambda item: int(getattr(item, "tick", 0)))
        ]
        return {
            "service": self.service_name,
            "entity_id": entity_id,
            "property": property_name,
            "data_points": len(history),
            "history": history,
        }
    
    def compare_snapshots(self, snapshot_id_a: str, snapshot_id_b: str) -> dict[str, object]:
        return {
            "service": self.service_name,
            "snapshot_a": snapshot_id_a,
            "snapshot_b": snapshot_id_b,
            "status": "not_implemented",
        }
    
    def align_to_tick(self, wall_clock: str) -> dict[str, object]:
        try:
            dt = datetime.fromisoformat(wall_clock.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
        tick_rate = 60
        sim_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        elapsed = (dt - sim_start).total_seconds()
        aligned_tick = int(elapsed * tick_rate)
        return {
            "service": self.service_name,
            "wall_clock": dt.isoformat(),
            "aligned_tick": aligned_tick,
            "tick_rate": tick_rate,
        }
    
    def get_retention_status(self) -> dict[str, object]:
        return {
            "service": self.service_name,
            "policies": {
                "raw": {"retention_days": self.RETENTION_RAW},
                "downsampled": {"retention_days": self.RETENTION_DOWNSAMPLED},
                "archive": {"retention_days": self.RETENTION_ARCHIVE},
            },
        }
    
    def flush(self) -> dict[str, object]:
        import asyncio
        asyncio.run(self._flush_buffer())
        return {"service": self.service_name, "status": "flushed", "buffer_size": 0}
    
    def shutdown(self) -> None:
        self._running = False
        self.flush()
