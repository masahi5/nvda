"""共通ユーティリティ: 出力先パス・JSON入出力・時刻。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYMBOL = "NVDA"

# リポジトリ直下の data/ に出力（GitHub Pages がそのまま配信する）
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def now_iso() -> str:
    """UTC の ISO8601 文字列。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_iso(ts: Any) -> str | None:
    """unix 秒 (int/float) を ISO8601 に変換。None はそのまま。"""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def save_json(name: str, payload: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {path}")


def load_json(name: str) -> dict[str, Any] | None:
    """既存JSONを読む。取得失敗時に前回値を温存するために使う。"""
    path = DATA_DIR / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
