"""全データを取得して data/*.json を生成するエントリポイント。

各取得は独立して try/except し、失敗した場合は前回JSONを温存する
（1つのソース障害でダッシュボード全体を壊さない）。
"""
from __future__ import annotations

import sys

import yfinance as yf

from common import SYMBOL, load_json, save_json
from fetch_fundamentals import fetch_fundamentals
from fetch_news import fetch_news
from fetch_price import fetch_price
from fetch_short_interest import fetch_short_interest
from fetch_x import fetch_x


def _run(name: str, filename: str, fn) -> bool:
    """fn() を実行し JSON 保存。失敗時は前回値を温存して False。"""
    try:
        payload = fn()
        save_json(filename, payload)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {name} failed: {exc}")
        prev = load_json(filename)
        if prev is not None:
            print(f"[info] {filename}: 前回値を温存します")
        return False


def main() -> int:
    ticker = yf.Ticker(SYMBOL)

    # info / fast_info は一度だけ取得して各 fetch で共有
    try:
        info = ticker.get_info()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] get_info failed: {exc}")
        info = {}
    fast_info = ticker.fast_info

    results = {
        "price": _run("price", "price.json", lambda: fetch_price(ticker, fast_info)),
        "fundamentals": _run("fundamentals", "fundamentals.json", lambda: fetch_fundamentals(info)),
        "short_interest": _run("short_interest", "short_interest.json", lambda: fetch_short_interest(info)),
        "news": _run("news", "news.json", fetch_news),
        "x": _run("x", "x.json", fetch_x),
    }

    ok = sum(results.values())
    print(f"\n=== 完了: {ok}/{len(results)} 成功 ===")
    for k, v in results.items():
        print(f"  {'OK ' if v else 'NG '} {k}")

    # 1つでも成功すればコミットする価値があるので 0 を返す
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
