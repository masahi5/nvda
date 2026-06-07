"""空売り残高 (short interest)。

米国株なので日本株の信用買い残/売り残は存在しない。yfinance が Yahoo 経由で
公開している FINRA ベースの short interest を取得する（月2回更新）。
"""
from __future__ import annotations

from typing import Any

from common import now_iso, to_iso


def _num(info: dict[str, Any], key: str) -> float | None:
    v = info.get(key)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def fetch_short_interest(info: dict[str, Any]) -> dict[str, Any]:
    shares_short = _num(info, "sharesShort")
    prior = _num(info, "sharesShortPriorMonth")
    change_pct = None
    if shares_short is not None and prior:
        change_pct = round((shares_short - prior) / prior * 100, 2)

    return {
        "updated_at": now_iso(),
        "source": "FINRA via Yahoo Finance",
        "shares_short": shares_short,
        "shares_short_prior_month": prior,
        "shares_short_change_pct": change_pct,
        # 空売り比率 (days-to-cover)
        "short_ratio": _num(info, "shortRatio"),
        # 浮動株に対する空売り比率（0-1）
        "short_percent_of_float": _num(info, "shortPercentOfFloat"),
        "shares_outstanding": _num(info, "sharesOutstanding"),
        "float_shares": _num(info, "floatShares"),
        "date_short_interest": to_iso(info.get("dateShortInterest")),
    }
