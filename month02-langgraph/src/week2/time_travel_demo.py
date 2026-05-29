"""
Week 2-Day3: Time Travel + 状态管理高级用法

学习目标：
1. 深入理解 Checkpoint 机制
2. get_state_history — 查看完整的执行历史
3. 从任意 checkpoint 恢复执行（Time Travel）
4. update_state — 修改状态后从断点继续
5. fork 分支：从历史 checkpoint 创建新分支探索不同路径

核心概念：
- 每个 checkpoint 都有一个唯一的 checkpoint_id
- thread_id 决定哪个会话的检查点被读取
- 可以从任意 checkpoint_id 恢复，实现"时间旅行"
- update_state 可以修改状态并指定从哪个节点"注入"
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================
# 1. State — 电商订单处理
# ============================================================

class OrderState(TypedDict, total=False):
    order_id: str
    items: list[dict]
    total: float
    status: str
    shipping_method: str
    discount_code: Optional[str]
    discount_applied: float
    steps: list[str]


# ============================================================
# 2. 节点 — 订单处理流水线
# ============================================================

def validate_order(state: OrderState) -> dict:
    """步骤 1：验证订单"""
    steps = state.get("steps", [])
    steps.append("✅ 验证订单：商品数量、库存检查")
    return {"status": "validated", "steps": steps}


def calculate_total(state: OrderState) -> dict:
    """步骤 2：计算总价"""
    total = sum(item["price"] * item.get("qty", 1) for item in state.get("items", []))
    steps = state.get("steps", [])
    steps.append(f"💰 计算总价: ¥{total:.2f}")
    return {"total": total, "status": "calculated", "steps": steps}


def apply_discount(state: OrderState) -> dict:
    """步骤 3：应用折扣"""
    steps = state.get("steps", [])
    code = state.get("discount_code")
    discount = 0.0

    # 模拟折扣规则
    discounts = {"SAVE10": 0.1, "VIP20": 0.2, "NEW50": 0.5}
    if code and code in discounts:
        discount = state["total"] * discounts[code]
        steps.append(f"🎫 应用折扣码 {code}: -¥{discount:.2f} ({discounts[code]*100:.0f}%)")
    else:
        steps.append("🎫 无有效折扣码")

    return {
        "discount_applied": discount,
        "total": state["total"] - discount,
        "status": "discounted",
        "steps": steps,
    }


def choose_shipping(state: OrderState) -> dict:
    """步骤 4：选择配送方式"""
    steps = state.get("steps", [])
    method = state.get("shipping_method", "standard")

    shipping_cost = {"standard": 0, "express": 15, "overnight": 30}
    cost = shipping_cost.get(method, 0)
    steps.append(f"🚚 配送方式: {method} (+¥{cost})")

    return {
        "shipping_method": method,
        "total": state["total"] + cost,
        "status": "shipping_chosen",
        "steps": steps,
    }


def confirm_order(state: OrderState) -> dict:
    """步骤 5：确认订单（interrupt_before 暂停点）"""
    steps = state.get("steps", [])
    steps.append("⏸️ 等待用户确认订单...")
    return {"status": "awaiting_confirmation", "steps": steps}


def finalize_order(state: OrderState) -> dict:
    """步骤 6：最终订单（需要用户确认后执行）"""
    steps = state.get("steps", [])
    steps.append(f"🎉 订单已确认！最终金额: ¥{state['total']:.2f}")
    return {"status": "confirmed", "steps": steps}


# ============================================================
# 3. 构建 Graph
# ============================================================

def build_order_graph():
    checkpointer = MemorySaver()

    graph = StateGraph(OrderState)

    graph.add_node("validate", validate_order)
    graph.add_node("calculate", calculate_total)
    graph.add_node("discount", apply_discount)
    graph.add_node("shipping", choose_shipping)
    graph.add_node("confirm", confirm_order)
    graph.add_node("finalize", finalize_order)

    graph.set_entry_point("validate")
    graph.add_edge("validate", "calculate")
    graph.add_edge("calculate", "discount")
    graph.add_edge("discount", "shipping")
    graph.add_edge("shipping", "confirm")
    graph.add_edge("confirm", "finalize")
    graph.add_edge("finalize", END)

    # 在 finalize 之前暂停，让用户确认订单详情
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["finalize"],
    )

    return app


# ============================================================
# 4. 演示
# ============================================================

def demo_time_travel():
    """
    演示：Time Travel — 从历史 checkpoint 恢复
    场景：用户下单 → 走到确认前暂停 → 查看历史 → 修改折扣码 → 继续
    """
    print("\n" + "=" * 60)
    print("🕰️  Time Travel: 修改折扣码后重新计算")
    print("=" * 60)

    app = build_order_graph()
    thread = "order-travel-1"
    config = {"configurable": {"thread_id": thread}}

    # 提交订单：初始折扣码无效
    print("\n📦 提交订单：")
    print("  商品: iPhone 15 Pro × 1 (¥7999)")
    print("  折扣码: INVALID (无效)")
    print("  配送: standard")

    result = app.invoke({
        "order_id": "ORD-NEW-001",
        "items": [{"name": "iPhone 15 Pro", "price": 7999, "qty": 1}],
        "discount_code": "INVALID",
        "shipping_method": "standard",
        "status": "new",
        "steps": [],
    }, config)

    print(f"\n当前总价: ¥{result['total']:.2f}")
    print("📜 执行日志:")
    for step in result["steps"]:
        print(f"  {step}")

    # 查看 checkpoint 历史
    print("\n📋 Checkpoint 历史:")
    history = list(app.get_state_history(config))
    for i, cp in enumerate(history):
        step_info = cp.values.get("steps", [])
        last_step = step_info[-1] if step_info else "N/A"
        print(f"  [{i}] step={cp.values.get('status', '?')} | {last_step[:50]}")

    print("\n💡 用户发现折扣码填错了，想改成 SAVE10")

    # ⭐ 正确的 Time Travel + Fork 方式：
    # 1. 找到 discount 节点之前（刚执行完 calculate）的 checkpoint
    # 2. 从那个 checkpoint 创建新 thread（fork），用正确的折扣码继续
    print("🔄 从 discount 之前的 checkpoint fork，用正确的折扣码重新计算...")

    history = list(app.get_state_history(config))
    # 找到 status == "calculated" 的 checkpoint（刚计算完总价，还没应用折扣）
    calc_cp = None
    for cp in history:
        if cp.values.get("status") == "calculated":
            calc_cp = cp
            break

    if calc_cp:
        # Fork：从那个 checkpoint 的状态创建新的 thread
        fork_thread = "order-travel-1-fork"
        fork_config = {"configurable": {"thread_id": fork_thread}}

        # 从 fork 点注入：用 calculated 状态 + 正确的折扣码
        app.update_state(
            fork_config,
            {
                "order_id": "ORD-NEW-001",
                "items": [{"name": "iPhone 15 Pro", "price": 7999, "qty": 1}],
                "discount_code": "SAVE10",
                "shipping_method": "standard",
                "status": "calculated",
                "total": 7999.0,
                "steps": calc_cp.values.get("steps", []).copy(),
            },
        )
        # 从这个点继续执行（会走 discount → shipping → confirm → 暂停 → finalize）
        result = app.invoke(None, fork_config)

        print(f"\n当前总价: ¥{result['total']:.2f}")
        print("📜 修改后执行日志:")
        for step in result["steps"]:
            print(f"  {step}")
    else:
        print("⚠️  未找到合适的 checkpoint，跳过 fork 演示")


def demo_fork():
    """
    演示：Fork — 从同一 checkpoint 探索不同配送方案
    """
    print("\n" + "=" * 60)
    print("🔀 Fork: 从同一状态探索不同配送方案")
    print("=" * 60)

    app = build_order_graph()

    # 方案比较
    shipping_options = ["standard", "express", "overnight"]
    results = {}

    for method in shipping_options:
        thread = f"order-fork-{method}"
        config = {"configurable": {"thread_id": thread}}

        result = app.invoke({
            "order_id": f"ORD-FORK-{method.upper()}",
            "items": [{"name": "MacBook Air M2", "price": 9499, "qty": 1}],
            "discount_code": "VIP20",
            "shipping_method": method,
            "status": "new",
            "steps": [],
        }, config)

        # 确认
        app.update_state(config, {}, as_node="finalize")
        final = app.invoke(None, config)
        results[method] = final["total"]

        print(f"\n🚚 {method}: ¥{final['total']:.2f}")
        # 只显示最后几步
        for step in final["steps"][-3:]:
            print(f"  {step}")

    print(f"\n📊 方案对比:")
    for method, total in results.items():
        diff = total - results["standard"]
        label = "基准" if diff == 0 else f"+¥{diff:.2f}"
        print(f"  {method:10s}: ¥{total:,.2f} ({label})")


# ============================================================
# 5. 运行
# ============================================================

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Time Travel + 状态管理高级用法                      ║")
    print("╚══════════════════════════════════════════════════════╝")

    demo_time_travel()
    demo_fork()

    print("\n" + "=" * 60)
    print("✅ Time Travel 演示完成！")
    print("=" * 60)
