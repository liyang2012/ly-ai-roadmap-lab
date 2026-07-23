"""
第 4 月 Week 3：Supervisor 层次化协作
===========================================================================
将 W1 三角色升级为 Supervisor 架构，实现多 Worker 并行执行。

架构：
  User → Supervisor（分解 + 分发 + 聚合）
            ├── PlannerWorker（规划子任务）
            ├── ExecutorWorker（执行子任务）──┐
            ├── WriterWorker（写作子任务）    ├─ 并行执行
            └── AnalystWorker（分析子任务）──┘

与 W1 的关键区别：
  - W1：Planner→Executor→Reviewer 串行直线
  - W3：Supervisor 同时分发多个子任务 → 并行执行 → 聚合结果

用法：
  python supervisor_agent.py                    # 交互模式
  python supervisor_agent.py --test             # 运行内置测试
  python supervisor_agent.py --task "需求"       # 单次执行
"""

import asyncio
import argparse
import os
import time
import uuid
import json
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

load_dotenv()
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "true"

EXTERNAL_CLIENT = AsyncOpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)
MODEL_NAME = "glm-4-flash"


# =============================================================================
# Tools：复用 W1/W2 的工具
# =============================================================================

@function_tool
def search_knowledge(query: str) -> str:
    """搜索知识库获取信息"""
    kb = {
        "ai": "人工智能(AI)是计算机科学分支，使计算机能执行通常需要人类智能的任务。"
              "子领域：机器学习、自然语言处理、计算机视觉、强化学习。",
        "agent": "AI Agent 是能感知环境、决策并行动的自主系统。"
                 "核心组件：感知模块、推理引擎、工具调用、记忆系统。"
                 "代表性框架：LangGraph、CrewAI、AutoGen、OpenAI Agents SDK。",
        "multi-agent": "多 Agent 系统由多个专门化 Agent 协作完成复杂任务。"
                       "常见模式：\n"
                       "- Supervisor/Subagent：一个管理者分配任务给子Agent\n"
                       "- Planner-Executor-Reviewer：规划→执行→审查循环\n"
                       "- Swarm：去中心化的 Agent 群协作\n"
                       "- Hierarchical：多层嵌套的 Agent 组织",
        "supervisor": "Supervisor 模式是多 Agent 系统的核心架构。"
                      "Supervisor（监督者）负责任务分解、路由分发、结果聚合。"
                      "Worker（工人）负责执行具体子任务。"
                      "优势：关注点分离、并行执行、容错隔离、易于扩展。"
                      "适用场景：复杂多步骤任务、需要并行处理的场景。",
        "langgraph": "LangGraph 是 LangChain 的图编排框架。"
                     "核心概念：StateGraph、节点、边、条件路由。"
                     "天然支持 Supervisor 模式：用条件边实现任务路由。"
                     "支持 Checkpoint 持久化和 Human-in-the-Loop。",
        "python": "Python 是高级编程语言，以简洁易读著称。"
                  "广泛应用于 AI、数据科学、Web 开发、自动化。",
    }
    for key, value in kb.items():
        if key in query.lower():
            return value
    words = query.lower().split()
    for key, value in kb.items():
        if any(w in key for w in words if len(w) > 1):
            return value
    return f"关于「{query}」的知识暂未收录，建议尝试其他关键词。"


@function_tool
def calculate_math(expression: str) -> str:
    """执行数学计算。expression: 数学表达式如 '2+3*4'"""
    try:
        import math as _m
        safe_dict = {"__builtins__": {}, "math": _m}
        result = eval(expression, safe_dict)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


# =============================================================================
# Worker Agent 定义（复用 W1 三角色概念，改造为并行 Worker）
# =============================================================================

planner_worker = Agent(
    name="PlannerWorker",
    instructions="""你是 PlannerWorker，专门负责规划和分解任务。
当你收到一个子任务时：
1. 分析任务目标
2. 用 search_knowledge 获取背景信息
3. 输出结构化的执行计划（编号步骤列表）
4. 只做规划，不执行具体步骤

输出格式：
## 任务分析
（简要分析）

## 执行计划
步骤1：...
步骤2：...
步骤3：...
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[search_knowledge],
)

executor_worker = Agent(
    name="ExecutorWorker",
    instructions="""你是 ExecutorWorker，专门负责执行具体操作。
当收到一个子任务时：
1. 用 search_knowledge 获取所需信息
2. 如涉及计算，用 calculate_math 精确计算
3. 逐项执行并输出详细结果

输出格式：
## 执行过程
（每步做了什么、调用了什么工具）

## 执行结果
（最终结果）
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[search_knowledge, calculate_math],
)

writer_worker = Agent(
    name="WriterWorker",
    instructions="""你是 WriterWorker，专门负责写作和内容生成。
收到子任务时：
1. 用 search_knowledge 获取主题信息
2. 撰写结构清晰的文章（有标题、分段）
3. 语言流畅、逻辑清晰

输出格式：
## {标题}
（正文内容）
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[search_knowledge],
)

analyst_worker = Agent(
    name="AnalystWorker",
    instructions="""你是 AnalystWorker，专门负责对比分析和给出建议。
收到子任务时：
1. 用 search_knowledge 获取各方的信息
2. 从多个维度进行对比分析
3. 给出结论和建议

输出格式：
## 对比分析
| 维度 | 方案A | 方案B |

## 结论与建议
（具体建议）
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[search_knowledge],
)


# =============================================================================
# Supervisor 调度核心
# =============================================================================

class SubtaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Subtask:
    """Supervisor 分发的子任务"""
    id: str
    description: str
    worker_name: str  # 分配给哪个 Worker
    status: SubtaskStatus = SubtaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def elapsed_ms(self) -> float:
        if not self.started_at:
            return 0
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000


@dataclass
class SupervisorResult:
    """Supervisor 完整执行结果"""
    original_request: str
    subtask_count: int
    subtasks: list[Subtask]
    aggregated_output: str
    total_elapsed_ms: float


# Worker 注册表
WORKERS = {
    "PlannerWorker": planner_worker,
    "ExecutorWorker": executor_worker,
    "WriterWorker": writer_worker,
    "AnalystWorker": analyst_worker,
}

# Worker 能力描述
WORKER_CAPABILITIES = {
    "PlannerWorker": {
        "description": "任务规划和分解",
        "keywords": ["规划", "分解", "步骤", "计划", "分析任务", "梳理"],
    },
    "ExecutorWorker": {
        "description": "执行操作和计算",
        "keywords": ["执行", "计算", "搜索", "操作", "处理", "获取"],
    },
    "WriterWorker": {
        "description": "写作和内容生成",
        "keywords": ["写", "文章", "总结", "报告", "文档", "撰写", "生成"],
    },
    "AnalystWorker": {
        "description": "对比分析和建议",
        "keywords": ["对比", "分析", "比较", "区别", "优劣", "建议", "评估"],
    },
}


# =============================================================================
# 步骤 1：Supervisor 分解任务
# =============================================================================

supervisor_planner = Agent(
    name="SupervisorPlanner",
    instructions=f"""你是 Supervisor（监督者），负责将用户需求分解为可并行执行的子任务。

可用 Worker 及其能力：
{json.dumps({k: v["description"] for k, v in WORKER_CAPABILITIES.items()}, ensure_ascii=False, indent=2)}

规则：
1. 分析需求中哪些部分可以并行执行
2. 每个子任务分配给最合适的 Worker
3. 子任务之间应该尽量独立，减少依赖
4. 如果需求简单，1-2 个子任务即可；复杂需求 3-5 个
5. 输出格式必须是 JSON 数组

输出格式（只输出 JSON，不要其他文字）：
[
  {{"worker": "WorkerName", "task": "子任务描述"}},
  ...
]

示例：
用户："写一篇 AI Agent 的文章并做技术分析"
输出：
[
  {{"worker": "WriterWorker", "task": "撰写一篇关于 AI Agent 的科普文章，包含定义、核心组件、代表性框架"}},
  {{"worker": "AnalystWorker", "task": "对比分析 AI Agent 主要框架（LangGraph/CrewAI/AutoGen）的优劣"}}
]
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[],
)


async def supervisor_plan(user_request: str) -> list[dict]:
    """Supervisor 分解用户需求为子任务列表"""
    result = await Runner.run(
        supervisor_planner,
        f"请将以下用户需求分解为子任务：\n\n{user_request}",
    )
    raw = result.final_output.strip()

    # 尝试提取 JSON（处理 LLM 可能输出的额外文本）
    try:
        # 找第一个 [ 和最后一个 ]
        start = raw.index("[")
        end = raw.rindex("]") + 1
        json_str = raw[start:end]
        subtasks = json.loads(json_str)
        return subtasks
    except (ValueError, json.JSONDecodeError):
        # 兜底：简单拆分
        print(f"  ⚠️ JSON 解析失败，使用默认拆分")
        return [{"worker": "ExecutorWorker", "task": user_request}]


# =============================================================================
# 步骤 2：并行执行子任务
# =============================================================================

async def execute_subtask(subtask: Subtask) -> Subtask:
    """执行单个子任务"""
    worker = WORKERS.get(subtask.worker_name)
    if not worker:
        subtask.status = SubtaskStatus.FAILED
        subtask.error = f"Worker '{subtask.worker_name}' 不存在"
        subtask.completed_at = time.time()
        return subtask

    subtask.status = SubtaskStatus.RUNNING
    subtask.started_at = time.time()

    try:
        result = await Runner.run(worker, subtask.description)
        subtask.result = result.final_output
        subtask.status = SubtaskStatus.COMPLETED
    except Exception as e:
        subtask.error = str(e)
        subtask.status = SubtaskStatus.FAILED
    finally:
        subtask.completed_at = time.time()

    return subtask


async def execute_parallel(subtasks: list[Subtask]) -> list[Subtask]:
    """并行执行所有子任务"""
    tasks = [execute_subtask(st) for st in subtasks]
    return list(await asyncio.gather(*tasks))


# =============================================================================
# 步骤 3：Supervisor 聚合结果
# =============================================================================

supervisor_aggregator = Agent(
    name="SupervisorAggregator",
    instructions="""你是 Supervisor（监督者），负责聚合多个 Worker 的执行结果。

你的任务：
1. 阅读所有 Worker 的输出
2. 检查结果是否完整覆盖用户需求
3. 整合为一份统一的输出报告
4. 标注每个 Worker 的贡献

输出格式：
## 📊 执行概览
（本次协作的基本信息：Worker 数量、状态等）

## 📋 各 Worker 结果
（按 Worker 整理输出）

## ✅ 总结
（对用户需求的完整回应）
""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
    tools=[],
)


async def aggregate_results(user_request: str, subtasks: list[Subtask]) -> str:
    """聚合子任务结果"""
    # 构建 Worker 结果摘要
    worker_reports = []
    for st in subtasks:
        status_icon = "✅" if st.status == SubtaskStatus.COMPLETED else "❌"
        worker_reports.append(
            f"### {status_icon} {st.worker_name}（{st.elapsed_ms:.0f}ms）\n"
            f"**子任务**：{st.description}\n\n"
            f"**结果**：\n{st.result or st.error}"
        )

    combined = "\n\n---\n\n".join(worker_reports)

    result = await Runner.run(
        supervisor_aggregator,
        f"用户需求：{user_request}\n\n以下各 Worker 的执行结果，请整合为统一报告：\n\n{combined}",
    )
    return result.final_output


# =============================================================================
# 完整 Supervisor 流程
# =============================================================================

async def run_supervisor(user_request: str) -> SupervisorResult:
    """运行完整 Supervisor 流程：分解 → 并行执行 → 聚合"""
    started = time.time()

    print("\n" + "=" * 65)
    print(f"  👤 用户需求：{user_request}")
    print("=" * 65)

    # Step 1: 分解
    print("\n🧠 [Supervisor] 正在分析需求并分解任务...")
    plan = await supervisor_plan(user_request)
    print(f"  → 分解为 {len(plan)} 个子任务：")
    for i, p in enumerate(plan):
        print(f"    {i+1}. [{p['worker']}] {p['task']}")

    # 创建 Subtask 对象
    subtasks = [
        Subtask(
            id=f"sub_{i+1}",
            description=p["task"],
            worker_name=p["worker"],
        )
        for i, p in enumerate(plan)
    ]

    # Step 2: 并行执行
    print(f"\n⚙️  [Supervisor] 分发 {len(subtasks)} 个子任务 → 并行执行...")
    print(f"  {'─' * 50}")

    async def execute_with_log(st: Subtask) -> Subtask:
        print(f"  🚀 [{st.worker_name}] 开始执行：{st.description[:40]}...")
        result = await execute_subtask(st)
        icon = "✅" if result.status == SubtaskStatus.COMPLETED else "❌"
        print(f"  {icon} [{st.worker_name}] 完成（{result.elapsed_ms:.0f}ms）")
        return result

    tasks = [execute_with_log(st) for st in subtasks]
    completed_subtasks = list(await asyncio.gather(*tasks))

    print(f"  {'─' * 50}")

    # 统计
    completed = sum(1 for st in completed_subtasks if st.status == SubtaskStatus.COMPLETED)
    failed = len(completed_subtasks) - completed
    print(f"  📊 完成 {completed}/{len(completed_subtasks)}，失败 {failed}")

    # Step 3: 聚合
    print(f"\n📋 [Supervisor] 正在聚合结果...")
    aggregated = await aggregate_results(user_request, completed_subtasks)

    total_elapsed = (time.time() - started) * 1000
    print(f"\n{'=' * 65}")
    print(f"  📊 最终结果（总耗时 {total_elapsed:.0f}ms）")
    print(f"{'=' * 65}\n")
    print(aggregated)
    print(f"\n{'=' * 65}")

    return SupervisorResult(
        original_request=user_request,
        subtask_count=len(subtasks),
        subtasks=completed_subtasks,
        aggregated_output=aggregated,
        total_elapsed_ms=total_elapsed,
    )


# =============================================================================
# 测试用例
# =============================================================================

TEST_CASES = [
    # 简单单任务
    {"request": "搜索 AI Agent 的知识并总结", "expected_workers": 1},
    # 双任务并行（写作 + 分析）
    {"request": "介绍 AI Agent 的概念并对比 LangGraph 和 CrewAI", "expected_workers": 2},
    # 多任务并行（规划 + 写作 + 分析）
    {
        "request": "规划一个多 Agent 系统的架构设计，写一篇总结文章，并分析各框架的优劣",
        "expected_workers": 3,
    },
    # 计算 + 搜索
    {"request": "搜索 Python 的知识，然后计算 1234 * 5678", "expected_workers": 2},
]


async def run_tests():
    """运行测试用例"""
    print("\n🧪" * 30)
    print("  Supervisor 层次化协作 — 测试模式")
    print("🧪" * 30)

    results = []
    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n{'#' * 65}")
        print(f"# 测试 {i}/{len(TEST_CASES)}")
        print(f"# 需求：{tc['request']}")
        print(f"{'#' * 65}")

        try:
            result = await run_supervisor(tc["request"])
            completed = sum(1 for st in result.subtasks if st.status == SubtaskStatus.COMPLETED)
            results.append({
                "task": tc["request"],
                "passed": completed == len(result.subtasks) and len(result.subtasks) > 0,
                "workers_used": len(result.subtasks),
                "completed": completed,
                "total_ms": result.total_elapsed_ms,
            })
        except Exception as e:
            results.append({
                "task": tc["request"],
                "passed": False,
                "workers_used": 0,
                "completed": 0,
                "total_ms": 0,
                "error": str(e)[:80],
            })

    # 汇总
    print("\n\n" + "=" * 65)
    print("  📊 测试汇总")
    print("=" * 65)
    passed = sum(1 for r in results if r["passed"])
    print(f"  通过率：{passed}/{len(results)}")
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        error = f" | 错误：{r.get('error', '')}" if not r["passed"] else ""
        print(f"  {icon} Workers: {r['workers_used']} | "
              f"完成: {r['completed']} | {r['total_ms']:.0f}ms | {r['task'][:50]}...{error}")


async def interactive_mode():
    """交互模式"""
    print("\n🤖 Supervisor 层次化协作系统")
    print("  Supervisor 管理以下 Worker：")
    for name, cap in WORKER_CAPABILITIES.items():
        print(f"    👷 {name} — {cap['description']}")
    print("  命令：quit 退出 | workers 查看 Worker | info 查看架构说明\n")

    while True:
        user_input = input("👤 请输入需求 > ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if user_input.lower() == "workers":
            for name, cap in WORKER_CAPABILITIES.items():
                keywords = ", ".join(cap["keywords"])
                print(f"  👷 {name}：{cap['description']}（关键词：{keywords}）")
            continue
        if user_input.lower() == "info":
            print("""
  🏗️  Supervisor 架构说明
  ═══════════════════════════
  Supervisor 是管弦乐队指挥，Worker 是乐手：
  
  用户 → Supervisor（分解 + 分发 + 聚合）
              ├── PlannerWorker   — 规划分解
              ├── ExecutorWorker  — 执行操作  ⎤
              ├── WriterWorker    — 内容写作  ⎥ 并行
              └── AnalystWorker   — 对比分析  ⎦

  与 W1 三角色区别：
  - W1：串行直线（P→E→R），单任务流转
  - W3：并行分发，多任务同时执行，效率更高
""")
            continue
        if not user_input:
            continue
        await run_supervisor(user_input)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supervisor 层次化协作系统")
    parser.add_argument("--test", action="store_true", help="运行内置测试用例")
    parser.add_argument("--task", type=str, help="单次任务输入")
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_tests())
    elif args.task:
        asyncio.run(run_supervisor(args.task))
    else:
        asyncio.run(interactive_mode())
