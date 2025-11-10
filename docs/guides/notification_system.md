# Notification System ガイド

Env-Sentinel の通知基盤は AlertManager・NotificationCoordinator・SlackNotifier を非同期に連携させ、定期レポートやアラート通知、システムイベント送信を統合的に扱います。本ガイドでは構成要素と運用手順をまとめます。

## アーキテクチャ overview
```
Sensor → AlertManager → NotificationCoordinator → NotificationQueue → SlackNotifier → Slack
                      ↘ ReportGenerator ↗
```
- **AlertManager**: 温湿度/センサイベントから `Alert` を生成し、Listener APIで通知層へ渡す。
- **NotificationCoordinator**: Alertを `NotificationMessage` に変換し、メンションポリシーや優先度を付与。定期レポート（ReportGenerator）やシステムイベント（起動/停止等）も同一経路で送信。
- **NotificationQueue & RateLimiter**: Slack API への送信を直列化し、`notifications.slack.rate_limit_per_minute` に基づきレート制御。
- **SlackNotifier**: Block Kit メッセージを構築して `slack_sdk.AsyncWebClient` を呼び出し、カスタム / @channel / @here メンションを付与。
- **NotificationRuntime**: Config/AlertManager/LocalStorage と SlackNotifier を束ね、ホットリロード時の再構成やシステムイベント送信を受け持つ。

## Config のポイント
`config/default_config.json` の `notifications.slack` セクションで主な動作を制御します。

| フィールド | 説明 |
| --- | --- |
| `channel` | 通知送信先 Slack チャンネル（例: `#baby-room`） |
| `report_interval_seconds` | 定期レポートの間隔（300〜7200秒） |
| `rate_limit_per_minute` | Slack通知の最大送信レート |
| `alert_mention_policy` | `none` / `here` / `channel` / `custom` によるメンション方針 |
| `alert_mention_targets` | `custom` 時にメンションするユーザーID（`U123...` または `<@U123>` 形式） |

Slack Bot Token は `.env` の `ENV_SENTINEL_SLACK_BOT_TOKEN` に保存します。起動時に未設定だと `NotificationConfigurationError` が発生します。

### .env 設定例
```
ENV_SENTINEL_SLACK_BOT_TOKEN=xoxb-XXXXXXXX
ENV_SENTINEL_LOG_LEVEL=INFO
```
`python -m env_sentinel.app` 実行前に `source .venv/bin/activate && export $(grep -v '^#' .env | xargs)` などで読み込む運用を推奨します。

## EnvSentinelApp を使った起動
`EnvSentinelApp` が ConfigManager、AlertManager、LocalStorage、NotificationRuntime の初期化とホットリロード連携を司ります。

### CLI 起動（推奨）
`python -m env_sentinel.app` で EnvSentinelApp + MonitoringLoop + ConfigPolling をまとめて起動できます。センサ設定（読み取り間隔やI2Cアドレス）を編集して保存すると、ConfigManager のホットリロード経由で Runtime と MonitoringLoop が自動的に再構成されます。  
停止は `Ctrl+C`（SIGINT / SIGTERM を検出してグレースフルシャットダウン）。

### カスタム起動（例）
```python
import asyncio
from pathlib import Path

from env_sentinel.config import ConfigManager
from env_sentinel.core import EnvSentinelApp, MonitoringLoop

async def main() -> None:
    manager = ConfigManager(Path("config/app_config.json"), Path("config/default_config.json"))
    app = EnvSentinelApp(manager)
    await app.start()

    loop = MonitoringLoop(
        config_provider=lambda: app.config,
        alert_manager=app.alert_manager,
        storage=app.storage,
    )
    await loop.start()
    manager.start_polling()

    try:
        await asyncio.sleep(3600)
    finally:
        manager.stop_polling()
        await loop.stop()
        await app.stop()

asyncio.run(main())
```

## 定期レポート
- `ReportGenerator` が最新の `SensorReading` を取得し、温度/湿度/測定時刻をMetricsとして通知。
- 既定では LocalStorage から直近1件を取得します（Storage未初期化の場合は `None` となりレポート送信をスキップ）。
- レポートは INFOレベルで送信され、メンションは常に `none`。必要に応じて `NotificationCoordinator` へカスタムジェネレーターを注入可能です。

## システムイベント通知
`NotificationCoordinator.emit_system_event()` / `NotificationRuntime.emit_system_event()` を利用して起動/停止/設定更新などを Slack へ送れます。EnvSentinelApp は起動時と停止時に自動で以下を送信します。
- `🚀 Env-Sentinel 起動` : プロセス開始時
- `🛑 Env-Sentinel 停止` : シャットダウン時

## テスト
- SlackNotifier, NotificationQueue, ReportGenerator, NotificationCoordinator の各挙動は `tests/notifications/` でカバー。
- EnvSentinelApp の統合シナリオは `tests/core/test_env_app.py` でスタブRuntimeを用いて検証。

## 運用メモ
- Slack API レート制限に達した場合、キューが自動的に送信を遅延させます。長時間の失敗が続く場合はログを確認してトークン・ネットワーク状態を見直してください。
- Slack API への送信が失敗すると `data/pending_notifications.json` に保留され、次回起動時または送信再開時に再キューされます。障害復旧後に再送されるため、ファイルは削除しないでください。
- Configの `storage.db_path` を変更した際は、EnvSentinelApp が警告ログを出力します。DBファイルの差し替えにはアプリ再起動が必要です。
- センサ設定（`sensor.type` / `sensor.i2c_address` / `sensor.failure_threshold` など）が変更されると、MonitoringLoop が自動的にセンサを再初期化し、新しい構成で読み取りを再開します。読み取り間隔 (`sensor.read_interval_seconds`) はループ毎に参照されるため、保存後すぐに適用されます。
- Sensorループやデータ保存処理は今後の Task 7/8 で統合予定。NotificationRuntime は独立して動作するため、徐々にメインループへ組み込めます。

---
このガイドを起点に、Slack通知ポリシーやレポート仕様をチームで調整し、Task 6以降の実装・運用を進めてください。
