# ConfigManager 利用ガイド

Env-Sentinel の設定は `ConfigManager` クラスで読み書き・ホットリロードが可能です。  
ここでは主なAPIと利用パターンをまとめます。

## パス構成
- アクティブ設定ファイル: `config/app_config.json` など任意のパス（存在しなければ自動生成）
- デフォルト設定: `config/default_config.json`

## 基本的な使い方
```python
from pathlib import Path

from env_sentinel.config import ConfigManager

manager = ConfigManager(
    config_path=Path("config/app_config.json"),
    default_path=Path("config/default_config.json"),
)
app_config = manager.load()  # ファイルが無ければデフォルトを生成して読み込み

# 参照
interval = app_config.sensor.read_interval_seconds

# 設定を変更して保存
updated = app_config.copy(update={"sensor": {"read_interval_seconds": 120}})
manager.save(updated)
```

## ホットリロード
- `reload_if_updated()` を定期的に呼び出すと、ファイル更新時に新しい設定が適用されます。
- `start_polling()` を使うとバックグラウンドスレッドで監視します（`poll_interval_seconds` で間隔を指定）。

```python
def on_reload(config):
    scheduler.update_interval(config.sensor.read_interval_seconds)

manager = ConfigManager(
    Path("config/app_config.json"),
    Path("config/default_config.json"),
    on_reload=on_reload,
    poll_interval_seconds=5,
)
manager.load()
manager.start_polling()
```

## フォールバックと通知
- 無効な設定が保存された場合、`ValidationError` を検知してデフォルト値へ自動復帰します。
- `fallback_callback` を渡すと、Slack通知の作成など異常検知時の処理を差し込めます。

```python
from pydantic import ValidationError

def on_invalid(exc: ValidationError) -> None:
    logger.error("Configuration rejected: %s", exc)

manager = ConfigManager(
    Path("config/app_config.json"),
    Path("config/default_config.json"),
    fallback_callback=on_invalid,
)
```

## テスト
- `tests/config/test_manager.py` で I/O・ホットリロード・フォールバックのテストを実装済み。
- 追加のユースケースをカバーする場合は `pytest` で動作確認してください。
