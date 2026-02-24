from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from ..config import load_settings

logger = logging.getLogger(__name__)


class TimescaleAdapter:
    """Production-grade TimescaleDB adapter for Genesis Studio timeseries backend."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if TimescaleAdapter._initialized:
            return
        
        self._settings = load_settings()
        self._connection_params: dict[str, Any] | None = None
        TimescaleAdapter._initialized = True

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.timeseries_backend_url)

    def _get_connection_params(self) -> dict[str, Any] | None:
        """Parse connection URL into psycopg2 parameters."""
        if not self.is_configured:
            return None
        
        if self._connection_params is None:
            try:
                # Parse postgres://user:pass@host:port/dbname format
                url = self._settings.timeseries_backend_url
                if url.startswith("postgres://") or url.startswith("postgresql://"):
                    # Simple URL parsing
                    url = url.replace("postgres://", "").replace("postgresql://", "")
                    if "@" in url:
                        auth, rest = url.split("@", 1)
                        if ":" in auth:
                            user, password = auth.split(":", 1)
                        else:
                            user, password = auth, ""
                        
                        if "/" in rest:
                            host_port, dbname = rest.split("/", 1)
                            if ":" in host_port:
                                host, port = host_port.rsplit(":", 1)
                                port = int(port)
                            else:
                                host, port = host_port, 5432
                        else:
                            host, port, dbname = rest, 5432, "postgres"
                        
                        self._connection_params = {
                            "host": host,
                            "port": port,
                            "dbname": dbname,
                            "user": user,
                            "password": password,
                        }
            except Exception as e:
                logger.warning(f"Failed to parse TimescaleDB URL: {e}")
                return None
        
        return self._connection_params

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
        """Context manager for database connections."""
        params = self._get_connection_params()
        if not params:
            yield None
            return
        
        conn = None
        try:
            conn = psycopg2.connect(**params)
            yield conn
        except Exception as e:
            logger.warning(f"TimescaleDB connection failed: {e}")
            yield None
        finally:
            if conn:
                conn.close()

    def ensure_schema(self) -> bool:
        """Create timeseries table and hypertable if not exists."""
        if not self.is_configured:
            return False
        
        with self._get_connection() as conn:
            if not conn:
                return False
            
            try:
                with conn.cursor() as cur:
                    # Create events table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS genesis_events (
                            event_id VARCHAR(64) PRIMARY KEY,
                            event_type VARCHAR(64) NOT NULL,
                            action_id VARCHAR(128),
                            source_id VARCHAR(256),
                            target_id VARCHAR(256),
                            actor VARCHAR(128),
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            payload JSONB,
                            correlation_id VARCHAR(256),
                            causation_id VARCHAR(256)
                        )
                    """)
                    
                    # Convert to hypertable if TimescaleDB extension is available
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                                PERFORM create_hypertable('genesis_events', 'created_at', 
                                    if_not_exists => TRUE, migrate_data => TRUE);
                            END IF;
                        END
                        $$;
                    """)
                    
                    # Create indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_events_created_at 
                        ON genesis_events (created_at DESC)
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_events_source_id 
                        ON genesis_events (source_id)
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_events_target_id 
                        ON genesis_events (target_id)
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_events_action_id 
                        ON genesis_events (action_id)
                    """)
                    
                conn.commit()
                logger.info("TimescaleDB schema initialized")
                return True
            except Exception as e:
                logger.warning(f"Failed to create TimescaleDB schema: {e}")
                conn.rollback()
                return False

    def insert_event(self, event: dict[str, Any]) -> bool:
        """Insert a single event into timeseries."""
        if not self.is_configured:
            return False
        
        with self._get_connection() as conn:
            if not conn:
                return False
            
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO genesis_events 
                        (event_id, event_type, action_id, source_id, target_id, actor, 
                         created_at, payload, correlation_id, causation_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id) DO NOTHING
                    """, (
                        event.get("event_id"),
                        event.get("event_type", "Unknown"),
                        event.get("action_id"),
                        event.get("source_id"),
                        event.get("target_id"),
                        event.get("actor"),
                        event.get("created_at") or datetime.now(timezone.utc),
                        event.get("payload"),
                        event.get("correlation_id"),
                        event.get("causation_id"),
                    ))
                conn.commit()
                return True
            except Exception as e:
                logger.warning(f"Failed to insert event: {e}")
                conn.rollback()
                return False

    def bulk_insert_events(self, events: list[dict[str, Any]]) -> int:
        """Bulk insert multiple events. Returns count of inserted rows."""
        if not self.is_configured or not events:
            return 0
        
        with self._get_connection() as conn:
            if not conn:
                return 0
            
            try:
                with conn.cursor() as cur:
                    from psycopg2.extras import execute_values
                    
                    values = [
                        (
                            e.get("event_id"),
                            e.get("event_type", "Unknown"),
                            e.get("action_id"),
                            e.get("source_id"),
                            e.get("target_id"),
                            e.get("actor"),
                            e.get("created_at") or datetime.now(timezone.utc),
                            e.get("payload"),
                            e.get("correlation_id"),
                            e.get("causation_id"),
                        )
                        for e in events
                    ]
                    
                    execute_values(cur, """
                        INSERT INTO genesis_events 
                        (event_id, event_type, action_id, source_id, target_id, actor, 
                         created_at, payload, correlation_id, causation_id)
                        VALUES %s
                        ON CONFLICT (event_id) DO NOTHING
                    """, values)
                conn.commit()
                return len(values)
            except Exception as e:
                logger.warning(f"Failed to bulk insert events: {e}")
                conn.rollback()
                return 0

    def query_events(
        self, 
        entity_id: str | None = None,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]] | None:
        """Query events by entity and time range."""
        if not self.is_configured:
            return None
        
        with self._get_connection() as conn:
            if not conn:
                return None
            
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT * FROM genesis_events 
                        WHERE 1=1
                    """
                    params = []
                    
                    if entity_id:
                        query += " AND (source_id = %s OR target_id = %s)"
                        params.extend([entity_id, entity_id])
                    
                    if start_ts:
                        query += " AND created_at >= %s"
                        params.append(start_ts)
                    
                    if end_ts:
                        query += " AND created_at <= %s"
                        params.append(end_ts)
                    
                    query += " ORDER BY created_at DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"Failed to query events: {e}")
                return None

    def get_stats(self) -> dict[str, Any]:
        """Get table statistics."""
        if not self.is_configured:
            return {"connected": False, "row_count": 0}
        
        with self._get_connection() as conn:
            if not conn:
                return {"connected": False, "row_count": 0}
            
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM genesis_events")
                    count = cur.fetchone()[0]
                    return {"connected": True, "row_count": count}
            except Exception as e:
                return {"connected": False, "error": str(e), "row_count": 0}


def get_timescale_adapter() -> TimescaleAdapter:
    """Factory function to get singleton TimescaleDB adapter instance."""
    return TimescaleAdapter()
