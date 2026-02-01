#!/usr/bin/env python3
"""Moltbook digest (zh-Hant) for David.

- Fetches latest Moltbook posts (global new) and selects items by keyword scoring.
- Writes to /home/ubuntu/clawd/moltbook/reports/YYYY-MM-DD.md
- Appends blocks so later runs appear lower.

Note: This does NOT require external translation APIs. We do lightweight "translation" by:
- If content already contains CJK → keep as-is.
- Else: produce a short zh-Hant summary line (heuristic, not perfect).

If you want high-quality translation, we can upgrade to an LLM-based summarizer step.
"""

from __future__ import annotations

import json
import re
import datetime as dt
from pathlib import Path
import urllib.request

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

API_BASE = "https://www.moltbook.com/api/v1"
CREDS_PATH = Path("/home/ubuntu/clawd/secrets/moltbook.json")
STATE_PATH = Path("/home/ubuntu/clawd/memory/moltbook-digest-state.json")

# Emphasize: clawdbot/moltbot usage ideas + David's interests
KEYWORDS = {
    # clawdbot / agents
    "clawdbot": 8,
    "moltbot": 8,
    "agent": 3,
    "tool": 2,
    "mcp": 2,
    "workflow": 2,

    # infra/storage/k8s
    "minio": 6,
    "s3": 2,
    "erasure": 3,
    "healing": 3,
    "kubernetes": 5,
    "k8s": 5,
    "cni": 2,
    "etcd": 2,
    "storage": 4,
    "nvme": 2,

    # markets/finance
    "vix": 3,
    "macro": 2,
    "nasdaq": 2,
    "sp500": 2,
    "s&p": 2,
    "gold": 2,
    "silver": 2,
    "bitcoin": 2,
    "btc": 2,
    "earnings": 2,
}


def tz_now():
    if ZoneInfo is None:
        return dt.datetime.now()
    return dt.datetime.now(tz=ZoneInfo("Asia/Taipei"))


def http_json(url: str, api_key: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "molt/digest",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state():
    if not STATE_PATH.exists():
        return {"seen_ids": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"seen_ids": []}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_cjk(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


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


def zh_hint(title: str, content: str) -> str:
    """Heuristic zh-Hant hint for English posts."""
    t = (title or "").strip()
    c = re.sub(r"\s+", " ", (content or "").strip())
    c = c[:200]
    # Very lightweight: just label + keep key nouns.
    return f"中文提示：此貼文可能在討論「{t}」；重點片段：{c}"


def render_entry(p: dict, score: int) -> str:
    title = (p.get("title") or "(no title)").strip()
    content = (p.get("content") or "").strip()
    url = p.get("url")
    sub = (p.get("submolt") or {}).get("name")
    pid = p.get("id")
    created = p.get("created_at")

    lines = []
    lines.append(f"- **{title}**")
    lines.append(f"  - submolt: `{sub}` | score: `{score}` | created: `{created}`")
    if pid:
        lines.append(f"  - post_id: `{pid}`")
    if url:
        lines.append(f"  - link: {url}")
    if content:
        snippet = re.sub(r"\s+", " ", content)
        if len(snippet) > 260:
            snippet = snippet[:260] + "…"
        lines.append(f"  - snippet: {snippet}")
        if not has_cjk(content):
            lines.append(f"  - {zh_hint(title, content)}")
    return "\n".join(lines)


def main():
    creds = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
    api_key = creds["api_key"]

    now = tz_now()
    day = now.date().isoformat()
    hhmm = now.strftime("%H:%M")

    j = http_json(f"{API_BASE}/posts?sort=new&limit=25", api_key)
    posts = j.get("posts") or []

    state = load_state()
    seen = set(state.get("seen_ids") or [])

    scored = []
    for p in posts:
        pid = p.get("id")
        if pid and pid in seen:
            continue
        s = score_post(p)
        scored.append((s, p))

    scored.sort(key=lambda x: (x[0], x[1].get("created_at") or ""), reverse=True)
    top = [p for s, p in scored if s > 0][:10]

    out_dir = Path("/home/ubuntu/clawd/moltbook/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{day}.md"

    if not out_file.exists():
        out_file.write_text(f"# Moltbook 精選點子（{day}）\n\n" 
                            f"偏好：moltbot/clawdbot、財經/市場、AI 應用、K8s、Storage。\n\n",
                            encoding="utf-8")

    block = []
    block.append(f"## {day} {hhmm} (Asia/Taipei)\n")
    block.append("本輪我覺得你可能有興趣的貼文：")

    if not top:
        block.append("- （本輪沒有找到明顯相關的貼文；可能需要擴大關鍵字或改抓特定 submolt。）")
    else:
        for p in top:
            block.append(render_entry(p, score_post(p)))

    block.append("")
    out_file.write_text(out_file.read_text(encoding="utf-8") + "\n" + "\n".join(block), encoding="utf-8")

    for p in posts:
        pid = p.get("id")
        if pid:
            seen.add(pid)
    state["seen_ids"] = list(seen)[-800:]
    save_state(state)

    print(str(out_file))


if __name__ == "__main__":
    main()
