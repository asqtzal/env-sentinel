---
inclusion: fileMatch
fileMatchPattern: '**/env-sentinel/**'
---

# Product Overview

## Product Vision & Mission
**Vision**: 新生児の環境を最適化し、将来のスマートハウス化を見据えた拡張可能なIoTモニタリングシステム

**Mission**: 技術的知識に関係なく、すべての親が赤ちゃんの快適で安全な環境を維持できるよう支援する

## Target Users
- **Primary**: 新生児を持つ親
- **Secondary**: 一般家庭でのIoT環境構築を目指すユーザー
- **Future**: スマートハウス愛好者、IoT開発者

## Core Values
- **安心**: 24時間の環境モニタリングで赤ちゃんの快適性を保証
- **利便性**: Slackを通じた手軽な通知とデータ確認
- **拡張性**: 将来的な機能追加やデバイス連携への対応
- **信頼性**: 堅牢な設計による長期間の安定稼働

## Key Features
- **環境モニタリング**: 温度・湿度の継続的な測定
- **リアルタイム通知**: Slackを通じた定期的な環境レポート
- **アラートシステム**: 環境が適切でない場合の即座の通知
- **データ履歴**: 過去のデータをグラフで可視化
- **拡張可能設計**: 将来的なセンサ追加や外部連携に対応

## Business Objectives

### Phase 1 (MVP)
- **Core Features**: 温湿度測定、直接Slack通知、アラート機能
- **Storage**: ローカルSQLiteでのデータ保存
- **Visualization**: 基本的なグラフ表示
- **Goal**: 確実に動作する基本システムの構築

### Phase 2 (Cloud Integration)
- **Cloud Features**: AWS IoT Core統合、DynamoDB保存
- **High Availability**: クラウド経由の高可用性通知
- **Scalability**: 複数デバイス対応の基盤構築
- **Goal**: エンタープライズレベルの信頼性実現

### Phase 3 (Smart Home Integration)
- **External Integration**: Home Assistant、Google Home連携
- **Advanced Analytics**: 機械学習による環境予測
- **Multi-room**: 複数部屋の統合管理
- **Goal**: 包括的なスマートハウス生態系の構築