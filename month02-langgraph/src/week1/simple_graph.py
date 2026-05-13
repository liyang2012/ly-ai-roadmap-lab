"""
Day 1-2: LangGraph 基础 - 简单 StateGraph 示例

学习目标：
1. 理解 StateGraph 基本结构
2. 定义 State schema（TypedDict）
3. 添加节点（nodes）和边（edges）
4. 编译并运行 graph
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


# ========== 1. 定义 State ==========
# State 是 graph 节点之间传递的数据结构
# 相当于 graph 的"记忆"
class SimpleState(TypedDict):
    """
    简单状态：
    - question: 用户输入的问题
    - step: 当前执行到第几步
    - answer: 最终答案
    - messages: 日志消息列表
    """
    question: str
    step: int
    answer: str
    messages: list[str]


# ========== 2. 定义节点（Nodes） ==========
# 每个节点是一个纯函数，接收当前 state，返回要更新的字段

def analyze_node(state: SimpleState) -> dict:
    """
    节点 1：分析问题类型
    根据问题内容判断类型（数学/编程/其他）
    """
    q = state["question"].lower()
    if any(k in q for k in ["多少", "计算", "求", "面积", "体积"]):
        category = "math"
    elif any(k in q for k in ["代码", "python", "写", "实现", "函数"]):
        category = "code"
    else:
        category = "general"

    return {
        "step": 1,
        "messages": [f"📋 分析完成，问题类型：{category}"],
        # 把分类结果也存到 state 里（需要先在 TypedDict 声明，
        # 这里用 messages 记录，避免 state 膨胀）
    }


def process_node(state: SimpleState) -> dict:
    """
    节点 2：根据问题类型处理
    这里用简单规则模拟，实际可以接 LLM
    """
    q = state["question"].lower()
    messages = state["messages"].copy()

    if "多少" in q and "加" in q:
        # 简单数学：提取数字
        import re
        nums = re.findall(r"\d+", q)
        if len(nums) >= 2:
            result = sum(int(n) for n in nums)
            answer = f"{q} = {result}"
        else:
            answer = "无法提取数字，请重新表述"
    elif "hello" in q or "你好" in q:
        answer = "你好！我是 LangGraph 助手 👋"
    else:
        answer = f"收到你的问题：{state['question']}（需要更复杂的处理）"

    messages.append(f"🔧 处理完成")
    return {
        "step": 2,
        "answer": answer,
        "messages": messages,
    }


def format_node(state: SimpleState) -> dict:
    """
    节点 3：格式化输出
    将结果整理为最终回复
    """
    messages = state["messages"].copy()
    messages.append(f"✅ 处理完成（共 {state['step']} 步）")

    final = "─── 回答 ───\n" + state["answer"] + "\n" + "─── 流程 ───\n" + "\n".join(messages)
    return {
        "step": 3,
        "messages": messages,
        "answer": final,
    }


# ========== 3. 构建 Graph ==========

def build_graph():
    """构建并编译 StateGraph"""
    # 创建 graph，指定 state 类型
    graph = StateGraph(SimpleState)

    # 添加节点
    graph.add_node("analyze", analyze_node)
    graph.add_node("process", process_node)
    graph.add_node("format", format_node)

    # 设置入口节点（第一个执行的节点）
    graph.set_entry_point("analyze")

    # 添加边：analyze → process → format → END
    graph.add_edge("analyze", "process")
    graph.add_edge("process", "format")
    graph.add_edge("format", END)

    # 编译
    return graph.compile()


# ========== 4. 运行 ==========

def run_demo():
    """运行示例"""
    app = build_graph()

    # 查看 graph 结构
    print("=" * 50)
    print("📊 Graph 结构（节点和边）")
    print("=" * 50)
    print(app.get_graph().draw_mermaid())
    print()

    # 测试 1：简单问候
    print("=" * 50)
    print("🧪 测试 1：你好")
    print("=" * 50)
    initial_state = {
        "question": "你好",
        "step": 0,
        "answer": "",
        "messages": ["🚀 开始处理"],
    }
    result = app.invoke(initial_state)
    print(result["answer"])
    print()

    # 测试 2：简单数学
    print("=" * 50)
    print("🧪 测试 2：15 加 27 等于多少")
    print("=" * 50)
    initial_state = {
        "question": "15 加 27 等于多少",
        "step": 0,
        "answer": "",
        "messages": ["🚀 开始处理"],
    }
    result = app.invoke(initial_state)
    print(result["answer"])
    print()

    # 测试 3：其他问题
    print("=" * 50)
    print("🧪 测试 3：Python 怎么实现快排？")
    print("=" * 50)
    initial_state = {
        "question": "Python 怎么实现快排？",
        "step": 0,
        "answer": "",
        "messages": ["🚀 开始处理"],
    }
    result = app.invoke(initial_state)
    print(result["answer"])


if __name__ == "__main__":
    run_demo()
