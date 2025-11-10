---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Coding Standards

## Code Quality Standards
- **Code Style**: Black + flake8 + isort
- **Type Hints**: 全ての関数にtype hintsを付与
- **Documentation**: docstring (Google Style)
- **Error Handling**: 適切な例外処理とログ出力

## Naming Conventions
- **Files**: snake_case (例: bme280_sensor.py)
- **Classes**: PascalCase (例: BME280Sensor)
- **Functions/Variables**: snake_case (例: read_temperature)
- **Constants**: UPPER_SNAKE_CASE (例: DEFAULT_INTERVAL)
- **Private Members**: 先頭にアンダースコア (例: _internal_method)

## Module Design Principles
- **Single Responsibility**: 各モジュールは単一の責任を持つ
- **Interface Segregation**: 小さく特化したインターフェース
- **Dependency Inversion**: 抽象に依存し、具象に依存しない
- **Plugin Architecture**: 新機能を既存コードを変更せずに追加可能

## Testing Strategy
- **Unit Tests**: pytest を使用、カバレッジ80%以上
- **Integration Tests**: 実際のセンサとの統合テスト
- **Mock Testing**: Slack API、クラウドサービスのモック
- **Hardware Testing**: Raspberry Pi実機での動作確認

## Performance Requirements
- **Sensor Reading**: 1分間隔での測定
- **Slack Notification**: 30分間隔での定期投稿
- **Response Time**: アラート発生から通知まで30秒以内
- **Resource Usage**: CPU使用率10%以下、メモリ使用量100MB以下

## Development Tools
- **Code Quality**: pre-commit hooks (black, flake8, mypy)
- **Testing**: pytest + coverage (80%以上)
- **CI/CD**: GitHub Actions
- **Containerization**: Docker (開発・テスト用)