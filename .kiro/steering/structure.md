---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Project Structure

## High-Level Structure Principles
- **src/**: メインのソースコード
- **tests/**: テストコード（ソース構造を反映）
- **config/**: 設定ファイル
- **docs/**: ドキュメント
- **scripts/**: 運用・デプロイスクリプト

## Module Organization Approach
- **機能別分離**: センサ、通知、ストレージなど機能ごとにモジュール分割
- **レイヤー分離**: データアクセス、ビジネスロジック、プレゼンテーション層の分離
- **プラグイン対応**: 新機能を既存コードに影響なく追加可能な構造

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
- **Configuration-Driven**: 設定ファイルによる動作制御
- **Async-First**: 非同期処理を基本とした設計