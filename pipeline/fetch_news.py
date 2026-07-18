"""ニュース取得: 複数の無料RSS（英語＋日本語）を集約して正規化。"""
from __future__ import annotations

import urllib.parse
from typing import Any

import feedparser

from common import feed_published_iso, now_iso


def _google_news_url(query: str, hl: str, gl: str, ceid_lang: str) -> str:
    """Google News 検索RSSのURLを組み立てる（クエリはUTF-8をパーセントエンコード）。"""
    q = urllib.parse.quote(query)
    return (
        f"https://news.google.com/rss/search?q={q}"
        f"&hl={hl}&gl={gl}&ceid={gl}:{ceid_lang}"
    )


# (表示名, RSS URL)。英語ソースに加え、日本語（日本版Google News）も集約する。
FEEDS: list[tuple[str, str]] = [
    ("Google News", _google_news_url("NVIDIA OR NVDA stock", "en-US", "US", "en")),
    ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US"),
    ("NVIDIA Newsroom", "https://nvidianews.nvidia.com/rss"),
    # 日本語ソース（エヌビディア関連の日本語記事：ロイター/Bloomberg日本版/日経 等が拾える）
    ("Googleニュース", _google_news_url("エヌビディア OR NVIDIA 株", "ja", "JP", "ja")),
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
