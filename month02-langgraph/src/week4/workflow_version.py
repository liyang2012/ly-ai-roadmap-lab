"""
Week 4: Workflow 版 - 纯规则路由的 LangGraph 实现

学习目标：
1. 用 LangGraph StateGraph 实现确定性路由
2. 意图识别用关键词规则（不依赖 LLM）
3. 每次执行路径完全确定，可追踪、可复现

特点：
- ✅ 确定性：相同输入 → 相同路径
- ✅ 可追踪：history 记录每一步
- ✅ 零 LLM 调用：纯规则，token 消耗为 0
- ✅ 延迟极低：毫秒级响应
- ❌ 灵活性差：关键词覆盖不到的意图走 fallback
"""

import re
import time
import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END


# ============================================================
# 模拟数据库（Week 1 同款，保证公平对比）
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
# State
# ============================================================

class WorkflowState(TypedDict):
    user_input: str
    user_id: str
    intent: str
    order_id: Optional[str]
    tracking_number: Optional[str]
    response: str
    history: list[str]
    # 对比实验专用
    metrics: dict  # {token_count, latency_ms, nodes_visited, llm_calls}


# ============================================================
# 意图识别（纯规则）
# ============================================================

def classify_intent_rules(user_input: str) -> str:
    """关键词规则意图分类"""
    q = user_input.lower()

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
    return "greeting"


def extract_info(user_input: str) -> dict:
    """提取关键信息"""
    order_id = None
    tracking = None
    user_id = "USER001"

    m = re.search(r"ORD\d+", user_input)
    if m:
        order_id = m.group(0)
    m = re.search(r"(SF|JD)\d+", user_input)
    if m:
        tracking = m.group(0)
    m = re.search(r"USER\d+", user_input)
    if m:
        user_id = m.group(0)

    return {"order_id": order_id, "tracking_number": tracking, "user_id": user_id}


# ============================================================
# 节点
# ============================================================

def intent_router_node(state: WorkflowState) -> dict:
    t0 = time.time()
    intent = classify_intent_rules(state["user_input"])
    info = extract_info(state["user_input"])

    history = state["history"] + [f"intent_router → {intent}"]
    metrics = state["metrics"].copy()
    metrics["nodes_visited"] += 1
    metrics["latency_ms"] += (time.time() - t0) * 1000

    return {
        "intent": intent,
        "order_id": info["order_id"],
        "tracking_number": info["tracking_number"],
        "user_id": info["user_id"],
        "history": history,
        "metrics": metrics,
    }


def make_business_node(name: str, handler):
    """工厂函数：创建业务节点"""
    def node(state: WorkflowState) -> dict:
        t0 = time.time()
        resp = handler(state)

        history = state["history"] + [f"{name} → 完成"]
        metrics = state["metrics"].copy()
        metrics["nodes_visited"] += 1
        metrics["latency_ms"] += (time.time() - t0) * 1000

        return {"response": resp, "history": history, "metrics": metrics}
    return node


def handle_order_query(state: WorkflowState) -> str:
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if order:
        return (
            f"📦 订单 {oid}：\n"
            f"  商品：{order['product']}\n"
            f"  状态：{order['status']}\n"
            f"  金额：¥{order['amount']:.2f}\n"
            f"  物流：{order['logistics']}"
        )
    return f"❌ 未找到订单 {oid}"


def handle_refund(state: WorkflowState) -> str:
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if not order:
        return f"❌ 未找到订单 {oid}"
    rule = REFUND_RULES.get(order["status"], {})
    return (
        f"💰 退款政策（订单 {oid}）：\n"
        f"  可退款：{'是' if rule.get('allowed') else '否'}\n"
        f"  到账：{rule.get('days', '未知')}\n"
        f"  手续费：{rule.get('fee', '未知')}"
    )


def handle_logistics(state: WorkflowState) -> str:
    tracking = state.get("tracking_number")
    if not tracking and state.get("order_id"):
        order = ORDERS_DB.get(state["order_id"])
        if order:
            parts = order["logistics"].split()
            tracking = parts[1] if len(parts) > 1 else order["logistics"]

    if tracking and tracking in LOGISTICS_DB:
        logs = LOGISTICS_DB[tracking]
        detail = "\n".join(f"  {l['time']} - {l['status']}" for l in logs)
        return f"🚚 物流 {tracking}：\n{detail}"
    return "❌ 未找到物流信息"


def handle_coupon(state: WorkflowState) -> str:
    uid = state.get("user_id", "USER001")
    coupons = COUPONS_DB.get(uid, [])
    if coupons:
        detail = "\n".join(
            f"  🎫 {c['code']}：减¥{c['discount']}（满¥{c['min_spend']}）过期{c['expire']}"
            for c in coupons
        )
        return f"🎁 用户 {uid} 的优惠券：\n{detail}"
    return f"🎁 用户 {uid} 暂无优惠券"


def handle_product(state: WorkflowState) -> str:
    q = state["user_input"].lower()
    matched = [name for name in PRODUCT_KB if name.lower() in q]
    if matched:
        info = PRODUCT_KB[matched[0]]
        return f"📱 {matched[0]}：¥{info['price']} | 保修{info['warranty']} | {info['return_policy']}"
    return "📱 请问您想了解哪款产品？"


def handle_escalate(state: WorkflowState) -> str:
    return "👤 已转接人工客服（模拟：工单已创建，预计30分钟内回复）"


def handle_greeting(state: WorkflowState) -> str:
    return "👋 您好！我是智能客服。可以问我订单/退款/物流/优惠券/产品信息。"


def finalize_node(state: WorkflowState) -> dict:
    t0 = time.time()
    history = state["history"] + ["✅ 完成"]
    metrics = state["metrics"].copy()
    metrics["nodes_visited"] += 1
    metrics["latency_ms"] += (time.time() - t0) * 1000

    flow = " → ".join(state["history"])
    final = f"{state['response']}\n\n[流程] {flow}"
    return {"response": final, "history": history, "metrics": metrics}


# ============================================================
# 路由
# ============================================================

def route_by_intent(state: WorkflowState) -> str:
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
# 构建 Graph
# ============================================================

def build_workflow_graph():
    graph = StateGraph(WorkflowState)

    graph.add_node("intent_router", intent_router_node)
    graph.add_node("order_query", make_business_node("order_query", handle_order_query))
    graph.add_node("refund", make_business_node("refund", handle_refund))
    graph.add_node("logistics", make_business_node("logistics", handle_logistics))
    graph.add_node("coupon", make_business_node("coupon", handle_coupon))
    graph.add_node("product", make_business_node("product", handle_product))
    graph.add_node("escalate", make_business_node("escalate", handle_escalate))
    graph.add_node("greeting", make_business_node("greeting", handle_greeting))
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("intent_router")

    graph.add_conditional_edges(
        "intent_router", route_by_intent,
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

    for n in ["order_query", "refund", "logistics", "coupon", "product", "escalate", "greeting"]:
        graph.add_edge(n, "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# ============================================================
# 运行单个测试用例（返回 metrics）
# ============================================================

def run_single(question: str) -> dict:
    """运行单个测试，返回 {response, metrics}"""
    app = build_workflow_graph()
    initial_state = {
        "user_input": question,
        "user_id": "USER001",
        "intent": "",
        "order_id": None,
        "tracking_number": None,
        "response": "",
        "history": [],
        "metrics": {
            "token_count": 0,       # 规则版不需要 token
            "latency_ms": 0.0,
            "nodes_visited": 0,
            "llm_calls": 0,
        },
    }
    result = app.invoke(initial_state)
    return {
        "response": result["response"],
        "metrics": result["metrics"],
    }


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    app = build_workflow_graph()
    print("📊 Workflow Graph 结构 (Mermaid):")
    print(app.get_graph().draw_mermaid())
    print()

    test_cases = [
        "帮我查一下订单 ORD20260417001 的状态",
        "退款需要什么条件？",
        "帮我查一下物流 SF1234567890",
        "USER001 有哪些优惠券？",
        "iPhone 15 Pro 多少钱？",
        "我要投诉！转人工！",
        "你好",
        "已发货的订单能退款吗？订单 ORD20260417001",
        # 模糊意图（Workflow 版的弱点）
        "我的东西什么时候到",
        "这个手机能退吗",
    ]

    total_latency = 0
    for i, q in enumerate(test_cases, 1):
        result = run_single(q)
        m = result["metrics"]
        total_latency += m["latency_ms"]
        print(f"--- 测试 {i}: {q}")
        print(f"    延迟: {m['latency_ms']:.2f}ms | 节点: {m['nodes_visited']} | Token: {m['token_count']}")
        print(f"    回复: {result['response'][:100]}...")
        print()

    print(f"📊 总延迟: {total_latency:.2f}ms | 平均: {total_latency/len(test_cases):.2f}ms/条")
