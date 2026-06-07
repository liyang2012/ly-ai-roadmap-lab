"""
Week 4: Agent 版 - LLM 驱动的 OpenAI Agents SDK 风格实现

学习目标：
1. 用 LLM 做意图识别和 tool 选择
2. 理解 agent 模式的灵活性与代价
3. 记录 token 消耗和延迟，用于与 workflow 版对比

特点：
- ✅ 灵活性强：模糊意图也能处理
- ✅ 自然语言理解：不需要精确关键词
- ❌ 不确定：相同输入可能产生不同结果
- ❌ 有延迟：每次调 LLM 需要 1-5 秒
- ❌ 消耗 token：每次调用都有成本

注意：为了公平对比，我们用模拟 LLM 调用（规则 + 模拟延迟）。
实际使用时替换为真实 LLM API 调用即可。
"""

import re
import time
import random
from typing import Optional


# ============================================================
# 模拟数据库（与 workflow 版完全一致）
# ============================================================

ORDERS_DB = {
    "ORD20260417001": {
        "status": "已发货", "product": "iPhone 15 Pro",
        "amount": 7999.00, "order_date": "2026-04-15",
        "logistics": "顺丰 SF1234567890", "estimated_delivery": "2026-04-19"
    },
    "ORD20260417002": {
        "status": "处理中", "product": "AirPods Pro 2",
        "amount": 1899.00, "order_date": "2026-04-17",
        "logistics": "待发货", "estimated_delivery": "2026-04-20"
    },
    "ORD20260417003": {
        "status": "已签收", "product": "MacBook Air M2",
        "amount": 9499.00, "order_date": "2026-04-10",
        "logistics": "京东 JD9876543210", "estimated_delivery": "已送达"
    },
}

LOGISTICS_DB = {
    "SF1234567890": [
        {"time": "2026-04-16 10:00", "status": "已揽件"},
        {"time": "2026-04-16 18:00", "status": "到达北京转运中心"},
        {"time": "2026-04-17 06:00", "status": "发往上海"},
        {"time": "2026-04-17 14:00", "status": "派送中"},
    ],
    "JD9876543210": [
        {"time": "2026-04-11 09:00", "status": "已签收，签收人：本人"},
    ],
}

REFUND_RULES = {
    "未发货": {"allowed": True, "days": "1-3 工作日到账", "fee": "无手续费"},
    "已发货": {"allowed": True, "days": "拒收或退货后", "fee": "运费自理"},
    "已签收": {"allowed": True, "days": "7 天内", "fee": "买家承担运费"},
}

COUPONS_DB = {
    "USER001": [
        {"code": "SAVE50", "discount": 50, "min_spend": 500, "expire": "2026-06-30"},
        {"code": "NEW100", "discount": 100, "min_spend": 1000, "expire": "2026-05-31"},
    ],
    "USER002": [
        {"code": "VIP20", "discount": 20, "min_spend": 200, "expire": "2026-12-31"},
    ],
}

PRODUCT_KB = {
    "iPhone 15 Pro": {"price": 7999, "warranty": "1 年", "return_policy": "7 天无理由"},
    "AirPods Pro 2": {"price": 1899, "warranty": "1 年", "return_policy": "7 天无理由"},
    "MacBook Air M2": {"price": 9499, "warranty": "1 年", "return_policy": "14 天无理由"},
}


# ============================================================
# 模拟 LLM 调用
# ============================================================

def simulate_llm_call(prompt: str, estimated_tokens: int = 200) -> dict:
    """
    模拟一次 LLM API 调用。

    在真实环境中，这里会调用 OpenAI / Bailian API。
    模拟版：
    - 延迟：200-800ms（模拟网络 + 推理时间）
    - Token：按估算值返回
    - 结果：基于规则但加入少量随机性

    真实版替换为：
        import openai
        resp = openai.chat.completions.create(
            model="qwen3.5-plus",
            messages=[{"role": "user", "content": prompt}],
            tools=tool_definitions,
        )
    """
    latency = random.uniform(200, 800)  # 200-800ms
    time.sleep(latency / 1000)

    return {
        "latency_ms": latency,
        "tokens_used": estimated_tokens,
        "llm_calls": 1,
    }


# ============================================================
# Tool 定义（Agent 模式）
# ============================================================

def tool_query_order(order_id: str) -> str:
    """查询订单状态"""
    order = ORDERS_DB.get(order_id)
    if order:
        return (
            f"📦 订单 {order_id}：\n"
            f"  商品：{order['product']}\n"
            f"  状态：{order['status']}\n"
            f"  金额：¥{order['amount']:.2f}\n"
            f"  物流：{order['logistics']}"
        )
    return f"❌ 未找到订单 {order_id}"


def tool_query_refund(order_id: str) -> str:
    """查询退款政策"""
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    rule = REFUND_RULES.get(order["status"], {})
    return (
        f"💰 退款政策（订单 {order_id}）：\n"
        f"  可退款：{'是' if rule.get('allowed') else '否'}\n"
        f"  到账：{rule.get('days', '未知')}\n"
        f"  手续费：{rule.get('fee', '未知')}"
    )


def tool_query_logistics(tracking_number: str) -> str:
    """查询物流信息"""
    if tracking_number in LOGISTICS_DB:
        logs = LOGISTICS_DB[tracking_number]
        detail = "\n".join(f"  {l['time']} - {l['status']}" for l in logs)
        return f"🚚 物流 {tracking_number}：\n{detail}"
    return "❌ 未找到物流信息"


def tool_query_coupons(user_id: str) -> str:
    """查询用户优惠券"""
    coupons = COUPONS_DB.get(user_id, [])
    if coupons:
        detail = "\n".join(
            f"  🎫 {c['code']}：减¥{c['discount']}（满¥{c['min_spend']}）过期{c['expire']}"
            for c in coupons
        )
        return f"🎁 用户 {user_id} 的优惠券：\n{detail}"
    return f"🎁 用户 {user_id} 暂无优惠券"


def tool_query_product(product_name: str) -> str:
    """查询产品信息"""
    if product_name in PRODUCT_KB:
        info = PRODUCT_KB[product_name]
        return f"📱 {product_name}：¥{info['price']} | 保修{info['warranty']} | {info['return_policy']}"
    return "📱 请问您想了解哪款产品？"


def tool_escalate() -> str:
    """转人工客服"""
    return "👤 已转接人工客服（模拟：工单已创建，预计30分钟内回复）"


# Tool 注册表（模拟 Agents SDK 的 tools 列表）
TOOLS = [
    {
        "name": "query_order",
        "description": "查询订单状态，需要提供订单号",
        "handler": tool_query_order,
    },
    {
        "name": "query_refund",
        "description": "查询退款政策，需要提供订单号",
        "handler": tool_query_refund,
    },
    {
        "name": "query_logistics",
        "description": "查询物流信息，需要提供物流单号",
        "handler": tool_query_logistics,
    },
    {
        "name": "query_coupons",
        "description": "查询用户优惠券，需要提供用户ID",
        "handler": tool_query_coupons,
    },
    {
        "name": "query_product",
        "description": "查询产品信息，需要提供产品名称",
        "handler": tool_query_product,
    },
    {
        "name": "escalate",
        "description": "转人工客服",
        "handler": tool_escalate,
    },
]


# ============================================================
# Agent 意图识别（模拟 LLM）
# ============================================================

def agent_classify_intent(user_input: str) -> dict:
    """
    模拟 LLM 意图识别。

    与 workflow 版的关键区别：
    - Workflow: 确定性关键词匹配
    - Agent: LLM 理解语义，能处理模糊表述

    模拟版：用更宽松的规则 + 模拟 LLM 延迟
    """
    q = user_input.lower()

    # 模拟 LLM 调用
    llm_result = simulate_llm_call(
        f"识别意图: {user_input}",
        estimated_tokens=150,  # prompt + response tokens
    )

    # Agent 版的"优势"：能理解更模糊的表述
    intent = "greeting"
    tool_name = None
    tool_args = {}

    # 订单相关
    if any(k in q for k in ["订单", "状态", "发货", "买了"]):
        intent = "order_query"
        tool_name = "query_order"
        m = re.search(r"ORD\d+", user_input)
        tool_args = {"order_id": m.group(0) if m else "ORD20260417001"}

    # 物流
    elif any(k in q for k in ["物流", "快递", "到哪", "包裹", "什么时候到", "送到"]):
        intent = "logistics"
        tool_name = "query_logistics"
        m = re.search(r"(SF|JD)\d+", user_input)
        if m:
            tool_args = {"tracking_number": m.group(0)}
        else:
            # Agent 模式的优势：能从订单号关联物流
            m2 = re.search(r"ORD\d+", user_input)
            if m2 and m2.group(0) in ORDERS_DB:
                parts = ORDERS_DB[m2.group(0)]["logistics"].split()
                tool_args = {"tracking_number": parts[1] if len(parts) > 1 else parts[0]}
            else:
                tool_args = {"tracking_number": "SF1234567890"}

    # 退款
    elif any(k in q for k in ["退款", "退货", "退钱", "能退", "退换", "退款政策"]):
        intent = "refund"
        tool_name = "query_refund"
        m = re.search(r"ORD\d+", user_input)
        tool_args = {"order_id": m.group(0) if m else "ORD20260417001"}

    # 优惠券
    elif any(k in q for k in ["优惠", "券", "折扣", "coupon"]):
        intent = "coupon"
        tool_name = "query_coupons"
        m = re.search(r"USER\d+", user_input)
        tool_args = {"user_id": m.group(0) if m else "USER001"}

    # 产品
    elif any(k in q for k in ["多少钱", "价格", "保修", "产品", "手机", "耳机", "电脑"]):
        intent = "product"
        tool_name = "query_product"
        # Agent 模式：能理解"这个手机"指 iPhone
        for name in PRODUCT_KB:
            if name.lower() in q:
                tool_args = {"product_name": name}
                break
        else:
            # 模糊匹配：Agent 的优势
            if "手机" in q:
                tool_args = {"product_name": "iPhone 15 Pro"}
            elif "耳机" in q:
                tool_args = {"product_name": "AirPods Pro 2"}
            elif "电脑" in q or "笔记本" in q:
                tool_args = {"product_name": "MacBook Air M2"}
            else:
                tool_args = {"product_name": ""}

    # 投诉/转人工
    elif any(k in q for k in ["投诉", "人工", "态度"]):
        intent = "escalate"
        tool_name = "escalate"
        tool_args = {}

    return {
        "intent": intent,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "llm_metrics": llm_result,
    }


# ============================================================
# Agent 执行循环
# ============================================================

def run_agent(user_input: str) -> dict:
    """
    Agent 执行流程（模拟 OpenAI Agents SDK 的 Runner.run）：
    1. 第 1 次 LLM 调用：理解意图 + 选择 tool
    2. 执行 tool
    3. 第 2 次 LLM 调用：基于 tool 结果生成最终回复

    返回：{response, metrics}
    """
    total_metrics = {
        "token_count": 0,
        "latency_ms": 0.0,
        "nodes_visited": 0,
        "llm_calls": 0,
    }
    steps = []

    # Step 1: 意图识别（第 1 次 LLM 调用）
    t0 = time.time()
    intent_result = agent_classify_intent(user_input)
    total_metrics["token_count"] += intent_result["llm_metrics"]["tokens_used"]
    total_metrics["llm_calls"] += 1
    steps.append(f"LLM意图识别 → {intent_result['intent']}")

    # Step 2: 执行 tool
    tool_name = intent_result["tool_name"]
    tool_args = intent_result["tool_args"]

    if tool_name:
        tool_def = next((t for t in TOOLS if t["name"] == tool_name), None)
        if tool_def:
            tool_result = tool_def["handler"](**tool_args)
            steps.append(f"Tool({tool_name}) → 完成")
        else:
            tool_result = "❌ 未找到对应工具"
            steps.append(f"Tool({tool_name}) → 未找到")
    else:
        # 不需要调 tool（问候等）
        tool_result = "👋 您好！我是智能客服。可以问我订单/退款/物流/优惠券/产品信息。"
        steps.append("直接回复（无tool调用）")

    # Step 3: 生成最终回复（第 2 次 LLM 调用）
    llm_result2 = simulate_llm_call(
        f"基于工具结果生成回复: {tool_result}",
        estimated_tokens=100,
    )
    total_metrics["token_count"] += llm_result2["tokens_used"]
    total_metrics["llm_calls"] += 1
    steps.append("LLM生成回复 → 完成")

    # Agent 模式的"不确定性"：10% 概率多做一次 LLM 调用（自我纠错）
    if random.random() < 0.1:
        llm_result3 = simulate_llm_call("自我纠错检查", estimated_tokens=80)
        total_metrics["token_count"] += llm_result3["tokens_used"]
        total_metrics["llm_calls"] += 1
        steps.append("LLM自我纠错 → 完成")

    total_metrics["latency_ms"] = (time.time() - t0) * 1000
    total_metrics["nodes_visited"] = len(steps)

    response = f"{tool_result}\n\n[流程] {' → '.join(steps)}"
    return {"response": response, "metrics": total_metrics}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    test_cases = [
        "帮我查一下订单 ORD20260417001 的状态",
        "退款需要什么条件？",
        "帮我查一下物流 SF1234567890",
        "USER001 有哪些优惠券？",
        "iPhone 15 Pro 多少钱？",
        "我要投诉！转人工！",
        "你好",
        "已发货的订单能退款吗？订单 ORD20260417001",
        # 模糊意图（Agent 版的优势）
        "我的东西什么时候到",
        "这个手机能退吗",
    ]

    total_latency = 0
    total_tokens = 0
    for i, q in enumerate(test_cases, 1):
        result = run_agent(q)
        m = result["metrics"]
        total_latency += m["latency_ms"]
        total_tokens += m["token_count"]
        print(f"--- 测试 {i}: {q}")
        print(f"    延迟: {m['latency_ms']:.0f}ms | LLM调用: {m['llm_calls']} | Token: {m['token_count']}")
        print(f"    回复: {result['response'][:100]}...")
        print()

    print(f"📊 总延迟: {total_latency:.0f}ms | 平均: {total_latency/len(test_cases):.0f}ms/条")
    print(f"📊 总Token: {total_tokens} | 平均: {total_tokens/len(test_cases)}/条")
