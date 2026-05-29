"""
Week 2-Day2: Human-in-the-Loop 完整实战

学习目标：
1. interrupt_before / interrupt_after — 在关键节点前后暂停
2. 人工审核、修改状态、继续执行
3. 多步骤审批流程实战：退款申请 → 主管审核 → 财务确认 → 执行退款
4. 对比 interrupt_before vs interrupt_after 的使用场景

核心 API：
- graph.compile(interrupt_before=["node_name"], interrupt_after=["node_name"])
- app.get_state(config) — 查看当前暂停状态
- app.update_state(config, new_values, as_node="node_name") — 人工注入决策
- app.invoke(None, config) — 从断点继续
- app.get_state_history(config) — 查看所有 checkpoint
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================
# 1. 定义 State — 多步骤审批流
# ============================================================

class ApprovalState(TypedDict, total=False):
    """
    退款审批流程状态：
    - request_id: 退款申请编号
    - order_id: 关联订单号
    - amount: 退款金额
    - reason: 退款原因
    - manager_approved: 主管是否批准
    - finance_approved: 财务是否批准
    - status: 当前状态
    - notes: 审核备注
    """
    request_id: str
    order_id: str
    amount: float
    reason: str
    manager_approved: Optional[bool]
    finance_approved: Optional[bool]
    status: str
    notes: list[str]


# ============================================================
# 2. 定义流程节点
# ============================================================

def create_request(state: ApprovalState) -> dict:
    """节点 1：创建退款申请"""
    notes = state.get("notes", [])
    notes.append(f"📝 创建退款申请: {state['request_id']}")
    notes.append(f"  订单: {state['order_id']}, 金额: ¥{state['amount']:.2f}")
    notes.append(f"  原因: {state['reason']}")
    return {"status": "pending_manager_review", "notes": notes}


def manager_review(state: ApprovalState) -> dict:
    """节点 2：主管审核（interrupt_before 暂停点）"""
    notes = state.get("notes", [])
    notes.append("⏸️ 等待主管审核...")
    return {"status": "awaiting_manager", "notes": notes}


def manager_decision(state: ApprovalState) -> dict:
    """节点 3：主管决策执行"""
    notes = state.get("notes", [])
    if state.get("manager_approved"):
        notes.append("✅ 主管审核通过")
        return {"status": "pending_finance_review", "notes": notes}
    else:
        notes.append("❌ 主管审核拒绝")
        return {"status": "rejected_by_manager", "notes": notes}


def finance_review(state: ApprovalState) -> dict:
    """节点 4：财务审核（interrupt_before 暂停点）"""
    notes = state.get("notes", [])
    notes.append("⏸️ 等待财务审核...")
    return {"status": "awaiting_finance", "notes": notes}


def finance_decision(state: ApprovalState) -> dict:
    """节点 5：财务决策执行"""
    notes = state.get("notes", [])
    if state.get("finance_approved"):
        notes.append(f"✅ 财务审核通过，退款 ¥{state['amount']:.2f} 已执行")
        return {"status": "refund_completed", "notes": notes}
    else:
        notes.append("❌ 财务审核拒绝")
        return {"status": "rejected_by_finance", "notes": notes}


def notify_result(state: ApprovalState) -> dict:
    """节点 6：通知结果"""
    notes = state.get("notes", [])
    status = state["status"]
    status_msg = {
        "refund_completed": "🎉 退款已完成，款项将在 1-3 个工作日内到账",
        "rejected_by_manager": "退款申请已被主管拒绝",
        "rejected_by_finance": "退款申请已被财务拒绝",
    }.get(status, "退款处理中")
    notes.append(f"📢 通知用户: {status_msg}")
    return {"notes": notes}


# ============================================================
# 3. 路由逻辑
# ============================================================

def route_after_manager(state: ApprovalState) -> str:
    """主管审核后路由"""
    if state.get("manager_approved"):
        return "finance_review"
    return "notify_result"


def route_after_finance(state: ApprovalState) -> str:
    """财务审核后路由"""
    return "notify_result"


# ============================================================
# 4. 构建 Graph
# ============================================================

def build_approval_graph():
    """
    构建多步骤审批 Graph：
    create_request → manager_review → ⏸️ → manager_decision → [条件路由]
      → 通过: finance_review → ⏸️ → finance_decision → notify_result → END
      → 拒绝: notify_result → END
    """
    checkpointer = MemorySaver()

    graph = StateGraph(ApprovalState)

    graph.add_node("create_request", create_request)
    graph.add_node("manager_review", manager_review)
    graph.add_node("manager_decision", manager_decision)
    graph.add_node("finance_review", finance_review)
    graph.add_node("finance_decision", finance_decision)
    graph.add_node("notify_result", notify_result)

    graph.set_entry_point("create_request")
    graph.add_edge("create_request", "manager_review")

    # manager_review 后暂停 → 人工决定 → manager_decision
    graph.add_edge("manager_review", "manager_decision")

    # manager_decision 后条件路由
    graph.add_conditional_edges(
        "manager_decision",
        route_after_manager,
        {
            "finance_review": "finance_review",
            "notify_result": "notify_result",
        },
    )

    # finance_review 后暂停 → 人工决定 → finance_decision
    graph.add_edge("finance_review", "finance_decision")
    graph.add_conditional_edges(
        "finance_decision",
        route_after_finance,
        {"notify_result": "notify_result"},
    )

    graph.add_edge("notify_result", END)

    # ⭐ 在 manager_decision 和 finance_decision 之前暂停
    # 这样人工可以注入 approved=True/False 后再继续
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["manager_decision", "finance_decision"],
    )

    return app


# ============================================================
# 5. 演示场景
# ============================================================

def demo_full_approval():
    """完整审批流程：主管通过 + 财务通过"""
    print("\n" + "=" * 60)
    print("🟢 场景 1：完整审批通过（主管✅ + 财务✅）")
    print("=" * 60)

    app = build_approval_graph()
    thread = "approval-demo-1"
    config = {"configurable": {"thread_id": thread}}

    # Step 1: 提交退款申请
    print("\n📝 用户提交退款申请...")
    result = app.invoke({
        "request_id": "REF-001",
        "order_id": "ORD20260417001",
        "amount": 7999.00,
        "reason": "商品与描述不符",
        "status": "created",
        "notes": [],
    }, config)

    print(f"当前状态: {result['status']}")
    for note in result["notes"]:
        print(f"  {note}")

    # Step 2: 主管审核 — 查看当前状态
    print("\n⏸️ Graph 暂停，等待主管审核...")
    current = app.get_state(config)
    print(f"  当前节点: {list(current.next)}")

    # 主管批准 — 直接 patch state（不用 as_node），然后让 manager_decision 节点执行
    print("👤 主管操作：批准退款")
    app.update_state(config, {"manager_approved": True})
    result = app.invoke(None, config)

    print(f"\n当前状态: {result['status']}")
    for note in result["notes"]:
        print(f"  {note}")

    # Step 3: 财务审核
    print("\n⏸️ Graph 暂停，等待财务审核...")
    current = app.get_state(config)
    print(f"  当前节点: {list(current.next)}")

    # 财务批准
    print("💰 财务操作：批准退款")
    app.update_state(config, {"finance_approved": True})
    result = app.invoke(None, config)

    print(f"\n✅ 最终状态: {result['status']}")
    print("\n📜 完整流程日志:")
    for note in result["notes"]:
        print(f"  {note}")


def demo_manager_reject():
    """主管直接拒绝"""
    print("\n" + "=" * 60)
    print("🔴 场景 2：主管拒绝（不走财务流程）")
    print("=" * 60)

    app = build_approval_graph()
    thread = "approval-demo-2"
    config = {"configurable": {"thread_id": thread}}

    print("\n📝 用户提交退款申请...")
    app.invoke({
        "request_id": "REF-002",
        "order_id": "ORD20260417002",
        "amount": 1899.00,
        "reason": "不想要了",
        "status": "created",
        "notes": [],
    }, config)

    print("⏸️ 等待主管审核...")

    # 主管拒绝
    print("👤 主管操作：拒绝退款")
    app.update_state(config, {"manager_approved": False})
    result = app.invoke(None, config)

    print(f"\n✅ 最终状态: {result['status']}")
    for note in result["notes"]:
        print(f"  {note}")


def demo_finance_reject():
    """主管通过但财务拒绝"""
    print("\n" + "=" * 60)
    print("🟡 场景 3：主管通过但财务拒绝")
    print("=" * 60)

    app = build_approval_graph()
    thread = "approval-demo-3"
    config = {"configurable": {"thread_id": thread}}

    print("\n📝 用户提交退款申请...")
    app.invoke({
        "request_id": "REF-003",
        "order_id": "ORD20260417003",
        "amount": 9499.00,
        "reason": "质量问题",
        "status": "created",
        "notes": [],
    }, config)

    # 主管通过
    print("👤 主管操作：批准")
    app.update_state(config, {"manager_approved": True})
    app.invoke(None, config)

    # 财务拒绝
    print("💰 财务操作：拒绝")
    app.update_state(config, {"finance_approved": False})
    result = app.invoke(None, config)

    print(f"\n✅ 最终状态: {result['status']}")
    for note in result["notes"]:
        print(f"  {note}")


# ============================================================
# 6. 运行
# ============================================================

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Human-in-the-Loop 完整实战                         ║")
    print("║   多步骤退款审批流                                    ║")
    print("╚══════════════════════════════════════════════════════╝")

    demo_full_approval()
    demo_manager_reject()
    demo_finance_reject()

    print("\n" + "=" * 60)
    print("✅ Human-in-the-Loop 实战完成！")
    print("=" * 60)
