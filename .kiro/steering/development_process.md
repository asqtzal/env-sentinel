---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Development Process

## Git Workflow

### Branch Strategy
- **main**: 本番リリース用ブランチ
- **develop**: 開発統合ブランチ
- **feature/**: 機能開発ブランチ (例: feature/sensor-module)
- **hotfix/**: 緊急修正ブランチ

### Commit Message Convention
- [Conventional Commits](https://www.conventionalcommits.org/)に従う
- 基本的にdescriptionは日本語で記載する


**Format**:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: 新機能追加
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードスタイル変更（機能に影響なし）
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルド・設定変更

**Scopes** (env-sentinel用):
- `sensor`: センサ関連
- `notification`: 通知関連
- `storage`: データ保存関連
- `config`: 設定管理関連
- `monitoring`: モニタリング・アラート関連
- `visualization`: データ可視化関連
- `iot`: AWS IoT関連
- `deploy`: デプロイメント関連

**Examples**:
```
feat(sensor): add BME280 sensor driver implementation

fix(notification): handle Slack API rate limiting properly

docs(setup): add Raspberry Pi installation guide

test(sensor): add unit tests for sensor error handling

chore(deps): update dependencies to latest versions
```

## Code Review Process

### Pull Request Guidelines
1. **Title**: コミットメッセージ規約に従う
2. **Description**: 変更内容と理由を明記
3. **Testing**: テスト結果とカバレッジを報告
4. **Screenshots**: UI変更がある場合は画像添付

### Review Checklist
- [ ] コードがcoding_standards.mdに準拠している
- [ ] 適切なテストが追加されている
- [ ] ドキュメントが更新されている
- [ ] セキュリティ要件を満たしている
- [ ] パフォーマンスへの影響を考慮している

## Release Process

### Version Numbering
[Semantic Versioning](https://semver.org/)に従う: `MAJOR.MINOR.PATCH`

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

### Release Workflow
1. **Feature Freeze**: 新機能の追加停止
2. **Testing**: 統合テスト・ハードウェアテストの実行
3. **Documentation**: リリースノート・ドキュメント更新
4. **Tagging**: Gitタグの作成
5. **Deployment**: 本番環境へのデプロイ

## Issue Management

### Issue Labels
- `bug`: バグ報告
- `enhancement`: 機能改善
- `feature`: 新機能要求
- `documentation`: ドキュメント関連
- `question`: 質問・サポート
- `priority:high`: 高優先度
- `priority:medium`: 中優先度
- `priority:low`: 低優先度
- `phase:1`: Phase 1関連
- `phase:2`: Phase 2関連

### Issue Templates
**Bug Report**:
```markdown
## 問題の説明
[バグの詳細な説明]

## 再現手順
1. [手順1]
2. [手順2]
3. [手順3]

## 期待される動作
[期待される結果]

## 実際の動作
[実際の結果]

## 環境
- OS: [例: Raspberry Pi OS]
- Python Version: [例: 3.9.2]
- Hardware: [例: Raspberry Pi 4B]
```

**Feature Request**:
```markdown
## 機能の説明
[新機能の詳細な説明]

## 動機・背景
[なぜこの機能が必要か]

## 提案する解決策
[実装方法の提案]

## 代替案
[他の解決方法があれば]
```

## Continuous Integration

### Pre-commit Hooks
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
```

### GitHub Actions Workflow
- **Lint**: コードスタイルチェック
- **Test**: ユニット・統合テスト実行
- **Coverage**: テストカバレッジ測定
- **Security**: セキュリティ脆弱性スキャン
- **Hardware Test**: Raspberry Pi実機テスト（手動トリガー）

## Documentation Standards

### Code Documentation
- **Docstrings**: Google Style docstringsを使用
- **Type Hints**: 全ての関数・メソッドに型注釈
- **Comments**: 複雑なロジックには説明コメント

### Project Documentation
- **README.md**: プロジェクト概要・セットアップ手順
- **CHANGELOG.md**: バージョン別変更履歴
- **docs/**: 詳細なドキュメント
  - `setup.md`: セットアップガイド
  - `api.md`: API仕様
  - `troubleshooting.md`: トラブルシューティング