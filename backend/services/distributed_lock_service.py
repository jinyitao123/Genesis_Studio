"""Redis Distributed Lock Service for Genesis Studio.

Provides distributed locking capabilities for:
- Action Dispatch (entity-level locks)
- Schema mutations
- Projection updates
- Concurrent access control

Features:
- Redlock algorithm support
- Automatic lock renewal (heartbeat)
- Lock timeout and expiry
- Safe release with Lua script
"""

from __future__ import annotations

import asyncio
import uuid
import time
from datetime import datetime, timezone
from typing import Callable, Any, TypedDict
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.exceptions import LockError, LockNotOwnedError

from ..config import load_settings


class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired."""
    pass


class LockExtensionError(Exception):
    """Raised when lock extension fails."""
    pass


class LockInfo(TypedDict):
    """Lock metadata returned to callers."""
    lock_id: str
    resource: str
    owner: str
    acquired_at: str
    expires_at: str
    ttl_seconds: int


class DistributedLockService:
    """Redis-based distributed locking service.
    
    Implements the Redlock algorithm for distributed locks.
    Supports automatic renewal and safe release.
    """
    
    service_name = "distributed-lock-service"
    
    # Default lock durations (seconds)
    DEFAULT_LOCK_TTL = 30  # 30 seconds
    ENTITY_LOCK_TTL = 60  # 60 seconds for entity operations
    SCHEMA_LOCK_TTL = 120  # 2 minutes for schema mutations
    
    # Lock prefixes
    ENTITY_LOCK_PREFIX = "lock:entity:"
    SCHEMA_LOCK_PREFIX = "lock:schema:"
    ACTION_LOCK_PREFIX = "lock:action:"
    PROJECTION_LOCK_PREFIX = "lock:projection:"
    
    # Heartbeat interval (should be less than TTL)
    HEARTBEAT_INTERVAL = 10  # seconds
    
    def __init__(self) -> None:
        settings = load_settings()
        redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
        
        self._redis = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._owner = f"genesis-{uuid.uuid4().hex[:8]}"
        self._active_locks: dict[str, str] = {}  # lock_key -> lock_id
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}
    
    async def health_check(self) -> dict[str, object]:
        """Check Redis connectivity."""
        try:
            await self._redis.ping()
            return {
                "service": self.service_name,
                "status": "healthy",
                "redis": "connected",
                "active_locks": len(self._active_locks),
            }
        except Exception as e:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "redis": "disconnected",
                "error": str(e),
            }
    
    async def acquire_entity_lock(
        self,
        entity_id: str,
        ttl: int | None = None,
        timeout: int = 10,
        blocking: bool = True,
    ) -> LockInfo | None:
        """Acquire a lock on an entity for mutation operations.
        
        Args:
            entity_id: Entity to lock
            ttl: Lock duration in seconds (default: ENTITY_LOCK_TTL)
            timeout: Max time to wait for lock acquisition
            blocking: Whether to wait for lock
            
        Returns:
            LockInfo dict if acquired, None otherwise
        """
        lock_key = f"{self.ENTITY_LOCK_PREFIX}{entity_id}"
        ttl = ttl or self.ENTITY_LOCK_TTL
        
        return await self._acquire_lock(
            lock_key=lock_key,
            resource=entity_id,
            ttl=ttl,
            timeout=timeout,
            blocking=blocking,
        )
    
    async def acquire_schema_lock(
        self,
        schema_path: str,
        ttl: int | None = None,
        timeout: int = 30,
        blocking: bool = True,
    ) -> LockInfo | None:
        """Acquire a lock on a schema for mutation operations.
        
        Args:
            schema_path: Schema path or URI to lock
            ttl: Lock duration in seconds (default: SCHEMA_LOCK_TTL)
            timeout: Max time to wait for lock
            blocking: Whether to wait for lock
            
        Returns:
            LockInfo dict if acquired, None otherwise
        """
        lock_key = f"{self.SCHEMA_LOCK_PREFIX}{schema_path}"
        ttl = ttl or self.SCHEMA_LOCK_TTL
        
        return await self._acquire_lock(
            lock_key=lock_key,
            resource=schema_path,
            ttl=ttl,
            timeout=timeout,
            blocking=blocking,
        )
    
    async def acquire_action_lock(
        self,
        action_id: str,
        ttl: int | None = None,
        timeout: int = 5,
        blocking: bool = True,
    ) -> LockInfo | None:
        """Acquire a lock on an action for execution.
        
        Args:
            action_id: Action to lock
            ttl: Lock duration in seconds (default: DEFAULT_LOCK_TTL)
            timeout: Max time to wait for lock
            blocking: Whether to wait for lock
            
        Returns:
            LockInfo dict if acquired, None otherwise
        """
        lock_key = f"{self.ACTION_LOCK_PREFIX}{action_id}"
        ttl = ttl or self.DEFAULT_LOCK_TTL
        
        return await self._acquire_lock(
            lock_key=lock_key,
            resource=action_id,
            ttl=ttl,
            timeout=timeout,
            blocking=blocking,
        )
    
    async def acquire_projection_lock(
        self,
        projection_id: str,
        ttl: int | None = None,
        timeout: int = 10,
        blocking: bool = True,
    ) -> LockInfo | None:
        """Acquire a lock on a projection for updates.
        
        Args:
            projection_id: Projection to lock
            ttl: Lock duration in seconds (default: ENTITY_LOCK_TTL)
            timeout: Max time to wait for lock
            blocking: Whether to wait for lock
            
        Returns:
            LockInfo dict if acquired, None otherwise
        """
        lock_key = f"{self.PROJECTION_LOCK_PREFIX}{projection_id}"
        ttl = ttl or self.ENTITY_LOCK_TTL
        
        return await self._acquire_lock(
            lock_key=lock_key,
            resource=projection_id,
            ttl=ttl,
            timeout=timeout,
            blocking=blocking,
        )
    
    async def _acquire_lock(
        self,
        lock_key: str,
        resource: str,
        ttl: int,
        timeout: int,
        blocking: bool,
    ) -> LockInfo | None:
        """Internal lock acquisition using Redis Lock.
        
        Uses Lua script for atomic acquisition.
        """
        lock_id = f"{self._owner}:{uuid.uuid4().hex[:8]}"
        
        # Lua script for atomic lock acquisition
        acquire_script = """
        if redis.call("GET", KEYS[1]) then
            return 0
        else
            redis.call("SET", KEYS[1], ARGV[1], "EX", ARGV[2])
            return 1
        end
        """
        
        start_time = time.time()

        # Register script once for reuse
        acquire_script_fn = self._redis.register_script(acquire_script)

        while True:
            # Try to acquire lock
            acquired = await acquire_script_fn(
                keys=[lock_key],
                args=[lock_id, ttl],
            )
            
            if acquired:
                # Track the lock
                self._active_locks[lock_key] = lock_id

                # Start heartbeat
                self._start_heartbeat(lock_key, ttl)
                
                # Calculate timestamps
                now = datetime.now(timezone.utc)
                expires_at = datetime.fromtimestamp(
                    time.time() + ttl,
                    tz=timezone.utc
                )
                
                return LockInfo(
                    lock_id=lock_id,
                    resource=resource,
                    owner=self._owner,
                    acquired_at=now.isoformat(),
                    expires_at=expires_at.isoformat(),
                    ttl_seconds=ttl,
                )
            
            # Check timeout
            if not blocking or (time.time() - start_time) >= timeout:
                return None
            
            # Wait before retry
            await asyncio.sleep(0.1)
    
    async def release_lock(self, lock_key: str, lock_id: str) -> bool:
        """Safely release a lock using Lua script.
        
        Only releases if the lock is still owned by the given lock_id.
        
        Args:
            lock_key: Full lock key
            lock_id: Lock ID that was returned on acquisition
            
        Returns:
            True if released, False otherwise
        """
        release_script = """
        local current = redis.call("GET", KEYS[1])
        if current == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        release_script_fn = self._redis.register_script(release_script)

        try:
            result = await release_script_fn(
                keys=[lock_key],
                args=[lock_id],
            )
            
            if result:
                # Stop heartbeat and remove from active locks
                self._stop_heartbeat(lock_key)
                self._active_locks.pop(lock_key, None)
                return True
            
            return False
            
        except (LockNotOwnedError, LockError):
            return False
    
    async def extend_lock(self, lock_key: str, lock_id: str, additional_ttl: int) -> bool:
        """Extend a lock's TTL if still owned.
        
        Args:
            lock_key: Full lock key
            lock_id: Lock ID
            additional_ttl: Additional seconds to add
            
        Returns:
            True if extended, False otherwise
        """
        extend_script = """
        local current = redis.call("GET", KEYS[1])
        if current == ARGV[1] then
            return redis.call("EXPIRE", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        extend_script_fn = self._redis.register_script(extend_script)

        try:
            result = await extend_script_fn(
                keys=[lock_key],
                args=[lock_id, additional_ttl],
            )
            
            if result and lock_key in self._heartbeat_tasks:
                # Reset heartbeat with new TTL
                self._heartbeat_tasks[lock_key].cancel()
                self._start_heartbeat(lock_key, additional_ttl)
            
            return bool(result)
            
        except (LockNotOwnedError, LockError):
            return False
    
    async def get_lock_info(self, lock_key: str) -> dict[str, object] | None:
        """Get information about a lock.

        Args:
            lock_key: Full lock key

        Returns:
            Lock info dict or None if not locked
        """
        # Check if lock key exists
        exists = await self._redis.exists(lock_key)
        if not exists:
            return None

        ttl = await self._redis.ttl(lock_key)

        return {
            "lock_key": lock_key,
            "remaining_ttl": ttl if ttl > 0 else 0,
        }
    
    def _start_heartbeat(self, lock_key: str, ttl: int) -> None:
        """Start automatic lock renewal heartbeat."""
        if lock_key in self._heartbeat_tasks:
            self._heartbeat_tasks[lock_key].cancel()

        async def heartbeat():
            """Renew lock periodically."""
            renewal_interval = ttl * 0.7  # Renew at 70% of TTL

            while True:
                try:
                    await asyncio.sleep(renewal_interval)

                    # Check if lock still exists and extend
                    if lock_key in self._active_locks:
                        await self._redis.expire(lock_key, ttl)

                except asyncio.CancelledError:
                    break
                except Exception:
                    # Heartbeat failed, stop trying
                    break

        self._heartbeat_tasks[lock_key] = asyncio.create_task(heartbeat())
    
    def _stop_heartbeat(self, lock_key: str) -> None:
        """Stop heartbeat for a lock."""
        task = self._heartbeat_tasks.pop(lock_key, None)
        if task:
            task.cancel()
    
    @asynccontextmanager
    async def entity_lock(
        self,
        entity_id: str,
        ttl: int | None = None,
        timeout: int = 10,
    ):
        """Context manager for entity locks.
        
        Usage:
            async with lock_service.entity_lock("entity-123") as lock_info:
                # Do work with lock held
                pass
        """
        lock_info = await self.acquire_entity_lock(entity_id, ttl, timeout)
        
        if not lock_info:
            raise LockAcquisitionError(f"Could not acquire lock on entity: {entity_id}")
        
        try:
            yield lock_info
        finally:
            await self.release_lock(
                f"{self.ENTITY_LOCK_PREFIX}{entity_id}",
                lock_info["lock_id"]
            )
    
    async def list_active_locks(self) -> list[dict[str, object]]:
        """List all currently active locks."""
        patterns = [
            self.ENTITY_LOCK_PREFIX + "*",
            self.SCHEMA_LOCK_PREFIX + "*",
            self.ACTION_LOCK_PREFIX + "*",
            self.PROJECTION_LOCK_PREFIX + "*",
        ]
        
        active_locks = []
        
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )
                
                for key in keys:
                    info = await self.get_lock_info(key)
                    if info:
                        active_locks.append(info)
                
                if cursor == 0:
                    break
        
        return active_locks
    
    async def cleanup(self) -> dict[str, int]:
        """Clean up expired/stale locks.
        
        Removes locks that are no longer present in Redis.
        
        Returns:
            Dict with count of cleaned locks
        """
        cleaned = 0
        
        # Remove locks that no longer exist
        expired_keys = [
            key for key in self._active_locks
            if not await self._redis.exists(key)
        ]
        
        for key in expired_keys:
            self._stop_heartbeat(key)
            self._active_locks.pop(key, None)
            cleaned += 1
        
        return {
            "cleaned": cleaned,
            "remaining": len(self._active_locks),
        }
    
    async def shutdown(self) -> None:
        """Shutdown the lock service.
        
        Releases all held locks and stops heartbeats.
        """
        # Stop all heartbeats
        for task in list(self._heartbeat_tasks.values()):
            task.cancel()
        
        self._heartbeat_tasks.clear()
        
        # Release all locks
        for lock_key in list(self._active_locks.keys()):
            lock_id = self._active_locks.pop(lock_key, None)
            if lock_id:
                try:
                    await self._redis.delete(lock_key)
                except Exception:
                    pass  # Best effort cleanup
        
        # Close Redis connection
        await self._redis.close()


# Singleton instance
_lock_service: DistributedLockService | None = None


def get_lock_service() -> DistributedLockService:
    """Get or create the lock service singleton."""
    global _lock_service
    
    if _lock_service is None:
        _lock_service = DistributedLockService()
    
    return _lock_service
