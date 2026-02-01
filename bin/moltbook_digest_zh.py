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
    # --- core interest: clawdbot / moltbots / agent tooling ---
    "clawdbot": 10,
    "moltbot": 10,
    "openclaw": 8,
    "clawd": 6,
    "agent": 4,
    "agents": 4,
    "ai agent": 5,
    "autonomous": 2,
    "automation": 4,
    "workflow": 4,
    "pipeline": 3,
    "orchestration": 3,
    "tool": 3,
    "tools": 3,
    "tool calling": 4,
    "mcp": 4,
    "webhook": 3,
    "cron": 3,
    "scheduler": 2,
    "github": 2,
    "actions": 2,
    "telegram": 2,
    "signal": 2,
    "slack": 2,

    # 中文關鍵字（moltbot/clawdbot 應用）
    "自動化": 5,
    "工作流": 5,
    "排程": 4,
    "腳本": 3,
    "工具": 3,
    "代理": 3,
    "智能體": 4,
    "機器人": 3,
    "通知": 2,

    # --- AI applications ---
    "llm": 3,
    "rag": 3,
    "embedding": 2,
    "inference": 3,
    "gpu": 3,
    "cuda": 2,
    "nvidia": 2,
    "openai": 2,
    "prompt": 2,
    "eval": 2,
    "agents sdk": 2,

    # 中文（AI 應用）
    "ai": 2,
    "應用": 2,
    "提示詞": 3,
    "向量": 2,
    "推理": 2,
    "模型": 2,

    # --- Kubernetes / cloud native ---
    "kubernetes": 6,
    "k8s": 6,
    "helm": 3,
    "cni": 3,
    "cilium": 3,
    "calico": 3,
    "ingress": 2,
    "service mesh": 2,
    "istio": 2,
    "etcd": 3,
    "kubelet": 2,
    "pod": 2,
    "node": 2,
    "operator": 3,

    # 中文（K8s）
    "容器": 3,
    "集群": 3,
    "叢集": 3,
    "網路": 2,
    "網路插件": 2,

    # --- Storage / infra ---
    "storage": 5,
    "s3": 3,
    "minio": 7,
    "erasure": 3,
    "healing": 3,
    "ceph": 4,
    "rook": 2,
    "longhorn": 3,
    "zfs": 3,
    "nfs": 2,
    "iscsi": 2,
    "nvme": 3,
    "nvmeof": 2,
    "lvm": 2,
    "raid": 2,
    "latency": 2,
    "throughput": 2,
    "observability": 2,
    "prometheus": 2,
    "grafana": 2,
    "loki": 2,

    # 中文（Storage）
    "儲存": 5,
    "存儲": 5,
    "物件儲存": 4,
    "檔案系統": 3,
    "磁碟": 3,
    "硬碟": 2,
    "延遲": 2,
    "吞吐": 2,

    # --- Markets / finance ---
    "markets": 4,
    "market": 3,
    "finance": 4,
    "macro": 3,
    "earnings": 3,
    "guidance": 2,
    "cpi": 2,
    "pce": 2,
    "fed": 3,
    "rate": 2,
    "cut": 1,
    "yield": 2,
    "treasury": 2,
    "bond": 2,
    "dxy": 2,
    "usd": 1,
    "vix": 4,
    "volatility": 3,
    "options": 2,
    "gold": 3,
    "xau": 2,
    "silver": 3,
    "xag": 2,
    "bitcoin": 3,
    "btc": 3,
    "crypto": 2,
    "etf": 2,

    # 中文（財經/市場）
    "財經": 5,
    "市場": 5,
    "美股": 3,
    "台股": 2,
    "匯率": 2,
    "美元": 2,
    "殖利率": 2,
    "通膨": 2,
    "降息": 2,
    "恐慌": 2,
    "黃金": 3,
    "白銀": 3,
    "比特幣": 3,
    "加密": 2,
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


def fetch_posts(api_key: str, sort: str, want: int) -> list[dict]:
    """Fetch posts with pagination using next_offset."""
    posts: list[dict] = []
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




def idea_bullets(text: str):
    """Return 3 actionable idea bullets in zh-Hant based on keywords."""
    t = (text or '').lower()
    ideas = []

    def add(*xs):
        for x in xs:
            if x not in ideas:
                ideas.append(x)

    # clawdbot/moltbot
    if 'clawdbot' in t or 'moltbot' in t or 'agent' in t:
        add(
            "把這個做成一個 cron/heartbeat：定期抓資料 → 產生摘要 → 推到 git（像你現在的 moltbook digest）。",
            "把流程拆成兩段：① 產生快取（cache）② 準點發送/寫入 git，避免延遲或 API 抖動影響準時性。",
            "把輸出改成『可機器解析』格式（JSON/固定段落），方便後續自動彙整、查詢與回填。"
        )

    # k8s/storage
    if 'kubernetes' in t or 'k8s' in t or 'cni' in t or 'etcd' in t:
        add(
            "建立『每日 K8s 健康巡檢』：節點資源/Pod 重啟/事件 top N → 產出清單與建議動作。",
            "針對 CNI/網路：加一個『最近 24h 網路錯誤關鍵字』彙整（conntrack/MTU/timeout）並附定位指令。",
            "把 troubleshooting SOP（像你 MinIO 的）寫成 wiki 頁＋每天增量補齊（commit 當作學習日誌）。"
        )
    if 'minio' in t or 's3' in t or 'erasure' in t or 'healing' in t:
        add(
            "把 log 關鍵字（例如 canceling remote connection）→ source trace → SOP 變成固定模板，遇到新錯就自動生成一頁。",
            "用 `mc admin heal --json` 落盤成 jsonl，定期把 Items[] 轉成『今日 heal 清單/失敗清單』並推 git。",
            "針對特定 bucket/prefix 建立『一鍵 heal 指令＋結果解析』腳本，縮小範圍避免掃全站。"
        )

    # markets/finance
    if any(k in t for k in ['vix','sp500','s&p','nasdaq','earnings','macro','gold','silver','bitcoin','btc']):
        add(
            "把 VIX/金銀/BTC 做成固定『風險儀表板』段落（數值 + 變化 + 3 行解讀 + 事件連結），每天自動寫入週報。",
            "把重大事件（財報/Fed/地緣）做成『事件→資產反應』對照表，累積成自己的交易/研究筆記庫。",
            "把 watchlist 的資料抓取與格式化獨立成工具，報告只做『解讀』，降低格式維護成本。"
        )

    # fallback
    if not ideas:
        ideas = [
            "把這篇貼文的想法收斂成『一個可重複的自動化流程』，先做 MVP（每天一次即可）。",
            "把輸出固定成 Markdown 模板（標題/重點/下一步），之後才能穩定累積成可搜尋的知識庫。",
            "遇到不確定的地方先加 TODO + 可執行的驗證指令，讓後續能快速補完。"
        ]

    return ideas[:3]


def render_entry(p: dict, score: int) -> str:
    title = (p.get("title") or "(no title)").strip()
    content = (p.get("content") or "").strip()
    ext_url = p.get("url")
    pid = p.get("id")

    # Moltbook post permalink (best-effort)
    post_url = f"https://www.moltbook.com/post/{pid}" if pid else "(no id)"

    snippet = re.sub(r"\s+", " ", content).strip()
    if len(snippet) > 260:
        snippet = snippet[:260] + "…"

    # Chinese summary (lightweight)
    if has_cjk(content):
        zh_summary = snippet
    else:
        zh_summary = f"主題：{title}。重點（原文摘錄）：{snippet}"

    lines = []
    lines.append(f"- **{title}**")
    lines.append(f"  - 連結：{post_url}")
    if ext_url:
        lines.append(f"  - 外部連結：{ext_url}")
    lines.append(f"  - 中文摘要：{zh_summary}")

    fulltext = f"{title} {content} {ext_url or ''}".lower()
    ideas = idea_bullets(fulltext)
    lines.append("  - 可直接用的 idea（Clawdbot / 工作流）：")
    for i, idea in enumerate(ideas, 1):
        lines.append(f"    {i}. {idea}")

    lines.append("  - 可複製給 molt 的任務（直接貼這段我就會做）：")
    lines.append("    ```")
    lines.append("    請閱讀下面這篇 Moltbook 貼文，並用繁體中文輸出：")
    lines.append("    1) 5–8 點中文重點摘要（偏研究/可執行）")
    lines.append("    2) 3 個可以落地到我現有 Clawdbot 的自動化/工作流 idea（最好能接 cron + git）")
    lines.append("    3) 若要實作其中 1 個 idea：給我具體步驟/檔案/cron 設定草案")
    lines.append(f"\n    Moltbook 連結：{post_url}")
    if ext_url:
        lines.append(f"    外部連結：{ext_url}")
    lines.append("    ```")

    return "\n".join(lines)


def main():
    creds = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
    api_key = creds["api_key"]

    now = tz_now()
    day = now.date().isoformat()
    hhmm = now.strftime("%H:%M")

    # Fetch 100 hot + 150 new (global)
    hot_posts = fetch_posts(api_key, sort="hot", want=200)
    new_posts = fetch_posts(api_key, sort="new", want=400)
    posts = hot_posts + new_posts
    # Note: do NOT skip previously-seen posts here.
    # We want discovery even if a post stays hot for a while.
    state = load_state()
    scored = []
    for p in posts:
        s = score_post(p)
        scored.append((s, p))

    scored.sort(key=lambda x: (x[0], x[1].get("created_at") or ""), reverse=True)
    top = [p for s, p in scored if s > 0][:10]
    if not top:
        # fallback: pick latest posts even if low score (discovery mode)
        top = [p for _, p in scored[:6]]

    ym = now.strftime("%Y%m")
    out_dir = Path("/home/ubuntu/clawd/moltbook/reports") / ym
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{now.strftime("%m-%d")}.md"

    if not out_file.exists():
        out_file.write_text(f"# Moltbook 精選點子（{day}）\n\n" 
                            f"偏好：moltbot/clawdbot、財經/市場、AI 應用、K8s、Storage。\n\n",
                            encoding="utf-8")

    block = []
    block.append(f"## {day} {hhmm} (Asia/Taipei)\n")
    block.append("本輪精選（來源：熱門前100 + 最新150；已篩選/摘要/給可落地點子）：")

    if not top:
        block.append("- （本輪沒有找到明顯相關的貼文；可能需要擴大關鍵字或改抓特定 submolt。）")
    else:
        for p in top:
            block.append(render_entry(p, score_post(p)))

    block.append("")
    out_file.write_text(out_file.read_text(encoding="utf-8") + "\n" + "\n".join(block), encoding="utf-8")
    # Persist minimal state (timestamp)
    state['last_run_at'] = now.isoformat()
    save_state(state)

    print(str(out_file))


if __name__ == "__main__":
    main()
