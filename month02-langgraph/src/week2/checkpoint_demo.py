"""
Week 2: LangGraph Persistence / Checkpoints / Human-in-the-Loop

学习目标：
1. MemorySaver — 让 Graph "记住" 状态，支持多轮对话
2. Thread ID — 区分不同用户/会话的上下文
3. Time Travel — 查看历史 checkpoint，回滚到之前的状态
4. Human-in-the-loop — 在关键步骤暂停，等待人工审核/修改
5. Interrupt 实战 — 退款审批需要人工确认

对比 Week 1 的差异：
- Week 1: graph.invoke(state) → 一次性运行，无记忆
- Week 2: graph.invoke(state, config={"configurable": {"thread_id": "xxx"}}) → 支持多轮 + 持久化
"""

from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================
# 复用 Week 1 的模拟数据库
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

REFUND_RULES = {
    "未发货": {"allowed": True, "days": "1-3 工作日到账", "fee": "无手续费"},
    "已发货": {"allowed": True, "days": "拒收或退货后", "fee": "运费自理"},
    "已签收": {"allowed": True, "days": "7 天内", "fee": "买家承担运费"},
}

PRODUCT_KB = {
    "iPhone 15 Pro": {"price": 7999, "warranty": "1 年", "return_policy": "7 天无理由"},
    "AirPods Pro 2": {"price": 1899, "warranty": "1 年", "return_policy": "7 天无理由"},
    "MacBook Air M2": {"price": 9499, "warranty": "1 年", "return_policy": "14 天无理由"},
}


# ============================================================
# 1. 定义 State（扩展 Week 1）
# ============================================================

class SupportState(TypedDict, total=False):
    """
    扩展状态：
    - messages: 对话历史（多轮支持）
    - user_input: 用户当前输入
    - user_id: 用户 ID
    - intent: 意图分类
    - order_id: 订单号
    - response: 当前回复
    - approved: 退款是否被批准（人工审核后设置）
    """
    messages: list[dict]
    user_input: str
    user_id: str
    intent: str
    order_id: Optional[str]
    response: str
    approved: bool


# ============================================================
# 2. 节点定义
# ============================================================

import re


def classify_intent(text: str) -> str:
    q = text.lower()
    if any(k in q for k in ["投诉", "举报", "太差", "转人工"]):
        return "escalate"
    if any(k in q for k in ["物流", "快递", "到哪了", "包裹"]):
        return "logistics"
    if any(k in q for k in ["退款", "退货", "退钱"]):
        return "refund"
    if any(k in q for k in ["订单", "状态", "发货了吗"]):
        return "order_query"
    if any(k in q for k in ["优惠", "券", "折扣"]):
        return "coupon"
    if any(k in q for k in ["保修", "介绍", "多少钱", "产品"]):
        return "product"
    return "greeting"


def extract_order_id(text: str) -> Optional[str]:
    match = re.search(r"ORD\d+", text)
    return match.group(0) if match else None


# ---------- 意图识别节点 ----------

def intent_node(state: SupportState) -> dict:
    """节点 1：识别意图，提取关键信息"""
    intent = classify_intent(state["user_input"])
    order_id = extract_order_id(state["user_input"])
    messages = state.get("messages", [])
    messages.append({"role": "user", "content": state["user_input"]})
    messages.append({"role": "system", "content": f"意图: {intent}"})
    return {
        "intent": intent,
        "order_id": order_id,
        "messages": messages,
    }


# ---------- 业务节点 ----------

def order_query_node(state: SupportState) -> dict:
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if order:
        resp = (
            f"📦 订单 {oid}\n"
            f"  商品：{order['product']}\n"
            f"  状态：{order['status']}\n"
            f"  金额：¥{order['amount']:.2f}"
        )
    else:
        resp = f"❌ 未找到订单 {oid}"
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": resp})
    return {"response": resp, "messages": messages}


def refund_node(state: SupportState) -> dict:
    """
    退款节点：检查退款政策，但 **不直接批准**。
    设置 interrupt_before 让 graph 在此暂停，等待人工审核。
    """
    oid = state.get("order_id") or "ORD20260417001"
    order = ORDERS_DB.get(oid)
    if not order:
        resp = f"❌ 未找到订单 {oid}"
    else:
        rule = REFUND_RULES.get(order["status"], {})
        resp = (
            f"💰 退款审核请求\n"
            f"  订单：{oid}\n"
            f"  商品：{order['product']}\n"
            f"  金额：¥{order['amount']:.2f}\n"
            f"  状态：{order['status']}\n"
            f"  政策：{'可退款' if rule.get('allowed') else '不可退款'}\n"
            f"  手续费：{rule.get('fee', '未知')}\n"
            f"  ⏸️ 等待人工审核..."
        )
    messages = state.get("messages", [])
    messages.append({"role": "system", "content": f"退款审核待批准: {oid}"})
    return {"response": resp, "messages": messages}


def approve_refund_node(state: SupportState) -> dict:
    """节点：人工审核通过后的处理"""
    if state.get("approved", False):
        resp = "✅ 退款已批准，1-3 工作日到账。"
    else:
        resp = "❌ 退款申请被拒绝。"
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": resp})
    return {"response": resp, "messages": messages}


def greeting_node(state: SupportState) -> dict:
    resp = "👋 你好！我是智能客服。可以问我订单、退款、物流等问题。"
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": resp})
    return {"response": resp, "messages": messages}


def fallback_node(state: SupportState) -> dict:
    resp = "🤔 我不太理解，请换个说法。"
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": resp})
    return {"response": resp, "messages": messages}


# ---------- 路由 ----------

def route_intent(state: SupportState) -> str:
    mapping = {
        "order_query": "order_query",
        "refund": "refund",
        "greeting": "greeting",
    }
    return mapping.get(state.get("intent", ""), "fallback")


# ============================================================
# 3. 构建带 Checkpoint 的 Graph
# ============================================================

def build_checkpoint_graph():
    """
    构建一个带持久化的客服 Graph。
    退款流程需要人工审核：intent_router → refund → ⏸️ interrupt → approve_refund → END
    """
    checkpointer = MemorySaver()

    graph = StateGraph(SupportState)

    graph.add_node("intent_router", intent_node)
    graph.add_node("order_query", order_query_node)
    graph.add_node("refund", refund_node)
    graph.add_node("approve_refund", approve_refund_node)
    graph.add_node("greeting", greeting_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("intent_router")

    graph.add_conditional_edges(
        "intent_router",
        route_intent,
        {
            "order_query": "order_query",
            "refund": "refund",
            "greeting": "greeting",
            "fallback": "fallback",
        },
    )

    # refund → approve_refund → END
    graph.add_edge("refund", "approve_refund")
    graph.add_edge("order_query", END)
    graph.add_edge("greeting", END)
    graph.add_edge("fallback", END)
    graph.add_edge("approve_refund", END)

    # ⭐ 编译时传入 checkpointer + interrupt_before
    # interrupt_before=["approve_refund"] 意味着：
    #   在执行 approve_refund 节点之前暂停，等待人工决策
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approve_refund"],
    )

    return app


# ============================================================
# 4. 演示：三大核心功能
# ============================================================

def demo_1_multiturn():
    """
    演示 1：多轮对话 + Thread ID
    
    关键点：
    - 同一个 thread_id 的不同 invoke 调用共享状态
    - 相当于给 Graph "加了记忆"
    """
    print("\n" + "=" * 60)
    print("🎯 演示 1：多轮对话（MemorySaver + Thread ID）")
    print("=" * 60)

    app = build_checkpoint_graph()
    thread_id = "user-alice-001"

    config = {"configurable": {"thread_id": thread_id}}

    # 第 1 轮：打招呼
    print("\n--- 第 1 轮 ---")
    state1 = {"messages": [], "user_input": "你好", "user_id": "USER001"}
    result1 = app.invoke(state1, config)
    print(f"用户: 你好")
    print(f"助手: {result1['response']}")

    # 第 2 轮：查订单（同一个 thread_id，Graph "记得" 上一轮）
    print("\n--- 第 2 轮 ---")
    state2 = {"user_input": "帮我查一下订单 ORD20260417001"}
    result2 = app.invoke(state2, config)
    print(f"用户: 帮我查一下订单 ORD20260417001")
    print(f"助手: {result2['response']}")

    # 查看完整的对话历史
    print("\n--- 📜 完整对话历史 ---")
    for msg in result2["messages"]:
        role = msg["role"]
        icon = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(role, "")
        print(f"  {icon} {msg['content']}")


def demo_2_time_travel():
    """
    演示 2：Time Travel（时间旅行）
    
    关键点：
    - 每个 checkpoint 都有唯一的 checkpoint_id
    - 可以用 aget_state / get_state 查看历史状态
    - 可以回滚到任意 checkpoint
    """
    print("\n" + "=" * 60)
    print("🕰️  演示 2：Time Travel（查看历史 + 回滚）")
    print("=" * 60)

    app = build_checkpoint_graph()
    thread_id = "user-bob-002"
    config = {"configurable": {"thread_id": thread_id}}

    # 第 1 轮
    print("\n--- 第 1 轮：打招呼 ---")
    r1 = app.invoke({"messages": [], "user_input": "你好", "user_id": "USER001"}, config)
    print(f"助手: {r1['response']}")

    # 第 2 轮
    print("\n--- 第 2 轮：查订单 ---")
    r2 = app.invoke({"user_input": "查订单 ORD20260417003"}, config)
    print(f"助手: {r2['response']}")

    # 列出所有 checkpoint
    print("\n--- 📋 所有 Checkpoint ---")
    # 使用 get_state_history 获取 checkpoint 历史
    history = list(app.get_state_history(config))
    print(f"  共 {len(history)} 个 checkpoint")
    for i, cp in enumerate(history):
        # 从 config 中获取 checkpoint_id
        cp_id = cp.config.get('configurable', {}).get('checkpoint_id', 'N/A') if cp.config else 'N/A'
        print(f"  [{i}] {cp_id[:20] if cp_id != 'N/A' else 'N/A'}... | "
              f"intent={cp.values.get('intent', '?')} | "
              f"response={cp.values.get('response', '?')[:30] if cp.values.get('response') else 'N/A'}...")

    # 回滚到第 1 个 checkpoint（打招呼之后）
    print("\n--- 🔄 回滚到初始状态 ---")
    if len(history) > 1:
        first_cp = history[-1]  # 最早的那个
        cp_id = first_cp.config.get('configurable', {}).get('checkpoint_id', 'N/A') if first_cp.config else 'N/A'
        print(f"  回到 checkpoint: {cp_id[:20] if cp_id != 'N/A' else 'N/A'}...")
        print(f"  当时的意图: {first_cp.values.get('intent', '?')}")
        print(f"  当时的回复: {first_cp.values.get('response', '?')}")

        # 从那个 checkpoint 继续执行不同分支
        print("\n  从该点执行不同操作：查另一个订单...")
        fork_config = {
            "configurable": {
                "thread_id": "user-bob-002-fork",
            }
        }
        # 实际上要从 checkpoint 恢复后再 invoke
        # 这里展示概念，实际回滚需要：
        # app.update_state(first_cp.config, {"user_input": "新输入"})
        print("  (概念演示：实际使用需要 app.update_state + invoke)")


def demo_3_human_in_the_loop():
    """
    演示 3：Human-in-the-loop（人工审核）
    
    关键点：
    - interrupt_before=["approve_refund"] 让 graph 在退款批准前暂停
    - 人工检查后，用 command 决定是否继续
    - 这是生产环境审批流的标准模式
    """
    print("\n" + "=" * 60)
    print("👤 演示 3：Human-in-the-loop（退款人工审核）")
    print("=" * 60)

    app = build_checkpoint_graph()
    thread_id = "refund-approval-001"
    config = {"configurable": {"thread_id": thread_id}}

    # 用户申请退款
    print("\n--- 用户申请退款 ---")
    print("👤: 我要退款，订单 ORD20260417001")

    # invoke 会停在 approve_refund 之前
    result = app.invoke({
        "messages": [],
        "user_input": "我要退款，订单 ORD20260417001",
        "user_id": "USER001",
        "approved": False,  # 默认未批准
    }, config)

    print(f"🤖: {result['response']}")

    # 检查当前节点 — 应该停在 refund，还没执行 approve_refund
    current = app.get_state(config)
    print(f"\n⏸️  当前状态: Graph 暂停")
    print(f"    下一个待执行节点: {[n.name for n in current.tasks] if current.tasks else '无'}")

    # --- 场景 A：人工批准 ---
    print("\n--- 🟢 场景 A：审核人员批准退款 ---")
    approved_config = {"configurable": {"thread_id": thread_id}}

    # 更新状态，设置 approved=True，然后从断点继续
    # 注意：不需要 as_node，直接 patch 当前 state 即可
    app.update_state(
        approved_config,
        {"approved": True},
    )
    # 继续执行
    result_approved = app.invoke(None, approved_config)
    print(f"🤖: {result_approved['response']}")

    # --- 场景 B：人工拒绝 ---
    print("\n--- 🔴 场景 B：创建新的退款申请（拒绝版本）---")
    thread_id_reject = "refund-reject-002"
    reject_config = {"configurable": {"thread_id": thread_id_reject}}

    app.invoke({
        "messages": [],
        "user_input": "我要退款，订单 ORD20260417002",
        "user_id": "USER001",
        "approved": False,
    }, reject_config)

    # 审核人员拒绝（直接 patch state，不用 as_node）
    app.update_state(reject_config, {"approved": False})
    result_rejected = app.invoke(None, reject_config)
    print(f"🤖: {result_rejected['response']}")


# ============================================================
# 5. 运行所有演示
# ============================================================

def run_all_demos():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   LangGraph Week 2: Persistence / Checkpoints       ║")
    print("║   + Human-in-the-Loop Demo                          ║")
    print("╚══════════════════════════════════════════════════════╝")

    demo_1_multiturn()
    demo_2_time_travel()
    demo_3_human_in_the_loop()

    print("\n" + "=" * 60)
    print("✅ Week 2 演示完成！")
    print("=" * 60)
    print("""
📝 本周核心知识点总结：

1. MemorySaver
   - checkpointer = MemorySaver()
   - app = graph.compile(checkpointer=checkpointer)
   - 让 Graph 记住状态，支持多轮对话

2. Thread ID
   - config = {"configurable": {"thread_id": "xxx"}}
   - app.invoke(state, config)
   - 不同 thread_id = 不同的会话上下文

3. Time Travel
   - app.get_state_history(config) 查看所有 checkpoint
   - 可以回滚到任意历史状态
   - 适合"撤销"和"分支探索"

4. Human-in-the-loop
   - interrupt_before=["node_name"] 在节点前暂停
   - interrupt_after=["node_name"] 在节点后暂停
   - app.update_state(config, updates, as_node="...") 注入人工决策
   - app.invoke(None, config) 从断点继续

5. 生产环境建议
   - MemorySaver 适合开发/测试
   - 生产用 PostgresSaver / SqliteSaver 等持久化方案
   - Human-in-the-loop 是审批流的标准模式
""")


if __name__ == "__main__":
    run_all_demos()
