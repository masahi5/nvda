# pipeline

NVDA の無料データを取得し、`/data/*.json` を生成するバッチ。

```bash
uv sync
uv run python main.py
```

GitHub Actions から定期実行される（`.github/workflows/update-data.yml`）。
