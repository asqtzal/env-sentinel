# Design Document

## Overview

Env-Sentinelは、新生児の安全を最優先とした環境モニタリングシステムです。Raspberry Pi上で動作し、BME280センサを使用して温湿度を継続的に監視し、Slackを通じて通知を行います。モジュラー設計により将来の拡張性を確保し、多重の安全機構により高い信頼性を実現します。

## Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Env-Sentinel System                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Sensor    │  │ Monitoring  │  │Notification │        │
│  │   Module    │──│   Module    │──│   Module    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Storage   │  │   Config    │  │Visualization│        │
│  │   Module    │  │   Module    │  │   Module    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                  Core Framework                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Logger    │  │ Health      │  │   Event     │        │
│  │   System    │  │ Monitor     │  │   Bus       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Phase 1 (MVP) - Direct Notification**:
```
BME280 Sensor → Sensor Module → Data Validation → Local Storage
                      ↓                              
              Monitoring Module ← Event Bus         
                      ↓                              
              Alert Manager → Slack Notifier → Slack API
```

**Phase 2 (Cloud Integration)**:
```
BME280 Sensor → Sensor Module → Data Validation → Local Storage
                      ↓                              ↓
              Monitoring Module ← Event Bus ← Cloud Sync
                      ↓                              ↓
              Alert Manager → IoT Notifier → AWS IoT Core → Lambda → Slack API
```

### Phase 2 - AWS Integration Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raspberry Pi  │    │   AWS IoT Core  │    │   Lambda        │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Sensor    │ │    │ │   Device    │ │    │ │ Notification│ │
│ │   Reading   │─┼────┼→│   Shadow    │─┼────┼→│  Handler    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Alert     │ │    │ │   Rules     │ │    │ │   Slack     │ │
│ │  Generator  │─┼────┼→│   Engine    │─┼────┼→│   Client    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ↓
                       ┌─────────────────┐
                       │   DynamoDB      │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │  Sensor     │ │
                       │ │  Data       │ │
                       │ └─────────────┘ │
                       └─────────────────┘
```

## Components and Interfaces

### 1. Sensor Module
**責任**: センサからのデータ取得と検証

**インターフェース実装状況**:
```python
class BaseSensor(ABC):
    def __init__(self, sensor_id: str, *, failure_threshold: int, max_retries: int, retry_delay_seconds: float):
        self.sensor_id = sensor_id
        ...

    async def read(self) -> SensorReading:          # 共通リトライ + 異常値補正
        reading = await self._read_sensor()
        ...
        return reading

    async def close(self) -> None:                  # リソース解放
        await self._close_impl()

    async def health_check(self) -> bool:           # 故障閾値ベースでヘルス判断
        return self.failure_count < self.failure_threshold and await self._perform_health_check()

    async def on_read_success(self, reading: SensorReading) -> None: ...
    async def on_read_failure(self, attempt: int, error: Exception) -> None: ...

    @abstractmethod
    async def _read_sensor(self) -> SensorReading: ...
    @abstractmethod
    async def _close_impl(self) -> None: ...


class BME280Sensor(BaseSensor):
    def __init__(self, *, driver: BME280Driver, config: SensorConfig, sensor_id: str):
        ...

    async def _read_sensor(self) -> SensorReading:
        sample = await self._driver.read_sample()
        return SensorReading.from_values(...)

    async def _close_impl(self) -> None:
        await self._driver.close()
```

- **Driver Abstraction**: `BME280Driver` / `BME280DriverFactory` で実機とシミュレータを差し替え。  
  - `SimulatedBME280Driver`: デフォルトの決定論的サンプル。  
  - `RaspberryPiBME280Driver`: Adafruit CircuitPython (`board`, `busio`, `adafruit_bme280`) を動的ロードし、I2C（`SensorConfig.i2c_address`）から読み取り。  
- **SensorFactory**: `SensorFactory` + `DEFAULT_BME280_BUILDER` / `RASPBERRY_PI_BME280_BUILDER` を介して Config 駆動でセンサ生成。`create_default_sensor_factory(prefer_hardware=None)` は環境に応じて自動判定。  
- **Event Hooks**: `SensorFailureEvent`（連続失敗閾値超過）と `SensorAnomalyEvent`（`SensorReading.invalid_fields` が発生）を `failure_callback` / `anomaly_callback` で購読でき、Monitoring/Alert モジュールに通知できる。

**安全機構**:
- 3回連続失敗でセンサ故障判定、`health_check()` が False を返す。
- `SensorReading.validate(prev)` により物理範囲外の値は最後の正常値で補間し `is_valid=False` でマーキング。
- I2C通信エラーは BaseSensor の共通リトライ (`max_retries`/`retry_delay_seconds`) で吸収し、失敗時は `SensorReadError` をraise。

### 2. Monitoring Module
**責任**: 環境データの監視とアラート判定

**インターフェース**:
```python
class AlertManager:
    def __init__(self, config: AlertConfig):
        self.temp_range = config.temperature_range
        self.humidity_range = config.humidity_range
    
    async def evaluate_reading(self, reading: SensorReading) -> List[Alert]:
        # 温湿度範囲チェック
        # 極端値チェック（緊急アラート）
        # アラート生成
        pass
```

- **状態遷移**: 温度/湿度ごとに現在状態（NORMAL / WARNING_LOW / WARNING_HIGH / CRITICAL_LOW / CRITICAL_HIGH）を保持し、状態が変化した瞬間のみアラートを生成する。連投は行わず、推奨レンジへ戻ったタイミングで「✅ 正常化」を個別に通知。
- **センサイベント統合**: `SensorFailureEvent` / `SensorAnomalyEvent` を Monitoring 層で受け取り、`Alert(level=EMERGENCY, category=SENSOR, ...)` に変換して通知層へ渡す。これにより Task 6 は Alert に対してメンション有無を切り替えるだけで良い。
- **Listener API**: `AlertManager.register_listener()` で通知モジュールなどが購読し、最新 Alert 履歴 (`get_recent_alerts(limit=N)`) も取得できる。

**アラートレベル**:
- **INFO**: 定期レポート
- **WARNING**: 推奨範囲外（温度18℃未満/26℃超、湿度40%未満/60%超）
- **CRITICAL**: 極端値（温度10℃未満/35℃超、湿度1%未満/99%以上 ※設定で変更可）
- **EMERGENCY**: センサ故障、システム障害

### 3. Notification Module
**責任**: 各種通知手段への配信

**Phase 1 Implementation**:
```python
class BaseNotifier(ABC):
    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        pass

class SlackNotifier(BaseNotifier):
    async def send_notification(self, message: NotificationMessage) -> bool:
        # 直接Slack APIに送信
        # Slack Block Kit形式でメッセージ構築
        # レート制限考慮
        # 送信失敗時のリトライ
        pass

class IoTNotifier(BaseNotifier):  # Phase 2で実装
    async def send_notification(self, message: NotificationMessage) -> bool:
        # AWS IoT Coreに送信
        # Lambda経由でSlack通知
        pass
```

**通知戦略**:
- **Phase 1**: Raspberry Pi → Slack API（直接）
- **Phase 2**: Raspberry Pi → AWS IoT → Lambda → Slack API
- **フォールバック**: ローカル通知失敗時はログ記録、復旧時に一括送信

**メッセージ形式**:
- 定期レポート: 温度、湿度、時刻、トレンド
- アラート: 警告レベル、具体的数値、推奨アクション
- システム状態: 起動、停止、エラー、復旧

#### NotificationRuntime / EnvSentinelApp
- `NotificationRuntime` が SlackNotifier・NotificationCoordinator・ReportGenerator を組み立て、`AlertManager` と LocalStorage から最新値を取得して通知を行う。
- `EnvSentinelApp` は ConfigManager / AlertManager / LocalStorage / NotificationRuntime / MonitoringLoop をまとめるオーケストレーション層。`python -m env_sentinel.app` で起動すると Config ホットリロードとセンサループが自動的に連携する。
- Configリロード時は `NotificationRuntime.reload()` が旧コーディネータのリスナーを解除してから再構築し、通知重複やメモリリークを防ぐ。MonitoringLoop もセンサ設定変更を検知して自動再初期化する。

#### Delivery Queue & Fallback
- `NotificationQueue` は優先度付きキュー＋レートリミッタで Slack API への送信を直列化し、`notifications.slack.rate_limit_per_minute` を守る。
- 送信に失敗したメッセージは `data/pending_notifications.json`（`NotificationFallbackStore`）に保留され、再起動/復旧時に再キューされる。これによりネットワーク障害やホットリロード中も通知が失われない。

### 4. Monitoring Runtime
- `MonitoringLoop` はセンサ工場で生成した `BaseSensor` を一定間隔でポーリングし、読み取り結果を LocalStorage へ保存した上で `AlertManager.evaluate_reading()` に渡す。
- Config の `sensor` 設定（タイプ/I2Cアドレス/失敗閾値など）が変更されるとセンサをクローズして再生成し、読み取り間隔も次のサイクルで即時反映する。
- センサからの `failure_callback` / `anomaly_callback` は AlertManager へ中継され、リスナーが重複しないよう開始・停止時に登録/解除を管理する。

### 4. Storage Module
**責任**: 段階的なデータ永続化戦略

**Phase 1 Implementation**:
```python
class LocalStorage:
    async def initialize(self) -> None:
        # SQLiteファイル作成、WAL有効化、メタデータテーブルとsensor_readingsテーブルをマイグレート
        ...

    async def store_reading(self, reading: SensorReading) -> bool:
        # 非同期接続経由でINSERT。invalid_fieldsやsynced_to_cloudを含む
        # INSERT後にretention日数を超過した行をクリーンアップ
        ...
    
    async def get_recent_data(self, hours: int, limit: Optional[int] = None) -> List[SensorReading]:
        # UTC基準で期間フィルタし、降順 + 任意limit付きで取得
        ...

    async def purge_expired_data(self) -> int:
        # retention日数に基づくDELETEを行い、削除件数を返す
        ...

    async def health_check(self) -> dict[str, int | str]:
        # schema_versionをstorage_metadataから読み出し、SELECT 1で疎通確認
        ...
```

**Phase 2 Implementation**:
```python
class HybridStorage:
    def __init__(self, local_storage: LocalStorage):
        self.local_storage = local_storage
        
    async def store_reading(self, reading: SensorReading) -> bool:
        # ローカル保存
        await self.local_storage.store_reading(reading)
        # IoT Core経由でクラウド同期
        await self.sync_to_cloud(reading)
        
    async def sync_to_cloud(self, reading: SensorReading) -> bool:
        # AWS IoT Core経由でDynamoDBに保存
        pass
```

**データモデル**:
```sql
CREATE TABLE storage_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sensor_readings (
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

CREATE INDEX idx_sensor_readings_timestamp
    ON sensor_readings (timestamp);
```

### 5. Configuration Module
**責任**: 設定の管理と動的更新

**設定構造**:
```json
{
  "sensor": {
    "type": "BME280",
    "i2c_address": "0x76",
    "read_interval_seconds": 60,
    "failure_threshold": 3
  },
  "alerts": {
    "temperature": {"min": 18, "max": 26, "critical_min": 10, "critical_max": 35},
    "humidity": {"min": 40, "max": 60, "critical_min": 1, "critical_max": 99}
  },
  "notifications": {
    "slack": {
      "channel": "#baby-room",
      "report_interval_seconds": 1800,
      "rate_limit_per_minute": 1
    }
  },
  "storage": {
    "db_path": "data/env_sentinel.db",
    "local_retention_days": 90,
    "cloud_sync_interval_seconds": 300,
    "cloud_provider": "aws"
  }
}
```

## Data Models

### SensorReading
```python
@dataclass
class SensorReading:
    timestamp: datetime
    temperature: float
    humidity: float
    pressure: Optional[float]
    sensor_id: str
    is_valid: bool = True
    
    def validate(self) -> bool:
        # 温度: -40℃ ～ 85℃ (BME280仕様範囲)
        # 湿度: 0% ～ 100%
        # 物理的妥当性チェック
        pass
```

### Alert
```python
@dataclass
class Alert:
    level: AlertLevel  # INFO, WARNING, CRITICAL, EMERGENCY
    message: str
    timestamp: datetime
    sensor_reading: Optional[SensorReading]
    recommended_action: Optional[str]
```

## Error Handling

### 1. センサエラー処理
- **I2C通信エラー**: 3回リトライ後、センサ故障判定
- **データ異常**: 妥当性チェック失敗時、前回値で補完
- **センサ故障**: 緊急アラート送信、手動確認促進

### 2. ネットワークエラー処理
- **Slack API失敗**: 指数バックオフでリトライ
- **クラウド同期失敗**: ローカルキューに蓄積、復旧時に同期
- **完全ネットワーク断**: ローカルログに記録、復旧時に一括報告

### 3. システムエラー処理
- **プロセス異常終了**: systemdによる自動再起動
- **メモリ不足**: ログローテーション、古いデータ削除
- **ディスク容量不足**: 古いデータのクラウド移行

## Testing Strategy

### 1. Unit Tests
- 各モジュールの独立テスト
- モックを使用したセンサ・API テスト
- エラーケースの網羅的テスト

### 2. Integration Tests
- 実際のBME280センサとの統合
- Slack API との実通信テスト
- データベース操作の整合性テスト

### 3. Hardware Tests
- Raspberry Pi実機での24時間稼働テスト
- 温度・湿度変化への応答テスト
- 電源断・復旧テスト

### 4. Safety Tests
- センサ故障シミュレーション
- ネットワーク断絶テスト
- 極端環境条件テスト

## Security Considerations

### 1. 認証・認可
- Slack Bot Token の安全な管理
- 環境変数による秘匿情報管理
- 最小権限の原則

### 2. データ保護
- ローカルデータベースの暗号化
- クラウド通信のTLS暗号化
- 個人情報の最小化

### 3. システムセキュリティ
- 定期的なセキュリティアップデート
- ファイアウォール設定
- 不正アクセス監視

## Performance Requirements

### 1. リアルタイム性
- センサ読み取り: 1分間隔
- アラート通知: 30秒以内
- システム応答: 5秒以内

### 2. リソース使用量
- CPU使用率: 10%以下
- メモリ使用量: 100MB以下
- ディスク使用量: 1GB以下（ログ含む）

### 3. 可用性
- システム稼働率: 99.9%以上
- データ損失: 0%
- 復旧時間: 5分以内
