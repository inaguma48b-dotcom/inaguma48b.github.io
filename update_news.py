#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_news.py — AIニュースのRSSを取得して news.json を生成する
標準ライブラリのみ使用（依存なし）。GitHub Actionsで週1回実行する想定。
"""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# 取得するRSSフィード（好みに応じて追加・削除OK）
FEEDS = [
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"),
    ("Publickey",   "https://www.publickey1.jp/atom.xml"),
    ("Google News", "https://news.google.com/rss/search?q=%E7%94%9F%E6%88%90AI&hl=ja&gl=JP&ceid=JP:ja"),
]

MAX_PER_FEED = 3   # 各フィードから最大何件取るか
MAX_TOTAL = 8      # 合計の最大件数
TIMEOUT = 20

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-updater)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return res.read()


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(source: str, data: bytes):
    """RSS 2.0 / Atom 両対応の簡易パーサ"""
    items = []
    root = ET.fromstring(data)

    # RSS 2.0
    for item in root.iter("item"):
        title = clean(item.findtext("title", ""))
        link = (item.findtext("link") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "source": source})

    # Atom
    if not items:
        for entry in root.iter(f"{ATOM_NS}entry"):
            title = clean(entry.findtext(f"{ATOM_NS}title", ""))
            link = ""
            for l in entry.findall(f"{ATOM_NS}link"):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href", "")
                    break
            if title and link:
                items.append({"title": title, "link": link, "source": source})

    return items[:MAX_PER_FEED]


def main():
    all_items = []
    for source, url in FEEDS:
        try:
            all_items.extend(parse_feed(source, fetch(url)))
            print(f"[OK] {source}")
        except Exception as e:
            print(f"[NG] {source}: {e}")  # 1フィード失敗しても続行

    # タイトル重複を除去
    seen, items = set(), []
    for it in all_items:
        key = it["title"]
        if key not in seen:
            seen.add(key)
            items.append(it)

    jst = timezone(timedelta(hours=9))
    out = {
        "updated": datetime.now(jst).strftime("%Y-%m-%d"),
        "items": items[:MAX_TOTAL],
    }
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"news.json を更新しました（{len(out['items'])}件）")


if __name__ == "__main__":
    main()
