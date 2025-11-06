---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Security Guidelines

## Security & Credentials
- **Environment Variables**: `.env`ファイルでAPI keys管理
- **Encryption**: 設定ファイル内の秘匿情報は暗号化
- **Network**: HTTPS/TLS通信必須
- **Access Control**: Slack Bot Tokenの最小権限設定

## Data Protection
- **Privacy by Design**: 個人データ保護を設計段階から考慮
- **Data Minimization**: 必要最小限のデータのみ収集・保存
- **Encryption at Rest**: ローカル・クラウド両方でデータ暗号化
- **Secure Transmission**: API通信は全てHTTPS/TLS

## Access Control
- **Authentication**: 強固な認証メカニズム
- **Authorization**: 最小権限の原則
- **API Security**: レート制限とトークン管理
- **Network Security**: ファイアウォール設定

## Operational Security
- **Log Security**: 機密情報をログに出力しない
- **Error Handling**: エラーメッセージで内部情報を漏洩しない
- **Update Management**: セキュリティパッチの迅速な適用
- **Backup Security**: バックアップデータの暗号化

## Compliance & Monitoring
- **Security Monitoring**: 異常なアクセスパターンの検知
- **Audit Logging**: セキュリティ関連イベントの記録
- **Vulnerability Assessment**: 定期的なセキュリティ評価
- **Incident Response**: セキュリティインシデント対応手順