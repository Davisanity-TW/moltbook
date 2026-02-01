# AGENTS.md — moltbook

This repo builds **Moltbook Digests**: 從 Moltbook 精選文章，輸出繁體中文摘要 +「可複製給 molt 的任務」，並用 VitePress 上站。

## 目標（What this repo is for）
- 定期（或手動）抓候選文章 → 精選 8–12 篇 → 產出 digest markdown → commit/push → GitHub Pages 自動更新。
- 產物設計重點：
  - 每篇有清楚連結
  - 摘要為繁中、可讀、可執行
  - 每篇附一段可直接丟給 molt 的任務 code block（含該篇 Moltbook 連結）

## 重要路徑（Key paths）
- `reports/YYYYMM/MM-DD.md`：每日 digest 產出（**以 Asia/Taipei 日期**命名）
- `bin/moltbook_fetch_candidates.py`：抓候選並輸出 `/tmp/moltbook_candidates.json`
- `bin/moltbook_digest_zh.py`：digest 產製主程式（繁中）
- `docs/`：VitePress 站點
  - `docs/.vitepress/config.mts`：側邊欄會掃 `docs/reports/<YYYYMM>/*.md`
  - `docs/reports/**`：網站呈現的報告（通常對應 `reports/**` 同步/引用的內容；若有同步腳本請以腳本為主）
- `README.md`：簡介

## 常用命令（Commands）
```bash
cd /home/ubuntu/clawd/moltbook

# 本機開發
npm run docs

# 建置
npm run build

# 1) 更新 repo
GIT_ASKPASS=/home/ubuntu/clawd/bin/git_askpass_moltbook.sh GIT_TERMINAL_PROMPT=0 git pull --rebase

# 2) 抓候選
python3 bin/moltbook_fetch_candidates.py
# 產出：/tmp/moltbook_candidates.json

# 3) 產出 digest（若你是用腳本產製）
python3 bin/moltbook_digest_zh.py

# 4) commit/push（產物在 reports/）
git add reports
git commit -m "Moltbook digest YYYY-MM-DD HH:MM"
GIT_ASKPASS=/home/ubuntu/clawd/bin/git_askpass_moltbook.sh GIT_TERMINAL_PROMPT=0 git push
```

## 產出規範（Output conventions）
- 時區：所有日期/時間一律以 **Asia/Taipei**。
- 每篇文章必須使用固定模板（縮排要一致）：
  - `- 文章標題`
  - `  - 連結：<moltbook post url>`
  - `  - 外部連結：<url>`（若有）
  - `  - 中文摘要：`（繁中，6–10 點，用 1. 2. 3. 編號）
  - `  - 可複製給 molt 的任務：`（每篇各自一段 code block，**code block 內必須包含該篇 Moltbook 連結**）
- 精選數量：通常 8–12 篇（依候選品質調整）。

## 禁止事項（Do not）
- 不要輸出/公開：submolt id、post_id、API key、claim url、cookie、或任何 secrets。
- 不要在任務 code block 外放「全域 prompt」或重複的系統指令（每篇任務必須針對該篇）。
- 不要把 `/tmp/moltbook_candidates.json` 直接 commit 進 repo。

## 失敗/異常處理（When things go wrong）
- git push 失敗：先 `git pull --rebase` 再重試。
- 抓候選失敗：檢查 Moltbook API 狀態與本機網路；避免重試造成大量請求。
- 若內容可能涉及隱私/安全：寧可跳過該篇，不要硬摘要。
