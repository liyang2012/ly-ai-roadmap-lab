#!/usr/bin/env python3
"""
Day 19-20: 错误样本集建立

目标: 用 mini_eval.csv 的 20 条用例跑 Agent，收集真实错误案例，
      区分 Prompt 问题、Schema 问题、以及其他。

核心方法: 基于 trace 数据判断 tool 调用，不依赖输出文本解析。
"""

import asyncio
import csv
import os
import logging
import json
from datetime import datetime
from typing import Optional

from agents import Agent, Runner, function_tool, trace
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 加载环境变量
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

set_use_responses_by_default(False)

client = AsyncOpenAI(
    # 智谱 AI API Key，从环境变量读取
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    # 智谱 AI API 地址
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)

# ============================================================
# 模拟数据库（与 week2 一致）
# ============================================================

ORDERS_DB = {
    "ORD20260417001": {
        "status": "已发货", "product": "iPhone 15 Pro", "amount": 7999.00,
        "order_date": "2026-04-15", "logistics": "顺丰 SF1234567890",
        "estimated_delivery": "2026-04-19"
    },
    "ORD20260417002": {
        "status": "处理中", "product": "AirPods Pro 2", "amount": 1899.00,
        "order_date": "2026-04-17", "logistics": "待发货",
        "estimated_delivery": "2026-04-20"
    },
    "ORD20260417003": {
        "status": "已签收", "product": "MacBook Air M2", "amount": 9499.00,
        "order_date": "2026-04-10", "logistics": "京东 JD9876543210",
        "estimated_delivery": "已送达"
    },
}

REFUND_RULES = {
    "未发货": {"allowed": True, "days": "1-3 工作日到账", "fee": "无手续费"},
    "已发货": {"allowed": True, "days": "拒收或退货后", "fee": "运费自理"},
    "已签收": {"allowed": True, "days": "7 天内", "fee": "无质量问题需自理运费"},
    "超过 7 天": {"allowed": False, "days": "仅质量问题", "fee": "免费"},
}

COUPONS_DB = {
    "USER001": [
        {"code": "NEW100", "discount": 100, "min_amount": 1000, "expire": "2026-05-01", "status": "可用"},
        {"code": "VIP50", "discount": 50, "min_amount": 500, "expire": "2026-04-30", "status": "可用"},
    ],
    "USER002": [
        {"code": "NEW100", "discount": 100, "min_amount": 1000, "expire": "2026-05-01", "status": "已使用"},
    ],
}

PRODUCT_KB = {
    "iPhone": {"warranty": "1 年全国联保", "return": "7 天无理由", "features": "A17 芯片、钛金属边框、4800 万像素"},
    "MacBook": {"warranty": "1 年全国联保", "return": "14 天无理由（未激活）", "features": "M 系列芯片、Liquid 视网膜屏、18 小时续航"},
    "AirPods": {"warranty": "1 年全国联保", "return": "7 天无理由", "features": "主动降噪、空间音频、MagSafe 充电"},
}


# ============================================================
# Tool 定义
# ============================================================

@function_tool
def query_order_status(order_id: str) -> str:
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"❌ 未找到订单 {order_id}，请确认订单号是否正确"
    return f"📦 订单号：{order_id} | 商品：{order['product']} | 金额：¥{order['amount']:,.2f} | 状态：{order['status']} | 物流：{order['logistics']}"


@function_tool
def query_refund_policy(order_status: str) -> str:
    matched_key = None
    for key in REFUND_RULES:
        if key in order_status:
            matched_key = key
            break
    if not matched_key:
        return f"❌ 无法识别订单状态：{order_status}，请提供：未发货/已发货/已签收/超过 7 天"
    rule = REFUND_RULES[matched_key]
    allowed = "✅ 支持退款" if rule["allowed"] else "❌ 不支持退款"
    return f"💰 状态【{order_status}】：{allowed} | 时效：{rule['days']} | 费用：{rule['fee']}"


@function_tool
def process_refund_apply(order_id: str, reason: str) -> str:
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"❌ 订单 {order_id} 不存在"
    status = order["status"]
    rule = REFUND_RULES.get(status, REFUND_RULES["超过 7 天"])
    if not rule["allowed"]:
        return f"❌ 订单 {order_id} 状态【{status}】不支持退款"
    refund_id = f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return f"✅ 退款已提交 | 单号：{refund_id} | 订单：{order_id} | 金额：¥{order['amount']:,.2f} | 原因：{reason}"


@function_tool
def query_logistics(logistics_no: str) -> str:
    tracks = {
        "SF1234567890": [("2026-04-18 14:30", "已签收"), ("2026-04-18 09:15", "派送中")],
        "JD9876543210": [("2026-04-12 16:00", "已签收"), ("2026-04-12 08:30", "派送中")],
    }.get(logistics_no)
    if not tracks:
        return f"❌ 未找到物流单号 {logistics_no}"
    return f"🚚 物流 {logistics_no}: {' → '.join(f'{t[0]} {t[1]}' for t in tracks)}"


@function_tool
def query_coupons(user_id: str) -> str:
    coupons = COUPONS_DB.get(user_id)
    if not coupons:
        return f"❌ 未找到用户 {user_id}"
    available = [c for c in coupons if c["status"] == "可用"]
    return f"🎫 用户 {user_id}: {len(available)} 张可用" if available else f"🎫 用户 {user_id}: 无可用优惠券"


@function_tool
def query_product_info(product_name: str) -> str:
    matched = None
    for key in PRODUCT_KB:
        if key.lower() in product_name.lower():
            matched = key
            break
    if not matched:
        return f"❌ 未找到产品【{product_name}】"
    info = PRODUCT_KB[matched]
    return f"📱 {matched} | 保修：{info['warranty']} | 退货：{info['return']}"


@function_tool
def escalate_to_human(issue_type, summary: str) -> str:
    import random
    ticket_id = f"TKT{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
    return f"👤 工单 {ticket_id} 已创建 | 类型：{issue_type} | 摘要：{summary[:50]}"


# ============================================================
# Agent 创建（与 week2 一致）
# ============================================================

def create_agent():
    tools = [query_order_status, query_refund_policy, process_refund_apply,
             query_logistics, query_coupons, query_product_info, escalate_to_human]

    instructions = """
你是一名专业的电商客服助手，服务于一家电子产品商城。

【工具选择指南】
- 查询订单状态 → query_order_status
- 询问退款政策 → query_refund_policy
- 提交退款申请 → process_refund_apply
- 查询物流轨迹 → query_logistics（需要物流单号）
- 查询优惠券 → query_coupons（需要用户 ID）
- 产品咨询 → query_product_info
- 投诉/复杂问题 → escalate_to_human

【回复规范】
1. 先理解用户意图，再选择工具
2. 如果缺少必要参数（如订单号），先礼貌询问
3. 回复要专业、友好、简洁
"""

    return Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="电商客服助手",
        instructions=instructions,
        tools=tools
    )


# ============================================================
# 从 trace 中提取实际调用的 tool
# ============================================================

def extract_tools_from_trace(trace_data) -> list[str]:
    """从 trace 数据中提取实际调用的 tool 名称"""
    called_tools = []
    if not trace_data:
        return called_tools
    
    # trace 是一个列表，每个元素是一次 run
    for run in trace_data:
        if isinstance(run, dict):
            # 查找 tool calls
            if 'turns' in run:
                for turn in run['turns']:
                    if 'tool_calls' in turn:
                        for tc in turn['tool_calls']:
                            if isinstance(tc, dict) and 'function' in tc:
                                called_tools.append(tc['function']['name'])
            # 也检查 agents 层面的 trace
            if 'agent' in run and 'turns' in run.get('agent', {}):
                for turn in run['agent']['turns']:
                    if 'tool_calls' in turn:
                        for tc in turn['tool_calls']:
                            if isinstance(tc, dict) and 'function' in tc:
                                called_tools.append(tc['function']['name'])
    
    return called_tools


def extract_tools_from_result(result) -> list[str]:
    """从 Runner.run result.new_items 中提取实际调用的 tool 名称"""
    called = []
    if hasattr(result, 'new_items'):
        for item in result.new_items:
            # ToolCallItem 表示一次 tool 调用
            item_type = getattr(item, 'type', '')
            if item_type == 'tool_call_item':
                # raw_item 是 ResponseFunctionToolCall，有 name 属性
                raw = getattr(item, 'raw_item', None)
                if raw:
                    name = getattr(raw, 'name', None)
                    if name:
                        called.append(name)
    return called


# ============================================================
# 评测用例（来自 mini_eval.csv）
# ============================================================

EVAL_CASES = [
    ("订单 ORD20260417001 到哪了", "query_order_status"),
    ("ORD20260417002 发货了吗", "query_order_status"),
    ("怎么退款", "query_refund_policy"),
    ("我要申请退款，订单 ORD20260417001，七天无理由", "process_refund_apply"),
    ("已发货的订单能退款吗", "query_refund_policy"),
    ("帮我查一下物流 SF1234567890", "query_logistics"),
    ("我的包裹到哪了？物流单号 JD9876543210", "query_logistics"),
    ("我有哪些优惠券？用户 ID 是 USER001", "query_coupons"),
    ("iPhone 的保修政策是什么", "query_product_info"),
    ("MacBook 有什么特点", "query_product_info"),
    ("我要投诉！服务态度太差了", "escalate_to_human"),
    ("这个情况太复杂了，叫人工客服", "escalate_to_human"),
    ("你好", None),  # 闲聊，不调用 tool
    ("谢谢", None),  # 闲聊，不调用 tool
    ("订单 ORD99999 存在吗", "query_order_status"),
    ("退款需要什么条件", "query_refund_policy"),
    ("USER002 的优惠券情况", "query_coupons"),
    ("AirPods 的保修期是多久", "query_product_info"),
    ("帮我查一下物流单号 SF999999999", "query_logistics"),
    ("我要退款，订单 ORD20260417003，质量问题", "process_refund_apply"),
]


async def run_error_collection():
    """运行错误样本收集"""
    agent = create_agent()
    
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(results_dir, f"error_cases_run_{timestamp}.csv")
    
    print("=" * 80)
    print(f"📋 Day 19-20: 错误样本集收集")
    print(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 用例数: {len(EVAL_CASES)}")
    print("=" * 80)
    
    rows = []
    error_cases = []
    passed = 0
    failed = 0
    
    for i, (question, expected_tool) in enumerate(EVAL_CASES, 1):
        print(f"\n[{i}/{len(EVAL_CASES)}] 👤 {question}")
        print(f"    🎯 预期: {expected_tool or '(无/tool-free)'}")
        
        try:
            result = await Runner.run(agent, question)
            actual_tools = extract_tools_from_result(result)
            actual_tool = actual_tools[0] if actual_tools else "(无)"
            output_text = result.final_output[:200] if result.final_output else "(空)"
            
            # 判断是否通过
            if expected_tool is None:
                # 闲聊：不应该调用 tool
                is_pass = len(actual_tools) == 0
            else:
                is_pass = expected_tool in actual_tools
            
            status = "✅ PASS" if is_pass else "❌ FAIL"
            if is_pass:
                passed += 1
            else:
                failed += 1
                error_cases.append({
                    "id": i,
                    "question": question,
                    "expected": expected_tool or "(无)",
                    "actual": actual_tool,
                    "output": output_text,
                })
            
            print(f"    {status} 实际: {actual_tool}")
            
            rows.append({
                "id": i,
                "question": question,
                "expected_tool": expected_tool or "",
                "actual_tool": actual_tool,
                "actual_tools": ",".join(actual_tools),
                "pass": "Y" if is_pass else "N",
                "output_preview": output_text[:150],
            })
            
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            failed += 1
            error_cases.append({
                "id": i,
                "question": question,
                "expected": expected_tool or "(无)",
                "actual": f"EXCEPTION: {e}",
                "output": str(e)[:200],
            })
            rows.append({
                "id": i,
                "question": question,
                "expected_tool": expected_tool or "",
                "actual_tool": f"ERROR",
                "actual_tools": "",
                "pass": "N",
                "output_preview": str(e)[:150],
            })
    
    # 写入 CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "question", "expected_tool", "actual_tool", "actual_tools", "pass", "output_preview"])
        writer.writeheader()
        writer.writerows(rows)
    
    # 打印汇总
    print("\n" + "=" * 80)
    print(f"📊 结果: 通过 {passed}/{len(EVAL_CASES)}  失败 {failed}/{len(EVAL_CASES)}  通过率 {passed/len(EVAL_CASES)*100:.0f}%")
    print("=" * 80)
    
    if error_cases:
        print(f"\n❌ 错误案例 ({len(error_cases)} 条):")
        for ec in error_cases:
            print(f"  #{ec['id']}: {ec['question'][:40]}")
            print(f"     预期: {ec['expected']} → 实际: {ec['actual']}")
            print(f"     输出: {ec['output'][:100]}")
            print()
    
    # 生成错误案例 Markdown 报告
    md_report = generate_error_report(error_cases, passed, failed, timestamp)
    report_path = os.path.join(results_dir, f"error_cases_report_{timestamp}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"📄 报告已保存: {report_path}")
    print(f"📄 CSV 已保存: {output_csv}")
    
    return rows, error_cases


def generate_error_report(error_cases, passed, failed, timestamp):
    """生成错误案例 Markdown 报告"""
    total = passed + failed
    pass_rate = passed / total * 100 if total > 0 else 0
    
    md = f"""# 错误样本集报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**用例总数**: {total}
**通过**: {passed} | **失败**: {failed} | **通过率**: {pass_rate:.0f}%

---

## 📊 错误分类统计

| 类别 | 数量 | 说明 |
|------|------|------|
| Prompt 问题 | {sum(1 for e in error_cases if 'prompt' in classify_error(e))} | instructions 不清晰导致误调 |
| Schema 问题 | {sum(1 for e in error_cases if 'schema' in classify_error(e))} | tool 描述模糊导致选错 tool |
| 其他 | {sum(1 for e in error_cases if 'other' in classify_error(e))} | 闲聊误调、异常等 |

---

## ❌ 错误案例详情

"""
    
    for ec in error_cases:
        category = classify_error(ec)
        md += f"""### 案例 #{ec['id']}

- **问题**: {ec['question']}
- **预期 tool**: `{ec['expected']}`
- **实际 tool**: `{ec['actual']}`
- **错误类别**: {category}
- **Agent 输出**: 
```
{ec['output'][:300]}
```

**分析**: {analyze_error(ec)}

---

"""
    
    md += f"""## 💡 总结与建议

1. **整体通过率 {pass_rate:.0f}%**，{'达标' if pass_rate >= 80 else '未达标'}（目标 ≥ 80%）
2. 主要错误类型集中在: {get_top_error_type(error_cases)}
3. 建议针对高频错误优化 instructions 或 tool 描述

"""
    
    return md


def classify_error(ec) -> str:
    """简单分类错误类型"""
    expected = ec.get("expected", "")
    actual = ec.get("actual", "")
    question = ec.get("question", "")
    
    if "EXCEPTION" in actual:
        return "other"
    
    # 闲聊但调用了 tool
    if expected == "(无)" and actual != "(无)":
        return "prompt"
    
    # 应该调用 tool 但没调用
    if expected != "(无)" and actual == "(无)":
        return "prompt"
    
    # 调用了错误的 tool
    if expected != actual and expected != "(无)" and actual != "(无)":
        # 判断是否是 tool 描述模糊导致的选错
        return "schema"
    
    return "other"


def analyze_error(ec) -> str:
    """分析错误原因"""
    expected = ec.get("expected", "")
    actual = ec.get("actual", "")
    
    if "EXCEPTION" in actual:
        return f"运行时异常: {actual}"
    
    if expected == "(无)" and actual != "(无)":
        return f"闲聊问题误触发了 tool 调用，instructions 中没有明确说明闲聊场景的处理方式"
    
    if expected != "(无)" and actual == "(无)":
        return f"Agent 没有识别出需要调用 tool，可能是 instructions 中 tool 使用场景描述不够清晰"
    
    if expected != actual:
        return f"Agent 选择了错误的 tool，{expected} 和 {actual} 的 tool 描述可能存在重叠或歧义"
    
    return "未知错误"


def get_top_error_type(error_cases) -> str:
    """获取主要错误类型"""
    if not error_cases:
        return "无"
    
    counts = {}
    for ec in error_cases:
        cat = classify_error(ec)
        counts[cat] = counts.get(cat, 0) + 1
    
    top = max(counts, key=counts.get)
    return f"{top} ({counts[top]} 条)"


if __name__ == "__main__":
    asyncio.run(run_error_collection())
