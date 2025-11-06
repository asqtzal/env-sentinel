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
- **センサ制御**: Adafruit CircuitPython libraries for BME280
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

## Technical Constraints
- **Resource Limits**: CPU 10%以下、メモリ 100MB以下
- **Network**: 家庭用Wi-Fi環境での動作
- **Power**: 24時間連続稼働対応
- **Environment**: 新生児の部屋での静音動作
- **Phase Migration**: Phase 1からPhase 2への無停止移行対応

