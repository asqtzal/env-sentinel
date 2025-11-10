# AlertManager ガイド

Task 5 で実装したアラート管理モジュールの使い方と通知モジュール（Task 6）からの利用パターンをまとめる。

## 役割
- 温湿度センサの読み取り結果 (`SensorReading`) を評価し、 WARNING / CRITICAL / INFO（正常化）アラートを状態遷移ベースで生成する。
- `SensorFailureEvent` / `SensorAnomalyEvent` を EMERGENCY アラートへ変換する。
- 直近のアラート履歴を保持し、通知モジュールが状況確認・再送制御に利用できるようにする。

## 主なAPI

```python
from env_sentinel.config import AppConfig
from env_sentinel.monitoring import AlertManager

alert_manager = AlertManager(AppConfig.defaults().alerts)

# 1. 監視ループで呼び出し
alerts = await alert_manager.evaluate_reading(sensor_reading)

# 2. センサイベント連携（BaseSensor callback から呼ぶ）
await alert_manager.handle_sensor_failure(sensor_failure_event)
await alert_manager.handle_sensor_anomaly(sensor_anomaly_event)

# 3. 通知サブスクライブ
def on_alert(alert: Alert) -> None:
    notifier.queue(alert, mention=alert.level != AlertLevel.INFO)

alert_manager.register_listener(on_alert)

# 4. 履歴取得
recent_alerts = alert_manager.get_recent_alerts(limit=10)
```

### evaluate_reading()
- 温度・湿度それぞれの状態を `NORMAL / WARNING_LOW / WARNING_HIGH / CRITICAL_LOW / CRITICAL_HIGH` で管理し、**状態が変化したタイミング**のみアラートを返す。
- 範囲外が継続する場合は新たなアラートを生成しない（連投抑止）。
- 推奨範囲に戻った瞬間には `level=INFO` の「✅ 正常化」を指標ごとに発行。

### handle_sensor_failure() / handle_sensor_anomaly()
- センサモジュールの `failure_callback` / `anomaly_callback` から呼び出し、`AlertLevel.EMERGENCY` の Alert を生成する。
- 生成された Alert は Listener / 履歴に同じく流れるため、通知モジュールは温湿度アラートと同じ経路で扱える。

### register_listener()
- 監視スレッド／メインループ開始時に通知モジュールへコールバックを登録。
- Listener は同期/非同期どちらでも良い。非同期の場合は await される。
- 通知ポリシー: Task 6 で定義した通り、定期レポートはメンションなし、Alert は WARNING 以上でメンションあり、といったルールを Listener 側で実装する。

### get_recent_alerts()
- `collections.deque` を用いたリングバッファで最新アラートを保持（デフォルト100件）。
- 引数 `limit` で最新N件を取得できる。Task 6 の通知失敗リカバリやダッシュボード表示に利用する。

## 状態とレベルの対応
| 状態 | レベル | 説明 |
| --- | --- | --- |
| `WARNING_LOW/HIGH` | WARNING | 温度18℃未満/26℃超、湿度40%未満/60%超 |
| `CRITICAL_LOW/HIGH` | CRITICAL | 温度10℃未満/35℃超、湿度1%未満/99%以上（Configで調整可） |
| `NORMAL` | INFO | 正常化通知 (`temperature_normalized`, `humidity_normalized`) |
| センサイベント | EMERGENCY | 連続失敗や異常値。`subject` は `sensor_failure` / `sensor_anomaly` |

## 実装ステータス
- コード: `src/env_sentinel/monitoring/manager.py`, `src/env_sentinel/monitoring/models.py`
- テスト: `tests/monitoring/test_alert_manager.py`（連投抑止、正常化、湿度クリティカル、EMERGENCY変換、Listener、履歴上限）

Task 6 では上記APIを利用して SlackNotifier を実装し、定期レポート（メンションなし）とアラート（メンションあり）の線引きを行う。
