"""X(Twitter) の NVIDIA 関連投稿取得。

公式 X API は有料のため、Twitter→RSS 変換サービス（Nitter 等）の無料RSSを経由する。

【方式】$NVDA の *キーワード検索* RSS は、公開インスタンスでは認証が必要になり
軒並み停止している（検索は空/403を返す）。一方で *ユーザータイムライン* の RSS
（例: https://nitter.net/NVIDIAAI/rss）は現在も取得できる。そこで2種類のアカウントの
タイムラインを集約する:
  - 公式系（NVIDIA本体）… 全投稿をそのまま採用。
  - 第三者系（金融/アナリスト/半導体系）… NVIDIA関連キーワードを含む投稿だけ採用。
    無料では真の「$NVDA検索」ができないため、著名アカウントのTLを関連フィルタで
    絞ることで "一般のNVIDIA関連の声" に近づける。
最後に重複除去して新しい順に並べる。

【上書き】環境変数で挙動を変更できる（本番はこれで安定運用する想定）:
  - `X_RSS_URLS`   … カンマ区切りのRSS URLを直接指定。指定時はこれだけを使う（最優先・無フィルタ）。
  - `X_NITTER_BASES` … カンマ区切りの Nitter ベースURL（例: https://nitter.net）。
  - `X_ACCOUNTS`   … 公式系（全件採用）アカウントの上書き（@なし。例: nvidia,NVIDIAAI）。
  - `X_THIRD_PARTY_ACCOUNTS` … 第三者系（関連フィルタ適用）アカウントの上書き。
"""
from __future__ import annotations

import os
import re
from typing import Any

import feedparser
import requests

from common import feed_published_iso, now_iso

# 公式系（NVIDIA本体）アカウント。投稿は全件そのまま採用する（@なし）。
DEFAULT_OFFICIAL_ACCOUNTS: list[str] = [
    "nvidia",
    "NVIDIAAI",
    "nvidianewsroom",
    "NVIDIAGeForce",
    "NVIDIAAIDev",
]

# 第三者系（金融/アナリスト/半導体系）アカウント。NVIDIA関連キーワードを含む
# 投稿のみ採用する（@なし）。無料では真の$NVDA検索ができないため、著名アカウントの
# タイムラインを関連フィルタで絞って "一般のNVIDIA関連の声" に近づける。
DEFAULT_THIRD_PARTY_ACCOUNTS: list[str] = [
    "dylan522p",       # SemiAnalysis（半導体）
    "IanCutress",      # TechTechPotato（半導体）
    "Beth_Kindig",     # I/O Fund（テック投資アナリスト）
    "DanielNewmanUV",  # Futurum（アナリスト）
    "firstadopter",    # テック/半導体ウォッチャー
    "StockMKTNewz",    # 市場ニュース
]

# 第三者系の投稿を NVIDIA 関連に絞るためのキーワード（大文字小文字無視）。
_RELEVANCE_RE = re.compile(
    r"nvidia|nvda|jensen|geforce|blackwell|\brtx\b|\bcuda\b|"
    r"\bh100\b|\bh200\b|\bb200\b|\bgb200\b|\bdgx\b|hopper gpu|rubin gpu",
    re.IGNORECASE,
)

# ユーザータイムラインRSSを提供する Nitter ベース。上から順に試し、
# 1件以上取れたベースを採用する。公開インスタンスは不安定なため、
# 本番は環境変数 X_NITTER_BASES / X_RSS_URLS での上書きを推奨。
DEFAULT_NITTER_BASES: list[str] = [
    "https://nitter.net",
]

MAX_ITEMS = 30
TIMEOUT = 12  # 秒
USER_AGENT = "Mozilla/5.0 (compatible; NVDA-Dashboard/1.0; +https://github.com/)"

_STATUS_RE = re.compile(r"^https?://[^/]+/([^/]+)/status/(\d+)")


def _env_list(name: str) -> list[str]:
    raw = os.environ.get(name, "").strip()
    return [v.strip() for v in raw.split(",") if v.strip()]


def _official_accounts() -> list[str]:
    return _env_list("X_ACCOUNTS") or DEFAULT_OFFICIAL_ACCOUNTS


def _third_party_accounts() -> list[str]:
    return _env_list("X_THIRD_PARTY_ACCOUNTS") or DEFAULT_THIRD_PARTY_ACCOUNTS


def _nitter_bases() -> list[str]:
    return _env_list("X_NITTER_BASES") or DEFAULT_NITTER_BASES


def _canonical_link(link: str) -> tuple[str, str | None, str | None]:
    """Nitter のリンクを x.com に正規化し、(url, handle, tweet_id) を返す。

    tweet_id が取れないもの（プロフィール等）は id=None。重複除去のキーに使う。
    """
    link = (link or "").strip()
    m = _STATUS_RE.match(link)
    if not m:
        return link, None, None
    handle, tweet_id = m.group(1), m.group(2)
    return f"https://x.com/{handle}/status/{tweet_id}", handle, tweet_id


def _parse_feed(url: str, fallback_handle: str | None = None) -> list[dict[str, Any]]:
    """1つのRSS URLを取得・正規化。失敗時は例外を送出。"""
    res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    res.raise_for_status()
    feed = feedparser.parse(res.content)

    items: list[dict[str, Any]] = []
    for entry in feed.entries:
        text = (entry.get("title") or "").strip()
        raw_link = (entry.get("link") or "").strip()
        if not text or not raw_link:
            continue
        link, handle, _ = _canonical_link(raw_link)
        author = handle or fallback_handle
        items.append(
            {
                "text": text,
                "author": f"@{author}" if author else None,
                "link": link,
                "source": "X",
                "published": feed_published_iso(entry),
            }
        )
    return items


def _fetch_accounts(
    base: str, accounts: list[str], *, relevance_filter: bool
) -> list[dict[str, Any]]:
    """1つのベースから複数アカウントを取得。relevance_filter=True なら関連投稿のみ。"""
    out: list[dict[str, Any]] = []
    for acct in accounts:
        url = f"{base}/{acct}/rss"
        try:
            items = _parse_feed(url, fallback_handle=acct)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] X timeline failed ({url}): {exc}")
            continue
        if relevance_filter:
            items = [it for it in items if _RELEVANCE_RE.search(it["text"])]
        out.extend(items)
    return out


def _collect_from_bases() -> list[dict[str, Any]]:
    """Nitter ベースを順に試し、最初に取得できたベースで公式+第三者を集約。"""
    official = _official_accounts()
    third_party = _third_party_accounts()
    for base in _nitter_bases():
        base = base.rstrip("/")
        collected = _fetch_accounts(base, official, relevance_filter=False)
        collected += _fetch_accounts(base, third_party, relevance_filter=True)
        if collected:
            print(
                f"[ok] X: {base} から {len(collected)} 件取得"
                f"（公式{len(official)} + 第三者{len(third_party)}アカウント）"
            )
            return collected
    return []


def _collect_from_urls(urls: list[str]) -> list[dict[str, Any]]:
    """X_RSS_URLS 直接指定時。取れたURLの結果を全て集約。"""
    collected: list[dict[str, Any]] = []
    for url in urls:
        try:
            collected.extend(_parse_feed(url))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] X feed failed ({url}): {exc}")
    if collected:
        print(f"[ok] X: 指定URLから {len(collected)} 件取得")
    return collected


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """tweet id（無ければ本文）で重複除去。"""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for it in items:
        _, _, tweet_id = _canonical_link(it["link"])
        key = tweet_id or it["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def fetch_x() -> dict[str, Any]:
    override = _env_list("X_RSS_URLS")
    items = _collect_from_urls(override) if override else _collect_from_bases()

    if not items:
        # 全候補が失敗/空。例外を投げて main 側で前回値を温存させる。
        raise RuntimeError("X投稿をどのRSSからも取得できませんでした")

    items = _dedupe(items)
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return {
        "updated_at": now_iso(),
        "items": items[:MAX_ITEMS],
    }
