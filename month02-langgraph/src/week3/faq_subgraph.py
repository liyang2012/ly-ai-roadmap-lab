"""
Week 3: FAQ 子图 (FAQ Subgraph)

学习目标：
1. 展示另一种子图模式：知识检索型子图
2. 分类 → 检索 → 生成的三步流程
3. 子图内部也有条件路由和 fallback 机制

与订单子图的差异：
- 订单子图：操作型（执行 CRUD）
- FAQ 子图：检索型（匹配知识 → 生成回复）

"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END


# ============================================================
# 子图 2：FAQ 子图 (FAQ Subgraph)
# ============================================================

class FAQState(TypedDict, total=False):
    """
    FAQ 子图的局部状态：
    - question: 用户问题
    - category: 问题分类
    - confidence: 匹配置信度
    - answer: 找到的答案
    - fallback: 是否触发 fallback
    """
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool


# 知识库：分类 → 常见问题列表
FAQ_KB = {
    "shipping": {
        "label": "物流相关",
        "questions": [
            {"q": "多久能到", "a": "一般情况下，下单后 1-3 天发货，国内 2-5 天送达。偏远地区可能稍晚。"},
            {"q": "快递查询", "a": "您可以在订单详情中查看物流单号，或告诉我订单号，我帮您查。"},
            {"q": "包邮吗", "a": "订单满 ¥99 包邮，不满则收取 ¥10 运费。会员免运费。"},
        ]
    },
    "refund": {
        "label": "退款退货",
        "questions": [
            {"q": "退款多久到账", "a": "退款申请通过后，1-3 个工作日原路退回。信用卡可能延长到 5-7 天。"},
            {"q": "能退货吗", "a": "支持 7 天无理由退货（已签收起算）。需商品完好、包装完整。"},
            {"q": "退款要手续费吗", "a": "未发货：无手续费。已发货：运费自理。已签收：买家承担退回运费。"},
        ]
    },
    "product": {
        "label": "产品信息",
        "questions": [
            {"q": "保修", "a": "所有产品享受 1 年官方保修。Apple 产品支持 AppleCare+ 延保。"},
            {"q": "正品", "a": "我们所有商品均为正品行货，支持官方验证。假一赔十。"},
            {"q": "有发票吗", "a": "支持开具电子发票，下单时选择即可。纸质发票需额外申请。"},
        ]
    },
    "account": {
        "label": "账户相关",
        "questions": [
            {"q": "修改地址", "a": "未发货订单可在订单详情修改收货地址。已发货订单无法修改。"},
            {"q": "忘记密码", "a": "登录页点击「忘记密码」，通过注册邮箱或手机号重置。"},
            {"q": "注销账户", "a": "请在「设置」→「账户安全」中申请注销。注销后数据无法恢复。"},
        ]
    },
}


def classify_question(state: FAQState) -> dict:
    """
    节点 1：问题分类
    
    根据关键词判断问题属于哪个类别。
    实际项目中这里应该用 LLM 做意图分类，这里用规则演示。
    """
    q = state["question"].lower()
    
    # 关键词映射 + 优先级权重（特定业务词权重更高）
    category_keywords = {
        "shipping": [("快递", 1), ("物流", 1), ("送达", 2), ("多久", 2), ("到", 1), ("包邮", 2), ("运费", 1)],
        "refund": [("退款", 2), ("退货", 2), ("退钱", 2), ("到账", 2), ("手续费", 1)],
        "product": [("保修", 2), ("正品", 2), ("发票", 1), ("质量", 1), ("真假", 2)],
        "account": [("地址", 2), ("密码", 2), ("注销", 2), ("账户", 1)],
    }
    
    best_category = None
    best_score = 0
    
    for cat, keywords in category_keywords.items():
        score = sum(weight for kw, weight in keywords if kw in q)
        if score > best_score:
            best_score = score
            best_category = cat
    
    if best_category and best_score > 0:
        # 简单计算置信度
        confidence = min(best_score / 2, 1.0)  # 最多 2 个关键词就算 100%
        return {
            "category": best_category,
            "confidence": confidence,
        }
    else:
        return {
            "category": "unknown",
            "confidence": 0.0,
        }


def route_by_confidence(state: FAQState) -> str:
    """
    条件路由：根据置信度决定是检索答案还是 fallback
    """
    if state.get("confidence", 0) >= 0.5:
        return "retrieve_answer"
    else:
        return "fallback"


def retrieve_answer(state: FAQState) -> dict:
    """
    节点 2a：检索答案
    
    在对应类别的知识库中，找到最匹配的问题。
    """
    category = state["category"]
    if category not in FAQ_KB:
        return {"answer": "🤔 抱歉，我没有找到相关信息。", "fallback": True}
    
    kb = FAQ_KB[category]
    q = state["question"].lower()
    
    best_match = None
    best_score = 0
    
    for item in kb["questions"]:
        # 简单关键词匹配：检查问题中的词是否出现在用户输入中
        score = sum(1 for word in item["q"] if word in q)
        # 也检查用户输入中的词是否在知识库问题中
        score += sum(1 for word in q if word in item["q"])
        # 精确包含加分
        if item["q"] in q or q in item["q"]:
            score += 3
        if score > best_score:
            best_score = score
            best_match = item
    
    if best_match and best_score > 0:
        return {
            "answer": f"💡 {kb['label']}：\n{best_match['a']}",
            "fallback": False,
        }
    else:
        return {
            "answer": f"📂 {kb['label']} 类别下没有找到精确匹配的问题。\n您可以换个说法，或者尝试以下常见问题...",
            "fallback": True,
        }


def fallback_node(state: FAQState) -> dict:
    """节点 2b：Fallback 回复"""
    # 列出一些常见问题引导用户
    suggestions = [
        "物流相关：多久能到？包邮吗？",
        "退款退货：退款多久到账？能退货吗？",
        "产品信息：保修政策？是正品吗？",
        "账户相关：修改地址？忘记密码？",
    ]
    suggestion_text = "\n".join(f"  • {s}" for s in suggestions)
    
    return {
        "answer": (
            f"🤔 我没有理解您的问题。\n\n"
            f"您可以问我：\n{suggestion_text}"
        ),
        "fallback": True,
    }


def build_faq_subgraph():
    """
    构建 FAQ 子图
    
    结构：
    classify_question → [置信度路由] → retrieve_answer / fallback → END
    """
    graph = StateGraph(FAQState)
    
    graph.add_node("classify_question", classify_question)
    graph.add_node("retrieve_answer", retrieve_answer)
    graph.add_node("fallback", fallback_node)
    
    graph.set_entry_point("classify_question")
    
    graph.add_conditional_edges(
        "classify_question",
        route_by_confidence,
        {
            "retrieve_answer": "retrieve_answer",
            "fallback": "fallback",
        },
    )
    
    graph.add_edge("retrieve_answer", END)
    graph.add_edge("fallback", END)
    
    return graph.compile()


# ============================================================
# 测试 FAQ 子图
# ============================================================

def test_faq_subgraph():
    print("\n" + "=" * 60)
    print("💡 测试 FAQ 子图")
    print("=" * 60)
    
    app = build_faq_subgraph()
    
    # 打印子图结构
    print("\n📊 子图结构:")
    print(app.get_graph().draw_mermaid())
    
    test_cases = [
        "多久能送到？",                    # → shipping, 高置信度
        "退款多久到账",                     # → refund, 高置信度
        "你们卖的东西是正品吗？",           # → product, 高置信度
        "怎么修改收货地址",                 # → account, 高置信度
        "今天天气怎么样",                   # → unknown, fallback
        "你们老板叫什么名字",               # → unknown, fallback
        "包邮有什么条件",                   # → shipping, 中置信度
    ]
    
    for i, question in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {question} ---")
        state = {
            "question": question,
            "category": "",
            "confidence": 0.0,
            "answer": "",
            "fallback": False,
        }
        result = app.invoke(state)
        print(f"  分类: {result['category']} (置信度: {result['confidence']:.0%})")
        print(f"  回复: {result['answer']}")


if __name__ == "__main__":
    test_faq_subgraph()
