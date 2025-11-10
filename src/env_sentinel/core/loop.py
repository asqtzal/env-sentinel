"""Asynchronous monitoring loop that polls sensors and persists readings."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Optional

from env_sentinel.monitoring import AlertManager
from env_sentinel.sensors import (
    BaseSensor,
    SensorFactory,
    SensorReadError,
    create_default_sensor_factory,
)
from env_sentinel.storage import LocalStorage, StorageError
from env_sentinel.utils.logger import get_logger


class MonitoringLoop:
    """Continuously poll the configured sensor and feed data to AlertManager/Storage."""

    SENSOR_ID = "sensor-001"

    def __init__(
        self,
        *,
        config_provider,
        alert_manager: AlertManager,
        storage: LocalStorage,
        sensor_factory: SensorFactory | None = None,
    ) -> None:
        self._config_provider = config_provider
        self._alert_manager = alert_manager
        self._storage = storage
        self._sensor_factory = sensor_factory or create_default_sensor_factory()

        self._sensor: Optional[BaseSensor] = None
        self._sensor_signature: tuple[str, str, int] | None = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._logger = get_logger(__name__)

    async def start(self) -> None:
        """Start the background monitoring loop."""
        if self._task:
            return

        config = self._config_provider()
        await self._initialize_sensor(config)

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        self._logger.info("Monitoring loop started (interval=%ss)", config.sensor.read_interval_seconds)

    async def stop(self) -> None:
        """Stop the monitoring loop and release sensor resources."""
        if not self._task:
            return

        self._stop_event.set()
        await self._task
        self._task = None

        await self._close_sensor()
        self._logger.info("Monitoring loop stopped")

    async def _initialize_sensor(self, app_config) -> None:
        sensor_config = app_config.sensor
        await self._close_sensor()
        sensor = self._sensor_factory.create(config=sensor_config, sensor_id=self.SENSOR_ID)
        sensor.set_failure_callback(self._alert_manager.handle_sensor_failure)
        sensor.set_anomaly_callback(self._alert_manager.handle_sensor_anomaly)
        self._sensor = sensor
        self._sensor_signature = self._signature(sensor_config)
        self._logger.info("Sensor instantiated (type=%s, address=%s)", sensor_config.type, sensor_config.i2c_address)

    async def _close_sensor(self) -> None:
        if self._sensor:
            await self._sensor.close()
        self._sensor = None
        self._sensor_signature = None

    async def _run(self) -> None:
        assert self._sensor is not None
        loop = asyncio.get_running_loop()

        while not self._stop_event.is_set():
            start = loop.time()
            await self._poll_once()
            await self._maybe_reconfigure_sensor()

            interval = max(0.01, self._config_provider().sensor.read_interval_seconds)
            elapsed = loop.time() - start
            delay = max(0.0, interval - elapsed)

            if delay == 0:
                continue
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                continue

    async def _poll_once(self) -> None:
        assert self._sensor is not None
        try:
            reading = await self._sensor.read()
        except SensorReadError as exc:
            self._logger.error("センサ読み取りに失敗しました: %s", exc)
            return
        except Exception:  # pragma: no cover - defensive guard
            self._logger.exception("センサ読み取りで予期せぬエラー")
            return

        try:
            await self._storage.store_reading(reading)
        except StorageError as exc:
            self._logger.error("データの保存に失敗しました: %s", exc)

        await self._alert_manager.evaluate_reading(reading)

    async def _maybe_reconfigure_sensor(self) -> None:
        config = self._config_provider()
        signature = self._signature(config.sensor)
        if signature == self._sensor_signature:
            return
        self._logger.info("センサ設定が変更されたため再初期化します")
        await self._initialize_sensor(config)

    @staticmethod
    def _signature(sensor_config) -> tuple[str, str, int]:
        return (
            sensor_config.type,
            sensor_config.i2c_address,
            sensor_config.failure_threshold,
        )
