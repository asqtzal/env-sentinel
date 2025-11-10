# Task 5: アラート・モニタリングシステム詳細タスク

## 概要
- タスク名: Task 5.1 / 5.2 アラート判定・管理
- 目的: センサ計測からアラート生成・状態追跡までを一元管理し、通知モジュール（Task 6）へ正規化した `Alert` を渡せるようにする。

## 背景
- 参照仕様:
  - `.kiro/specs/env-sentinel/tasks.md` タスク5
  - `.kiro/specs/env-sentinel/requirements.md` Requirement 2, 3, 6
  - `.kiro/specs/env-sentinel/design.md` Monitoring Module
- 関連ドキュメント:
  - `.kiro/steering/coding_standards.md`
  - `.kiro/steering/structure.md`
  - `docs/reference/config_parameters.md`

## スコープ
- 実施内容:
  - 温湿度の閾値判定・アラートレベル付与ロジック実装
  - センサ故障/異常イベントの取り込みと EMERGENCY アラート生成
  - アラート状態管理（発火抑止、正常化検知、ヒストリー集約）
  - ConfigManager・Sensorモジュールとの結線、およびユニットテスト
- アウトオブスコープ:
  - Slackなど実際の送信処理（Task 6で実装）
  - グラフ表示/可視化（Task 7）

## 細分化タスク

### Task 5.1: アラート判定エンジン
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 5.1-a | `AlertManager` API確定と状態管理方針の実装 | `evaluate_reading()` が SensorReading を入力に WARNING/CRITICAL/EMERGENCY を返却し、温度・湿度ごとの現在状態を保持できる | 3.2 |
| 5.1-b | 温度/湿度閾値判定と連投抑止 | 初回のみアラート生成・レンジ外継続中はミュート、範囲復帰時のリセットロジックを実装 | 5.1-a |
| 5.1-c | センサイベント取込 | `SensorFailureEvent`/`SensorAnomalyEvent` を受け取るハンドラを追加し、EMERGENCY アラートを生成（折衷案: MonitoringでAlert化） | 5.1-a |
| 5.1-d | ユニットテスト | 正/異常判定、連投抑止、イベント→EMERGENCY変換を pytest で網羅 | 5.1-b |

### Task 5.2: アラート管理機能
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 5.2-a | アラートライフサイクル追跡 | 指標ごとの状態テーブル（active/resolved）を保持し、正常化通知を温度・湿度それぞれ独立に生成 | 5.1 |
| 5.2-b | 正常化検知ロジック | WARNING/CRITICAL 状態からレンジ内へ戻った瞬間に `✅` 通知用 Alert を生成し、記録を更新 | 5.2-a |
| 5.2-c | アラート履歴・重複抑止 | 最近の Alert を集約・重複排除して Notification モジュールへ渡せるようにする（例: 直近N件や状態マップ） | 5.2-a |
| 5.2-d | インターフェース整備 | 通知層が `AlertManager.subscribe()` などで Alert を受け取り、Task 6 側でメンション有無を切り替えられる API を提供 | 5.2-a |
| 5.2-e | テスト/モック | 正常化、複数指標並走、履歴クエリ等のテストを追加 | 5.2-b |

## 完了条件
- [ ] 温度・湿度の WARNING/CRITICAL 閾値が Config 値に準拠し、連続状態でも二重送信しない。
- [ ] 正常化通知は指標ごとに生成され、推奨レンジへ復帰した瞬間に一回だけ Alert を発行する。
- [ ] センサ故障/異常イベントを Monitoring 層で受け取り EMERGENCY レベルの Alert に変換できる。
- [ ] ユニットテストが全て通過し、異常系・フォールバックを網羅。
- [ ] Task 6 へ渡すための Alert API と利用手順を docs/guides 等に追記（このタスクでドラフト、Task 6完了時に最終化）。

## 依存関係
- 必須完了タスク: Task 2（設定管理）、Task 3.2/3.3（センサ・イベントフック）
- 外部要因: Configの閾値更新、Slack通知仕様（Task 6の要件）への追随

## リソース
- 担当: コア開発者
- レビュー担当: TBD
- 想定作業時間: 2.0〜2.5日

## メモ
- アラートは状態遷移時のみ送信し、連投は行わない（WARNING/CRITICALへ入った瞬間、および正常化時）。
- 正常化通知は温度・湿度それぞれ独立して扱う。
- Task 6 の範囲: 定期レポートはメンションなしで 30 分間隔など一定周期、アラート通知はメンション付きで送信する方針。Monitoring は Alert を用途非依存で発火し、通知層がメンション有無を切替える。

## 進捗メモ（最新）
- ✅ `Alert` / `AlertLevel` / `AlertCategory` を `src/env_sentinel/monitoring/models.py` に定義し、通知モジュールと共有できる共通ペイロードを整備。
- ✅ `AlertManager`（`src/env_sentinel/monitoring/manager.py`）を実装。温湿度の WARNING/CRITICAL 判定、状態遷移による単発通知、正常化アラート、および `SensorFailureEvent` / `SensorAnomalyEvent` を EMERGENCY Alert へ変換する処理を完了。Listener API と履歴保持 (`get_recent_alerts`) も実装済み。
- ✅ `tests/monitoring/test_alert_manager.py` で連投抑止、正常化通知、湿度クリティカル、センサイベント変換、Listener 呼び出し、履歴上限をカバーし `pytest` パスを確認 (`tests/config` との併走で 18件成功)。
- ✅ `docs/guides/alert_manager.md` を追加し、AlertManager の API 仕様・通知ポリシー・履歴の使い方をタスクドキュメントから参照できるようにした。
- 🔜 Task 6 で SlackNotifier を AlertManager Listener と接続し、メンション制御や定期レポートの実装を行う。
