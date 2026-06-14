"""ニュース取得: 複数の無料RSSを集約して正規化。"""
from __future__ import annotations

from typing import Any

import feedparser

from common import feed_published_iso, now_iso

# (表示名, RSS URL)
FEEDS: list[tuple[str, str]] = [
    ("Google News", "https://news.google.com/rss/search?q=NVIDIA+OR+NVDA+stock&hl=en-US&gl=US&ceid=US:en"),
    ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US"),
    ("NVIDIA Newsroom", "https://nvidianews.nvidia.com/rss"),
]

MAX_ITEMS = 30


def fetch_news() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] feed {source} failed: {exc}")
            continue
        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "published": feed_published_iso(entry),
                }
            )

    # 公開日時の降順（None は末尾）
    items.sort(key=lambda x: x["published"] or "", reverse=True)

    return {
        "updated_at": now_iso(),
        "items": items[:MAX_ITEMS],
    }
