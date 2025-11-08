---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Build & Test Guidelines

## Development Environment Requirements

### Hardware Prerequisites
- Raspberry Pi 4 Model B (推奨)
- BME280 温湿度センサ
- I2C接続用ジャンパーワイヤ
- MicroSD カード (32GB以上)

### Software Prerequisites
- Python 3.9+
- Git
- I2C tools (Raspberry Pi OS)

## Setup & Tooling

### 仮想環境
1. `python -m venv .venv`
2. `source .venv/bin/activate` （Windows: `.venv\Scripts\activate`）
3. 依存関係インストール  
   - ランタイム: `pip install -r requirements.txt`  
   - 開発/テスト: `pip install -r requirements-dev.txt`

### 環境変数
- `ENV_SENTINEL_LOG_LEVEL`: `INFO` / `DEBUG` などログレベルを制御
- SlackトークンやAPIキーは `.env` 管理（コード直書き禁止）

### コマンド一覧

| コマンド | 用途 |
| --- | --- |
| `pytest` | ユニットテスト実行 |
| `black . && isort .` | フォーマット整形 |
| `flake8` | スタイル/静的解析 |
| `mypy` | 型検査 |
| `pytest --maxfail=1 -q` | 軽量検証（PR前など） |

## Testing Strategy

### Test Categories
- **Unit Tests**: 各モジュールの独立テスト
- **Integration Tests**: モジュール間の統合テスト
- **Hardware Tests**: 実際のセンサとの統合テスト
- **Mock Tests**: ハードウェアなしでの開発テスト

### Test-Driven Development
- 機能実装前にテストを作成
- Red-Green-Refactorサイクル
- 最低80%のテストカバレッジ

### 実機テスト（Raspberry Pi + BME280）
1. 依存インストール  
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   pip install adafruit-circuitpython-bme280 adafruit-blinka
   ```
2. I2C を有効化し `i2cdetect -y 1` でアドレス（0x76/0x77）を確認し、`sensor.i2c_address` と一致させる。  
3. ハードウェア向けテストコマンド  
   ```bash
   python -m pytest tests/sensors/test_bme280_sensor.py
   python -m pytest tests/sensors/test_bme280_sensor.py -k "raspberry" --maxfail=1 -vv
   ```
   `create_default_sensor_factory()` が Adafruit ライブラリの有無で自動的に実機ドライバを選択するため、追加の切り替え操作は不要。  
4. 実機テスト結果と使用した commit hash を `docs/tasks/task_3_sensors.md` に記録する。

## Code Quality Standards

### Automated Checks
- **Black**: コードフォーマット
- **flake8**: リンティング
- **mypy**: 型チェック
- **isort**: インポート整理
- `pytest.ini` で `src/` を `PYTHONPATH` に追加済み

### Pre-commit Hooks
実装時にpre-commit設定を追加予定

## Continuous Integration

### GitHub Actions (予定)
- プルリクエスト時の自動テスト
- コード品質チェック
- セキュリティスキャン
- 手順案: `pip install -r requirements-dev.txt` → `black --check .` → `isort --check-only .` → `flake8` → `mypy` → `pytest`

### Hardware Testing
- Raspberry Pi実機での定期テスト
- 長時間稼働テスト

## Build Process (実装後に詳細化)

### Phase 1 Build
基本的なPythonパッケージとしてのビルド

### Phase 2 Build
AWS IoT統合を含むビルド

## Deployment Strategy

### Local Deployment
- systemdサービスとしての登録
- 自動起動設定
- デプロイスクリプト実行前に `pytest` 合格およびリンタ通過を必須

### Configuration Management
- JSON設定ファイル
- 環境変数による秘匿情報管理

---

**Note**: このガイドラインは実装の進行に合わせて具体的な手順を追加していきます。
