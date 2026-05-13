"""
Day 3-4: 把 month01 电商客服 Agent 翻译成 LangGraph

学习目标：
1. 把 Tool 路由逻辑翻译成 StateGraph
2. 用条件边（conditional edges）实现意图分支
3. 理解 graph 思维 vs agent 脚本思维的差异

对比 month01 vs month02：
- month01 (Agents SDK): Agent + Tools → LLM 自动决定调用哪个 tool
- month02 (LangGraph): StateGraph + Nodes + Edges → 我们显式定义流程
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END


# ============================================================
# 模拟数据库（复用 month01 的数据）
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
# 1. 定义 State
# ============================================================

class SupportState(TypedDict):
    """
    客服对话状态：
    - user_input: 用户输入
    - user_id: 用户 ID（从输入中提取或默认）
    - intent: 意图分类结果
    - order_id: 从输入中提取的订单号
    - tracking_number: 从输入中提取的物流单号
    - response: 最终回复
    - history: 对话历史
    """
    user_input: str
    user_id: str
    intent: str
    order_id: Optional[str]
    tracking_number: Optional[str]
    response: str
    history: list[str]


# ============================================================
# 2. 辅助函数：意图识别 & 信息提取
# ============================================================

def classify_intent(user_input: str) -> str:
    """
    根据关键词判断用户意图。
    实际项目中这里应该调 LLM，这里用规则做演示。
    """
    q = user_input.lower()

    # 优先级：越具体的意图越先判断
    if any(k in q for k in ["投诉", "举报", "太差", "态度", "转人工"]):
        return "escalate"
    if any(k in q for k in ["物流", "快递", "到哪了", "包裹"]):
        return "logistics"
    if any(k in q for k in ["退款", "退货", "退钱"]):
        return "refund"
    if any(k in q for k in ["优惠", "券", "折扣", "coupon"]):
        return "coupon"
    if any(k in q for k in ["保修", "介绍", "什么价格", "多少钱", "产品"]):
        return "product"
    if any(k in q for k in ["订单", "状态", "发货了吗", "发货没"]):
        return "order_query"
    if any(k in q for k in ["优惠", "券", "折扣", "coupon"]):
        return "coupon"
    return "greeting"


def extract_order_id(user_input: str) -> Optional[str]:
    """提取订单号：ORD 开头的数字串"""
    import re
    match = re.search(r"ORD\d+", user_input)
    return match.group(0) if match else None


def extract_tracking_number(user_input: str) -> Optional[str]:
    """提取物流单号：SF/JD 开头的数字串"""
    import re
    match = re.search(r"(SF|JD)\d+", user_input)
    return match.group(0) if match else None


def extract_user_id(user_input: str) -> str:
    """提取用户 ID"""
    import re
    match = re.search(r"USER\d+", user_input)
    return match.group(0) if match else "USER001"


# ============================================================
# 3. 定义意图路由节点
# ============================================================

def intent_router(state: SupportState) -> dict:
    """
    节点 1：意图识别
    分析用户输入，判断意图并提取关键信息
    """
    intent = classify_intent(state["user_input"])
    order_id = extract_order_id(state["user_input"])
    tracking = extract_tracking_number(state["user_input"])
    user_id = extract_user_id(state["user_input"])

    history = state["history"].copy()
    history.append(f"📋 意图识别 → {intent}")

    return {
        "intent": intent,
        "order_id": order_id,
        "tracking_number": tracking,
        "user_id": user_id,
        "history": history,
    }


def order_query_node(state: SupportState) -> dict:
    """节点 2a：订单查询"""
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if order:
        resp = (
            f"📦 订单 {oid}：\n"
            f"  商品：{order['product']}\n"
            f"  状态：{order['status']}\n"
            f"  金额：¥{order['amount']:.2f}\n"
            f"  物流：{order['logistics']}"
        )
    else:
        resp = f"❌ 未找到订单 {oid}"
    history = state["history"].copy()
    history.append(f"📦 查询订单 → {'成功' if order else '失败'}")
    return {"response": resp, "history": history}


def refund_node(state: SupportState) -> dict:
    """节点 2b：退款处理"""
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if not order:
        resp = f"❌ 未找到订单 {oid}"
    else:
        rule = REFUND_RULES.get(order["status"], {})
        allowed = rule.get("allowed", False)
        resp = (
            f"💰 退款政策（订单 {oid}）：\n"
            f"  状态：{order['status']}\n"
            f"  可退款：{'是' if allowed else '否'}\n"
            f"  到账时间：{rule.get('days', '未知')}\n"
            f"  手续费：{rule.get('fee', '未知')}"
        )
    history = state["history"].copy()
    history.append(f"💰 查询退款政策")
    return {"response": resp, "history": history}


def logistics_node(state: SupportState) -> dict:
    """节点 2c：物流查询"""
    # 优先从输入提取，其次从订单关联
    tracking = state.get("tracking_number")
    if not tracking and state.get("order_id"):
        order = ORDERS_DB.get(state["order_id"])
        if order:
            parts = order["logistics"].split()
            tracking = parts[1] if len(parts) > 1 else order["logistics"]

    if tracking and tracking in LOGISTICS_DB:
        logs = LOGISTICS_DB[tracking]
        detail = "\n".join(f"  {l['time']} - {l['status']}" for l in logs)
        resp = f"🚚 物流 {tracking}：\n{detail}"
    elif tracking:
        resp = f"❌ 未找到物流 {tracking}"
    else:
        resp = "❌ 未找到物流单号，请提供订单号或物流单号"
    history = state["history"].copy()
    history.append(f"🚚 查询物流")
    return {"response": resp, "history": history}


def coupon_node(state: SupportState) -> dict:
    """节点 2d：优惠券查询"""
    uid = state.get("user_id", "USER001")
    coupons = COUPONS_DB.get(uid, [])
    if coupons:
        detail = "\n".join(
            f"  🎫 {c['code']}：减 ¥{c['discount']}（满 ¥{c['min_spend']}）\n"
            f"     过期：{c['expire']}"
            for c in coupons
        )
        resp = f"🎁 用户 {uid} 的优惠券：\n{detail}"
    else:
        resp = f"🎁 用户 {uid} 暂无优惠券"
    history = state["history"].copy()
    history.append(f"🎁 查询优惠券")
    return {"response": resp, "history": history}


def product_node(state: SupportState) -> dict:
    """节点 2e：产品咨询"""
    q = state["user_input"].lower()
    matched = [name for name in PRODUCT_KB if name.lower() in q]
    if matched:
        info = PRODUCT_KB[matched[0]]
        resp = (
            f"📱 {matched[0]}：\n"
            f"  价格：¥{info['price']}\n"
            f"  保修：{info['warranty']}\n"
            f"  退换：{info['return_policy']}"
        )
    else:
        resp = "📱 请问您想了解哪款产品？目前支持：iPhone 15 Pro, AirPods Pro 2, MacBook Air M2"
    history = state["history"].copy()
    history.append(f"📱 产品咨询")
    return {"response": resp, "history": history}


def escalate_node(state: SupportState) -> dict:
    """节点 2f：转人工"""
    resp = "👤 已为您转接人工客服，请稍候...\n（模拟：工单已创建，预计 30 分钟内回复）"
    history = state["history"].copy()
    history.append(f"👤 转人工客服")
    return {"response": resp, "history": history}


def greeting_node(state: SupportState) -> dict:
    """节点 2g：问候"""
    resp = "👋 您好！我是智能客服助手。\n您可以问我：\n  • 订单状态：查一下订单 ORD20260417001\n  • 退款政策：已发货能退款吗\n  • 物流查询：帮我查物流 SF1234567890\n  • 优惠券：USER001 有哪些优惠券\n  • 产品咨询：iPhone 15 Pro 多少钱"
    history = state["history"].copy()
    history.append(f"👋 问候回复")
    return {"response": resp, "history": history}


# ============================================================
# 4. 条件路由函数
# ============================================================

def route_by_intent(state: SupportState) -> str:
    """
    条件路由：根据 intent 决定下一步走哪个节点
    这是 LangGraph 的核心——用条件边替代 LLM 的自动 tool 选择
    """
    mapping = {
        "order_query": "order_query",
        "refund": "refund",
        "logistics": "logistics",
        "coupon": "coupon",
        "product": "product",
        "escalate": "escalate",
        "greeting": "greeting",
    }
    return mapping.get(state["intent"], "greeting")


# ============================================================
# 5. 汇总节点
# ============================================================

def summarize_node(state: SupportState) -> dict:
    """
    最终节点：汇总整个流程
    """
    history = state["history"].copy()
    history.append("✅ 处理完成")
    flow = " → ".join(h.split(" ")[0] if " " in h else h for h in history)

    final = (
        f"{state['response']}\n\n"
        f"─── 处理流程 ───\n"
        + "\n".join(f"  {i+1}. {h}" for i, h in enumerate(history))
    )
    return {"response": final, "history": history}


# ============================================================
# 6. 构建 Graph
# ============================================================

def build_support_graph():
    """
    构建电商客服 StateGraph

    流程：
    __start__ → intent_router → [条件路由] → 各业务节点 → summarize → __end__
    """
    graph = StateGraph(SupportState)

    # 添加所有节点
    graph.add_node("intent_router", intent_router)
    graph.add_node("order_query", order_query_node)
    graph.add_node("refund", refund_node)
    graph.add_node("logistics", logistics_node)
    graph.add_node("coupon", coupon_node)
    graph.add_node("product", product_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("greeting", greeting_node)
    graph.add_node("summarize", summarize_node)

    # 入口
    graph.set_entry_point("intent_router")

    # 条件路由：intent_router 根据意图分发到不同节点
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "order_query": "order_query",
            "refund": "refund",
            "logistics": "logistics",
            "coupon": "coupon",
            "product": "product",
            "escalate": "escalate",
            "greeting": "greeting",
        },
    )

    # 所有业务节点完成后汇总
    for node_name in ["order_query", "refund", "logistics", "coupon", "product", "escalate", "greeting"]:
        graph.add_edge(node_name, "summarize")

    graph.add_edge("summarize", END)

    return graph.compile()


# ============================================================
# 7. 运行测试
# ============================================================

def run_tests():
    """运行测试用例"""
    app = build_support_graph()

    # 查看 graph 结构
    print("=" * 60)
    print("📊 客服 Graph 结构")
    print("=" * 60)
    print(app.get_graph().draw_mermaid())
    print()

    test_cases = [
        "帮我查一下订单 ORD20260417001 的状态",
        "退款需要什么条件？",
        "帮我查一下物流 SF1234567890",
        "USER001 有哪些优惠券？",
        "iPhone 15 Pro 多少钱？保修政策是什么？",
        "我要投诉！服务态度太差了！转人工！",
        "你好",
        "已发货的订单能退款吗？订单 ORD20260417001",
    ]

    for i, question in enumerate(test_cases, 1):
        print("=" * 60)
        print(f"🧪 测试 {i}：{question}")
        print("=" * 60)
        state = {
            "user_input": question,
            "user_id": "USER001",
            "intent": "",
            "order_id": None,
            "tracking_number": None,
            "response": "",
            "history": ["🚀 收到用户输入"],
        }
        result = app.invoke(state)
        print(result["response"])
        print()


if __name__ == "__main__":
    run_tests()
