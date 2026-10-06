#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 fund-pool.js 拆分为 base + detail 两个文件，减少首屏加载体积。
- base: 首页列表/筛选/排序需要的字段（含 industryConfig 用于 AI 主题过滤）。
- detail: 详情页按需取的重仓股、估值、风险因子，以 fundCode 为 key。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "fund-pool.js"
BASE_OUT = ROOT / "fund-pool-base.js"
DETAIL_OUT = ROOT / "fund-pool-detail.js"

BASE_FIELDS = {
    "fundCode", "fundName", "fundFullName", "fundTypeTag",
    "riskLevelNum", "riskLevel", "fundScale", "managementFee", "purchaseFee",
    "reportDate", "matchTags", "performance", "industryConfig",
    "topIndustryCode", "topHoldingStock"
}
DETAIL_FIELDS = {"valuation", "riskFactors", "topHoldings"}


def main():
    text = SRC.read_text(encoding="utf-8")
    m = re.search(r"window\.FUND_POOL\s*=\s*(\[.*?\]);\s*$", text, re.DOTALL)
    if not m:
        raise RuntimeError("无法解析 fund-pool.js 中的 FUND_POOL 数组")
    funds = json.loads(m.group(1))

    base_list = []
    detail_map = {}
    for f in funds:
        base = {k: v for k, v in f.items() if k in BASE_FIELDS}
        detail = {k: v for k, v in f.items() if k in DETAIL_FIELDS}
        base_list.append(base)
        detail_map[f["fundCode"]] = detail

    BASE_OUT.write_text(
        "// 由 split_fund_pool.py 生成 — 首页基础字段\n"
        "// 全局变量 window.FUND_POOL_BASE，供 index.html 首页筛选/列表/排序使用\n"
        "window.FUND_POOL_BASE = " + json.dumps(base_list, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8"
    )
    DETAIL_OUT.write_text(
        "// 由 split_fund_pool.py 生成 — 详情页按需字段\n"
        "// 全局变量 window.FUND_POOL_DETAIL，以 fundCode 为 key，进入基金详情时按需合并\n"
        "window.FUND_POOL_DETAIL = " + json.dumps(detail_map, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8"
    )

    print(f"源文件: {SRC} ({SRC.stat().st_size / 1024:.1f} KB)")
    print(f"base  : {BASE_OUT} ({BASE_OUT.stat().st_size / 1024:.1f} KB)")
    print(f"detail: {DETAIL_OUT} ({DETAIL_OUT.stat().st_size / 1024:.1f} KB)")
    print(f"基金数: {len(base_list)}")


if __name__ == "__main__":
    main()
