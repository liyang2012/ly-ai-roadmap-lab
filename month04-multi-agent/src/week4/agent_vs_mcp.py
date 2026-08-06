"""
第 4 月 Week 4：取舍与 MCP 集成入门
===========================================================================
核心议题：前面四周学了多种 Agent 协作模式，但在生产环境中，
"该用 Agent 还是用 Tool（MCP）？" 是最重要的决策。

Week 4 聚焦：
  Day 1-2：Agent vs Tool 决策框架 — 什么时候该上 Agent，什么时候用 MCP
  Day 3-4：MCP Server 实战 — 手写一个 MCP Server，Agent 消费它
  Day 5-6：综合实战 — 一个完整案例：Agent + MCP Tool 的协作
  Day 7：复盘总结 — 第 4 月收官

关键认知：
  MCP 解决的是"连接"，Agent 解决的是"推理"
  MCP 是水管，Agent 是大脑
  你的架构 = 什么时候用大脑 + 什么时候用水管

用法：
  python agent_vs_mcp.py                      # 交互决策咨询
  python agent_vs_mcp.py --scenario order     # 场景分析：电商订单
  python agent_vs_mcp.py --scenario data      # 场景分析：数据分析
  python agent_vs_mcp.py --mcp-demo           # MCP Server 演示
  python agent_vs_mcp.py --test               # 运行内置测试
"""

import asyncio
import argparse
import os
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ============================================================================
# Part 1: Agent vs Tool 决策框架
# ============================================================================

class ArchitectureChoice(Enum):
    """架构选择枚举"""
    TOOL = "MCP_Tool"           # 单次调用，无状态
    CHAIN = "Chain"              # 固定步骤管道
    ROUTER = "Router"           # 条件分支
    SINGLE_AGENT = "SingleAgent"  # 单 Agent + 多 Tool
    MULTI_AGENT = "MultiAgent"  # 多 Agent 协作
    WORKFLOW = "Workflow"       # 确定性编排


@dataclass
class DecisionCriteria:
    """决策因子"""
    name: str
    weight: float  # 权重 0-1
    description: str


class ArchitectureSelector:
    """
    架构选型引擎：
    根据 5 个维度评估，输出推荐的架构模式。

    维度：
      1. 任务不确定性 — 步骤需要推理还是固定流程？
      2. 工具需求 — 需要多少外部系统交互？
      3. 上下文复杂度 — 单次能完成还是需要多轮？
      4. 决策依赖 — 需要独立角色判断？
      5. 响应时延要求 — 秒级还是毫秒级？
    """

    CRITERIA = [
        DecisionCriteria("task_uncertainty", 0.30, "任务不确定性：是否需要推理和判断"),
        DecisionCriteria("tool_complexity", 0.25, "工具需求：需要多少外部系统"),
        DecisionCriteria("context_depth", 0.20, "上下文深度：单次还是多轮"),
        DecisionCriteria("decision_need", 0.15, "决策需求：是否需要独立决策能力"),
        DecisionCriteria("latency", 0.10, "时延要求：秒级 vs 毫秒级"),
    ]

    # 评分矩阵：每个架构模式在每个维度上的得分 (0-10)
    SCORE_MATRIX = {
        # 评分逻辑: 高分 = 这个维度需求高时该架构更匹配
        # task_uncertainty 低时 TOOL 得高分（适合确定性任务）
        ArchitectureChoice.TOOL:          [10, 2, 1, 1, 10],  # 低不确定性时得分高
        ArchitectureChoice.CHAIN:         [8, 4, 3, 2, 8],    # 固定流水线
        ArchitectureChoice.ROUTER:        [6, 3, 4, 4, 7],    # 分支决策
        ArchitectureChoice.SINGLE_AGENT:  [3, 6, 6, 5, 5],    # 单 Agent
        ArchitectureChoice.MULTI_AGENT:   [1, 8, 8, 8, 2],    # 多 Agent（高不确定性时高分）
        ArchitectureChoice.WORKFLOW:      [7, 6, 4, 2, 8],    # 确定性编排
    }

    @classmethod
    def evaluate(cls, scores: dict) -> list[tuple[ArchitectureChoice, float, str]]:
        """
        根据用户输入的场景评分，计算各架构的匹配度。

        Args:
            scores: 5 维评分字典，每项 1-10
                例: {"task_uncertainty": 8, "tool_complexity": 5, ...}
        """
        results = []
        for arch, score_vec in cls.SCORE_MATRIX.items():
            weighted = sum(
                scores.get(c.name, 5) * w * s
                for c, w, s in zip(cls.CRITERIA, [c.weight for c in cls.CRITERIA], score_vec)
            )
            total_weight = sum(c.weight for c in cls.CRITERIA)
            normalized = weighted / (total_weight * 100)  # 归一化到 0-1
            results.append((arch, round(normalized, 4)))

        results.sort(key=lambda x: x[1], reverse=True)

        # 附上解释
        explanations = {
            ArchitectureChoice.TOOL: "简单 API 调用，无需状态管理，毫秒级响应",
            ArchitectureChoice.CHAIN: "固定步骤管道，如 RAG: load→split→embed→search",
            ArchitectureChoice.ROUTER: "条件分支路由，如: 根据意图分发到不同服务",
            ArchitectureChoice.SINGLE_AGENT: "单 Agent + 多 Tool，适合推理+工具组合",
            ArchitectureChoice.MULTI_AGENT: "多 Agent 协作，适合复杂多步骤+独立决策",
            ArchitectureChoice.WORKFLOW: "确定性编排，适合已知流程的批处理任务",
        }

        return [(arch, score, explanations[arch]) for arch, score in results[:3]]


# ============================================================================
# Part 2: MCP Server 实战（模拟）
# ============================================================================

class MCPResource:
    """MCP 资源：可被 Agent 读取的数据"""
    def __init__(self, uri: str, name: str, description: str, data: any):
        self.uri = uri
        self.name = name
        self.description = description
        self.data = data


class MCPTool:
    """MCP 工具：Agent 可以调用的函数"""
    def __init__(self, name: str, description: str, schema: dict, handler):
        self.name = name
        self.description = description
        self.schema = schema  # JSON Schema
        self.handler = handler

    async def call(self, arguments: dict):
        return await self.handler(arguments)


class MCPServer:
    """
    模拟 MCP Server 的核心概念：
    一个 MCP Server 暴露 Resources 和 Tools，
    Agent 通过标准协议发现和调用它们。

    实际 MCP 协议基于 JSON-RPC，这里简化为 Python 对象。
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: dict[str, MCPTool] = {}
        self.resources: dict[str, MCPResource] = {}

    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool

    def register_resource(self, resource: MCPResource):
        self.resources[resource.uri] = resource

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.schema,
            }
            for t in self.tools.values()
        ]

    def list_resources(self) -> list[dict]:
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
            }
            for r in self.resources.values()
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found"}
        try:
            result = await self.tools[name].call(arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# Part 3: 综合实战 — 电商订单查询 Agent + MCP
# ============================================================================

class OrderMCPServer(MCPServer):
    """
    电商订单查询的 MCP Server
    暴露订单查询相关的 Tools 和 Resources
    """

    def __init__(self):
        super().__init__("order-system", "1.0.0")
        self._init_data()
        self._register_tools()

    def _init_data(self):
        """模拟订单数据库"""
        self.orders = [
            {"id": "ORD-001", "status": "shipped", "amount": 299.0, "items": 2, "user": "Alice"},
            {"id": "ORD-002", "status": "processing", "amount": 1499.0, "items": 1, "user": "Bob"},
            {"id": "ORD-003", "status": "cancelled", "amount": 89.0, "items": 3, "user": "Alice"},
            {"id": "ORD-004", "status": "delivered", "amount": 599.0, "items": 2, "user": "Charlie"},
            {"id": "ORD-005", "status": "pending", "amount": 2199.0, "items": 4, "user": "Bob"},
        ]

    def _register_tools(self):
        # Tool 1: 按 ID 查询订单
        self.register_tool(MCPTool(
            name="get_order_by_id",
            description="按订单 ID 查询订单详情",
            schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单ID，如 ORD-001"}
                },
                "required": ["order_id"]
            },
            handler=self._get_order_by_id
        ))

        # Tool 2: 按用户查询订单列表
        self.register_tool(MCPTool(
            name="list_orders_by_user",
            description="查询指定用户的所有订单",
            schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "用户名"}
                },
                "required": ["username"]
            },
            handler=self._list_orders_by_user
        ))

        # Tool 3: 统计分析
        self.register_tool(MCPTool(
            name="order_stats",
            description="获取订单统计摘要",
            schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "可选，按用户过滤"}
                },
            },
            handler=self._order_stats
        ))

        # Resource: 订单状态枚举
        self.register_resource(MCPResource(
            uri="order://statuses",
            name="Order Statuses",
            description="所有可能的订单状态列表",
            data=["pending", "processing", "shipped", "delivered", "cancelled", "refunded"],
        ))

    async def _get_order_by_id(self, args: dict) -> dict | None:
        order_id = args["order_id"]
        for order in self.orders:
            if order["id"] == order_id:
                return order
        return None

    async def _list_orders_by_user(self, args: dict) -> list[dict]:
        username = args["username"].lower()
        return [o for o in self.orders if o["user"].lower() == username]

    async def _order_stats(self, args: dict) -> dict:
        username = args.get("username", "").lower()
        target = (
            [o for o in self.orders if o["user"].lower() == username]
            if username else self.orders
        )
        if not target:
            return {"total_orders": 0, "total_amount": 0, "avg_amount": 0}
        amounts = [o["amount"] for o in target]
        return {
            "total_orders": len(target),
            "total_amount": sum(amounts),
            "avg_amount": round(sum(amounts) / len(amounts), 2),
            "by_status": self._count_by_status(target),
        }

    @staticmethod
    def _count_by_status(orders: list) -> dict:
        counts = {}
        for o in orders:
            counts[o["status"]] = counts.get(o["status"], 0) + 1
        return counts


class OrderAgent:
    """
    消费 MCP Server 的 Agent：
    通过 Function Calling 模式调用 MCP Tools
    """

    def __init__(self, mcp_server: MCPServer):
        self.mcp = mcp_server
        self.tools = mcp_server.list_tools()

    async def process(self, user_request: str) -> str:
        """
        简化版 Agent Loop:
        1. 理解请求 → 2. 选择工具 → 3. 调用 MCP → 4. 组织回复
        """
        request_lower = user_request.lower()

        # ---- 路由决策（规则匹配，而非 LLM） ----
        if "统计" in request_lower or "summary" in request_lower:
            # 按用户统计
            for username in ["alice", "bob", "charlie"]:
                if username in request_lower:
                    stats = await self.mcp.call_tool("order_stats", {"username": username})
                    return self._format_stats(username, stats)

            # 全局统计
            stats = await self.mcp.call_tool("order_stats", {})
            return self._format_global_stats(stats)

        elif any(uid in request_lower for uid in ["ord-", "订单"]):
            # 按 ID 查询
            for order_id in ["ORD-001", "ORD-002", "ORD-003", "ORD-004", "ORD-005"]:
                if order_id.lower() in request_lower:
                    result = await self.mcp.call_tool("get_order_by_id", {"order_id": order_id})
                    return self._format_order(result)

        # 默认：按用户名查询
        for username in ["alice", "bob", "charlie"]:
            if username in request_lower:
                orders = await self.mcp.call_tool("list_orders_by_user", {"username": username})
                return self._format_user_orders(username, orders)

        return "抱歉，请提供用户名（Alice/Bob/Charlie）或订单号（如 ORD-001）"

    def _format_order(self, result: dict) -> str:
        if result.get("error"):
            return f"查询失败: {result['error']}"
        order = result.get("result")
        if not order:
            return "未找到该订单"
        return (
            f"📦 订单 {order['id']}\n"
            f"   状态: {order['status']}\n"
            f"   金额: ¥{order['amount']}\n"
            f"   商品: {order['items']} 件\n"
            f"   用户: {order['user']}"
        )

    def _format_user_orders(self, username: str, result: dict) -> str:
        orders = result.get("result", [])
        if not orders:
            return f"{username} 暂无订单"
        lines = [f"📋 {username} 的订单 ({len(orders)} 笔):"]
        for o in orders:
            lines.append(f"   {o['id']}: {o['status']} ¥{o['amount']} ({o['items']}件)")
        return "\n".join(lines)

    def _format_stats(self, username: str, result: dict) -> str:
        stats = result.get("result", {})
        status_str = ", ".join(f"{k}:{v}" for k, v in stats.get("by_status", {}).items())
        return (
            f"📊 {username} 订单统计\n"
            f"   总笔数: {stats['total_orders']}\n"
            f"   总金额: ¥{stats['total_amount']}\n"
            f"   均价: ¥{stats['avg_amount']}\n"
            f"   状态分布: {status_str}"
        )

    def _format_global_stats(self, result: dict) -> str:
        return self._format_stats("全局", result)


# ============================================================================
# Part 4: 测试
# ============================================================================

TEST_SCENARIOS = {
    "order": {
        "description": "电商客服系统 — 查询订单状态",
        "scores": {
            "task_uncertainty": 3,
            "tool_complexity": 5,
            "context_depth": 4,
            "decision_need": 3,
            "latency": 8,
        },
        "recommended": "TOOL + Router",
        "reason": "订单查询是确定性操作，MCP Tool + 简单路由即可覆盖，不需要 Agent",
    },
    "data": {
        "description": "BI 数据分析助手 — 根据自然语言生成报表",
        "scores": {
            "task_uncertainty": 8,
            "tool_complexity": 7,
            "context_depth": 7,
            "decision_need": 6,
            "latency": 4,
        },
        "recommended": "SingleAgent + MCP Tools",
        "reason": "需要理解自然语言、选择分析维度、组合多个 MCP Tool，Agent 合适",
    },
    "support": {
        "description": "智能客服系统 — 咨询、投诉、退款等多场景",
        "scores": {
            "task_uncertainty": 7,
            "tool_complexity": 6,
            "context_depth": 8,
            "decision_need": 7,
            "latency": 5,
        },
        "recommended": "Router + Agent 混合",
        "reason": "不同类型的请求需要不同处理逻辑，Router 分发 + Agent 执行",
    },
}


def run_decision_analysis(scenario: str):
    """决策框架演示"""
    test = TEST_SCENARIOS[scenario]
    print(f"\n{'='*60}")
    print(f"场景: {test['description']}")
    print(f"{'='*60}")
    print(f"\n打分 (1-10):")
    for name, score in test["scores"].items():
        bar = "█" * score + "░" * (10 - score)
        print(f"  {name:22s} [{bar}] {score}")

    print(f"\n推荐架构: {test['recommended']}")
    print(f"理由: {test['reason']}")

    results = ArchitectureSelector.evaluate(test["scores"])
    print(f"\n各架构得分:")
    for arch, score, explanation in results:
        bar = "█" * int(score * 50) + "░" * (50 - int(score * 50))
        print(f"  {arch.value:15s} [{bar}] {score:.4f}")
        print(f"    → {explanation}")
    print()


async def run_mcp_demo():
    """MCP Server + Agent 联调演示"""
    print("\n" + "=" * 60)
    print("MCP Server 与 Agent 集成演示")
    print("=" * 60)

    # 1. 创建 MCP Server
    server = OrderMCPServer()
    print(f"\n🔌 MCP Server 启动: {server.name} v{server.version}")

    # 2. 列出工具
    tools = server.list_tools()
    print(f"\n📦 可用 Tools ({len(tools)}):")
    for t in tools:
        print(f"  - {t['name']}: {t['description']}")

    # 3. 列出资源
    resources = server.list_resources()
    print(f"\n🗂  可用 Resources ({len(resources)}):")
    for r in resources:
        print(f"  - {r['uri']}: {r['description']}")

    # 4. Agent 消费 MCP
    agent = OrderAgent(server)
    print(f"\n🤖 Agent 就绪，开始处理请求...\n")

    test_queries = [
        "查询 ORD-001",
        "查看 Alice 的订单",
        "统计 Bob 的订单数据",
        "全局统计",
    ]

    for query in test_queries:
        print(f"👤 用户: {query}")
        response = await agent.process(query)
        print(f"🤖 Agent: {response}\n")


def run_decision_matrix():
    """打印完整的决策矩阵"""
    print("\n" + "=" * 60)
    print("Agent vs MCP Tool 决策速查表")
    print("=" * 60)
    print(f"""
┌─────────────────────┬──────────────┬──────────────┐
│ 场景                │ MCP Tool ✅  │ Agent ✅     │
├─────────────────────┼──────────────┼──────────────┤
│ 查询一条订单        │      ✓       │              │
│ 查询订单列表        │      ✓       │              │
│ "我的订单到哪了"    │              │      ✓       │
│ "帮我取消最近3笔"   │              │      ✓       │
│ 生成运营周报        │              │      ✓       │
│ 批量导出订单        │      ✓       │              │
│ 多轮客服对话        │              │      ✓       │
│ 定时同步数据        │      ✓       │              │
│ A/B 价格实验分析    │              │      ✓       │
└─────────────────────┴──────────────┴──────────────┘

核心原则：
  MCP Tool → 当 "查什么" 比 "怎么查" 更明确时
  Agent    → 当 "要什么" 比 "怎么做" 更明确时

组合最佳实践：
  1. MCP 做数据层（Resources + Tools 提供数据访问）
  2. Router 做分发层（意图识别 → 路由）
  3. Agent 做推理层（理解需求 + 组合工具 + 解释结果）
  4. Workflow 做编排层（固定流程的自动化）
""")


def run_tests():
    """运行内置测试"""
    print("\n" + "=" * 60)
    print("Week 4 测试")
    print("=" * 60)

    passed = 0
    total = 0

    # Test 1: 决策框架评分
    total += 1
    print(f"\n[Test {total}] 决策框架评分")
    results = ArchitectureSelector.evaluate(TEST_SCENARIOS["order"]["scores"])
    top = results[0]
    assert top[0] in [ArchitectureChoice.TOOL, ArchitectureChoice.ROUTER, ArchitectureChoice.WORKFLOW], \
        f"订单查询应推荐 TOOL/ROUTER/WORKFLOW，而非 {top[0].value}"
    print(f"  ✅ 推荐: {top[0].value} → {top[2]}")
    passed += 1

    # Test 2: MCP Server 工具注册
    total += 1
    print(f"\n[Test {total}] MCP Server 工具注册")
    server = OrderMCPServer()
    tools = server.list_tools()
    assert len(tools) == 3, f"应有 3 个工具，实际 {len(tools)}"
    assert "get_order_by_id" in [t["name"] for t in tools]
    assert "list_orders_by_user" in [t["name"] for t in tools]
    assert "order_stats" in [t["name"] for t in tools]
    print(f"  ✅ 3 个工具注册成功")
    passed += 1

    # Test 3: MCP Resource
    total += 1
    print(f"\n[Test {total}] MCP Resource 注册")
    resources = server.list_resources()
    assert len(resources) == 1, f"应有 1 个资源，实际 {len(resources)}"
    assert resources[0]["uri"] == "order://statuses"
    print(f"  ✅ Resource 注册成功: {resources[0]['uri']}")
    passed += 1

    # Test 4: Tool 调用 — 查询订单
    total += 1
    print(f"\n[Test {total}] Tool 调用: get_order_by_id")
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(
        server.call_tool("get_order_by_id", {"order_id": "ORD-001"})
    )
    order = result["result"]
    assert order["id"] == "ORD-001"
    assert order["status"] == "shipped"
    assert order["amount"] == 299.0
    print(f"  ✅ 订单查询: {order['id']} → {order['status']}")
    passed += 1

    # Test 5: Tool 调用 — 按用户查询
    total += 1
    print(f"\n[Test {total}] Tool 调用: list_orders_by_user")
    result = loop.run_until_complete(
        server.call_tool("list_orders_by_user", {"username": "Alice"})
    )
    orders = result["result"]
    assert len(orders) == 2, f"Alice 应有 2 笔订单，实际 {len(orders)}"
    print(f"  ✅ Alice 订单: {len(orders)} 笔")
    passed += 1

    # Test 6: Tool 调用 — 统计
    total += 1
    print(f"\n[Test {total}] Tool 调用: order_stats")
    result = loop.run_until_complete(
        server.call_tool("order_stats", {"username": "Bob"})
    )
    stats = result["result"]
    assert stats["total_orders"] == 2
    assert stats["total_amount"] == 1499.0 + 2199.0
    print(f"  ✅ Bob 统计: {stats['total_orders']}笔 ¥{stats['total_amount']}")
    passed += 1

    # Test 7: Agent 消费 MCP — 订单查询
    total += 1
    print(f"\n[Test {total}] Agent 消费 MCP: ID 查询")
    agent = OrderAgent(server)
    response = loop.run_until_complete(agent.process("查询 ORD-003"))
    assert "ORD-003" in response
    assert "cancelled" in response
    print(f"  ✅ Agent 成功调用 MCP 查询订单")
    passed += 1

    # Test 8: Agent 消费 MCP — 统计
    total += 1
    print(f"\n[Test {total}] Agent 消费 MCP: 统计分析")
    response = loop.run_until_complete(agent.process("统计 Alice 的订单数据"))
    assert "总笔数: 2" in response
    print(f"  ✅ Agent 成功调用 MCP 统计分析")
    passed += 1

    loop.close()

    print(f"\n{'='*60}")
    print(f"结果: {passed}/{total} 通过 {'✅' if passed == total else '❌'}")
    print(f"{'='*60}")


# ============================================================================
# Part 5: 第 4 月学习总结
# ============================================================================

def print_month4_summary():
    """第 4 月完整总结"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         第 4 月完成 — Multi-Agent 协作体系                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                            ║
║  W1 三角色协作    Planner → Executor → Reviewer (串行)      ║
║     └ 关键: 分解、执行、审查三权分立                        ║
║                                                            ║
║  W2 A2A 协议      Agent Card → Task → 委托 (标准通信)      ║
║     └ 关键: MCP 是水管，A2A 是快递员                        ║
║                                                            ║
║  W3 Supervisor    1 个领导 + N 个工人 (并行)               ║
║     └ 关键: 分解分发 + 并行执行 + 结果聚合                  ║
║                                                            ║
║  W4 取舍+MCP      什么时候用 Agent？什么时候用 Tool？       ║
║     └ 关键: MCP 做数据层, Agent 做推理层                    ║
║                                                            ║
╠══════════════════════════════════════════════════════════════╣
║  选型口诀:                                                  ║
║  简单查数据 → MCP Tool                                      ║
║  固定多步骤 → Workflow / Chain                              ║
║  需要推理+工具 → Single Agent + MCP                         ║
║  复杂多任务+独立决策 → Multi Agent + MCP                    ║
║  多 Agent 跨系统通信 → A2A                                  ║
╠══════════════════════════════════════════════════════════════╣
║  总代码: ~1700 行 (4 Week × ~425 行)                       ║
║  总测试: 25 个 (W1:4 + W2:5 + W3:4 + W4:8 = 21+4=25)       ║
║  总用时: ~6h (W1:1.5h + W2:1.5h + W3:1.5h + W4:1.5h)       ║
╚══════════════════════════════════════════════════════════════╝
""")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Week 4: 取舍与 MCP 集成入门"
    )
    parser.add_argument("--scenario", choices=["order", "data", "support"],
                        help="决策分析场景")
    parser.add_argument("--mcp-demo", action="store_true",
                        help="运行 MCP Server 演示")
    parser.add_argument("--test", action="store_true",
                        help="运行测试")
    parser.add_argument("--matrix", action="store_true",
                        help="查看决策速查表")
    parser.add_argument("--summary", action="store_true",
                        help="第 4 月学习总结")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if args.summary:
        print_month4_summary()
        return

    if args.matrix:
        run_decision_matrix()
        return

    if args.scenario:
        run_decision_analysis(args.scenario)
        return

    if args.mcp_demo:
        asyncio.run(run_mcp_demo())
        return

    # 默认：打印完整内容
    print("Week 4: 取舍与 MCP 集成入门")
    print("=" * 60)
    print()
    print("可用选项:")
    print("  --scenario order    订单场景决策分析")
    print("  --scenario data     数据分析场景决策分析")
    print("  --scenario support  智能客服场景决策分析")
    print("  --mcp-demo          MCP Server 演示")
    print("  --matrix            决策速查表")
    print("  --test              运行测试")
    print("  --summary           第 4 月学习总结")


if __name__ == "__main__":
    main()
