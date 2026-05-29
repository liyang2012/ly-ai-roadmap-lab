"""
Week 3: 主图 — 组合子图 (Master Graph with Subgraphs)

学习目标：
1. 展示如何把独立子图组合到主图中
2. 主图负责编排：接收用户输入 → 判断路由到哪个子图 → 汇总输出
3. 子图可以独立开发和测试，也能作为整体的一部分运行

架构：
                        ┌─ order_subgraph (订单处理)
                        │
user_input → router ────┼─ faq_subgraph (FAQ 问答)
                        │
                        └─ greeting / fallback

关键 API：
- subgraph = build_order_subgraph()  # 子图编译后就是一个可调用对象
- graph.add_node("orders", subgraph)  # 子图作为节点添加到主图
- 主图 State 和子图 State 通过字段映射通信
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

# 导入子图构建函数
from order_subgraph import build_order_subgraph, OrderState
from faq_subgraph import build_faq_subgraph, FAQState


# ============================================================
# 主图 State
# ============================================================

class MasterState(TypedDict, total=False):
    """
    主图状态：面向用户的顶层状态
    
    注意：主图 State 必须包含子图需要读写的所有字段。
    子图编译后作为节点加入主图，state 是共享的——
    子图能读到的就是主图 state 中同名的字段。
    """
    user_input: str
    route: str           # 路由目标：order / faq / greeting / fallback
    response: str        # 最终回复
    
    # 订单子图需要的字段
    order_id: str
    action: str
    exists: bool
    order_data: dict
    result: str
    error: str
    
    # FAQ 子图需要的字段
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool


# ============================================================
# 路由逻辑
# ============================================================

def determine_route(state: MasterState) -> dict:
    """
    节点 1：判断用户输入应该路由到哪个子图
    
    路由优先级：
    1. 问候（最高优先级，避免误判）
    2. 订单操作（包含订单号/明确操作意图）
    3. FAQ 咨询（通用问题）
    4. fallback
    """
    q = state["user_input"].lower()
    
    # 1. 问候优先
    greeting_keywords = ["你好", "hello", "hi", "在吗", "在不在"]
    if any(kw in q for kw in greeting_keywords):
        return {"route": "greeting"}
    
    # 2. 订单操作：订单号 OR 明确查询/操作订单的意图
    import re
    has_order_id = bool(re.search(r"ORD\d+", q))
    
    # 退款/退货（即使没有订单号，也走订单子图处理政策）
    has_refund = any(kw in q for kw in ["退款", "退货", "退钱"])
    
    # 订单查询/物流查询
    has_order_query = any(kw in q for kw in ["订单", "发货", "物流", "ORD"])
    
    if has_order_id or has_refund or has_order_query:
        return {"route": "order"}
    
    # 3. FAQ：通用知识型问题
    faq_keywords = ["多久", "包邮", "保修", "正品", "发票", "地址", "密码", "运费", "退款政策"]
    if any(kw in q for kw in faq_keywords):
        return {"route": "faq"}
    
    return {"route": "fallback"}


def route_to_subgraph(state: MasterState) -> str:
    """条件路由函数"""
    mapping = {
        "order": "order_subgraph",
        "faq": "faq_subgraph",
        "greeting": "greeting_node",
        "fallback": "fallback_node",
    }
    return mapping.get(state["route"], "fallback_node")


# ============================================================
# 简单节点
# ============================================================

def greeting_node(state: MasterState) -> dict:
    return {
        "response": (
            "👋 你好！我是智能客服助手，可以帮您：\n"
            "  📦 查询订单状态和物流\n"
            "  💰 申请退款退货\n"
            "  💡 常见问题解答\n\n"
            "试试问我：\n"
            "  • 查一下订单 ORD20260417001\n"
            "  • 多久能送到？\n"
            "  • 退款多久到账？"
        )
    }


def fallback_node(state: MasterState) -> dict:
    return {
        "response": (
            "🤔 我不太理解您的问题。\n\n"
            "您可以问我：\n"
            "  📦 订单相关：查订单、查物流、退款\n"
            "  💡 常见问题：多久能到、包邮吗、保修政策"
        )
    }


# ============================================================
# 子图适配节点
# ============================================================
#
# 核心难点：主图 State 和子图 State 字段不一致
# 解决方案：用适配节点做字段转换

def order_adapter(state: MasterState) -> dict:
    """
    节点 2a：主图 → 订单子图 的适配器
    
    把 MasterState 的 user_input 解析成 OrderState 需要的字段
    注意：返回的字段名必须和 OrderState 一致，子图才能读取
    """
    import re
    
    user_input = state["user_input"]
    
    # 提取订单号
    order_match = re.search(r"ORD\d+", user_input)
    order_id = order_match.group(0) if order_match else "ORD20260417001"  # 默认
    
    # 判断操作类型
    action = "query"
    if any(kw in user_input for kw in ["退款", "退货", "退钱"]):
        action = "refund"
    elif any(kw in user_input for kw in ["物流", "到哪了", "快递", "物流状态"]):
        action = "status"
    
    return {
        "order_id": order_id,
        "action": action,
    }


def faq_adapter(state: MasterState) -> dict:
    """
    节点 2b：主图 → FAQ 子图 的适配器
    
    直接传递 user_input 作为 question
    注意：返回的字段名必须和 FAQState 一致
    """
    return {
        "question": state["user_input"],
    }


def format_order_result(state: MasterState) -> dict:
    """
    节点 3a：格式化订单子图的输出
    
    子图结束后，它的 result 字段会合并到主图 state 中。
    这里把子图的 result 提取为 response。
    """
    result = state.get("result", state.get("subgraph_result", ""))
    return {
        "response": result,
    }


def format_faq_result(state: MasterState) -> dict:
    """
    节点 3b：格式化 FAQ 子图的输出
    """
    result = state.get("answer", state.get("subgraph_result", ""))
    return {
        "response": result,
    }


# ============================================================
# 构建主图
# ============================================================

def build_master_graph():
    """
    构建主图，组合订单子图和 FAQ 子图
    
    结构：
    __start__ → determine_route → [条件路由]
                                         ├─ order_adapter → order_subgraph → format_order_result → END
                                         ├─ faq_adapter → faq_subgraph → format_faq_result → END
                                         ├─ greeting_node → END
                                         └─ fallback_node → END
    """
    # 先构建子图（编译后的对象可以直接作为节点使用）
    order_subgraph = build_order_subgraph()
    faq_subgraph = build_faq_subgraph()
    
    graph = StateGraph(MasterState)
    
    # 添加路由和简单节点
    graph.add_node("determine_route", determine_route)
    graph.add_node("greeting_node", greeting_node)
    graph.add_node("fallback_node", fallback_node)
    
    # 添加适配器节点
    graph.add_node("order_adapter", order_adapter)
    graph.add_node("faq_adapter", faq_adapter)
    
    # 添加结果格式化节点
    graph.add_node("format_order_result", format_order_result)
    graph.add_node("format_faq_result", format_faq_result)
    
    # ⭐ 子图作为节点添加
    graph.add_node("order_subgraph", order_subgraph)
    graph.add_node("faq_subgraph", faq_subgraph)
    
    # 入口
    graph.set_entry_point("determine_route")
    
    # 条件路由
    graph.add_conditional_edges(
        "determine_route",
        route_to_subgraph,
        {
            "order_subgraph": "order_adapter",
            "faq_subgraph": "faq_adapter",
            "greeting_node": "greeting_node",
            "fallback_node": "fallback_node",
        },
    )
    
    # 订单流程链路
    graph.add_edge("order_adapter", "order_subgraph")
    graph.add_edge("order_subgraph", "format_order_result")
    graph.add_edge("format_order_result", END)
    
    # FAQ 流程链路
    graph.add_edge("faq_adapter", "faq_subgraph")
    graph.add_edge("faq_subgraph", "format_faq_result")
    graph.add_edge("format_faq_result", END)
    
    # 问候和 fallback 直接结束
    graph.add_edge("greeting_node", END)
    graph.add_edge("fallback_node", END)
    
    return graph.compile()


# ============================================================
# 测试主图
# ============================================================

def run_tests():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   LangGraph Week 3: Subgraph 组合测试              ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    app = build_master_graph()
    
    # 打印主图结构
    print("\n📊 主图结构:")
    print(app.get_graph().draw_mermaid())
    
    test_cases = [
        # 路由到订单子图
        "帮我查一下订单 ORD20260417001",
        "我要退款，订单 ORD20260417001",
        "查物流 ORD20260417003",
        "不存在的订单 ORD0000000000",
        
        # 路由到 FAQ 子图
        "多久能送到？",
        "退款多久到账？",
        "你们的东西是正品吗？",
        "怎么修改收货地址？",
        "今天天气怎么样？",  # → fallback
        
        # 问候
        "你好！",
        "Hello!",
    ]
    
    for i, question in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"🧪 测试 {i}: {question}")
        print(f"{'=' * 60}")
        
        state: MasterState = {
            "user_input": question,
            "route": "",
            "response": "",
            "order_id": "",
            "action": "",
            "exists": False,
            "order_data": {},
            "result": "",
            "error": "",
            "question": "",
            "category": "",
            "confidence": 0.0,
            "answer": "",
            "fallback": False,
        }
        result = app.invoke(state)
        print(result["response"])


if __name__ == "__main__":
    run_tests()
