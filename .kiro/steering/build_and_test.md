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

## Code Quality Standards

### Automated Checks
- **Black**: コードフォーマット
- **flake8**: リンティング
- **mypy**: 型チェック
- **isort**: インポート整理

### Pre-commit Hooks
実装時にpre-commit設定を追加予定

## Continuous Integration

### GitHub Actions (予定)
- プルリクエスト時の自動テスト
- コード品質チェック
- セキュリティスキャン

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

### Configuration Management
- JSON設定ファイル
- 環境変数による秘匿情報管理

---

**Note**: このガイドラインは実装の進行に合わせて具体的な手順を追加していきます。