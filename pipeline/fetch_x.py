"""X(Twitter) の $NVDA 投稿取得。

公式 X API は有料のため、Twitter→RSS 変換サービス（RSSHub / Nitter 等）の
無料RSSを経由して取得する。公開インスタンスは停止・不安定なことが多いため、
複数の候補エンドポイントを順に試し、最初に取得できたものを採用する。

環境変数 `X_RSS_URLS`（カンマ区切り）を設定すると、それを最優先で使う。
安定運用したい場合は自前の RSSHub インスタンス等を指定する想定。
"""
from __future__ import annotations

import os
from typing import Any

import feedparser
import requests

from common import feed_published_iso, now_iso

# $NVDA 投稿を返す候補RSS。上から順に試し、1件以上取れたら打ち切る。
# 公開インスタンスは不安定なため、本番は環境変数 X_RSS_URLS での上書きを推奨。
DEFAULT_RSS_URLS: list[str] = [
    "https://rsshub.app/twitter/keyword/%24NVDA",
    "https://nitter.net/search/rss?f=tweets&q=%24NVDA",
    "https://nitter.poast.org/search/rss?f=tweets&q=%24NVDA",
]

MAX_ITEMS = 30
TIMEOUT = 12  # 秒
USER_AGENT = "Mozilla/5.0 (compatible; NVDA-Dashboard/1.0; +https://github.com/)"


def _rss_urls() -> list[str]:
    env = os.environ.get("X_RSS_URLS", "").strip()
    if env:
        return [u.strip() for u in env.split(",") if u.strip()]
    return DEFAULT_RSS_URLS


def _parse_feed(url: str) -> list[dict[str, Any]]:
    """1つのRSS URLを取得・正規化。失敗時は空リスト。"""
    res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    res.raise_for_status()
    feed = feedparser.parse(res.content)

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in feed.entries:
        text = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not text or not link:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "text": text,
                "author": (entry.get("author") or "").strip() or None,
                "link": link,
                "source": "X",
                "published": feed_published_iso(entry),
            }
        )
    return items


def fetch_x() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for url in _rss_urls():
        try:
            items = _parse_feed(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] X feed failed ({url}): {exc}")
            continue
        if items:
            print(f"[ok] X feed: {len(items)} 件取得 ({url})")
            break

    if not items:
        # 全候補が失敗/空。例外を投げて main 側で前回値を温存させる。
        raise RuntimeError("X投稿をどのRSSからも取得できませんでした")

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return {
        "updated_at": now_iso(),
        "items": items[:MAX_ITEMS],
    }
