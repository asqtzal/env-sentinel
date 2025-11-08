"""SQLite-backed storage implementation for sensor readings."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, List, Optional

import aiosqlite

from env_sentinel.config import StorageConfig
from env_sentinel.sensors import SensorReading
from env_sentinel.utils.logger import get_logger

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.9 compatibility
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]


logger = get_logger(__name__)

SCHEMA_VERSION = 1
SCHEMA_VERSION_KEY = "schema_version"

CREATE_METADATA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS storage_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    pressure REAL,
    sensor_id TEXT NOT NULL,
    is_valid INTEGER NOT NULL,
    invalid_fields TEXT NOT NULL,
    synced_to_cloud INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp
ON sensor_readings (timestamp);
"""


class StorageError(RuntimeError):
    """Raised when storage operations fail."""


class LocalStorage:
    """Persist SensorReading objects into a local SQLite database."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        retention_days: int,
    ) -> None:
        self._db_path = Path(db_path)
        self._retention_days = retention_days
        self._lock = asyncio.Lock()
        self._initialized = False

    @classmethod
    def from_config(cls, config: StorageConfig) -> "LocalStorage":
        """Factory helper using StorageConfig values."""
        return cls(
            db_path=config.db_path,
            retention_days=config.local_retention_days,
        )

    async def initialize(self) -> None:
        """Create database directories and schema if needed."""
        async with self._lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(self._db_path.as_posix()) as db:
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute(CREATE_METADATA_TABLE_SQL)
                await db.execute(CREATE_TABLE_SQL)
                await db.execute(CREATE_INDEX_SQL)
                await self._record_schema_version(db, SCHEMA_VERSION)
                await db.commit()
            self._initialized = True
            logger.info("Local storage initialized at %s (schema v%s)", self._db_path, SCHEMA_VERSION)

    async def store_reading(self, reading: SensorReading) -> bool:
        """Persist a single SensorReading."""
        payload_invalid_fields = list(getattr(reading, "invalid_fields", tuple()))
        try:
            async with self._connection() as db:
                await db.execute(
                    """
                    INSERT INTO sensor_readings (
                        timestamp,
                        temperature,
                        humidity,
                        pressure,
                        sensor_id,
                        is_valid,
                        invalid_fields,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._serialize_datetime(reading.timestamp),
                        reading.temperature,
                        reading.humidity,
                        reading.pressure,
                        reading.sensor_id,
                        1 if reading.is_valid else 0,
                        json.dumps(payload_invalid_fields),
                        self._serialize_datetime(datetime.now(tz=UTC)),
                    ),
                )
                await db.commit()
            await self.purge_expired_data()
            return True
        except Exception as exc:  # pragma: no cover - unexpected SQLite errors
            raise StorageError(f"Failed to store reading: {exc}") from exc

    async def get_recent_data(self, hours: int, limit: Optional[int] = None) -> List[SensorReading]:
        """Return readings recorded within the given timeframe."""
        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)
        query = """
            SELECT
                timestamp,
                temperature,
                humidity,
                pressure,
                sensor_id,
                is_valid,
                invalid_fields
            FROM sensor_readings
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """
        params: list[object] = [self._serialize_datetime(cutoff)]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        try:
            async with self._connection() as db:
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
        except Exception as exc:  # pragma: no cover - unexpected SQLite errors
            raise StorageError(f"Failed to fetch readings: {exc}") from exc

        readings: List[SensorReading] = []
        for row in rows:
            timestamp, temperature, humidity, pressure, sensor_id, is_valid, invalid_fields = row
            reading = SensorReading(
                timestamp=self._deserialize_datetime(timestamp),
                temperature=temperature,
                humidity=humidity,
                pressure=pressure,
                sensor_id=sensor_id,
                is_valid=bool(is_valid),
            )
            fields = tuple(json.loads(invalid_fields) if invalid_fields else [])
            reading.invalid_fields = fields
            readings.append(reading)
        return readings

    async def purge_expired_data(self) -> int:
        """Delete readings older than the configured retention period."""
        cutoff = datetime.now(tz=UTC) - timedelta(days=self._retention_days)
        try:
            async with self._connection() as db:
                before = db.total_changes
                await db.execute(
                    "DELETE FROM sensor_readings WHERE timestamp < ?",
                    (self._serialize_datetime(cutoff),),
                )
                await db.commit()
                purged = db.total_changes - before
        except Exception as exc:  # pragma: no cover
            raise StorageError(f"Failed to purge historical data: {exc}") from exc

        if purged:
            logger.info("Purged %s expired rows older than %s days", purged, self._retention_days)
        return purged

    async def health_check(self) -> dict[str, int | str]:
        """Return basic diagnostic information for monitoring."""
        try:
            async with self._connection() as db:
                version = await self._read_schema_version(db)
                async with db.execute("SELECT 1 FROM sensor_readings LIMIT 1;") as cursor:
                    await cursor.fetchone()
                return {"status": "ok", "schema_version": version or 0}
        except Exception as exc:  # pragma: no cover
            raise StorageError(f"Storage health check failed: {exc}") from exc

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    @asynccontextmanager
    async def _connection(self) -> AsyncIterator[aiosqlite.Connection]:
        await self._ensure_initialized()
        async with aiosqlite.connect(self._db_path.as_posix()) as db:
            yield db

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _deserialize_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    async def _record_schema_version(self, db: aiosqlite.Connection, version: int) -> None:
        await db.execute(
            """
            INSERT INTO storage_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (SCHEMA_VERSION_KEY, str(version)),
        )

    async def _read_schema_version(self, db: aiosqlite.Connection) -> Optional[int]:
        async with db.execute(
            "SELECT value FROM storage_metadata WHERE key = ? LIMIT 1",
            (SCHEMA_VERSION_KEY,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return int(row[0])
