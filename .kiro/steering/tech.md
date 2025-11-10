---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Technology Stack

## Hardware Platform
- **Primary Platform**: Raspberry Pi Zero WH
- **OS**: Raspberry Pi OS Lite (64-bit)
- **Sensor**: BME280 (温度・湿度・気圧センサ)
- **Connection**: I2C接続 (GPIO 2: SDA, GPIO 3: SCL)
- **Power**: 公式電源アダプタ (5V 3A) + UPS Hat (停電対策)

## Core Technologies
- **Language**: Python 3.9+
- **Async Framework**: asyncio + aiohttp
- **Database**: SQLite (Phase 1) + DynamoDB (Phase 2)
- **IoT Communication**: AWS IoT Core SDK (Phase 2)
- **Web Framework**: FastAPI (ダッシュボード用)
- **Task Scheduler**: APScheduler

## Library Categories
- **センサ制御**: Adafruit CircuitPython libraries for BME280（`adafruit-circuitpython-bme280`, `adafruit-blinka`）。ローカル開発では `SimulatedBME280Driver` を使用しハードウェア不要で挙動確認可能。
- **通信・API**: 
  - Phase 1: aiohttp, slack-sdk for direct Slack integration
  - Phase 2: AWSIoTDeviceSDK for IoT Core communication
- **データ処理**: pandas for data manipulation, matplotlib/plotly for visualization
- **クラウド**: boto3 for AWS services (Phase 2)
- **設定・ログ**: pydantic for configuration validation, structured logging
- **テスト・品質**: pytest ecosystem, code formatting and linting tools

## Development Tools
- **Code Quality**: Black, flake8, isort, mypy
- **Testing**: pytest + pytest-asyncio + coverage
- **CI/CD**: GitHub Actions
- **Containerization**: Docker (開発・テスト用)
- **Version Control**: Git with conventional commits

## Sensor Stack Notes
- **BaseSensor**: 共通のリトライ／ヘルスチェック／異常値補完を提供し、 `_read_sensor` / `_close_impl` のみドライバ固有実装。連続失敗は `SensorReadError` で通知。
- **BME280 Drivers**:
  - `SimulatedBME280Driver`: テスト・CI 用。追加依存不要で決定論的な値を提供。
  - `RaspberryPiBME280Driver`: `board`, `busio`, `adafruit_bme280` を `asyncio.to_thread` でラップしてI2C読み取り。導入コマンド例:  
    ```bash
    pip install adafruit-circuitpython-bme280 adafruit-blinka
    ```
- **Factory Wiring**: `create_default_sensor_factory(prefer_hardware=None)` が、Adafruit依存がロード可能かをチェックして自動で実機/シミュレータを切り替える。ハードウェアを強制したい場合のみ `prefer_hardware=True` や `RASPBERRY_PI_BME280_BUILDER` の明示登録が必要。
- **Python 3.9 互換性**: Raspberry Pi OS 標準の Python 3.9 では `datetime.UTC` や `dataclass(slots=True)` が未サポートのため、`timezone.utc` フォールバックと通常の `@dataclass` を使用している。新しい構文を追加する際は 3.9 で動作するか確認すること。

## Technical Constraints
- **Resource Limits**: CPU 10%以下、メモリ 100MB以下
- **Network**: 家庭用Wi-Fi環境での動作
- **Power**: 24時間連続稼働対応
- **Environment**: 新生児の部屋での静音動作
- **Phase Migration**: Phase 1からPhase 2への無停止移行対応
