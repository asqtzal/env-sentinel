# Task 4: ストレージモジュール詳細タスク

## 概要
- タスク名: Task 4.1〜4.2 ストレージモジュール
- 目的: センサデータのローカル永続化と取得インターフェースを整備し、可視化・分析・将来のクラウド同期に備える。

## 背景
- 参照仕様: `.kiro/specs/env-sentinel/tasks.md` タスク4、`.kiro/specs/env-sentinel/design.md` Storage Module、`.kiro/specs/env-sentinel/requirements.md` Requirement 4 系列
- 関連ドキュメント: `.kiro/steering/tech.md` Storage/DB 記述、`.kiro/steering/build_and_test.md` ビルド/テスト手順、`docs/reference/config_parameters.md` storage セクション

## スコープ
- SQLite ベースの `LocalStorage` 実装（非同期 API）
- DB スキーマ/マイグレーション/接続管理
- データ保持期間とクリーンアップ
- 時系列取得 API（グラフ/アラート用）
- 単体テスト（インメモリSQLite）

## 細分化タスク

### Task 4.1: SQLiteデータベース設計と初期化
| ID | 内容 | 現状/完了条件 | 依存 |
| --- | --- | --- | --- |
| 4.1-a | DB スキーマ定義 | ✅ `storage_metadata` + `sensor_readings`（`synced_to_cloud`/`invalid_fields`/`created_at`含む）を `src/env_sentinel/storage/local.py` で作成 | 3.3 |
| 4.1-b | 接続/トランザクション管理 | ✅ `asynccontextmanager` ベースの `_connection()` を導入し、全APIで共有 | 4.1-a |
| 4.1-c | 設定項目と DB パス | ✅ `StorageConfig.db_path`（Path型、デフォルト `data/env_sentinel.db`）と ConfigManager のシリアライズを実装 | 4.1-a |
| 4.1-d | マイグレーション/ヘルスチェック | ✅ `storage_metadata` で schema version を保持し、`LocalStorage.health_check()` 追加 | 4.1-b |

### Task 4.2: データ保存・取得機能の実装
| ID | 内容 | 現状/完了条件 | 依存 |
| --- | --- | --- | --- |
| 4.2-a | `LocalStorage.store_reading` | ✅ invalid_fieldsをJSON化しINSERT、失敗時は `StorageError` ラップ | 4.1 |
| 4.2-b | `LocalStorage.get_recent_data` | ✅ UTCベース + 任意 `limit` サポートで降順取得 | 4.2-a |
| 4.2-c | データ保持/クリーンアップ | ✅ INSERT後に `purge_expired_data()` を呼び出し、削除件数をログ出力 | 4.2-a |
| 4.2-d | テスト | ✅ `tests/storage/test_local_storage.py` で保存/取得/保持/invalid回収/health-checkを網羅 | 4.2-b |

## インターフェース要件
- `LocalStorage` は非同期メソッド (`async def store_reading(...)`) を提供し、呼び出し側メインループから await 可能にする。
- 戻り値は bool（成功/失敗）または `List[SensorReading]`、失敗時は `StorageError`（独自例外）を raise。
- バッチ取得 API は後続の可視化/通知処理で再利用できるよう `List[SensorReading]` を返し、呼び出し側で時間・件数制御を行う。

## エラーハンドリング
- DB 接続・クエリ失敗時は再試行（設定可能）やロギングを行い、アラートモジュールに通知できるよう後続タスクでフックを追加。
- ディスクフルやファイル権限エラーは `StorageError` として検出し、Monitoring/Notification へ伝播できるようメッセージを整備。

## テストと検証
- `source .venv/bin/activate && python -m pytest tests/storage/test_local_storage.py` で以下をカバー
  - 正常保存/取得
  - `storage.local_retention_days` に基づく削除
  - `get_recent_data(limit=...)` の降順取得
  - DB 再接続/マイグレーション（schema_version維持）
  - エラーハンドリング（health check、invalid data round-trip）
- CI ではインメモリまたはテンポラリディレクトリで完結させ、Raspberry Pi 実機では実ファイルを使ったスモークも任意で追加。

## 完了条件
- `LocalStorage` の API と内部スキーマが確定し、センサモジュールから呼び出し可能。
- データ保持ポリシー（retention days）が設定値に従って動作。
- 新規テストが `pytest` でパス。
- ドキュメント（本ファイル、`.kiro/steering/build_and_test.md` 等）に手順と制約が反映されている。

## リソース
- 担当: コア開発者
- レビュー: TBD
- 想定時間: 2〜3日（DBスキーマ + API + テスト）

## メモ
- Phase 2 で `HybridStorage` を導入するため、`LocalStorage` の API はクラウド同期層からも再利用できるよう疎結合に保つ。
- 将来的なデータ圧縮やバッチ同期を見据え、INSERT/SELECT 文は SQL ビルダーまたはシンプルな SQL に分離しておくとよい。
- `storage_metadata` で schema version を追跡し、今後のマイグレーションでは version をインクリメントして `health_check` で検出できるようにする。
