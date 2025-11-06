# Requirements Document

## Introduction

Env-Sentinelは、新生児の環境を最適化するためのIoTモニタリングシステムです。Raspberry Piと温湿度センサを使用して環境データを継続的に測定し、Slackを通じて親に通知することで、赤ちゃんの快適で安全な環境維持を支援します。将来的なスマートハウス化も見据えた拡張可能な設計を採用します。

## Requirements

### Requirement 1

**User Story:** 新生児の親として、部屋の温度と湿度をリアルタイムで把握したいので、Raspberry Piで測定したデータを定期的にSlackで受け取りたい

#### Acceptance Criteria

1. WHEN Raspberry Piが起動している THEN システムは温湿度センサから継続的にデータを取得する SHALL
2. WHEN 測定データが取得される THEN システムは温度（摂氏）と湿度（パーセント）を正確に記録する SHALL
3. WHEN 設定された間隔（例：30分）が経過する THEN システムは最新の測定値をSlackチャンネルに投稿する SHALL
4. WHEN Slackに投稿する THEN メッセージには現在の温度、湿度、測定時刻が含まれる SHALL

### Requirement 2

**User Story:** 新生児の親として、環境が適切でない場合にすぐに気づきたいので、温湿度が推奨範囲を外れた時にアラート通知を受け取りたい

#### Acceptance Criteria

1. WHEN 温度が18℃未満または26℃を超える THEN システムは緊急アラートをSlackに送信する SHALL
2. WHEN 湿度が40%未満または60%を超える THEN システムは緊急アラートをSlackに送信する SHALL
3. WHEN アラートが発生する THEN メッセージには「⚠️ 環境アラート」の表示と具体的な数値が含まれる SHALL
4. WHEN 環境が正常範囲に戻る THEN システムは「✅ 環境正常化」の通知を送信する SHALL

### Requirement 3

**User Story:** システム管理者として、Raspberry Piの動作状況を把握したいので、システムの稼働状態とエラー情報をモニタリングしたい

#### Acceptance Criteria

1. WHEN システムが起動する THEN 起動完了メッセージをSlackに送信する SHALL
2. WHEN センサの読み取りエラーが発生する THEN エラー詳細をSlackに報告する SHALL
3. WHEN システムが24時間連続稼働する THEN 稼働状況レポートをSlackに送信する SHALL
4. WHEN ネットワーク接続が失敗する THEN ローカルログにエラーを記録し、接続復旧時にSlackに報告する SHALL

### Requirement 4

**User Story:** 新生児の親として、過去の環境データを確認して傾向を把握したいので、測定データの履歴を保存し、グラフで視覚的に参照できるようにしたい

#### Acceptance Criteria

1. WHEN 測定データが取得される THEN システムはローカルデータベースとクラウドストレージの両方にタイムスタンプ付きでデータを保存する SHALL
2. WHEN ローカルデータが一定期間を超える THEN 古いデータをクラウドに移行し、ローカルには直近データのみ保持する SHALL
3. WHEN 過去データの参照が要求される THEN ローカルとクラウドの両方からデータを検索し、指定期間の温湿度データを時系列グラフとして生成できる SHALL
4. WHEN グラフが生成される THEN 温度と湿度の推移、アラート発生箇所が視覚的に分かりやすく表示される SHALL
5. WHEN システムが再起動する THEN 保存されたデータは失われず、クラウドから復旧できる SHALL
6. WHEN ネットワーク接続が不安定な場合 THEN ローカルにデータを蓄積し、接続復旧時にクラウドに同期する SHALL

### Requirement 5

**User Story:** システム管理者として、設定を柔軟に変更したいので、投稿間隔やアラート閾値を設定ファイルで管理したい

#### Acceptance Criteria

1. WHEN システムが起動する THEN 設定ファイル（JSON形式）から投稿間隔、アラート閾値、Slack設定を読み込む SHALL
2. WHEN 設定ファイルが存在しない THEN デフォルト設定でシステムを起動し、設定ファイルを自動生成する SHALL
3. WHEN 設定ファイルが更新される THEN システム再起動なしで新しい設定を適用する SHALL
4. WHEN 無効な設定値が検出される THEN エラーメッセージをSlackに送信し、デフォルト値を使用する SHALL

### Requirement 6

**User Story:** 新生児の親として、システムが正常に動作していることを確信したいので、センサやシステムの故障を即座に検知し、安全を確保したい

#### Acceptance Criteria

1. WHEN センサが3回連続で読み取りに失敗する THEN システムは緊急アラートをSlackに送信し、センサ故障を報告する SHALL
2. WHEN 測定値が物理的に不可能な範囲（例：温度-50℃や100℃）を示す THEN システムはデータを無効とし、センサ異常をSlackに報告する SHALL
3. WHEN システムが5分間以上データを送信しない THEN 外部監視システムまたは別の通知手段で障害を報告する SHALL
4. WHEN 温度が極端な値（10℃未満または35℃超）を示す THEN システムは即座に緊急アラートを送信し、手動確認を促す SHALL
5. WHEN システムの重要なプロセスが停止する THEN 自動復旧を試行し、失敗した場合は緊急通知を送信する SHALL

### Requirement 7

**User Story:** 将来のスマートハウス化を見据えて、システムを拡張できるよう、柔軟なアーキテクチャを構築したい

#### Acceptance Criteria

1. WHEN システムが設計される THEN モジュラー構造で各機能（センサ読み取り、通知、データ保存）が独立したコンポーネントとして実装される SHALL
2. WHEN 新しいセンサタイプを追加する THEN 既存コードを変更せずにプラグイン方式で追加できる SHALL
3. WHEN 他の通知手段を追加する THEN 通知インターフェースを実装するだけで対応できる SHALL
4. WHEN 設定を変更する THEN システム再起動なしで新しい設定を適用できる SHALL
5. WHEN 外部システムとの連携が必要になる THEN APIまたは標準プロトコルでデータを提供できる SHALL