"""
第 4 月 Week 2：A2A 协议入门 — Agent Card、任务委托
===========================================================================
模拟 A2A 协议核心概念，理解 Agent 间通信的设计思想。

Day 1-2：Agent Card 定义与 Agent 注册/发现
Day 3-4：Task 生命周期管理
Day 5-6：完整委托流程（发现 → 委托 → 执行 → 返回）
Day 7：复盘笔记

核心设计：
  1. AgentCard — 数字名片，声明能力
  2. Task — 有状态的工作单元（submitted → working → completed/failed）
  3. AgentRegistry — 服务发现（类比 DNS）
  4. Delegation — 任务委托（类比 HTTP 请求）

用法：
  python a2a_simulator.py                    # 交互模式
  python a2a_simulator.py --test             # 运行内置测试
  python a2a_simulator.py --task "需求"       # 单次委托
"""

import asyncio
import argparse
import os
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from agents import Agent, Runner, trace, function_tool
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
# Part 1: Agent Card — A2A 的核心发现机制
# =============================================================================

@dataclass
class AgentSkill:
    """Agent 的一项技能"""
    name: str
    description: str
    examples: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)  # 匹配关键词


@dataclass
class AgentCard:
    """Agent 的数字名片（对应 A2A AgentCard JSON）

    A2A 中这是客户端发现 Agent 的唯一入口：
    GET /.well-known/agent-card.json → 返回此 JSON
    """
    name: str
    description: str
    endpoint: str  # 通信端点（实际 A2A 是 URL，这里简化为标识符）
    version: str = "1.0.0"
    skills: list[AgentSkill] = field(default_factory=list)
    capabilities: dict = field(default_factory=lambda: {
        "streaming": False,
        "push_notifications": False,
    })

    def to_json(self) -> str:
        import json as _json
        return _json.dumps({
            "name": self.name,
            "description": self.description,
            "url": self.endpoint,
            "version": self.version,
            "skills": [asdict(s) for s in self.skills],
            "capabilities": self.capabilities,
        }, ensure_ascii=False, indent=2)

    def score_relevance(self, query: str) -> float:
        """计算此 Agent 对查询的相关性分数（简单关键词匹配）"""
        query_lower = query.lower()
        score = 0.0
        for skill in self.skills:
            # 技能名匹配
            if skill.name.lower() in query_lower or any(
                kw.lower() in query_lower for kw in skill.keywords
            ):
                score += 1.0
            # 示例匹配加分
            for ex in skill.examples:
                if ex.lower() in query_lower:
                    score += 0.5
        return score


# =============================================================================
# Part 2: Agent 注册中心 — 模拟 A2A Agent Discovery
# =============================================================================

class AgentRegistry:
    """Agent 注册中心

    实际 A2A 中，Agent Discovery 可以通过：
    1. 静态配置（已知的 agent-card URL）
    2. DNS-based discovery
    3. 注册中心服务

    这里用内存注册表模拟。
    """
    def __init__(self):
        self._cards: dict[str, AgentCard] = {}

    def register(self, card: AgentCard):
        self._cards[card.name] = card

    def discover(self, query: str, top_k: int = 3) -> list[tuple[AgentCard, float]]:
        """根据查询发现合适的 Agent（按相关性排序）"""
        scored = []
        for card in self._cards.values():
            s = card.score_relevance(query)
            if s > 0:
                scored.append((card, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get(self, name: str) -> Optional[AgentCard]:
        return self._cards.get(name)

    def list_all(self) -> list[AgentCard]:
        return list(self._cards.values())


# =============================================================================
# Part 3: Task 生命周期管理
# =============================================================================

class TaskStatus(str, Enum):
    """A2A Task 状态机"""
    SUBMITTED = "submitted"   # 已提交，等待处理
    WORKING = "working"       # 正在执行
    COMPLETED = "completed"   # 成功完成
    FAILED = "failed"         # 执行失败
    CANCELED = "canceled"     # 已取消


@dataclass
class Task:
    """A2A 任务对象

    A2A 规范中 Task 是核心概念：
    - 有唯一 ID
    - 有明确定义的状态机
    - 支持长任务轮询
    - 可关联 contextId 分组
    """
    id: str
    description: str
    status: TaskStatus = TaskStatus.SUBMITTED
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    context_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    @property
    def elapsed_ms(self) -> float:
        end = self.completed_at or time.time()
        return (end - self.created_at) * 1000

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "context_id": self.context_id,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }


class TaskManager:
    """任务管理器"""
    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def create(self, description: str, context_id: str = None) -> Task:
        t = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            context_id=context_id,
        )
        self._tasks[t.id] = t
        return t

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_all(self) -> list[Task]:
        return list(self._tasks.values())

    def stats(self) -> dict:
        tasks = self.list_all()
        return {
            "total": len(tasks),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "working": sum(1 for t in tasks if t.status == TaskStatus.WORKING),
        }


# =============================================================================
# Part 4: Remote Agent 定义
# =============================================================================

@function_tool
def search_knowledge(query: str) -> str:
    """搜索知识库获取信息"""
    kb = {
        "ai": "人工智能(AI)是计算机科学分支，使计算机能执行通常需要人类智能的任务。" 
              "子领域：机器学习、自然语言处理、计算机视觉。",
        "agent": "AI Agent 是能感知环境、决策并行动的自主系统。"
                 "核心组件：感知模块、推理引擎、工具调用、记忆系统。"
                 "代表性框架：LangGraph、CrewAI、AutoGen、OpenAI Agents SDK。",
        "a2a": "A2A(Agent-to-Agent)协议是 Google 开源的 Agent 间通信标准，"
               "由 Linux Foundation 维护。核心概念：\n"
               "1. Agent Card：声明 Agent 身份和能力的 JSON 文档\n"
               "2. Task：有状态的工作单元（submitted→working→completed/failed）\n"
               "3. Message：单轮通信单元，由 Part 组成（text/file/data）\n"
               "4. Artifact：Agent 产出的具体成果（文档、图片、代码等）\n"
               "A2A 与 MCP 互补：MCP 是 Agent↔Tool，A2A 是 Agent↔Agent。",
        "multi-agent": "多 Agent 系统由多个专门化 Agent 协作完成复杂任务。"
                       "常见模式：\n"
                       "- Supervisor/Subagent：一个管理者分配任务给子Agent\n"
                       "- Planner-Executor-Reviewer：规划→执行→审查循环\n"
                       "- Swarm：去中心化的 Agent 群协作\n"
                       "A2A 协议为这些模式提供了标准化的通信层。",
        "python": "Python 是高级编程语言，以简洁易读著称。"
                  "广泛应用于 AI、数据科学、Web 开发、自动化。"
                  "AI 生态：PyTorch、TensorFlow、LangChain、OpenAI SDK。",
    }
    for key, value in kb.items():
        if key in query.lower():
            return value
    # 模糊匹配
    words = query.lower().split()
    for key, value in kb.items():
        if any(w in key for w in words if len(w) > 1):
            return value
    return f"关于「{query}」的知识暂未收录，建议尝试其他关键词。"


@function_tool
def calculate_math(expression: str) -> str:
    """执行数学计算。参数 expression: 数学表达式如 '2+3*4'"""
    try:
        import math
        safe_dict = {"__builtins__": {}, "math": math}
        result = eval(expression, safe_dict)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


# 定义 Remote Agent
REMOTE_AGENTS = {
    "SearchAgent": Agent(
        name="SearchAgent",
        instructions="你是搜索专家。用 search_knowledge 获取信息并整理成清晰回答。",
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
        tools=[search_knowledge],
    ),
    "WriterAgent": Agent(
        name="WriterAgent",
        instructions="你是写作专家。先 search_knowledge 获取信息，再写成结构清晰的文章（有标题分段）。",
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
        tools=[search_knowledge],
    ),
    "MathAgent": Agent(
        name="MathAgent",
        instructions="你是数学专家。用 calculate_math 精确计算并展示步骤。",
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
        tools=[calculate_math],
    ),
    "AnalystAgent": Agent(
        name="AnalystAgent",
        instructions="你是分析专家。先 search_knowledge 获取各方信息，再对比分析异同优劣。",
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=EXTERNAL_CLIENT),
        tools=[search_knowledge],
    ),
}

# AgentCard 注册
AGENT_CARDS = [
    AgentCard("SearchAgent", "知识搜索专家", "search-agent", skills=[
        AgentSkill("搜索知识", "搜索 AI、编程等领域知识", keywords=["搜索", "查找", "什么是", "知识", "介绍"]),
    ]),
    AgentCard("WriterAgent", "写作专家", "writer-agent", skills=[
        AgentSkill("写文章", "撰写文章、报告、总结", keywords=["写", "文章", "总结", "报告", "文档"]),
        AgentSkill("搜索补充", "搜索信息辅助写作", keywords=["搜索", "查找"]),
    ]),
    AgentCard("MathAgent", "数学计算专家", "math-agent", skills=[
        AgentSkill("数学计算", "精确的算术运算", keywords=["计算", "算", "等于", "求和", "乘", "除", "加", "减"]),
    ]),
    AgentCard("AnalystAgent", "信息分析专家", "analyst-agent", skills=[
        AgentSkill("对比分析", "对比不同概念/方案的异同", keywords=["对比", "分析", "区别", "比较", "差异"]),
        AgentSkill("搜索背景", "搜索相关背景信息", keywords=["搜索", "查找"]),
    ]),
]


# =============================================================================
# Part 5: 委托执行引擎（核心）
# =============================================================================

async def delegate(agent_name: str, task_description: str,
                   registry: AgentRegistry, task_mgr: TaskManager) -> Task:
    """核心委托函数 — 模拟 A2A 的 tasks/send

    流程：
    1. 查找 AgentCard（验证 Agent 存在）
    2. 创建 Task（status = submitted）
    3. 执行（status → working → completed/failed）
    4. 返回 Task 对象

    这就是 A2A 的一次完整 tasks/send → tasks/get 流程。
    """
    card = registry.get(agent_name)
    if not card:
        t = task_mgr.create(task_description)
        t.status = TaskStatus.FAILED
        t.error = f"Agent '{agent_name}' 未注册"
        return t

    agent = REMOTE_AGENTS.get(agent_name)
    if not agent:
        t = task_mgr.create(task_description)
        t.status = TaskStatus.FAILED
        t.error = f"Agent '{agent_name}' 没有实现"
        return t

    # 创建任务
    t = task_mgr.create(task_description)
    t.assigned_to = agent_name
    t.status = TaskStatus.WORKING

    # 执行
    try:
        result = await Runner.run(agent, task_description)
        t.result = result.final_output
        t.status = TaskStatus.COMPLETED
    except Exception as e:
        t.error = str(e)
        t.status = TaskStatus.FAILED
    finally:
        t.completed_at = time.time()

    return t


# =============================================================================
# Part 6: 调度器 — 基于规则的委托决策（不是 LLM）
# =============================================================================

def select_agent(query: str, registry: AgentRegistry) -> Optional[AgentCard]:
    """根据用户需求选择最合适的 Agent

    这里用基于规则的方法（不是 LLM），因为：
    1. 更可控、更可预测
    2. 展示 A2A 中"发现"这个步骤的本质
    3. 实际系统中这也是决策逻辑的一部分
    """
    candidates = registry.discover(query)
    if not candidates:
        return None
    # 返回分数最高的
    return candidates[0][0]


async def run_delegation(user_input: str,
                         registry: AgentRegistry,
                         task_mgr: TaskManager) -> dict:
    """执行一次完整的 A2A 委托流程

    对应 A2A 协议的一次完整交互：
    1. Client 分析需求 → 发现合适的 Remote Agent
    2. Client → Remote Agent: tasks/send（发送任务）
    3. Remote Agent 执行（poll 或 streaming）
    4. Client ← Remote Agent: 返回 Task（含结果/Artifact）
    """
    print("\n" + "=" * 60)
    print(f"👤 用户需求：{user_input}")
    print("=" * 60)

    # Step 1: 发现 — 对应 A2A Agent Discovery
    print("\n🔍 [Step 1: Agent 发现]")
    candidates = registry.discover(user_input)
    if not candidates:
        print("  ❌ 未找到合适的 Agent")
        return {"status": "no_agent", "result": "未找到合适的 Agent"}

    print(f"  找到 {len(candidates)} 个候选 Agent：")
    for card, score in candidates:
        skills = ", ".join(s.name for s in card.skills)
        print(f"    📋 {card.name}（得分 {score:.1f}）— {skills}")

    # Step 2: 选择 — 选最高分
    best_card, best_score = candidates[0]
    print(f"\n✅ [Step 2: 选择 Agent] → {best_card.name}（得分 {best_score:.1f}）")
    print(f"   {best_card.description}")
    print(f"   AgentCard JSON: {best_card.to_json()[:200]}...")

    # Step 3: 委托 — 对应 A2A tasks/send
    print(f"\n📤 [Step 3: 任务委托] → {best_card.name}")
    print(f"   📋 任务描述：{user_input}")

    task = await delegate(best_card.name, user_input, registry, task_mgr)

    # Step 4: 结果 — 对应 A2A tasks/get 返回
    print(f"\n📥 [Step 4: 任务完成]")
    print(f"   任务 ID：{task.id}")
    print(f"   状态：{task.status.value}")
    print(f"   耗时：{task.elapsed_ms:.0f}ms")

    if task.status == TaskStatus.COMPLETED:
        print(f"   结果预览：{task.result[:100]}...")
    else:
        print(f"   错误：{task.error}")

    # 输出完整结果
    print(f"\n{'=' * 60}")
    print(f"📊 最终结果：\n{task.result or task.error}")
    print("=" * 60)

    return {
        "status": task.status.value,
        "agent": best_card.name,
        "task_id": task.id,
        "elapsed_ms": task.elapsed_ms,
        "result": task.result or task.error,
        "candidates": [(c.name, s) for c, s in candidates],
    }


# =============================================================================
# 测试与交互
# =============================================================================

TEST_CASES = [
    ("搜索 A2A 协议的知识", "SearchAgent"),
    ("写一篇关于 AI Agent 的文章", "WriterAgent"),
    ("计算 1234 乘以 5678", "MathAgent"),
    ("对比分析 AI Agent 和 Multi-Agent 系统", "AnalystAgent"),
    ("搜索 Python 资料并写总结", "WriterAgent"),  # 写作权重 > 搜索
]

async def run_tests():
    """运行测试用例"""
    registry = AgentRegistry()
    for card in AGENT_CARDS:
        registry.register(card)
    task_mgr = TaskManager()

    print("\n🧪" * 30)
    print("  A2A 任务委托 — 测试模式")
    print("🧪" * 30)

    results = []
    for i, (task_desc, expected_agent) in enumerate(TEST_CASES, 1):
        print(f"\n{'#' * 60}")
        print(f"# 测试 {i}/{len(TEST_CASES)}")
        print(f"# 需求：{task_desc}")
        print(f"# 期望委托给：{expected_agent}")
        print(f"{'#' * 60}")

        try:
            r = await run_delegation(task_desc, registry, task_mgr)
            selected = r["agent"]
            passed = selected == expected_agent
            results.append({
                "task": task_desc,
                "selected": selected,
                "expected": expected_agent,
                "passed": passed,
                "status": r["status"],
                "elapsed_ms": r["elapsed_ms"],
            })
        except Exception as e:
            results.append({
                "task": task_desc,
                "selected": "N/A",
                "expected": expected_agent,
                "passed": False,
                "status": f"error: {str(e)[:50]}",
                "elapsed_ms": 0,
            })

    # 汇总
    print("\n\n" + "=" * 60)
    print("  📊 测试汇总")
    print("=" * 60)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"  委托准确率：{passed_count}/{len(results)}")
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} 选 {r['selected']}（期望 {r['expected']}）| "
              f"{r['status']} | {r['elapsed_ms']:.0f}ms | {r['task']}")

    # Task 统计
    stats = task_mgr.stats()
    print(f"\n  📋 任务统计：共 {stats['total']} 个 | "
          f"完成 {stats['completed']} | 失败 {stats['failed']}")


async def interactive_mode():
    """交互模式"""
    registry = AgentRegistry()
    for card in AGENT_CARDS:
        registry.register(card)
    task_mgr = TaskManager()

    print("\n🤖 A2A 任务委托系统")
    print("  已注册 Agent：", ", ".join(c.name for c in AGENT_CARDS))
    print("  命令：quit 退出 | list 查看 Agent | tasks 查看任务 | card <名> 查看 AgentCard\n")

    while True:
        user_input = input("👤 请输入需求 > ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            stats = task_mgr.stats()
            print(f"📊 本次会话：共 {stats['total']} 个任务，"
                  f"完成 {stats['completed']}，失败 {stats['failed']}")
            break
        if user_input.lower() == "list":
            for card in registry.list_all():
                skills = ", ".join(s.name for s in card.skills)
                print(f"  📋 {card.name}：{card.description}（{skills}）")
            continue
        if user_input.lower().startswith("card "):
            name = user_input[5:].strip()
            card = registry.get(name)
            if card:
                print(card.to_json())
            else:
                print(f"  ❌ 未找到 Agent：{name}")
            continue
        if user_input.lower() == "tasks":
            all_tasks = task_mgr.list_all()
            if not all_tasks:
                print("  暂无任务")
                continue
            for t in sorted(all_tasks, key=lambda x: x.created_at):
                icon = {"completed": "✅", "failed": "❌", "working": "⚙️", "submitted": "📋"}.get(t.status.value, "❓")
                print(f"  {icon} [{t.id}] → {t.assigned_to or '?'} | {t.elapsed_ms:.0f}ms | {t.description[:50]}")
            continue
        if not user_input:
            continue
        await run_delegation(user_input, registry, task_mgr)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A2A 任务委托模拟器")
    parser.add_argument("--test", action="store_true", help="运行内置测试用例")
    parser.add_argument("--task", type=str, help="单次任务输入")
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_tests())
    elif args.task:
        registry = AgentRegistry()
        for card in AGENT_CARDS:
            registry.register(card)
        task_mgr = TaskManager()
        asyncio.run(run_delegation(args.task, registry, task_mgr))
    else:
        asyncio.run(interactive_mode())
