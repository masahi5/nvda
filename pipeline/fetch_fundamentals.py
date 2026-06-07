"""ファンダメンタル指標: PER・フォワードPER・時価総額など。"""
from __future__ import annotations

from typing import Any

from common import now_iso


def _num(info: dict[str, Any], key: str) -> float | None:
    v = info.get(key)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # NaN チェック
    return f if f == f else None


def fetch_fundamentals(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "updated_at": now_iso(),
        "metrics": {
            "trailingPE": _num(info, "trailingPE"),
            "forwardPE": _num(info, "forwardPE"),
            "marketCap": _num(info, "marketCap"),
            "trailingEps": _num(info, "trailingEps"),
            "forwardEps": _num(info, "forwardEps"),
            "priceToBook": _num(info, "priceToBook"),
            "pegRatio": _num(info, "trailingPegRatio"),
            "dividendYield": _num(info, "dividendYield"),
            "beta": _num(info, "beta"),
            "fiftyTwoWeekHigh": _num(info, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _num(info, "fiftyTwoWeekLow"),
            "targetMeanPrice": _num(info, "targetMeanPrice"),
            "recommendationKey": info.get("recommendationKey"),
            "profitMargins": _num(info, "profitMargins"),
            "revenueGrowth": _num(info, "revenueGrowth"),
        },
    }
