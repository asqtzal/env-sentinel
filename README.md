# Env-Sentinel

環境センサー（BME280）とSlack通知を用いた新生児向けの環境モニタリングシステムです。Raspberry Pi上で稼働し、温湿度の常時監視・アラート通知・データ永続化を段階的に実装していきます。

## セットアップ手順

### 必要要件
- Python 3.12 以上
- `pip`, `venv`（または `pyenv` 等の仮想環境管理ツール）

### 手順
1. 仮想環境を作成  
   ```bash
   python -m venv .venv
   ```
2. 仮想環境を有効化  
   ```bash
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 依存関係をインストール  
   ```bash
   pip install -r requirements-dev.txt
   ```

### 環境変数・設定ファイル
- `ENV_SENTINEL_LOG_LEVEL`（任意）: `INFO`/`DEBUG` などのログレベルを指定。
- 設定ファイルは `config/default_config.json` をベースに `config/app_config.json`（任意）などへコピーして編集。未作成の場合は `ConfigManager` がデフォルトを自動生成。
- APIキーやSlackトークンは `.env` で管理し、コードに埋め込まない。

## コマンド一覧

| コマンド | 説明 |
| --- | --- |
| `pip install -r requirements.txt` | 本番実行用の最小依存関係をインストール |
| `pip install -r requirements-dev.txt` | 開発・テストに必要なツール群をインストール |
| `pytest` | ユニットテストを実行（仮想環境有効化後） |
| `black . && isort . && flake8` | コード整形と静的解析（任意） |

## ビルド & テスト
- 本プロジェクトはPythonアプリケーションのため、追加ビルド手順は不要です。
- テストは `pytest` で実行します。仮想環境を有効化し、`pytest` を実行してください。
- CI/CDでは `pytest` 実行と `black` / `flake8` / `mypy` を順次追加予定です。

## 設定管理
- `ConfigManager` が設定ファイルのロード/保存/ホットリロード/フォールバックを担当します。
- 基本利用例: `ConfigManager(Path("config/app_config.json"), Path("config/default_config.json")).load()`
- `start_polling()` でバックグラウンド監視可能。`fallback_callback` で異常検知時の通知を挿入できます。
- 詳細は `docs/guides/config_manager.md` を参照。

## 技術スタック

| カテゴリ | ライブラリ / ツール | 概要 | バージョン例 |
| --- | --- | --- | --- |
| 言語 | Python | コア実装言語 | 3.12 |
| 設定/バリデーション | Pydantic | 設定スキーマ・バリデーション | 1.10系 |
| 通信/非同期 | aiohttp, asyncio | Slack/API通信・非同期処理 | 3.9系 |
| ストレージ | aiosqlite | ローカルSQLite操作 | 0.19系 |
| 通知 | slack_sdk | Slack Bot連携 | 3.27系 |
| スケジューラ | APScheduler | センサ/通知スケジューリング | 3.10系 |
| テスト | pytest | ユニットテストフレームワーク | 8.4系 |
| 品質 | black / isort / flake8 / mypy | コード整形と静的解析 | 最新安定版 |

## 参考ドキュメント
- `.kiro/specs/env-sentinel/` : 要求仕様・設計・タスク計画
- `.kiro/steering/` : プロダクト方針、コーディング規約、セキュリティ指針
- `docs/reference/config_parameters.md` : 設定パラメータ一覧とデフォルト値
- `docs/tasks/task_2_config.md` : 設定モジュールに関するタスク分解
- `docs/guides/config_manager.md` : ConfigManager の使い方と監視/フォールバック手順
