"""
Week 3: LangGraph Subgraph 与模块化设计

学习目标：
1. 理解 Subgraph 概念：把一个复杂 graph 拆成可复用的子模块
2. 设计「订单处理子图」：查询 → 验证 → 处理 → 反馈
3. 设计「FAQ 子图」：分类 → 检索 → 生成回复
4. 主图组合两个子图，展示嵌套调用

对比 Week 1 的扁平结构：
- Week 1: 所有节点都在一个 graph 里，越来越臃肿
- Week 3: 子图独立定义、独立测试、主图只负责编排

"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END


# ============================================================
# 子图 1：订单处理子图 (Order Processing Subgraph)
# ============================================================

class OrderState(TypedDict, total=False):
    """
    订单子图的局部状态：
    - order_id: 订单号
    - exists: 订单是否存在
    - order_data: 订单详情
    - action: 要执行的操作 (query/refund/status)
    - result: 处理结果
    - error: 错误信息
    """
    order_id: str
    exists: bool
    order_data: dict
    action: str
    result: str
    error: str


# 模拟订单数据库
ORDERS_DB = {
    "ORD20260417001": {
        "status": "已发货", "product": "iPhone 15 Pro",
        "amount": 7999.00, "order_date": "2026-04-15",
        "logistics": "顺丰 SF1234567890", "estimated_delivery": "2026-04-19",
        "user_id": "USER001"
    },
    "ORD20260417002": {
        "status": "处理中", "product": "AirPods Pro 2",
        "amount": 1899.00, "order_date": "2026-04-17",
        "logistics": "待发货", "estimated_delivery": "2026-04-20",
        "user_id": "USER002"
    },
    "ORD20260417003": {
        "status": "已签收", "product": "MacBook Air M2",
        "amount": 9499.00, "order_date": "2026-04-10",
        "logistics": "京东 JD9876543210", "estimated_delivery": "已送达",
        "user_id": "USER001"
    },
}


def validate_order(state: OrderState) -> dict:
    """节点 1：验证订单是否存在"""
    order = ORDERS_DB.get(state["order_id"])
    if order:
        return {
            "exists": True,
            "order_data": order,
        }
    else:
        return {
            "exists": False,
            "error": f"❌ 未找到订单 {state['order_id']}",
        }


def route_order_action(state: OrderState) -> str:
    """条件路由：根据 action 决定下一步"""
    if not state.get("exists"):
        return "error_handler"
    
    action = state.get("action", "query")
    mapping = {
        "query": "query_order",
        "refund": "process_refund",
        "status": "check_status",
    }
    return mapping.get(action, "query_order")


def query_order_node(state: OrderState) -> dict:
    """节点 2a：查询订单详情"""
    data = state["order_data"]
    result = (
        f"📦 订单 {state['order_id']}：\n"
        f"  商品：{data['product']}\n"
        f"  金额：¥{data['amount']:.2f}\n"
        f"  状态：{data['status']}\n"
        f"  下单时间：{data['order_date']}"
    )
    return {"result": result}


def process_refund_node(state: OrderState) -> dict:
    """节点 2b：处理退款"""
    data = state["order_data"]
    status = data["status"]
    
    # 退款规则
    rules = {
        "未发货": {"allowed": True, "msg": "1-3 工作日到账，无手续费"},
        "已发货": {"allowed": True, "msg": "需拒收或退货，运费自理"},
        "已签收": {"allowed": True, "msg": "7 天内可退，买家承担运费"},
        "已取消": {"allowed": False, "msg": "订单已取消，无需退款"},
    }
    
    rule = rules.get(status, {"allowed": False, "msg": "未知状态"})
    
    if rule["allowed"]:
        result = (
            f"💰 退款申请已受理\n"
            f"  订单：{state['order_id']}\n"
            f"  商品：{data['product']}\n"
            f"  金额：¥{data['amount']:.2f}\n"
            f"  规则：{rule['msg']}"
        )
    else:
        result = (
            f"❌ 退款不符合条件\n"
            f"  订单状态：{status}\n"
            f"  原因：{rule['msg']}"
        )
    
    return {"result": result}


def check_status_node(state: OrderState) -> dict:
    """节点 2c：仅查询物流状态"""
    data = state["order_data"]
    result = (
        f"🚚 订单 {state['order_id']} 物流状态：\n"
        f"  商品：{data['product']}\n"
        f"  当前状态：{data['status']}\n"
        f"  物流：{data['logistics']}\n"
        f"  预计送达：{data['estimated_delivery']}"
    )
    return {"result": result}


def error_handler_node(state: OrderState) -> dict:
    """节点 3：错误处理"""
    return {
        "result": state.get("error", "❌ 订单处理失败"),
    }


def build_order_subgraph():
    """
    构建订单处理子图
    
    结构：
    validate_order → [条件路由] → query_order / process_refund / check_status / error_handler → END
    """
    graph = StateGraph(OrderState)
    
    graph.add_node("validate_order", validate_order)
    graph.add_node("query_order", query_order_node)
    graph.add_node("process_refund", process_refund_node)
    graph.add_node("check_status", check_status_node)
    graph.add_node("error_handler", error_handler_node)
    
    graph.set_entry_point("validate_order")
    
    graph.add_conditional_edges(
        "validate_order",
        route_order_action,
        {
            "query_order": "query_order",
            "process_refund": "process_refund",
            "check_status": "check_status",
            "error_handler": "error_handler",
        },
    )
    
    for node in ["query_order", "process_refund", "check_status", "error_handler"]:
        graph.add_edge(node, END)
    
    return graph.compile()


# ============================================================
# 测试订单子图
# ============================================================

def test_order_subgraph():
    print("\n" + "=" * 60)
    print("📦 测试订单处理子图")
    print("=" * 60)
    
    app = build_order_subgraph()
    
    # 打印子图结构
    print("\n📊 子图结构:")
    print(app.get_graph().draw_mermaid())
    
    test_cases = [
        {"order_id": "ORD20260417001", "action": "query"},
        {"order_id": "ORD20260417001", "action": "refund"},
        {"order_id": "ORD20260417002", "action": "status"},
        {"order_id": "ORD20260417003", "action": "refund"},
        {"order_id": "ORD9999999999", "action": "query"},  # 不存在的订单
    ]
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {tc['action']} 订单 {tc['order_id']} ---")
        state = {
            "order_id": tc["order_id"],
            "action": tc["action"],
            "exists": False,
            "order_data": {},
            "result": "",
            "error": "",
        }
        result = app.invoke(state)
        print(result["result"])


if __name__ == "__main__":
    test_order_subgraph()
