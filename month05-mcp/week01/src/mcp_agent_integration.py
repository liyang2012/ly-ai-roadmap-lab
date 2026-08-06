"""
month05-mcp/src/mcp_agent_integration.py
========================================
LangGraph Agent 集成 MCP Client — 核心联调代码

架构:
  Agent (LangGraph)
    ├── MCP Client → Filesystem MCP Server (stdio)
    └── MCP Client → Weather MCP Server (stdio)

流程:
  1. Agent 收到用户问题
  2. LLM 决定调用哪个 MCP Server 的工具
  3. Agent 通过 MCP Client 发送 tools/call 请求
  4. MCP Server 处理并返回结果
  5. Agent 整合结果回复用户

MCP 协议要点（本实战验证）:
  - Server/Client 分离: 工具逻辑 vs Agent 逻辑完全解耦
  - 标准化发现: Agent 通过 list_tools() 自动发现可用工具
  - Transport 抽象: 底层 stdio 对 Agent 透明
"""

import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated


# ── 路径配置 ─────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
FS_SERVER = PROJECT_ROOT / "filesystem_mcp_server.py"
WEATHER_SERVER = PROJECT_ROOT / "weather_mcp_server.py"

# 为 Filesystem MCP Server 准备沙盒目录
SANDBOX_DIR = Path.home() / "mcp-filesystem-sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
(SANDBOX_DIR / "sample.txt").write_text("Hello from MCP filesystem sandbox!\n这是一行测试文本。")
(SANDBOX_DIR / "subdir").mkdir(exist_ok=True)
(SANDBOX_DIR / "subdir" / "data.json").write_text('{"name":"mcp-test","version":1}')


# ── MCP 工具适配器 ──────────────────────────────────

class MCPToolAdapter:
    """管理多个 MCP Server 连接，提供统一的工具发现和调用接口"""

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}     # name -> session
        self.tools_openai: list[dict] = []               # OpenAI 格式工具列表
        # server mapping: openai_func_name -> server_name
        self.tool_server_map: dict[str, str] = {}

    async def connect_server(self, name: str, script_path: Path) -> int:
        """
        连接一个 MCP Server（stdio transport），注册其工具

        这是 MCP 的核心价值体现：
        - Agent 不需要知道 Server 的内部实现
        - 只需处理标准化的 tools/list 和 tools/call
        """
        server_params = StdioServerParameters(
            command="python3",
            args=[str(script_path)],
            env={"MCP_FS_ROOT": str(SANDBOX_DIR)},  # Filesystem Server 需要
        )
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self.sessions[name] = session

        # 获取 Server 的工具列表 —— MCP 的标准化发现机制
        response = await session.list_tools()
        count = 0
        for tool in response.tools:
            func_name = f"{name}__{tool.name}"
            self.tool_server_map[func_name] = name
            self.tools_openai.append({
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })
            count += 1

        print(f"  ✅ [{name}] 已连接，{count} 个工具")
        for tool in response.tools:
            print(f"     └─ {name}__{tool.name}: {tool.description or '(无描述)'}")
        return count

    async def call_tool(self, func_name: str, arguments: dict) -> str:
        """通过 MCP 协议调用工具，返回格式化文本结果"""
        if func_name not in self.tool_server_map:
            return f"❌ 未知工具: {func_name}"

        server_name = self.tool_server_map[func_name]
        # 去除前缀，得到原始工具名
        tool_name = func_name[len(server_name) + 2:]
        session = self.sessions[server_name]

        try:
            result = await session.call_tool(tool_name, arguments)
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
            return "\n".join(texts)
        except Exception as e:
            return f"❌ 工具调用异常: {e}"

    async def close(self):
        await self.exit_stack.aclose()


# ── LangGraph Agent ──────────────────────────────────

SYSTEM_PROMPT = """你是一个智能助手，通过 MCP 协议连接了文件系统和天气服务。

可用工具说明:
- filesystem__list_dir: 列出目录内容（path: 相对路径，空字符串=根）
- filesystem__read_file: 读取文件（path: 文件相对路径）
- filesystem__write_file: 写入文件（path, content）
- filesystem__search_files: glob 搜索（pattern: 如 "*.txt", "**/*.json"）
- weather__get_current_weather: 当前天气（city: beijing/shanghai/shenzhen/chengdu/tokyo）
- weather__get_forecast: 未来3天预报

规则: 用中文回复；简洁准确；需要数据时调用工具后再回答。"""


class AgentState(TypedDict):
    messages: Annotated[list[dict], "对话历史"]


class MCPAgent:
    """将异步 MCP 操作封装为 LangGraph 可用的 Agent"""

    def __init__(self, client: OpenAI, adapter: MCPToolAdapter, model: str = "gpt-4o-mini"):
        self.client = client
        self.adapter = adapter
        self.model = model
        self.graph = self._build_graph()

    def _llm_decision(self, state: AgentState) -> AgentState:
        """LLM 决策节点：分析用户问题，决定是否调用工具"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.adapter.tools_openai if self.adapter.tools_openai else None,
            tool_choice="auto" if self.adapter.tools_openai else None,
        )
        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            state["messages"].append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
        else:
            state["messages"].append({"role": "assistant", "content": msg.content})

        return state

    def _execute_tools(self, state: AgentState) -> AgentState:
        """执行 MCP 工具调用（同步封装异步操作）"""
        last_msg = state["messages"][-1]
        tool_calls = last_msg.get("tool_calls", [])

        async def _exec():
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                arguments = json.loads(tc["function"]["arguments"])
                print(f"\n  🔧 MCP 调用 → {func_name}({json.dumps(arguments, ensure_ascii=False)})")
                result = await self.adapter.call_tool(func_name, arguments)
                print(f"  📋 结果预览: {result[:120]}...")
                state["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        asyncio.run(_exec())
        return state

    def _should_use_tool(self, state: AgentState) -> str:
        last = state["messages"][-1]
        if last.get("role") == "assistant" and last.get("tool_calls"):
            return "tools"
        return "end"

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("agent", self._llm_decision)
        graph.add_node("tools", self._execute_tools)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", self._should_use_tool, {
            "tools": "tools",
            "end": END,
        })
        graph.add_edge("tools", "agent")
        return graph.compile()

    def run(self, query: str) -> str:
        """运行 Agent 处理用户查询"""
        state: AgentState = {"messages": [{"role": "user", "content": query}]}
        result = self.graph.invoke(state)
        final = result["messages"][-1]
        return final.get("content", str(final))


# ── 独立测试：绕过 LLM 直接测试 MCP 通信 ───────────

async def test_mcp_direct():
    """不依赖 LLM/OpenAI，直接测试 MCP 协议通信"""
    print("=" * 60)
    print("🧪 单元测试：MCP 协议直连（不需要 API Key）")
    print("=" * 60)

    adapter = MCPToolAdapter()
    tests_passed = 0
    tests_total = 0

    try:
        # 连接 Server
        print("\n📡 连接 Filesystem MCP Server...")
        await adapter.connect_server("filesystem", FS_SERVER)
        print("📡 连接 Weather MCP Server...")
        await adapter.connect_server("weather", WEATHER_SERVER)

        # Test 1: list_dir
        tests_total += 1
        print("\n🧪 Test 1: filesystem__list_dir('')")
        result = await adapter.call_tool("filesystem__list_dir", {"path": ""})
        print(f"   结果: {result[:200]}")
        assert "sample.txt" in result, f"应包含 sample.txt"
        assert "subdir" in result, f"应包含 subdir"
        print("   ✅ 通过")
        tests_passed += 1

        # Test 2: read_file
        tests_total += 1
        print("\n🧪 Test 2: filesystem__read_file('sample.txt')")
        result = await adapter.call_tool("filesystem__read_file", {"path": "sample.txt"})
        assert "Hello from MCP" in result
        print(f"   结果: {result.strip()}")
        print("   ✅ 通过")
        tests_passed += 1

        # Test 3: write_file
        tests_total += 1
        print("\n🧪 Test 3: filesystem__write_file('hello.txt', 'Hello MCP!')")
        result = await adapter.call_tool("filesystem__write_file", {
            "path": "hello.txt",
            "content": "Hello MCP! 👋",
        })
        assert "写入成功" in result
        print(f"   结果: {result}")
        # 验证写入
        written = (SANDBOX_DIR / "hello.txt").read_text()
        assert written == "Hello MCP! 👋"
        print("   ✅ 通过")
        tests_passed += 1

        # Test 4: search_files
        tests_total += 1
        print("\n🧪 Test 4: filesystem__search_files('**/*.json')")
        result = await adapter.call_tool("filesystem__search_files", {"pattern": "**/*.json"})
        assert "data.json" in result
        print(f"   结果: {result.strip()}")
        print("   ✅ 通过")
        tests_passed += 1

        # Test 5: 路径越界安全检测
        tests_total += 1
        print("\n🧪 Test 5: 路径越界安全（尝试访问 ../etc/passwd）")
        result = await adapter.call_tool("filesystem__read_file", {"path": "../../etc/passwd"})
        assert "路径越界" in result or "PermissionError" in result or "不存在" in result
        print(f"   结果: {result[:100]}")
        print("   ✅ 通过（安全拦截）")
        tests_passed += 1

        # Test 6: weather current
        tests_total += 1
        print("\n🧪 Test 6: weather__get_current_weather('beijing')")
        result = await adapter.call_tool("weather__get_current_weather", {"city": "beijing"})
        assert "32" in result and "°C" in result
        print(f"   结果: {result.strip()}")
        print("   ✅ 通过")
        tests_passed += 1

        # Test 7: weather forecast
        tests_total += 1
        print("\n🧪 Test 7: weather__get_forecast('shanghai')")
        result = await adapter.call_tool("weather__get_forecast", {"city": "shanghai"})
        assert "周一" in result and "多云" in result
        print(f"   结果: {result.strip()}")
        print("   ✅ 通过")
        tests_passed += 1

        # Test 8: weather resource (新版 SDK 返回 ResourceResult 对象)
        tests_total += 1
        print("\n🧪 Test 8: 读取 weather://cities 资源")
        result = await adapter.sessions["weather"].read_resource("weather://cities")
        # 提取文本内容
        text_content = ""
        for c in result.contents:
            if hasattr(c, "text"):
                text_content += c.text
        assert "beijing" in text_content
        print(f"   支持城市: {text_content}")
        print("   ✅ 通过")
        tests_passed += 1

    finally:
        await adapter.close()

    print(f"\n{'=' * 60}")
    print(f"📊 测试结果: {tests_passed}/{tests_total} 通过")
    return tests_passed == tests_total


# ── 主流程 ──────────────────────────────────────────

async def run_with_llm():
    """完整流程：LangGraph Agent + MCP Client + LLM（支持百炼/OpenAI）"""
    import os

    print("=" * 60)
    print("🤖 LangGraph Agent + MCP Client 集成测试")
    print("=" * 60)

    adapter = MCPToolAdapter()

    # 检测 LLM 配置
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if dashscope_key:
        print("\n🔑 使用百炼 (DashScope) API")
        client = OpenAI(
            api_key=dashscope_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model = "qwen-plus"
    elif openai_key:
        print("\n🔑 使用 OpenAI API")
        client = OpenAI()
        model = "gpt-4o-mini"
    else:
        print("\n⚠️ 未设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，跳过 LLM 测试")
        print("   设置方法: export DASHSCOPE_API_KEY='your-key'")
        await adapter.close()
        return

    try:
        print("\n📡 连接 MCP Servers...")
        await adapter.connect_server("filesystem", FS_SERVER)
        await adapter.connect_server("weather", WEATHER_SERVER)

        agent = MCPAgent(client, adapter, model=model)

        test_queries = [
            "北京今天天气怎么样？空气质量如何？",
            "列出沙盒目录里的所有文件",
            "北京和上海哪个城市更热？比较一下",
            "在沙盒里创建一个文件 readme.md，内容写 # MCP 实战项目",
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n{'─' * 60}")
            print(f"📝 查询 {i}: {query}")
            print(f"{'─' * 60}")
            reply = agent.run(query)
            print(f"\n🤖 回复: {reply}")

        print(f"\n{'=' * 60}")
        print("✅ LangGraph + MCP 集成测试完成")

    finally:
        await adapter.close()


async def main():
    import sys

    if "--no-llm" in sys.argv or "--direct-only" in sys.argv:
        # 直连测试后不跑 LLM
        ok = await test_mcp_direct()
        if not ok:
            sys.exit(1)
        return

    if "--llm-only" in sys.argv:
        # 只跑 LLM 集成测试
        await run_with_llm()
        return

    # 默认：先直连再 LLM
    direct_ok = await test_mcp_direct()
    if not direct_ok:
        print("\n⚠️ 直连测试失败，跳过 LLM 集成测试")
        return

    print("\n")
    await run_with_llm()


if __name__ == "__main__":
    asyncio.run(main())
