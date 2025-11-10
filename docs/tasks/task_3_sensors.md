# Task 3: センサモジュール詳細タスク

## 概要
- タスク名: Task 3.1〜3.3 センサモジュール
- 目的: Sensor モジュールの基礎を実装し、BME280 ドライバとエラーハンドリングを整備する。

## 背景
- 参照仕様: `.kiro/specs/env-sentinel/tasks.md` タスク3、`.kiro/specs/env-sentinel/design.md` Sensor Module、`.kiro/specs/env-sentinel/requirements.md` Requirement 1/2/6
- 関連ドキュメント: `.kiro/steering/tech.md`, `.kiro/steering/structure.md`

## スコープ
- SensorReading データモデルと検証
- BaseSensor インターフェース、センサファクトリ
- BME280 実装の土台（I2Cドライバはモック/抽象化）
- エラーハンドリング（リトライ、異常値無効化、故障通知フック）
- ユニットテスト

## 細分化タスク

### Task 3.1: センサ基底実装
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 3.1-a | SensorReading実装 | dataclass + validate() で温度/湿度範囲チェック、前回値補間、`is_valid` フラグ | Task 2 | Done |
| 3.1-b | BaseSensor抽象クラス | `async read()` / `close()`、共通リトライ・ヘルスチェックのフック定義 | 3.1-a |
| 3.1-c | SensorFactory | Configからセンサを生成、未対応タイプは例外 | 3.1-b |
| 3.1-d | ユニットテスト | SensorReading検証、ファクトリ挙動、抽象クラスの契約テスト | 3.1-a |

### Task 3.2: BME280ドライバ実装
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 3.2-a | ドライバラッパ設計 | 実デバイス/モックを切替可能なインターフェース設計 | 3.1 |
| 3.2-b | BME280センサ実装 | `read()` で温度/湿度/圧力を取得し、SensorReadingに変換 | 3.2-a |
| 3.2-c | I2Cセットアップコード | Raspberry Pi 上での I2C 初期化（実装は後から追加でもOK） | 3.2-b |
| 3.2-d | テスト | モックドライバで値取得、失敗時のリトライ等を検証 | 3.2-b |

### Task 3.3: センサエラーハンドリング
| ID | 内容 | 完了条件 | 依存 |
| --- | --- | --- | --- |
| 3.3-a | 故障検知ロジック | 連続失敗回数をカウントし、閾値で `SensorFailure` イベントを発行 | 3.1 |
| 3.3-b | 異常値検出 | 物理的に不可能な値を弾き、前回値で補完、`is_valid=False` でマーク | 3.1 |
| 3.3-c | エラー通知フック | ConfigManagerやAlertシステムに連携できるコールバックを定義 | 3.2 |
| 3.3-d | テスト | 連続失敗→故障、異常値→補完/無効化をユニットテスト | 3.3-a |

## 完了条件
- [ ] SensorReading と BaseSensor のAPI定義が固まり、データ検証が行われる。
- [ ] BME280 実装が最低限の読取処理を行い、モックテストが通過。
- [ ] エラーハンドリング・通知ルートが提供され、要件6（安全性）に沿った挙動を担保。
- [ ] 追加したテストが `pytest` で成功。

## 進捗メモ（最新）

- ✅ **3.1 センサ基底実装**  
  - `SensorReading`（`src/env_sentinel/sensors/models.py`）とバリデーション/補完ロジック済み。  
  - `BaseSensor`・`SensorError`系例外を `src/env_sentinel/sensors/base.py` に実装。共通リトライ、ヘルスチェック、直近正常値の保持を提供。  
  - `SensorFactory` を `src/env_sentinel/sensors/factory.py` に追加し、`SensorConfig` からセンサを生成できるようになった（未登録タイプは `SensorFactoryError`）。  
  - テスト: `tests/sensors/test_base_sensor.py`, `tests/sensors/test_sensor_factory.py`, `tests/sensors/test_sensor_reading.py` を `.venv` 有効化後に `python -m pytest tests/sensors` で実行し 12 件成功。
- ✅ **3.2-a/b BME280 ドライバ/センサ土台**  
  - `src/env_sentinel/sensors/bme280.py` に BME280 ドライバ Protocol・サンプルデータクラス・`BME280Sensor` を追加。  
  - ドライバファクトリ経由でモック/実機を差し替え可能。デフォルトは `SimulatedBME280Driver`。  
  - `DEFAULT_BME280_BUILDER` を `SensorFactory` に登録すれば設定値から `BME280Sensor` を生成できる。  
  - テスト: `tests/sensors/test_bme280_sensor.py` でドライバ差し替え・リトライ・ファクトリ統合を検証済み。  
- ✅ **3.2-c I2C セットアップコード**  
  - Adafruit CircuitPython スタックを利用する `RaspberryPiBME280Driver` を追加。`create_raspberry_pi_driver_factory()` でドライバを組み立て。  
  - `create_default_sensor_factory(prefer_hardware=None)` はハードウェア依存を自動検出し、利用不可の場合はシミュレータにフォールバック。  
  - ハードウェア向けには `pip install adafruit-circuitpython-bme280 adafruit-blinka` を Raspberry Pi 上で実行し、`SensorFactory` に `RASPBERRY_PI_BME280_BUILDER` を登録すれば実機動作可能。  
- 🚧 **3.2-d モック/実機テスト**  
  - 追加済み:  
    - `tests/sensors/test_bme280_sensor.py` にリトライ限界（`SensorReadError`）、I2C初期化失敗、`RaspberryPiBME280Driver` の読み取り失敗を再現するケースを追加。  
    - `pytest tests/sensors/test_bme280_sensor.py` で 9 ケース成功（CI向けはシミュレータのみ）。  
  - 未了: 実機（Raspberry Pi）で `RASPBERRY_PI_BME280_BUILDER` を使い `python -m pytest tests/sensors/test_bme280_sensor.py -k raspberry --maxfail=1` などを実行し I2C 通信を確認。  
- ✅ **3.3 エラーハンドリング**  
  - `SensorFailureEvent` / `SensorAnomalyEvent` を `src/env_sentinel/sensors/models.py` に定義。  
  - `BaseSensor` が `failure_callback` / `anomaly_callback` を受け取り、連続失敗閾値超過や `SensorReading` の `invalid_fields` を検知して通知。  
  - 失敗イベントは閾値到達時に一度発火し、成功でリセット。異常値は `SensorReading.validate()` の結果に応じて通知。  
  - テスト: `tests/sensors/test_base_sensor.py` / `tests/sensors/test_sensor_reading.py` でイベント発火・invalid_fields 記録を検証。  
- ⏳ **次ステップ候補**  
  1. Task 3.2-d 残件: Raspberry Pi 上で依存 (`pip install adafruit-circuitpython-bme280 adafruit-blinka`) を導入し、センサ接続した状態で読取テスト・ログ取得（Phase1 終盤の実機検証タイミングで実施予定）。  
  2. Monitoring/Alert連携: `failure_callback` / `anomaly_callback` に Monitoring モジュールや ConfigManager のフックを接続し、通知/アラートラインへ伝播する処理を実装。  
  3. 運用ドキュメント更新: センサイベントのサブスクライブ手順・設定例を `docs/guides` 配下に追記。  
- 📌 **動作確認手順**  
  ```bash
  source .venv/bin/activate
  python -m pytest tests/sensors
  ```
  `pyenv: cannot rehash` の警告は書き込み権限が無いだけで動作に影響しないことを確認済み（18件成功）。

## リソース
- 担当: コア開発者
- レビュー: TBD
- 想定時間: 2〜3日

## メモ
- BME280 のライブラリ差し替えに備え、ドライバ抽象を維持。
- 実機テストが難しい段階ではモックで整合性を確保し、Phase 1 終盤でRaspberry Pi + BME280実機検証を計画。
