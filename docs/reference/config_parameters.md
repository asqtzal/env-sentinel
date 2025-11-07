# 設定パラメータ一覧（Task 2.1-a）

| セクション | パラメータ | 型 / 例 | デフォルト | 制約・説明 |
| --- | --- | --- | --- | --- |
| sensor | `type` | str (`"BME280"`) | `BME280` | 実装済みセンサ識別子。Phase1では固定値。 |
| sensor | `i2c_address` | str (`"0x76"`) | `0x76` | I2Cアドレス、`0x76` or `0x77`。 |
| sensor | `read_interval_seconds` | int (60) | 60 | 10〜3600秒。センサ読み取り間隔。 |
| sensor | `failure_threshold` | int (3) | 3 | 1〜10。連続失敗数で故障判定。 |
| alerts.temperature | `min` | float (18.0) | 18.0 | 0〜40℃で設定。推奨範囲下限。 |
| alerts.temperature | `max` | float (26.0) | 26.0 | 10〜45℃で設定。推奨範囲上限。 |
| alerts.temperature | `critical_min` | float (10.0) | 10.0 | `min` 未満。即時アラート閾値。 |
| alerts.temperature | `critical_max` | float (35.0) | 35.0 | `max` 超。即時アラート閾値。 |
| alerts.humidity | `min` | float (40.0) | 40.0 | 20〜60%。推奨範囲下限。 |
| alerts.humidity | `max` | float (60.0) | 60.0 | 40〜80%。推奨範囲上限。 |
| notifications.slack | `channel` | str (`"#baby-room"`) | `#baby-room` | Slackチャンネル名。 |
| notifications.slack | `report_interval_seconds` | int (1800) | 1800 | 300〜7200秒。定期レポート間隔。 |
| notifications.slack | `rate_limit_per_minute` | int (1) | 1 | 1〜5件/分。過剰通知防止。 |
| storage | `local_retention_days` | int (90) | 90 | 1〜365日。ローカル保持期間。 |
| storage | `cloud_sync_interval_seconds` | int (300) | 300 | 60〜3600秒。クラウド同期間隔。 |
| storage | `cloud_provider` | str (`"aws"`) | `aws` | `aws`（Phase1固定）。 |

補足:
- すべての時間値は秒単位で保持する。
- SlackトークンやAPIキーは `.env` で管理し、本設定では参照しない。
- Phase2 以降でセンサ追加・通知先追加に対応できるよう、セクション単位で拡張可能な構造を維持する。
