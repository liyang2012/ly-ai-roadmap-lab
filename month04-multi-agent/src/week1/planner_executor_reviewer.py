"""
第 4 月 Week 1：Planner / Executor / Reviewer 三角色协作
===========================================================================
使用 OpenAI Agents SDK 实现 Multi-Agent 协作模式。

流程：
  User → Planner（分解任务）→ Executor（逐步执行）→ Reviewer（审查质量）
                                                         ├── ✅ 通过 → 输出给 User
                                                         └── ❌ 退回 → Executor 修改

用法：
  python planner_executor_reviewer.py              # 交互模式
  python planner_executor_reviewer.py --test        # 内置测试用例
  python planner_executor_reviewer.py --task "写一篇200字关于AI的文章"
"""

import asyncio
import argparse
import os
from agents import Agent, Runner, trace, function_tool
from agents.items import ItemHelpers
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 加载环境变量
load_dotenv()

# 禁用内置 Tracing
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "true"

# 智谱 AI 客户端
EXTERNAL_CLIENT = AsyncOpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)

MODEL_NAME = "glm-4-flash"  # 智谱免费模型，足够用了


# =============================================================================
# Tool：Executor 可用的执行工具
# =============================================================================

@function_tool
def search_knowledge(query: str) -> str:
    """搜索知识库获取信息。参数 query: 搜索关键词"""
    kb = {
        "ai": "人工智能(AI)是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。"
              "包括机器学习、自然语言处理、计算机视觉等子领域。",
        "agent": "AI Agent 是能够感知环境、做出决策并采取行动以实现目标的自主系统。"
                 "核心组件包括：感知模块、推理引擎、工具使用、记忆系统。",
        "multi-agent": "Multi-Agent 系统由多个专门的 Agent 组成，通过协作完成单个 Agent 难以处理的复杂任务。"
                       "常见架构：Supervisor/Subagent、Planner-Executor-Reviewer、Swarm。",
        "python": "Python 是一种高级编程语言，以简洁、易读著称，广泛用于 AI、数据科学、Web 开发等领域。",
    }
    for key, value in kb.items():
        if key in query.lower():
            return value
    return f"未找到关于 '{query}' 的相关知识。"


@function_tool
def calculate(expression: str) -> str:
    """执行数学计算。参数 expression: 数学表达式，如 '2+3*4'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


# =============================================================================
# Agent 定义
# =============================================================================

# --- Planner ---
planner = Agent(
    name="Planner",
    instructions="""你是 Planner（规划者）。
你的唯一职责是将用户需求分解为清晰可执行的步骤列表。

规则：
1. 输出格式必须是编号的步骤列表，每步一个动词开头
2. 每步应该是 Executor 可以直接执行的（调用工具或推理）
3. 步骤数量控制在 3-5 步
4. 不要自己执行任何步骤，只做规划
5. 规划完成后，立即 handoff 给 Executor

示例输出：
步骤1：搜索关于 AI 的知识
步骤2：搜索关于 Agent 的知识  
步骤3：将搜索结果整合成文章
步骤4：计算文章字数确认达标

完成后说"规划完成，转交 Executor 执行"
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[],  # Planner 不需要工具
)

# --- Executor ---
executor = Agent(
    name="Executor",
    instructions="""你是 Executor（执行者）。
你的唯一职责是按 Planner 制定的计划逐步执行。

规则：
1. 严格按照计划步骤顺序执行
2. 每步调用对应工具或进行推理
3. 执行完所有步骤后，汇总结果
4. 不要做计划外的额外步骤
5. 执行完成后说"执行完成，转交 Reviewer 审查"

可用工具：
- search_knowledge(query)：搜索知识库
- calculate(expression)：执行数学计算
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[search_knowledge, calculate],
)

# --- Reviewer ---
reviewer = Agent(
    name="Reviewer",
    instructions="""你是 Reviewer（审查者）。
你的唯一职责是审查 Executor 的输出质量。

审查维度：
1. **完整性**：计划中的所有步骤都执行了吗？
2. **准确性**：执行结果是否正确、合理？
3. **格式**：输出格式是否符合要求？

判定规则：
- 全部通过 → 输出 "✅ 审查通过"，然后将最终结果呈现给用户
- 有缺陷 → 输出 "❌ 退回修改：{具体问题}"，并 handoff 回 Executor

审查通过后，用简洁清晰的语言将最终结果反馈给用户。
不要做计划或执行工作。
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[],
)


# =============================================================================
# Handoff 编排
# =============================================================================

async def run_planner_executor_reviewer(user_input: str):
    """
    运行三角色协作流程。

    由于 Agents SDK 的 handoff 是 Agent 间直接转移，我们用如下方式：
    1. Planner 接收用户输入，输出计划
    2. Executor 接收计划，逐步执行
    3. Reviewer 审查 Executor 结果
    4. 如果不通过，Reviewer handoff 回 Executor
    """

    print("\n" + "=" * 60)
    print(f"📋 用户需求：{user_input}")
    print("=" * 60)

    with trace("Planner-Executor-Reviewer"):
        # Phase 1: Planner 规划
        print("\n🧠 [Planner] 正在分析需求并制定计划...")
        plan_result = await Runner.run(
            planner,
            f"请为以下需求制定执行计划：\n\n{user_input}",
        )
        plan = plan_result.final_output
        print(f"\n📐 执行计划：\n{plan}")

        # Phase 2: Executor 执行
        print("\n⚙️  [Executor] 正在执行计划...")
        exec_result = await Runner.run(
            executor,
            f"请按以下计划执行：\n\n{plan}\n\n原始需求回顾：{user_input}",
        )
        execution_output = exec_result.final_output
        print(f"\n📝 执行结果：\n{execution_output}")

        # Phase 3: Reviewer 审查
        print("\n🔍 [Reviewer] 正在审查...")
        review_result = await Runner.run(
            reviewer,
            f"请审查以下内容：\n\n## 原始需求\n{user_input}\n\n## 执行计划\n{plan}\n\n## 执行结果\n{execution_output}",
        )
        review_output = review_result.final_output

        # Phase 4: 如果不通过，退回 Executor 修改（最多 3 轮）
        max_rounds = 3
        current_round = 1
        final_output = execution_output

        while "❌" in review_output and current_round <= max_rounds:
            print(f"\n🔄 [Reviewer] 退回第 {current_round} 轮修改：\n{review_output}")

            # Executor 根据反馈修改
            revise_result = await Runner.run(
                executor,
                f"Reviewer 退回修改，请根据反馈改进：\n\n## 原始需求\n{user_input}\n\n## 之前结果\n{final_output}\n\n## Reviewer 反馈\n{review_output}\n\n请改进后重新输出。",
            )
            final_output = revise_result.final_output
            print(f"\n📝 第 {current_round} 轮修改结果：\n{final_output}")

            # 重新审查
            review_result = await Runner.run(
                reviewer,
                f"请重新审查：\n\n## 原始需求\n{user_input}\n\n## 修改结果\n{final_output}\n\n## 上次反馈\n{review_output}",
            )
            review_output = review_result.final_output
            current_round += 1

        # 最终输出
        if "✅" in review_output:
            print(f"\n✅ 审查通过！")
        else:
            print(f"\n⚠️  达到最大修改轮次，采纳最后结果。")

        print(f"\n{'=' * 60}")
        print(f"📊 最终输出：\n{final_output}")
        print("=" * 60)

        return {
            "plan": plan,
            "execution": execution_output,
            "review": review_output,
            "final": final_output,
            "rounds": current_round,
        }


# =============================================================================
# 内置测试用例
# =============================================================================

TEST_CASES = [
    "写一篇100字关于AI的文章",
    "搜索关于Multi-Agent的知识并总结",
    "搜索AI和Agent的知识，然后写一个对比分析",
    "计算 (100 + 200) * 3，然后搜索AI相关知识",
]


async def run_tests():
    """批量运行测试用例"""
    print("\n" + "🧪" * 30)
    print("  测试模式：运行内置测试用例")
    print("🧪" * 30)

    results = []
    for i, task in enumerate(TEST_CASES, 1):
        print(f"\n\n{'#' * 60}")
        print(f"#  测试 {i}/{len(TEST_CASES)}")
        print(f"{'#' * 60}")
        try:
            result = await run_planner_executor_reviewer(task)
            results.append({"task": task, "status": "✅", "rounds": result["rounds"]})
        except Exception as e:
            results.append({"task": task, "status": f"❌ {e}", "rounds": 0})
            print(f"\n❌ 测试失败：{e}")

    # 汇总
    print("\n\n" + "📊" * 30)
    print("  测试汇总")
    print("📊" * 30)
    for r in results:
        print(f"  {r['status']} [{r['rounds']}轮] {r['task']}")


async def interactive():
    """交互模式"""
    print("\n🤖 Multi-Agent 协作系统已启动")
    print("   角色：Planner → Executor → Reviewer")
    print("   输入 'quit' 退出\n")

    while True:
        user_input = input("👤 请输入需求 > ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue
        await run_planner_executor_reviewer(user_input)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Planner/Executor/Reviewer 三角色协作")
    parser.add_argument("--test", action="store_true", help="运行内置测试用例")
    parser.add_argument("--task", type=str, help="单次任务输入")
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_tests())
    elif args.task:
        asyncio.run(run_planner_executor_reviewer(args.task))
    else:
        asyncio.run(interactive())
