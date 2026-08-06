# Week 1：MCP 协议基础与 Server 开发实战

> **学习目标**：理解 MCP 三层架构与三原语，掌握 stdio Transport，能独立开发 MCP Server 并与 LangGraph Agent 集成。
>
> **建议用时**：3-4 小时
>
> **前置知识**：了解 LangGraph Agent 基本概念（Month 02）、Tool Calling 机制（Month 04）

---

## 📋 本周学习路线

```
Day 1-2                 Day 3-4                 Day 5-6                 Day 7
MCP 协议理论        →   Filesystem Server    →   Weather Server      →   Agent 集成
三层架构 + 三原语        4 个 Tools 实战          Tools + Resources         LangGraph + MCP Client
stdio Transport        路径沙盒安全              资源声明与读取             多 Server 编排
```

---

## 1. MCP 协议核心理论

### 1.1 为什么需要 MCP？

在 Month 04 中，我们通过 Function Call 让 Agent 调用工具。但这种方式有一个根本问题：**工具逻辑和 Agent 逻辑紧耦合**。

```
传统 Function Call 方式：
  Agent A → 自己写 get_weather()
  Agent B → 重写一遍 get_weather()
  Agent C → 再重写一遍...

MCP 方式：
  Weather MCP Server（一次开发）
      ↑          ↑          ↑
  Agent A    Agent B    Agent C
  （通过标准协议调用）
```

**MCP 的价值**：一次开发，到处使用。就像 USB 接口统一了外设连接一样，MCP 统一了 AI Agent 与工具的通信协议。

### 1.2 三层架构

```
┌──────────────────────────────────────────────────┐
│              MCP Host (如 Claude Desktop)           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ MCP Client │  │ MCP Client │  │ MCP Client │  │
│  │  (Agent端)  │  │  (Agent端)  │  │  (Agent端)  │  │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘  │
└─────────┼───────────────┼───────────────┼────────┘
          │ Transport     │               │
          │ stdio/SSE     │               │
    ┌─────▼─────┐  ┌──────▼──────┐  ┌─────▼─────┐
    │   MCP     │  │    MCP      │  │   MCP     │
    │  Server   │  │   Server    │  │  Server   │
    │ (Files)   │  │  (Weather)  │  │   (DB)    │
    └───────────┘  └─────────────┘  └───────────┘
```

- **Host**：运行 Agent 的应用（如 Claude Desktop、我们的 LangGraph 应用）
- **Client**：Host 内的 MCP 客户端，负责与 Server 建立连接
- **Server**：独立的工具服务进程，通过标准协议暴露能力

### 1.3 三个原语

| 原语 | 方向 | 用途 | 代码体现 |
|------|------|------|---------|
| **Tools** | Client → Server 调用 | 让 LLM 主动触发的操作 | `@server.list_tools()` + `@server.call_tool()` |
| **Resources** | Client 读取 Server 数据 | 暴露只读数据给 Agent | `@server.list_resources()` + `@server.read_resource()` |
| **Prompts** | Client 获取预定义提示 | 模板化提示词 | `@server.list_prompts()` |

> **重点**：Week 1 主要实践 Tools 和 Resources，Prompts 在 Week 2 深入。

### 1.4 通信流程

```
Client                               Server
  │                                    │
  │──── initialize ───────────────────→│  1. 握手（协商能力）
  │←─── capabilities ─────────────────│
  │                                    │
  │──── tools/list ───────────────────→│  2. 发现工具
  │←─── [{name, description, schema}]──│
  │                                    │
  │──── tools/call {name, arguments} ─→│  3. 调用工具
  │←─── {result} ─────────────────────│
```

### 1.5 Transport 方式

| 方式 | 场景 | 特点 | 本周使用 |
|------|------|------|---------|
| **stdio** | 本地工具 | 简单，通过标准输入输出通信 | ✅ 本周使用 |
| **HTTP SSE** | 远程服务 | 跨网络，Server-Sent Events | Week 4 |
| **Streamable HTTP** | 新标准 | 替代 SSE，2026 年推荐方式 | Week 4 |

---

## 2. 实战：Filesystem MCP Server

### 2.1 设计目标

构建一个安全的文件系统 MCP Server，提供以下工具：

| 工具名 | 功能 | 输入 |
|--------|------|------|
| `list_dir` | 列出目录内容 | `path`（相对路径） |
| `read_file` | 读取文件内容 | `path`（文件路径） |
| `write_file` | 写入文件 | `path`, `content` |
| `search_files` | glob 搜索文件 | `pattern` |

### 2.2 核心代码解析

**Step 1：创建 Server 实例**

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("filesystem-mcp", version="1.0.0")
```

**Step 2：声明可用工具（`tools/list` 响应）**

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_dir",
            description="列出指定目录下的文件和子目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对路径，空字符串表示根目录",
                        "default": "",
                    }
                },
            },
        ),
        # ... 其他工具
    ]
```

**Step 3：处理工具调用（`tools/call` 响应）**

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "list_dir":
        path = arguments.get("path", "")
        target = is_safe_path(path)
        # ... 处理逻辑
        return [TextContent(type="text", text=result)]
```

**Step 4：启动 Server**

```python
async def main():
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)
```

### 2.3 安全设计：路径沙盒

**核心原则**：所有文件操作限制在 `ALLOWED_ROOT` 目录内，防止路径穿越攻击。

```python
ALLOWED_ROOT = Path(os.environ.get("MCP_FS_ROOT", "~/mcp-filesystem-sandbox")).resolve()

def is_safe_path(path: str) -> Path:
    resolved = (ALLOWED_ROOT / path).resolve()
    if not str(resolved).startswith(str(ALLOWED_ROOT)):
        raise PermissionError(f"路径越界: {path}")
    return resolved
```

**测试越界拦截**：
```python
# 尝试读取 ../../etc/passwd → 被 is_safe_path() 拦截
result = await session.call_tool("read_file", {"path": "../../etc/passwd"})
# 返回: "❌ 路径越界" 或 "❌ 文件不存在"
```

---

## 3. 实战：Weather MCP Server

### 3.1 新增能力：Resources

Weather Server 除了 Tools，还暴露了 **Resources**（只读数据）：

```python
@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="weather://cities",          # 资源 URI
            name="Supported Cities",
            description="天气服务支持的城市列表",
            mimeType="text/plain",
        )
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if str(uri) == "weather://cities":
        return "\n".join(SUPPORTED_CITIES)   # beijing\nshanghai\n...
    return f"未知资源: {uri}"
```

### 3.2 Tools vs Resources 的区别

| 维度 | Tools | Resources |
|------|-------|-----------|
| 触发方式 | LLM 主动调用 | Client 主动读取 |
| 参数 | 接受参数 | 通过 URI 定位 |
| 用途 | 执行操作 | 暴露静态/半静态数据 |
| 示例 | `get_weather(city="beijing")` | `weather://cities` |

---

## 4. MCP Client 与 Agent 集成

### 4.1 架构

```
LangGraph Agent
    └── MCPToolAdapter（MCP Client 封装）
            ├── → Filesystem MCP Server (stdio)
            └── → Weather MCP Server (stdio)
```

### 4.2 MCPToolAdapter：核心封装

`MCPToolAdapter` 负责管理多个 MCP Server 连接，并将 MCP 工具转换为 OpenAI Function Call 格式：

```python
class MCPToolAdapter:
    async def connect_server(self, name: str, script_path: Path) -> int:
        # 1. 建立 stdio 连接
        server_params = StdioServerParameters(command="python3", args=[str(script_path)])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport

        # 2. 创建 Client Session
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        # 3. 发现工具（MCP 标准化！）
        response = await session.list_tools()
        for tool in response.tools:
            func_name = f"{name}__{tool.name}"   # 如 filesystem__list_dir
            self.tool_server_map[func_name] = name
            # 转换为 OpenAI 格式
            self.tools_openai.append({
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })
```

### 4.3 LangGraph Agent 图结构

```
用户输入
    ↓
[agent] → LLM 决策（是否调用工具？）
    ├── 需要工具 → [tools] → 执行 MCP 调用 → 回到 [agent]
    └── 不需要   → END（直接回复）
```

关键代码：

```python
def _build_graph(self):
    graph = StateGraph(AgentState)
    graph.add_node("agent", self._llm_decision)    # LLM 决策节点
    graph.add_node("tools", self._execute_tools)   # MCP 工具执行节点
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", self._should_use_tool, {
        "tools": "tools",
        "end": END,
    })
    graph.add_edge("tools", "agent")   # 工具执行后回到 Agent 继续推理
    return graph.compile()
```

### 4.4 工具命名约定

为避免多个 Server 的工具名冲突，采用 `{server_name}__{tool_name}` 格式：

| OpenAI 工具名 | MCP Server | 原始工具名 |
|--------------|-----------|----------|
| `filesystem__list_dir` | filesystem | `list_dir` |
| `filesystem__read_file` | filesystem | `read_file` |
| `weather__get_current_weather` | weather | `get_current_weather` |
| `weather__get_forecast` | weather | `get_forecast` |

---

## 5. 测试策略

### 5.1 三层测试体系

```
week01/
├── src/
│   ├── test_filesystem_mcp.py   ← Layer 1: 单 Server 独立测试
│   ├── test_weather_mcp.py      ← Layer 1: 单 Server 独立测试
│   └── mcp_agent_integration.py ← Layer 2: 多 Server 集成测试（含直连 + LLM）
└── tests/
    └── test_mcp_integration.py  ← Layer 3: 完整测试套件
```

### 5.2 Layer 1：单 Server 独立测试

直接连接单个 Server，验证协议通信：

```bash
# 测试 Filesystem Server
python3 week01/src/test_filesystem_mcp.py

# 测试 Weather Server
python3 week01/src/test_weather_mcp.py
```

### 5.3 Layer 2：直连集成测试（不需要 API Key）

绕过 LLM，直接测试 MCP 协议通信：

```bash
python3 week01/src/mcp_agent_integration.py --no-llm
```

测试覆盖 8 个场景：
1. `filesystem__list_dir` - 目录列表
2. `filesystem__read_file` - 文件读取
3. `filesystem__write_file` - 文件写入 + 验证
4. `filesystem__search_files` - glob 搜索
5. 路径越界安全拦截
6. `weather__get_current_weather` - 当前天气
7. `weather__get_forecast` - 天气预报
8. `weather://cities` 资源读取

### 5.4 Layer 2+：LLM 集成测试

需要 API Key（百炼或 OpenAI）：

```bash
# 使用百炼（推荐国内用户）
export DASHSCOPE_API_KEY='your-key'
python3 week01/src/mcp_agent_integration.py

# 使用 OpenAI
export OPENAI_API_KEY='your-key'
python3 week01/src/mcp_agent_integration.py
```

### 5.5 Layer 3：完整测试套件

```bash
python3 week01/tests/test_mcp_integration.py
```

---

## 6. 运行指南

### 环境准备

```bash
# 安装依赖
pip install mcp langgraph openai pydantic

# 验证 MCP SDK 版本（需要 1.28+）
python3 -c "import mcp; print(mcp.__version__)"
```

### 快速开始

```bash
cd month05-mcp

# 1. 先测试单 Server
python3 week01/src/test_weather_mcp.py

# 2. 运行完整直连测试（不需要 API Key）
python3 week01/src/mcp_agent_integration.py --no-llm

# 3. 有 API Key 时运行完整集成测试
export DASHSCOPE_API_KEY='your-key'
python3 week01/src/mcp_agent_integration.py
```

---

## 7. 关键知识点总结

### 7.1 MCP Server 开发四步法

```
1. 创建 Server 实例     →  Server("name", version="1.0.0")
2. 声明工具列表          →  @server.list_tools()
3. 实现工具处理逻辑      →  @server.call_tool()
4. 启动 Server          →  server.run(read, write, init_options)
```

### 7.2 MCP Client 使用三步法

```
1. 建立连接             →  stdio_client(params) + ClientSession
2. 发现工具             →  session.list_tools()
3. 调用工具             →  session.call_tool(name, arguments)
```

### 7.3 安全要点

- **路径沙盒**：所有文件操作限制在 `ALLOWED_ROOT` 内
- **进程隔离**：MCP Server 是独立进程，崩溃不影响 Agent
- **输入校验**：每个工具都要校验参数合法性

### 7.4 与 Month 04 的联系

| Month 04 概念 | Month 05 MCP 对应 |
|--------------|----------------|
| Function Call | MCP Tools |
| Agent 内置工具 | 独立 MCP Server |
| 手工配置工具列表 | 自动发现（`list_tools()`） |
| 单进程 | 多进程（stdio 隔离） |

--

## 8. 常见错误排查

| 错误 | 原因 | 解决方案 |
|------|------|--------|
| `ModuleNotFoundError: No module named 'mcp'` | MCP SDK 未安装 | `pip install mcp` |
| `AttributeError: 'Server' has no attribute 'list_tools'` | SDK 版本太低 | `pip install --upgrade mcp` |
| `ConnectionRefusedError` | Server 进程启动失败 | 检查 Server 脚本路径是否正确 |
| `PermissionError: 路径越界` | 访问了沙盒外的路径 | 这是安全机制正常工作 |
| LLM 不调用工具 | 工具描述不够清晰 | 完善 `description` 字段 |

---

## 8.5 踩坑记录与工程经验

### 坑 1：MCP SDK 版本 API 差异

`mcp` 包在不同版本 API 变动较大。旧版没有 `server.list_tools()` 装饰器，新版改了 `read_resource` 返回类型。**解决**：确认使用 `mcp >= 1.28`：

```bash
python3 -c "import mcp; print(mcp.__version__)"
```

### 坑 2：read_resource 返回类型变化

新版 SDK `session.read_resource()` 返回 `ResourceResult` 对象，包含 `contents` 列表，而不是直接返回字符串：

```python
# ❌ 旧版写法（已失效）
text = await session.read_resource("weather://cities")

# ✅ 新版写法
result = await session.read_resource("weather://cities")
text = ""
for c in result.contents:
    if hasattr(c, "text"):
        text += c.text
```

### 坑 3：stdio Transport 环境变量传递

`StdioServerParameters` 中若不显式传 `env`，子进程继承父进程全部环境变量。但 `MCP_FS_ROOT` 等自定义变量需要在 Client 端显式设置：

```python
server_params = StdioServerParameters(
    command="python3",
    args=[str(script_path)],
    env={"MCP_FS_ROOT": str(SANDBOX_DIR)},  # 显式传入
)
```

### 坑 4：LangGraph 同步节点调用异步 MCP

LangGraph 节点函数是同步的，但 MCP `call_tool()` 是异步的。需要在同步节点中用 `asyncio.run()` 桥接：

```python
def _execute_tools(self, state: AgentState) -> AgentState:
    async def _exec():
        result = await self.adapter.call_tool(func_name, arguments)
    asyncio.run(_exec())  # 同步节点桥接异步调用
    return state
```

### 坑 5：工具描述质量直接影响 LLM 调用准确率

`Tool.description` 不是可选的装饰，它是 LLM 理解工具的唯一依据。写得越精确，LLM 调用越准确。建议在 description 中明确：
- 工具做什么（功能）
- 需要什么参数（参数语义）
- 支持哪些值（如城市名列表）

---

## 8.6 思考题

**Q1：什么时候不需要 MCP？**
- 工具只在一个 Agent 里用，且永远不会复用 → Function Call 更简单
- 需要极低延迟的场景 → 进程间通信有额外开销
- 简单脚本/原型验证阶段 → 先跑通再考虑标准化

**Q2：为什么 Server 要独立进程而不是同进程？**
1. 安全隔离：Server 崩溃不影响 Agent
2. 权限隔离：每个 Server 可以有独立的安全策略
3. 语言无关：Server 可以用任何语言编写
4. 独立部署：Server 可以单独更新而不影响 Agent

**Q3：Resources 的价值是什么？**
Agent 可以在调用 Tools 之前先读取 Resources 获取上下文（如支持的城市列表），从而避免传递无效参数。这是「上下文注入」的基础模式。

---

## 9. 下一步

Week 1 掌握了 MCP 基础和 Server 开发。Week 2 将深入：
- Resources 原语的动态资源与资源模板（Resource Templates）
- Prompts 原语的实践（预定义提示模板、参数化提示）
- 多 Server 生命周期管理（健康检查、优雅关闭）
- 错误处理与重试策略（超时控制、异常传播）
- Server 能力声明（Capabilities 协商）

**继续学习**：[Week 2（计划中）] | [返回 Month 05 总览](../README.md)

---

## 10. 自检清单

完成以下所有检查点，说明 Week 1 核心概念已掌握：

- [ ] 能解释 MCP 三层架构（Host / Client / Server）各层的职责
- [ ] 能说出 Tools 与 Resources 的核心区别（谁发起、用途、定位方式）
- [ ] 理解 stdio Transport 的通信原理和局限性
- [ ] 成功运行 `test_weather_mcp.py` 并理解每步输出
- [ ] 成功运行 `mcp_agent_integration.py --no-llm` 且 8 个测试全部通过
- [ ] 理解路径沙盒安全机制的原理（resolve + startswith 校验）
- [ ] 能说出 MCP 相比 Function Call 的 3 个核心优势
- [ ] 理解 MCPToolAdapter 如何将 MCP 工具转换为 OpenAI Function Call 格式
- [ ] 理解 AsyncExitStack 管理多个异步 Server 连接的方式
- [ ] 能独立从零开发一个符合 MCP 标准的 Server（四步法）
