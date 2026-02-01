#!/usr/bin/env python3
"""Fetch Moltbook candidates (hot 200 + new 400) and output JSON.

Writes /tmp/moltbook_candidates.json by default.
Reads API key from /home/ubuntu/clawd/secrets/moltbook.json.

This script only fetches and scores; translation/summarization is done by the caller (agent).
"""

from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
import urllib.request

API_BASE = "https://www.moltbook.com/api/v1"
CREDS_PATH = Path("/home/ubuntu/clawd/secrets/moltbook.json")
OUT_PATH = Path("/tmp/moltbook_candidates.json")

# Expanded keyword weights (zh/en)
KEYWORDS = {
    # clawdbot/moltbot
    "clawdbot": 10, "moltbot": 10, "openclaw": 8, "clawd": 6,
    "agent": 4, "agents": 4, "ai agent": 5, "automation": 4, "workflow": 4,
    "tool": 3, "tools": 3, "tool calling": 4, "mcp": 4, "webhook": 3,
    "cron": 3, "scheduler": 2, "github": 2, "actions": 2,
    "自動化": 5, "工作流": 5, "排程": 4, "腳本": 3, "工具": 3, "智能體": 4,

    # AI
    "llm": 3, "rag": 3, "embedding": 2, "inference": 3, "gpu": 3, "cuda": 2,
    "nvidia": 2, "openai": 2, "prompt": 2,
    "提示詞": 3, "向量": 2, "推理": 2,

    # k8s
    "kubernetes": 6, "k8s": 6, "helm": 3, "cni": 3, "cilium": 3, "calico": 3,
    "ingress": 2, "service mesh": 2, "istio": 2, "etcd": 3, "operator": 3,
    "容器": 3, "叢集": 3, "集群": 3,

    # storage
    "storage": 5, "minio": 7, "s3": 3, "erasure": 3, "healing": 3,
    "ceph": 4, "longhorn": 3, "zfs": 3, "nfs": 2, "nvme": 3, "raid": 2,
    "儲存": 5, "存儲": 5, "物件儲存": 4, "磁碟": 3,

    # markets
    "markets": 4, "finance": 4, "macro": 3, "earnings": 3, "fed": 3,
    "vix": 4, "volatility": 3, "gold": 3, "silver": 3, "bitcoin": 3, "btc": 3,
    "財經": 5, "市場": 5, "美股": 3, "通膨": 2, "降息": 2, "黃金": 3, "白銀": 3, "比特幣": 3,
}


def http_json(url: str, api_key: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "molt/digest-fetch",
        },
        method="GET",
    )
    # Moltbook API can be slow at times; use a longer timeout + light retry.
    last_err = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise last_err


def fetch_posts(api_key: str, sort: str, want: int):
    posts = []
    offset = 0
    while len(posts) < want:
        limit = min(50, want - len(posts))
        url = f"{API_BASE}/posts?sort={sort}&limit={limit}&offset={offset}"
        j = http_json(url, api_key)
        batch = j.get("posts") or []
        posts.extend(batch)
        if not j.get("has_more"):
            break
        nxt = j.get("next_offset")
        if nxt is None or nxt == offset:
            break
        offset = int(nxt)
    return posts


def score_post(p: dict) -> int:
    text = " ".join([
        str(p.get("title") or ""),
        str(p.get("content") or ""),
        str(p.get("url") or ""),
        str((p.get("submolt") or {}).get("name") or ""),
    ]).lower()
    s = 0
    for k, w in KEYWORDS.items():
        if k in text:
            s += w
    if p.get("url"):
        s += 1
    return s


def main():
    api_key = json.loads(CREDS_PATH.read_text(encoding="utf-8"))["api_key"]
    hot = fetch_posts(api_key, "hot", 200)
    new = fetch_posts(api_key, "new", 400)

    merged = {}
    for p in hot + new:
        pid = p.get("id")
        if not pid:
            continue
        merged[pid] = p

    scored = []
    for pid, p in merged.items():
        scored.append((score_post(p), p))
    scored.sort(key=lambda x: (x[0], x[1].get("created_at") or ""), reverse=True)

    # keep top candidates + a few low-score newest for discovery
    top = [p for s, p in scored if s > 0][:30]
    if not top:
        top = [p for _, p in scored[:10]]

    out = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "counts": {"hot": len(hot), "new": len(new), "unique": len(merged), "selected": len(top)},
        "posts": top,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT_PATH))


if __name__ == "__main__":
    main()
