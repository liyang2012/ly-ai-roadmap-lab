# Week 1 综合笔记：MCP 协议基础与 Server 开发

> **学习日期**：2026-08-03
> **状态**：✅ 已完成
> **用时**：~3.5h
> **代码位置**：`month05-mcp/week01/`

---

## 💡 小白科普：本周在学什么？

前几个月我们用 Function Call 让 Agent 调用工具。这有一个根本问题：**工具代码和 Agent 代码耦合在一起**。

想象你要给 3 个 App 都接入天气查询：
- Function Call 方式：每个 App 里都写一遍 `get_weather()` 函数
- MCP 方式：写一个「天气 MCP Server」，3 个 App 都通过标准协议来调用

本周你会学到：

| 概念 | 一句话解释 | 类比 |
|------|-----------|------|
| **MCP 三层架构** | Host（宿主）/ Client（客户端）/ Server（服务端）分离 | 浏览器 / HTTP 客户端 / Web 服务器 |
| **三个原语** | Tools（工具）/ Resources（资源）/ Prompts（提示） | POST / GET / 模板 |
| **stdio Transport** | 通过标准输入输出通信 | 进程间传纸条 |
| **路径沙盒** | 文件操作限制在指定目录内 | 只允许在沙坑里玩 |

> 📖 更详细的理论请阅读 `doc/Week1-MCP-Fundamentals.md`

---

## 📊 本周完成情况

| Day | 任务 | 产出 | 状态 |
|-----|------|------|------|
| Day 1-2 | MCP 协议理论 + 三层架构 + 三原语 | 概念速查卡 `mcp_concepts.md` | ✅ |
| Day 3-4 | Filesystem MCP Server（4 Tools） | `filesystem_mcp_server.py` | ✅ |
| Day 5 | Weather MCP Server（2 Tools + 1 Resource） | `weather_mcp_server.py` | ✅ |
| Day 6 | LangGraph Agent + MCP Client 集成 | `mcp_agent_integration.py` | ✅ |
| Day 7 | 测试套件 + 复盘笔记 | 本文件 + tests | ✅ |

---

## 🔑 核心知识点

### 1. MCP 三层架构：为什么分三层？

```
Host（宿主应用）
  └── Client（协议客户端）  ← 一个 Host 可以有多个 Client
        └── Server（工具服务端）  ← 每个 Server 是独立进程
```

**关键理解**：
- **Host ≠ Client**：Host 是运行 Agent 的应用（如 Claude Desktop），Client 是 Host 内负责 MCP 通信的模块
- **一个 Host 可以连接多个 Server**：通过多个 Client 实例
- **Server 是独立进程**：崩溃不影响 Agent，这是安全隔离的基础

### 2. 三个原语：Tools / Resources / Prompts

| 原语 | 谁发起 | 方向 | HTTP 类比 | 本周实践 |
|------|--------|------|----------|---------|
| **Tools** | LLM 主动调用 | Client → Server | POST /api/tools | ✅ list_dir, get_weather |
| **Resources** | Client 主动读取 | Client ← Server | GET /api/resources | ✅ weather://cities |
| **Prompts** | Client 获取模板 | Client ← Server | GET /api/prompts | ⏳ Week 2 |

**最容易混淆的点**：Tools vs Resources
- Tools：LLM 决定什么时候调用，带参数，执行操作
- Resources：Client（程序逻辑）决定什么时候读，用 URI 定位，只读数据

### 3. stdio Transport 通信原理

```
Client 进程                        Server 进程
    │                                  │
    │──stdin──→ JSON-RPC ──────────→   │  Client 往 Server 的 stdin 写
    │                                  │
    │←─stdout── JSON-RPC ←─────────    │  Server 往自己的 stdout 写
    │                                  │
```

**关键点**：
- Server 进程由 Client 通过 `StdioServerParameters` 启动（子进程）
- Client 通过 `stdio_client()` 管理子进程生命周期
- 底层是 JSON-RPC 2.0 协议，但开发者只需处理 Python 对象

### 4. MCP Server 开发四步法

```python
# 第 1 步：创建 Server 实例
server = Server("my-server", version="1.0.0")

# 第 2 步：声明工具（响应 tools/list 请求）
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(name="my_tool", description="...", inputSchema={...})]

# 第 3 步：处理调用（响应 tools/call 请求）
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text="result")]

# 第 4 步：启动（stdio transport）
async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
```

### 5. MCPToolAdapter：桥接 MCP 与 OpenAI

`MCPToolAdapter` 是本周代码的核心桥梁，它解决了一个现实问题：**LLM（百炼/OpenAI）只认 OpenAI Function Call 格式，不认 MCP 协议**。

```
MCP 协议世界                    OpenAI 世界
─────────────                  ─────────────
Tool(name="list_dir")    →    {"type": "function", "function": {...}}
session.call_tool()      →    tool_calls[] → tool message
```

转换规则：
- 工具名：`{server_name}__{tool_name}`（如 `filesystem__list_dir`）
- 参数：直接透传（MCP inputSchema 与 OpenAI parameters 格式兼容）
- 结果：提取 `TextContent.text` 作为 tool message content

### 6. 路径沙盒安全机制

```python
ALLOWED_ROOT = Path("~/mcp-filesystem-sandbox").resolve()

def is_safe_path(path: str) -> Path:
    resolved = (ALLOWED_ROOT / path).resolve()  # 规范化路径
    if not str(resolved).startswith(str(ALLOWED_ROOT)):
        raise PermissionError(f"路径越界: {path}")  # 拦截 ../../etc/passwd
    return resolved
```

**攻击原理**：`../../etc/passwd` → resolve 后变成 `/etc/passwd` → 不以 `ALLOWED_ROOT` 开头 → 拦截

---

## 🔍 关键发现

### 发现 1：MCP 工具声明格式与 OpenAI 完全兼容

MCP `Tool.inputSchema` 就是 JSON Schema，和 OpenAI `function.parameters` 格式一模一样。这意味着 MCP 工具可以**零转换成本**直接用于 OpenAI Function Calling。MCP 在设计时就考虑了与主流 LLM 的兼容性。

### 发现 2：stdio Transport 简单但有限

stdio 模式优点：零配置、天然隔离。
但局限：
- 只能本地使用（同一台机器）
- Server 必须由 Client 启动（不能独立部署）
- 不支持多 Client 同时连接同一 Server

生产环境需要 Streamable HTTP Transport（Week 4）。

### 发现 3：Resources 的价值在于「上下文注入」

`weather://cities` 这个 Resource 看起来简单，但它体现了一个重要模式：**Agent 可以在调用 Tools 之前先读取 Resources 获取上下文**。

例如：Agent 先读 `weather://cities` 知道支持哪些城市，再调用 `get_current_weather(city="beijing")` 时就不会传无效参数。

### 发现 4：MCP Server 的错误处理很重要

在 `call_tool()` 中，每个工具都有完整的错误处理：
- 路径不存在 → 友好提示而非崩溃
- 二进制文件 → 提示无法读取
- 无效城市 → 列出支持的城市

Server 永远不应该因为参数错误而崩溃——返回错误信息让 LLM 自行调整。

### 发现 5：AsyncExitStack 是管理多个异步资源的关键

`MCPToolAdapter` 用 `AsyncExitStack` 管理多个 Server 连接：

```python
self.exit_stack = AsyncExitStack()
# 每连接一个 Server，就注册一个 async context manager
stdio_transport = await self.exit_stack.enter_async_context(stdio_client(params))
session = await self.exit_stack.enter_async_context(ClientSession(read, write))
# 最后统一清理
await self.exit_stack.aclose()
```

这比手动管理每个连接的生命周期优雅得多。

---

## ⚠️ 踩坑记录

### 1. MCP SDK 版本 API 差异大

**问题**：`mcp` 包在不同版本中 API 变动较大。旧版没有 `server.list_tools()` 装饰器，新版改了 `read_resource` 返回类型。

**解决**：确认使用 `mcp >= 1.28`，通过 `python3 -c "import mcp; print(mcp.__version__)"` 检查。

### 2. read_resource 返回 ResourceResult 而非纯字符串

**问题**：新版 SDK `session.read_resource()` 返回 `ResourceResult` 对象，包含 `contents` 列表，不是直接返回字符串。

**解决**：需要遍历 `result.contents` 提取 `text` 字段：
```python
result = await session.read_resource("weather://cities")
text = ""
for c in result.contents:
    if hasattr(c, "text"):
        text += c.text
```

### 3. stdio Transport 子进程环境变量传递

**问题**：`StdioServerParameters` 如果不传 `env`，子进程继承父进程全部环境变量，但 `MCP_FS_ROOT` 需要在 Client 端显式设置。

**解决**：在 `StdioServerParameters` 中显式传入 `env` 字典：
```python
server_params = StdioServerParameters(
    command="python3",
    args=[str(script_path)],
    env={"MCP_FS_ROOT": str(SANDBOX_DIR)},
)
```

### 4. LangGraph 节点中调用异步 MCP 工具

**问题**：LangGraph 节点函数是同步的，但 `session.call_tool()` 是异步的。

**解决**：在同步节点中用 `asyncio.run()` 桥接：
```python
def _execute_tools(self, state):
    async def _exec():
        result = await self.adapter.call_tool(func_name, arguments)
    asyncio.run(_exec())
```

### 5. 工具描述质量直接影响 LLM 调用准确率

**问题**：当 `Tool.description` 写得不够清晰时，LLM 会选错工具或传错参数。

**教训**：MCP Server 的 `description` 字段不是可选的装饰，它是 LLM 理解工具的唯一依据。写得越精确，LLM 调用越准确。

---

## 📊 测试结果

### 直连测试（不需要 API Key）

| # | 测试场景 | 工具 | 结果 |
|---|---------|------|------|
| 1 | 目录列表 | `filesystem__list_dir` | ✅ |
| 2 | 文件读取 | `filesystem__read_file` | ✅ |
| 3 | 文件写入+验证 | `filesystem__write_file` | ✅ |
| 4 | glob 搜索 | `filesystem__search_files` | ✅ |
| 5 | 路径越界拦截 | `filesystem__read_file` + `../../etc/passwd` | ✅ 安全拦截 |
| 6 | 当前天气 | `weather__get_current_weather` | ✅ |
| 7 | 天气预报 | `weather__get_forecast` | ✅ |
| 8 | 资源读取 | `weather://cities` Resource | ✅ |

**通过率：8/8 (100%)**

---

## 🤔 思考题

### Q1：MCP 比 Function Call 好在哪里？

| 维度 | Function Call | MCP |
|------|--------------|-----|
| 复用性 | 每个 Agent 重写 | 一次开发，多 Agent 共享 |
| 隔离性 | 同进程，崩溃传染 | 独立进程，互不影响 |
| 发现 | 手工配置 | `list_tools()` 自动发现 |
| 标准化 | 各家不同 | 统一协议，生态共享 |
| 安全 | 代码内控制 | 进程隔离 + 沙盒 |

### Q2：什么时候不需要 MCP？

- 工具只在一个 Agent 里用，且永远不会复用 → Function Call 更简单
- 需要极低延迟的场景 → 进程间通信有开销
- 简单脚本/原型验证阶段 → 先跑通再考虑标准化

### Q3：为什么 Server 要独立进程而不是同进程？

1. **安全隔离**：Server 崩溃不影响 Agent
2. **权限隔离**：每个 Server 可以有独立的安全策略
3. **语言无关**：Server 可以用任何语言编写
4. **独立部署**：Server 可以单独更新而不影响 Agent

---

## ✅ 自检清单

- [x] 能解释 MCP 三层架构（Host / Client / Server）的职责
- [x] 能说出 Tools 与 Resources 的核心区别
- [x] 理解 stdio Transport 的通信原理和局限
- [x] 成功运行 `test_weather_mcp.py` 并理解输出
- [x] 成功运行 `mcp_agent_integration.py --no-llm` 且 8 个测试全部通过
- [x] 理解路径沙盒安全机制的原理和攻击向量
- [x] 能说出 MCP 相比 Function Call 的核心优势
- [x] 理解 MCPToolAdapter 如何将 MCP 工具转换为 OpenAI 格式
- [x] 理解 AsyncExitStack 管理多个异步资源的方式
- [x] 能独立开发一个符合 MCP 标准的 Server

---

## 🎯 Week 2 预告

| 主题 | 内容 |
|------|------|
| 动态 Resources | 资源模板（Resource Templates）、动态资源列表 |
| Prompts 原语 | 预定义提示模板、提示参数化 |
| 多 Server 管理 | Server 生命周期、健康检查、优雅关闭 |
| 错误处理 | 重试策略、超时控制、异常传播 |
| 能力声明 | Server Capabilities、协议版本协商 |

Week 1 掌握了「MCP 是什么 + 怎么写 Server」，Week 2 要深入「怎么把 Server 写得更健壮」。
