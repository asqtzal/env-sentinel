---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Project Structure

## High-Level Structure Principles
- **src/**: メインのソースコード
- **src/env_sentinel/core/**: アプリケーションオーケストレーション (`EnvSentinelApp`, `NotificationRuntime`, `MonitoringLoop`, CLI entry `app.py`)
- **tests/**: テストコード（ソース構造を反映）
- **config/**: 設定ファイル
- **docs/**: ドキュメント
- **scripts/**: 運用・デプロイスクリプト

## Module Organization Approach
- **機能別分離**: センサ (`src/env_sentinel/sensors`)、通知 (`src/env_sentinel/notifications`)、ストレージ (`src/env_sentinel/storage`)、コアオーケストレーション (`src/env_sentinel/core`) など機能ごとに分割
- **レイヤー分離**: データアクセス、ビジネスロジック（AlertManager/NotificationRuntime）、エントリポイント（`app.py`）を層別に整理
- **プラグイン対応**: センサや通知チャネルはファクトリ/インターフェース経由で追加する

## Import Patterns
```python
# 絶対インポートを使用
from src.sensors.bme280_sensor import BME280Sensor
from src.notifications.slack_notifier import SlackNotifier
from src.config.config_manager import ConfigManager

# 相対インポートは同一パッケージ内のみ
from .base_sensor import BaseSensor
from ..utils.logger import get_logger
```

## Naming Conventions
- **Files**: snake_case (例: bme280_sensor.py)
- **Classes**: PascalCase (例: BME280Sensor)
- **Functions/Variables**: snake_case (例: read_temperature)
- **Constants**: UPPER_SNAKE_CASE (例: DEFAULT_INTERVAL)
- **Private Members**: 先頭にアンダースコア (例: _internal_method)

## Architectural Decisions
- **Modular Design**: 機能別にモジュールを分離
- **Plugin Architecture**: インターフェースベースの拡張可能設計
- **Configuration-Driven**: 設定ファイルによる動作制御 (`ConfigManager` + EnvSentinelApp)
- **Async-First**: 非同期処理を基本とした設計（MonitoringLoop、NotificationRuntime、SlackNotifier）
