#!/usr/bin/env python3
"""
Week 2: Handoff（职责转交）示例（Day 12）

学习目标：
1. 理解 Handoff 的核心概念：Agent 之间的职责转交
2. 实现多 Agent 协作：Triage → Support / FAQ / Escalation
3. 观察对话历史在转交中的完整传递
4. 与单 Agent 多 Tool 方案对比，理解 Handoff 的适用场景

核心概念：
- TriageAgent（分诊台）：只负责理解意图和转交，不处理具体问题
- 专家 Agent：各自有专属 Tool 和 Instructions，处理特定领域问题
- Handoff 机制：对话历史完整传递，用户无感知切换

运行方式：
  python handoff_example.py              # 交互模式
  python handoff_example.py --test       # 批量测试模式

对比学习：
  - ecommerce_support_agent.py = 单 Agent + 7 个 Tool（集中式）
  - 本文件 = 多 Agent + Handoff（分布式）
  - 核心差异：职责是否拆分到不同 Agent，Instructions 是否更聚焦
"""

import asyncio
import os
import sys
import logging
from typing import Optional

from agents import Agent, Runner, handoff, function_tool
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 禁用 OpenAI Agents SDK 内置 Tracing（避免向 api.openai.com 发送追踪数据）
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "true"

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用 Responses API，使用 Chat Completions
set_use_responses_by_default(False)

# 初始化智谱 AI 客户端（通过 OpenAI 兼容接口）
client = AsyncOpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)

# 模型名称（通过 OpenAIChatCompletionsModel 包装）
MODEL_NAME = "glm-5.1"


# ============================================================
# 模拟数据库
# ============================================================

ORDERS_DB = {
    "ORD1001": {"status": "已发货", "logistics_no": "SF1234567890", "product": "蓝牙耳机"},
    "ORD1002": {"status": "待发货", "logistics_no": None, "product": "手机壳"},
    "ORD1003": {"status": "已签收", "logistics_no": "YT9876543210", "product": "充电宝"},
    "ORD1004": {"status": "退款中", "logistics_no": None, "product": "数据线"},
}

REFUND_RULES = {
    "未发货": "全额退款，1-3 个工作日到账",
    "已发货": "需退回商品，运费自理，确认收货后 7 天内退款",
    "已签收": "确认收货后 7 天内可申请，需保持商品完好",
}

FAQ_KB = {
    "支付方式": "支持微信支付、支付宝、银行卡，暂不支持货到付款。",
    "发货时间": "下单后 24 小时内发货（节假日顺延），发货后可在订单详情查看物流。",
    "配送范围": "全国包邮（港澳台及偏远地区需额外运费），一般 3-5 天到达。",
    "发票": "支持电子发票，下单时备注即可，发货后 3 天内发送到邮箱。",
    "售后": "7 天无理由退货，15 天质量问题包换，1 年保修。",
}


# ============================================================
# Tool 定义 — 按职责分组给不同的 Agent
# ============================================================

# --- SupportAgent 专属 Tools ---

@function_tool
def query_order_status(order_id: str) -> str:
    """查询订单状态和商品信息。参数 order_id 为订单号。"""
    order = ORDERS_DB.get(order_id.upper())
    if not order:
        return f"未找到订单 {order_id}，请检查订单号是否正确。"
    logistics = f"，物流单号：{order['logistics_no']}" if order.get("logistics_no") else ""
    return f"订单 {order_id} 状态：{order['status']}，商品：{order['product']}{logistics}"


@function_tool
def query_refund_policy(order_status: str) -> str:
    """查询退款政策。参数 order_status 为订单当前状态。"""
    for key, policy in REFUND_RULES.items():
        if key in order_status:
            return f"退款政策（{key}）：{policy}"
    return "未找到对应状态的退款政策，请联系人工客服。"


@function_tool
def process_refund(order_id: str, reason: str) -> str:
    """提交退款申请。参数 order_id 为订单号，reason 为退款原因。"""
    oid = order_id.upper()
    if oid not in ORDERS_DB:
        return f"订单 {order_id} 不存在。"
    order = ORDERS_DB[oid]
    if order["status"] == "退款中":
        return f"订单 {order_id} 已在退款流程中，请勿重复申请。"
    order["status"] = "退款中"
    return f"退款申请已提交！订单：{order_id}，商品：{order['product']}，原因：{reason}。客服将在 24 小时内审核。"


# --- FAQAgent 专属 Tools ---

@function_tool
def search_faq(keyword: str) -> str:
    """搜索常见问题。参数 keyword 为搜索关键词，如'支付''发货''发票'。"""
    results = []
    for key, answer in FAQ_KB.items():
        if keyword in key or keyword in answer:
            results.append(f"【{key}】{answer}")
    if results:
        return "\n".join(results)
    return f"未找到与'{keyword}'相关的常见问题，建议转接人工客服。"


# --- EscalationAgent 专属 Tools ---

@function_tool
def create_ticket(issue_type: str, summary: str) -> str:
    """创建工单转交人工客服。参数 issue_type 为问题类型，summary 为问题描述。"""
    ticket_id = f"TK{hash(summary) % 10000:04d}"
    return (
        f"已创建工单 {ticket_id}\n"
        f"问题类型：{issue_type}\n"
        f"问题描述：{summary}\n"
        f"预计 30 分钟内有客服联系您，请保持电话畅通。"
    )


# ============================================================
# Agent 定义
# ============================================================

# 1. SupportAgent — 订单/退款专家
support_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="SupportAgent",
    instructions="""你是电商客服专家，专门处理订单和退款问题。

工作流程：
1. 用户提到订单 → 用 query_order_status 查询
2. 用户问退款政策 → 用 query_refund_policy 查询
3. 用户要退款 → 先确认订单号，再用 process_refund 处理

回复要求：
- 使用中文，语气亲切专业
- 必须先查到订单才能操作退款
- 退款需要用户提供原因""",
    tools=[query_order_status, query_refund_policy, process_refund],
)

# 2. FAQAgent — 常见问题客服
faq_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="FAQAgent",
    instructions="""你是电商 FAQ 客服，处理常见问题。

你能回答的问题：支付方式、发货时间、配送范围、发票、售后政策

工作流程：
1. 用户问常见问题 → 用 search_faq 搜索知识库
2. 搜索不到 → 建议用户换关键词或联系人工

回复要求：
- 使用中文，简洁明了
- 如果 search_faq 没找到结果，直接说"这个问题我暂时无法回答"
- 不要编造信息""",
    tools=[search_faq],
)

# 3. EscalationAgent — 人工转接
escalation_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="EscalationAgent",
    instructions="""你是工单创建专员，负责把复杂问题转交给人工客服。

工作流程：
1. 了解用户的问题类型和详细描述
2. 用 create_ticket 创建工单

回复要求：
- 使用中文
- 创建工单后告知用户工单号和预计回复时间
- 如果用户描述不清楚，先追问再创建工单""",
    tools=[create_ticket],
)

# 4. TriageAgent — 分诊台（入口 Agent）
triage_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="TriageAgent",
    instructions="""你是电商客服的分诊台（Triage），负责理解用户意图并转交给合适的专家。

转交规则：
- 提到订单（查询/状态/物流）→ 转交 SupportAgent
- 提到退款/退货 → 转交 SupportAgent
- 问支付方式/发货时间/配送/发票/售后 → 转交 FAQAgent
- 投诉/要找人工/问题太复杂 → 转交 EscalationAgent
- 简单问候（你好/谢谢）→ 自己回答，不用转交

⚠️ 重要：你只负责分类和转交，不要尝试直接处理具体问题！
如果不确定，优先转交给 SupportAgent。""",
    handoffs=[
        handoff(support_agent),
        handoff(faq_agent),
        handoff(escalation_agent),
    ],
)


# ============================================================
# 运行逻辑
# ============================================================

async def run_single_query(query: str) -> None:
    """运行单条查询并打印结果"""
    print(f"\n{'='*60}")
    print(f"👤 用户: {query}")
    print(f"{'='*60}")

    result = await Runner.run(
        triage_agent,
        query,
    )

    print(f"🤖 回复: {result.final_output}")
    print(f"   最终处理 Agent: {result.last_agent.name}")
    print()


async def interactive_mode():
    """交互模式：持续对话"""
    print("=" * 60)
    print("🔄 Handoff 示例 — 电商客服多 Agent 协作")
    print("=" * 60)
    print()
    print("可用命令:")
    print("  直接输入问题 → 自动分诊转交")
    print("  quit / exit  → 退出")
    print()
    print("试试这些:")
    print("  - 我的订单 ORD1001 到哪了？")
    print("  - 我要退款")
    print("  - 你们支持什么支付方式？")
    print("  - 我要投诉")
    print()

    while True:
        try:
            user_input = input("👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        await run_single_query(user_input)


async def test_mode():
    """批量测试模式：验证 Handoff 路由是否正确"""
    test_cases = [
        # (用户输入, 期望的最终 Agent 名称)
        ("我的订单 ORD1001 到哪了？", "SupportAgent"),
        ("我要退款", "SupportAgent"),
        ("订单 ORD1003 可以退吗？", "SupportAgent"),
        ("你们支持什么支付方式？", "FAQAgent"),
        ("多久能发货？", "FAQAgent"),
        ("发票怎么开？", "FAQAgent"),
        ("我要投诉，你们服务太差了", "EscalationAgent"),
        ("找人工客服", "EscalationAgent"),
        ("你好", "TriageAgent"),
    ]

    print("=" * 60)
    print("🧪 Handoff 路由测试")
    print("=" * 60)

    passed = 0
    failed = 0

    for query, expected_agent in test_cases:
        result = await Runner.run(triage_agent, query)
        actual_agent = result.last_agent.name
        is_pass = actual_agent == expected_agent
        status = "✅ PASS" if is_pass else "❌ FAIL"

        print(f"{status} | 用户: {query}")
        print(f"       期望: {expected_agent} | 实际: {actual_agent}")
        print(f"       回复: {result.final_output[:80]}...")
        print()

        if is_pass:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"📊 测试结果: {passed}/{len(test_cases)} 通过, {failed} 失败")
    print("=" * 60)


async def main():
    if "--test" in sys.argv:
        await test_mode()
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
