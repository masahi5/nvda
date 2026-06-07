"""株価データ取得: 現在値と複数期間のローソク足シリーズ。"""
from __future__ import annotations

from typing import Any

import yfinance as yf

from common import SYMBOL, now_iso

# lightweight-charts 用に (period, interval) を期間キーごとに定義
RANGES: dict[str, dict[str, str]] = {
    "1D": {"period": "1d", "interval": "5m"},
    "1W": {"period": "5d", "interval": "30m"},
    "1M": {"period": "1mo", "interval": "1d"},
    "6M": {"period": "6mo", "interval": "1d"},
    "1Y": {"period": "1y", "interval": "1d"},
    "5Y": {"period": "5y", "interval": "1wk"},
}


def _series(ticker: yf.Ticker, period: str, interval: str) -> list[dict[str, Any]]:
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    out: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        # lightweight-charts は time = unix 秒(UTC)を受け付ける
        ts = int(idx.timestamp())
        try:
            out.append(
                {
                    "time": ts,
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
                }
            )
        except (ValueError, KeyError):
            # NaN 行などはスキップ
            continue
    return out


def fetch_price(ticker: yf.Ticker, fast_info: Any) -> dict[str, Any]:
    series: dict[str, list[dict[str, Any]]] = {}
    for key, cfg in RANGES.items():
        try:
            series[key] = _series(ticker, cfg["period"], cfg["interval"])
        except Exception as exc:  # noqa: BLE001 - 1期間の失敗で全体を止めない
            print(f"[warn] price series {key} failed: {exc}")
            series[key] = []

    last = getattr(fast_info, "last_price", None)
    prev = getattr(fast_info, "previous_close", None)
    change = None
    change_pct = None
    if last is not None and prev:
        change = round(float(last) - float(prev), 4)
        change_pct = round((float(last) - float(prev)) / float(prev) * 100, 2)

    return {
        "symbol": SYMBOL,
        "updated_at": now_iso(),
        "quote": {
            "price": round(float(last), 4) if last is not None else None,
            "previous_close": round(float(prev), 4) if prev is not None else None,
            "change": change,
            "change_pct": change_pct,
            "currency": getattr(fast_info, "currency", "USD") or "USD",
            "day_high": _opt(getattr(fast_info, "day_high", None)),
            "day_low": _opt(getattr(fast_info, "day_low", None)),
        },
        "series": series,
    }


def _opt(v: Any) -> float | None:
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None
