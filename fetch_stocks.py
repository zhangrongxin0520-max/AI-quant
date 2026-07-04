#!/usr/bin/env python3
"""
fetch_stocks.py — 通用股票数据获取脚本
========================================
基于 stock_data_spec.yaml 规范文件，批量获取多只股票的多维度数据。

两种运行模式：
  1. MCP 模式（推荐）: 在 WorkBuddy 中由 AI Agent 调用 Tushare MCP 工具
  2. HTTP API 模式: 直接调用 Tushare HTTP API（需配置 TOKEN）

用法：
  python fetch_stocks.py                       # 按 spec 默认配置取数
  python fetch_stocks.py --stock smic          # 只取单只股票
  python fetch_stocks.py --dim daily_price     # 只取单个维度
  python fetch_stocks.py --time-range all      # 使用全历史时间范围
  python fetch_stocks.py --mode dry-run         # 预览而不实际取数
  python fetch_stocks.py --mode http            # 使用 HTTP API 模式

数据源优先级: Tushare MCP > Tushare HTTP API

输出目录结构（由 spec 定义）:
  data/
  ├── stock_info.csv
  ├── daily/        → {stock_id}_daily.csv
  ├── daily_basic/  → {stock_id}_daily_basic.csv
  ├── financial/    → {stock_id}_financial.csv
  ├── money_flow/   → {stock_id}_money_flow.csv
  ├── technical/    → {stock_id}_technical.csv
  └── adj_factor/   → {stock_id}_adj_factor.csv
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 尝试加载 YAML（需要 PyYAML），否则回退到 JSON 解析
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
    print("[WARN] PyYAML 未安装，将使用内置 JSON 解析 spec")
    print("       安装: pip install pyyaml")


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("TUSHARE_TOKEN", "")
API_URL = "https://api.tushare.pro"

# Tushare API 限速：每分钟最多 200 次
RATE_LIMIT_INTERVAL = 0.35  # 秒

PROJECT_ROOT = Path(__file__).resolve().parent
SPEC_FILE = PROJECT_ROOT / "stock_data_spec.yaml"


# ============================================================================
# Spec 解析
# ============================================================================
def load_spec(path: Path) -> dict:
    """加载 spec 文件，支持 YAML 和 JSON"""
    if _HAS_YAML:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        # 简易 JSON 回退：先尝试读为 JSON，失败则提示安装 PyYAML
        with open(path, encoding="utf-8") as f:
            content = f.read()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print("错误: spec 文件不是有效的 JSON，请安装 PyYAML: pip install pyyaml")
            sys.exit(1)


# ============================================================================
# Tushare HTTP API 调用
# ============================================================================
def call_tushare_http(api_name: str, params: dict, fields: list[str] | None = None) -> dict:
    """通过 HTTP API 调用 Tushare 接口"""
    payload: dict[str, Any] = {
        "api_name": api_name,
        "token": TOKEN,
        "params": params,
    }
    if fields:
        payload["fields"] = ",".join(fields)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read().decode("utf-8"))


# ============================================================================
# MCP 工具调用参考（在 WorkBuddy 环境中由 AI Agent 执行）
# ============================================================================
def generate_mcp_call(stock: dict, dimension: dict, time_range: dict) -> dict:
    """
    生成单次 MCP 工具调用的参数。
    
    对应关系：
      stk_factor    → mcp__tushareMcp__stk_factor    (日线含复权, daily_price + technical 共用)
      daily_basic   → mcp__tushareMcp__daily_basic
      financial     → mcp__tushareMcp__fina_indicator
      money_flow    → mcp__tushareMcp__moneyflow
      adj_factor    → mcp__tushareMcp__adj_factor
      stock_basic   → mcp__tushareMcp__stock_basic
    """
    api_name = dimension["api"]
    mcp_tool = f"mcp__tushareMcp__{api_name}"

    # 提取字段名列表
    field_names = [f["name"] for f in dimension.get("fields", [])]

    # 构建参数
    params: dict[str, Any] = {
        "ts_code": stock["ts_code"],
    }

    if api_name in ("stk_factor", "daily_basic", "adj_factor", "moneyflow"):
        params["start_date"] = time_range["start"]
        params["end_date"] = time_range["end"]

    if api_name == "fina_indicator":
        params["start_date"] = time_range["start"]
        params["end_date"] = time_range["end"]

    if field_names:
        params["fields"] = field_names

    output_dir = PROJECT_ROOT / dimension["output"]["dir"]
    output_file = output_dir / dimension["output"]["naming"].format(stock_id=stock["id"])

    return {
        "mcp_tool": mcp_tool,
        "params": params,
        "output_file": str(output_file),
        "stock": stock["name"],
        "dimension": dimension["name"],
    }


# ============================================================================
# 数据保存
# ============================================================================
def save_to_csv(records: list[dict], field_names: list[str], output_path: Path, encoding: str = "utf-8-sig"):
    """保存记录为 CSV 文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(records)
    print(f"  ✓ 已保存: {output_path} ({len(records)} 条)")


# ============================================================================
# 数据校验
# ============================================================================
def validate_daily_data(records: list[dict], stock_name: str) -> list[str]:
    """校验日线行情数据"""
    warnings: list[str] = []
    for i, r in enumerate(records):
        try:
            o, h, l, c = float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])
            vol, amount = float(r.get("vol", 0)), float(r.get("amount", 0))
        except (KeyError, ValueError):
            warnings.append(f"  [WARN] 第{i+1}行数据类型错误")
            continue

        if h < l:
            warnings.append(f"  [WARN] {r['trade_date']}: 最高价({h}) < 最低价({l})")
        if h < o or h < c:
            warnings.append(f"  [WARN] {r['trade_date']}: 最高价 < 开盘/收盘")
        if l > o or l > c:
            warnings.append(f"  [WARN] {r['trade_date']}: 最低价 > 开盘/收盘")
        if vol < 0:
            warnings.append(f"  [WARN] {r['trade_date']}: 成交量为负")
        if amount < 0:
            warnings.append(f"  [WARN] {r['trade_date']}: 成交额为负")

    if not warnings:
        print(f"  ✓ {stock_name}: 数据校验通过")
    return warnings


# ============================================================================
# HTTP API 取数
# ============================================================================
def fetch_dimension_http(stock: dict, dimension: dict, time_range: dict, spec: dict) -> tuple[list[dict], list[str]]:
    """
    通过 HTTP API 获取单个维度数据。
    返回 (records, field_names)
    """
    api_name = dimension["api"]
    field_names = [f["name"] for f in dimension.get("fields", [])]

    params: dict[str, str] = {"ts_code": stock["ts_code"]}
    if api_name in ("stk_factor", "daily_basic", "adj_factor", "moneyflow"):
        params["start_date"] = time_range["start"]
        params["end_date"] = time_range["end"]
    if api_name == "fina_indicator":
        params["start_date"] = time_range["start"]
        params["end_date"] = time_range["end"]

    # 限速
    time.sleep(RATE_LIMIT_INTERVAL)

    resp = call_tushare_http(api_name, params, field_names if field_names else None)

    if resp.get("code") != 0:
        raise RuntimeError(f"API {api_name} 返回错误: {resp.get('msg', 'unknown')}")

    data = resp.get("data", {})
    items = data.get("items", [])
    returned_fields = data.get("fields", [])

    if not items:
        print(f"  ⚠ {api_name}: 无数据返回（可能权限不足或时间范围无数据）")
        return [], returned_fields

    records = [dict(zip(returned_fields, item)) for item in items]
    records.sort(key=lambda x: x.get("trade_date", x.get("end_date", x.get("ann_date", ""))))

    return records, returned_fields


# ============================================================================
# 主流程
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="通用股票数据获取脚本 — 基于 stock_data_spec.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 按默认配置获取所有维度的数据
  %(prog)s --stock smic                 # 只取中芯国际
  %(prog)s --stock smic,byd             # 取中芯国际和比亚迪
  %(prog)s --dim daily_price            # 只取日线行情
  %(prog)s --dim daily,financial        # 取日线和财务数据
  %(prog)s --time-range all --stock byd # 比亚迪全历史数据
  %(prog)s --mode dry-run               # 预览而不实际取数
  %(prog)s --mode http                  # 强制使用 HTTP API 模式
        """,
    )
    parser.add_argument("--stock", type=str, default="", help="股票 ID 列表（逗号分隔），默认全部")
    parser.add_argument("--dim", type=str, default="", help="维度 ID 列表（逗号分隔），默认全部")
    parser.add_argument("--time-range", type=str, default="y1", help="时间范围标签: y1|y3|y5|all，默认 y1（近一年）")
    parser.add_argument("--mode", type=str, default="mcp", choices=["mcp", "http", "dry-run"],
                        help="取数模式: mcp（默认）| http | dry-run")
    parser.add_argument("--no-validate", action="store_true", help="跳过数据校验")
    parser.add_argument("--spec", type=str, default=str(SPEC_FILE), help="spec 文件路径")
    args = parser.parse_args()

    # ── 加载 spec ──
    if not os.path.exists(args.spec):
        print(f"错误: spec 文件不存在: {args.spec}")
        sys.exit(1)

    spec = load_spec(Path(args.spec))
    print(f"📋 已加载 spec: {args.spec}")

    # ── 解析参数 ──
    stock_ids = set(args.stock.split(",")) if args.stock else set()
    dim_ids = set(args.dim.split(",")) if args.dim else set()

    # 过滤股票
    stocks = [
        s for s in spec["stock_pool"]
        if not stock_ids or s["id"] in stock_ids
    ]
    if not stocks:
        print("错误: 没有匹配的股票")
        sys.exit(1)

    # 获取时间范围
    time_ranges = spec["time_range"]["histories"]
    if args.time_range not in time_ranges:
        print(f"错误: 未知时间范围 '{args.time_range}'，可选: {list(time_ranges.keys())}")
        sys.exit(1)
    time_range = time_ranges[args.time_range]

    # 过滤维度
    dimensions = [
        d for d in spec["dimensions"]
        if not dim_ids or d["id"] in dim_ids
    ]
    if not dimensions:
        print("错误: 没有匹配的数据维度")
        sys.exit(1)

    # ── 打印执行计划 ──
    print(f"\n{'='*60}")
    print(f"股票数量: {len(stocks)}  维度数量: {len(dimensions)}  时间范围: {args.time_range}")
    print(f"取数模式: {args.mode}")
    print(f"{'='*60}")

    for stock in stocks:
        print(f"\n  📊 {stock['name']} ({stock['ts_code']})  [{stock['industry']}]")
        for dim in dimensions:
            print(f"     └─ {dim['name']} ({dim['api']})  [{len(dim.get('fields', []))} 个字段]")

    if args.mode == "dry-run":
        print(f"\n✅ 预演完成。共 {len(stocks)*len(dimensions)} 个取数任务。")
        print("   使用 --mode http 或 --mode mcp 实际执行取数。")
        return

    # ── HTTP 模式 ──
    if args.mode == "http":
        if not TOKEN:
            print("\n错误: 请设置环境变量 TUSHARE_TOKEN")
            print("  export TUSHARE_TOKEN='your_token_here'")
            sys.exit(1)

        total_success = 0
        total_fail = 0

        for stock in stocks:
            print(f"\n{'─'*60}")
            print(f"📊 {stock['name']} ({stock['ts_code']})")
            print(f"{'─'*60}")

            for dim in dimensions:
                print(f"  ⏳ {dim['name']} ({dim['api']}) ...", end="", flush=True)
                try:
                    records, field_names = fetch_dimension_http(stock, dim, time_range, spec)
                    if not records:
                        print(" 无数据")
                        total_fail += 1
                        continue

                    # 保存
                    output_dir = PROJECT_ROOT / dim["output"]["dir"]
                    filename = dim["output"]["naming"].format(stock_id=stock["id"])
                    save_to_csv(records, field_names, output_dir / filename)

                    # 校验
                    if not args.no_validate and dim["api"] == "daily":
                        warnings = validate_daily_data(records, stock["name"])
                        for w in warnings:
                            print(f"    {w}")

                    total_success += 1
                except Exception as e:
                    print(f" 失败: {e}")
                    total_fail += 1

        print(f"\n{'='*60}")
        print(f"✅ 完成: 成功 {total_success}, 失败 {total_fail}")
        print(f"{'='*60}")

    # ── MCP 模式（输出所有 MCP 调用指令供 AI Agent 执行） ──
    elif args.mode == "mcp":
        print(f"\n{'='*60}")
        print("MCP 工具调用清单（共 {} 个调用）".format(len(stocks) * len(dimensions)))
        print(f"{'='*60}")

        calls = []
        for i, stock in enumerate(stocks):
            for j, dim in enumerate(dimensions):
                call = generate_mcp_call(stock, dim, time_range)
                calls.append(call)
                print(f"\n  [{i*len(dimensions)+j+1}] {call['mcp_tool']}")
                print(f"      股票: {call['stock']}")
                print(f"      维度: {call['dimension']}")
                print(f"      参数: {json.dumps(call['params'], ensure_ascii=False)}")
                print(f"      输出: {call['output_file']}")

        # 保存调用清单到 JSON
        manifest_path = PROJECT_ROOT / "data" / "mcp_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(calls, f, ensure_ascii=False, indent=2)
        print(f"\n✅ MCP 调用清单已保存: {manifest_path}")
        print("   请在 WorkBuddy 中由 AI Agent 依次执行上述 MCP 工具调用。")


if __name__ == "__main__":
    main()
