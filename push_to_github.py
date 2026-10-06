#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推送到 GitHub 仓库（通过 REST API + keychain token）"""
import base64, json, urllib.request, os, sys

TOKEN = "REDACTED_REVOKED_TOKEN"
OWNER, REPO, BRANCH = "cyz87687", "ai-fund-selection-h5", "main"
BASE = "https://api.github.com/repos/%s/%s/contents" % (OWNER, REPO)
DIR = "/Users/yzreal/WorkBuddy/2026-09-22-09-21-20/交付物/ai-fund-selection-h5-fixed"

def api(method, url, payload):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github+json")
    data = json.dumps(payload).encode()
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print("  ✗ HTTP %s: %s" % (e.code, body[:200]))
        return None

def get_sha(path):
    url = BASE + "/" + path
    req = urllib.request.Request(url)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("sha")
    except Exception:
        return None

def push(path, message, update=True):
    local = os.path.join(DIR, path)
    if not os.path.exists(local):
        print("  ✗ 本地文件不存在:", path); return
    with open(local, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    sha = get_sha(path) if update else None
    payload = {"message": message, "content": b64, "branch": BRANCH}
    if sha: payload["sha"] = sha
    print("推送 %s (%d KB%s)..." % (path, os.path.getsize(local)//1024, " [更新]" if sha else " [新增]"))
    r = api("PUT", BASE + "/" + path, payload)
    if r:
        print("  ✓ commit:", r.get("commit", {}).get("sha", "")[:10])
    else:
        print("  ✗ 失败:", path)

push("index.html", "feat: 接入真实投研基金数据池(9988只)+deepseek-v4-flash+修复CORS/行业筛选/合规过滤", True)
push("fund-pool.js", "feat: 新增真实基金数据池(9988只, 基于研究所投研数据重构)", False)
push("ark-key-encode.js", "feat: 新增方舟API Key编码校验工具", False)
push("build_fund_pool.py", "feat: 新增基金池构建脚本(数据源→fund-pool.js)", False)
push("README.md", "docs: 更新README说明修复内容与部署方式", True)
print("\n全部推送完成")
