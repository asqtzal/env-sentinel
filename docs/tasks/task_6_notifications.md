# Task 6: Slack通知システム詳細タスク

## 概要
- タスク名: Task 6.1〜6.3 Slack通知システム
- 目的: AlertManager・ストレージ各モジュールと連携し、Slackへの定期レポート/アラート/システム通知を非同期で安全に配信できる通知基盤を整備する。

## 背景
- 参照仕様: `.kiro/specs/env-sentinel/tasks.md` タスク6、`.kiro/specs/env-sentinel/design.md` Notification Module、`.kiro/specs/env-sentinel/requirements.md` Requirement 1/2/3/6、`.kiro/steering/security.md`
- 関連ドキュメント: `.kiro/steering/coding_standards.md`, `.kiro/steering/structure.md`, `.kiro/steering/build_and_test.md`, `docs/reference/config_parameters.md`, `docs/guides/alert_manager.md`

## スコープ
- Slack通知用データモデル (`NotificationMessage`, `NotificationKind`, `MentionPolicy`) と `BaseNotifier` 抽象の定義
- `SlackNotifier`（`slack_sdk.AsyncWebClient` ラッパー）、Block Kit メッセージビルダー
- 通知コーディネータ（Alert listener登録、定期レポート生成、システムイベント通知、キュー/レート制御、再送管理）
- ConfigManager / AlertManager / LocalStorage / Logger との結線、メトリクス・ログ整備
- 単体テスト・モック（Slack API呼び出し、バックオフ、テンプレート生成、rate-limit 時の挙動）

### アウトオブスコープ
- Phase 2 の AWS IoT / Lambda 通知経路
- Slack以外の通知チャネル（メール/SMS）実装
- メインループ統合（Task 8で実際のスケジューラと結線）

## アーキテクチャ概要
```
AlertManager ──▶ NotificationCoordinator ──▶ NotificationQueue ─▶ SlackNotifier ─▶ Slack
        ▲                │                         ▲
        │                ├─ 定期レポートタイマー ──┤
   Sensor/Storage ───────┘                ConfigManager(Hot Reload)
```
- `NotificationCoordinator` が AlertManager Listener 登録・LocalStorage/ConfigManager からの入力を束ね、`NotificationMessage` をキューに投入
- `SlackNotifier` は `AsyncWebClient` を隠蔽し、Block Kit に変換したpayloadを送信。再送・レートリミットを内部で処理
- Mentionポリシー: INFO（定期/正常化）はメンション無し、WARNING以上は `<@channel>` 等で明示通知（要確認）

## 細分化タスク

### Task 6.1: Slack通知基盤
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 6.1-a | 通知データモデル設計 | `NotificationMessage`/`NotificationKind`/`MentionPolicy` を `src/env_sentinel/notifications/models.py` に実装し、Alert・レポート・システムイベントを共通表現で扱える | 5.2 |
| 6.1-b | BaseNotifier 抽象 | Async API (`send_notification`, `close`) と共通例外 `NotificationError` を定義。typing/Docstringを整備 | 6.1-a |
| 6.1-c | Slackクライアント実装 | `SlackNotifier` を `src/env_sentinel/notifications/slack.py` に作成。`AsyncWebClient`, envベースのBot Token, Configのchannel/メンション/Rateを参照 | 6.1-b |
| 6.1-d | Block Kitビルダー | `SlackMessageBuilder` で header/section/context/fields を組み立て、Alertやレポート毎にカラーテーマ・アイコンを付与 | 6.1-c |
| 6.1-e | テストセットアップ | `tests/notifications/conftest.py` に Dummy Slack client を用意し、API呼び出しの引数検証・Token未設定時の例外を確認 | 6.1-c |

### Task 6.2: 通知メッセージ機能
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 6.2-a | Alert→Slack連携 | AlertManager Listener をラップする `NotificationCoordinator` を実装。WARNING/CRITICAL/EMERGENCY のメンション有無制御を行い、Alert詳細を Block Kit へ反映 | 6.1 |
| 6.2-b | 定期レポート生成 | `ReportGenerator` が LocalStorage から最新読み取り (および直近N件) を取得し、平均/最終値/推奨範囲との乖離をメッセージ化。Configの `report_interval_seconds` で APScheduler/asyncioタスクを起動 | 4.2 |
| 6.2-c | システム状態通知 | 起動/停止/24h稼働/設定更新/センサ復旧等のイベント用 API (`NotificationCoordinator.emit_system_event`) を定義し、Block Kit テンプレートを追加 | 6.2-a |
| 6.2-d | Hot Reload連携 | ConfigManager `on_reload` から `NotificationRuntime.reload()` を呼び出し、Slack設定（チャンネル/レート/メンション/レポート間隔）を再適用 | 2.2 |
| 6.2-e | APIドキュメント | `docs/guides/notification_system.md`（新規）か既存READMEへ通知モジュールの使い方/イベント一覧/メンションルールを記載 | 6.2-a |

### Task 6.3: 通知エラーハンドリング
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 6.3-a | リトライ/バックオフ | Slack API 4xx/5xx/RateLimit を分類し、指数バックオフ＋最大試行回数（Config/定数）を実装。失敗時はアラート履歴とローカルログへ記録 | 6.2 |
| 6.3-b | Rate Limit ガード | `NotificationQueue` にトークンバケット/タイムウィンドウを設け、`rate_limit_per_minute` 超過時は遅延送信または INFO優先度をドロップする戦略を実装 | 6.3-a |
| 6.3-c | フォールバック通知 | 連続失敗時はローカルに `pending_notifications.json` を保存し、復旧時に再送。必要に応じてログ/CLI警告 | 6.3-a |
| 6.3-d | 監視/メトリクス | 送信成功率、残キュー長、連続失敗カウントをログ出力し、将来のPrometheus統合（Phase2）を見据えてメトリクス抽象を入れる | 6.3-b |
| 6.3-e | エラーテスト | RateLimitレスポンス/ネットワーク例外/Token欠落などのシナリオをpytest + monkeypatchで再現し、再送/フォールバック挙動を検証 | 6.3-b |

## インターフェース / データモデル要件
- `NotificationMessage` fields（案）:
  - `kind`: `report | alert | system`
  - `level`: `AlertLevel` 互換 or `NotificationLevel`
  - `title`, `body`, `blocks`, `attachments`
  - `context`: dict（温湿度値、トレンド、Alert detailsなど）
  - `mention`: `MentionPolicy`（`NONE`, `HERE`, `CHANNEL`, `CUSTOM`）。Phase1は複数ユーザーIDへの `CUSTOM` メンションをデフォルトとし、設定値で `@channel` / `@here` へ切り替え可能にする。
- `NotificationCoordinator`:
  - `async def start()` / `async def stop()` でレポートタスクと送信ワーカーを管理
  - `enqueue(message: NotificationMessage, priority: int = 0)`
  - `attach_alert_manager(alert_manager: AlertManager)`
- Slack token: `.env` から取得（例: `ENV_SENTINEL_SLACK_BOT_TOKEN`）。環境変数未設定時は起動時に検知して `NotificationConfigurationError` をraise。将来的に Secrets Manager 等へ移行しやすい抽象にしておく。
- Config更新: `notifications.slack.channel`, `report_interval_seconds`, `rate_limit_per_minute`
- Block Kit テンプレート:
  - レポート: Header「Env-Sentinel 定期レポート」、fields で温度/湿度/測定時刻のみ（現時点の要件で十分）
  - アラート: Emoji/色（WARNING=yellow, CRITICAL=red, EMERGENCY=dark red）、Alert detail, recommended action
  - システム: `:satellite:` などのアイコンとステータス文

## エラーハンドリング & フォールバック
- Slack API 429: `Retry-After` を尊重して再試行、超過時はメッセージをキューへ戻す
- ネットワーク断: エラー内容をログに残し、フォールバックファイルへバッファリング。復旧後 `NotificationCoordinator.flush_pending()` で再送
- Configミス: ValidationError を Slack へ送らず、AlertManager 経由で EMERGENCY を発火（Task5 連携）
- Requirement 6.3（5分以上無通知）: Phase1は Slack への緊急通知で代替。Phase2以降でクラウド経由の外部通知を検討する。

## テスト戦略
- `tests/notifications/test_slack_notifier.py`: Token必須、メッセージ変換、Block構造、メンション付与、環境変数読み込み
- `tests/notifications/test_notification_coordinator.py`: Alert listener統合、rate-limitシミュレーション、再送キュー
- `tests/notifications/test_report_generator.py`: LocalStorageモックから統計を生成、Config間隔変更に追従
- `tests/notifications/test_error_handling.py`: 429/500/Timeout/Invalid Config でリトライ・フォールバックを確認

## 完了条件
- [x] BaseNotifier/SlackNotifier/NotificationMessage 等のAPIが確定し、`src/env_sentinel/notifications/` に配置される
- [x] AlertManagerとのListener連携により、WARNING以上のアラートがメンション付きでSlackに送信される
- [x] 定期レポートが設定間隔で生成され、温度・湿度・時刻情報を含む
- [x] システム状態（起動・停止・24h稼働・設定更新・センサ故障/復旧）がSlackで可視化される
- [x] Slack API失敗時のリトライ/レート制限/フォールバックが動作し、テストでカバーされる
- [x] `docs/guides/notification_system.md`（または既存ドキュメント）が更新され、利用手順・環境変数・トラブルシュートを記載

## 最新進捗メモ
- ✅ `NotificationRuntime` と `NotificationCoordinator` を追加し、SlackNotifier・メンションポリシー・定期レポートを統合。
- ✅ `EnvSentinelApp` が ConfigManager / AlertManager / LocalStorage を束ね、起動・停止時のシステム通知や設定ホットリロード経由の `NotificationRuntime.reload()` を呼び出せるようになった。
- ✅ `ConfigManager.set_reload_callback()` とユニットテストを追加し、ランタイムへの設定伝播を明示的に制御可能。
- ✅ `MonitoringLoop` + CLI (`python -m env_sentinel.app`) を追加し、センサ読み取り・ストレージ保存・AlertManager評価・Slack通知までを一括で起動。センサ設定（タイプ/I2C/閾値）変更時は自動的に再初期化される。
- ✅ Slack API 失敗時に `data/pending_notifications.json` へ保留し、起動時や送信再開時に再キューするフォールバックストアを実装（Task 6.3-c）。
- ✅ タスク完了条件をすべて満たし、README / 設計資料 / ガイドへ反映済み。Task 6 は Done。

## 依存関係
- 必須完了: Task 2（Config Manager）, Task 3（センサ）, Task 4（LocalStorage-最新値取得）, Task 5（AlertManager）
- 外部要因: Slack Bot Token 発行と権限付与、ネットワーク可用性、APScheduler選定（Task8統合時）

## リソース
- 担当: コア開発者
- レビュー: TBD
- 想定時間: 3〜4日（メッセージ生成 + Slack統合 + エラーハンドリング + テスト）

## リスク / 懸念
- Slack API レート制限: 頻繁なAlertで `rate_limit_per_minute` を超える可能性 → 優先度付きキューとバッチングで緩和
- Token管理: `.env` 読み込み忘れや権限不足 → 起動時バリデーションとドキュメント整備（将来Secrets Manager前提）
- ReportGeneratorのデータ源: LocalStorage未導入環境では利用できないため、フォールバックとして最新SensorReadingキャッシュを使う仕組みを検討
- Requirement 6.3（5分以上無通知）: 外部監視/別チャネルの詳細仕様が Phase2 まで未確定（Phase1はSlackのみで対応）
- システム状態通知: 起動/停止が必須。他イベントは任意で段階的に追加。

## オープン質問
- 解消済み（2025-02-14):
  1. メンション: 特定ユーザー（ダミーID）を `CUSTOM` で通知。Config切替で `@channel`/`@here` も可。
  2. Slack Bot Token: `.env` 管理 (`ENV_SENTINEL_SLACK_BOT_TOKEN` 想定)。将来Secrets Manager移行余地あり。
  3. 定期レポート: 最新値 + 測定時刻のみ。
  4. Requirement 6.3: Phase1はSlack通知、クラウド化後に外部通知へ拡張。
  5. システム状態通知: 起動/停止が必須、その他は準必須/任意。

--- 

（本ドキュメントは Task 6 の作業ブレークダウンおよび参照仕様として運用します。進捗に応じてステータス欄を更新してください。）
