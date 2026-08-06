# MCP 协议核心概念速查

> 本文件作为 MCP 协议学习速查卡，快速查阅核心概念和 API。

---

## 三层架构

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

## 三个原语

| 原语 | 方向 | 用途 | HTTP 类比 | 示例 |
|------|------|------|----------|------|
| **Tools** | Client → Server | 让 LLM 主动触发的操作 | POST /api | read_file, get_weather |
| **Resources** | Client ← Server | 暴露只读数据给 Agent | GET /api | 文件内容、城市列表 |
| **Prompts** | Client ← Server | 预定义提示模板 | GET /templates | “帮我总结这段代码” |

## Transport 方式

| 方式 | 场景 | 特点 |
|------|------|------|
| **stdio** | 本地工具 | 简单，进程间通信 |
| **HTTP SSE** | 远程服务 | 跨网络，Server-Sent Events |
| **Streamable HTTP** | 新标准 | 替代 SSE，2026 年推荐 |

## MCP vs Function Call

| 维度 | Function Call | MCP |
|------|--------------|-----|
| 耦合度 | 紧耦合（定义在 Agent 内） | 松耦合（独立 Server） |
| 复用性 | 每个 Agent 重写一遍 | 一次编写，到处使用 |
| 标准化 | 各家实现不同 | 统一协议，生态共享 |
| 发现机制 | 手工配置 | 自动发现（list_tools） |
| 安全 | 代码内控制 | 进程隔离 + OAuth |
| 隔离性 | 同进程，崩溃传染 | 独立进程，互不影响 |

## MCP 通信流程

```
Client                               Server
  │                                    │
  │──── initialize ───────────────────→│  握手
  │←─── capabilities ─────────────────│
  │                                    │
  │──── tools/list ───────────────────→│  发现工具
  │←─── [{name, description, schema}]──│
  │                                    │
  │──── tools/call {name, arguments} ─→│  调用工具
  │←─── {result} ─────────────────────│
  │                                    │
  │──── resources/list ───────────────→│  发现资源
  │←─── [{uri, name, description}]───│
  │                                    │
  │──── resources/read {uri} ────────→│  读取资源
  │←─── {content} ───────────────────│
```

---

## SDK API 速查

### Server 端 API（mcp.server）

| API | 用途 | 示例 |
|-----|------|------|
| `Server(name, version)` | 创建 Server 实例 | `server = Server("fs-mcp", version="1.0.0")` |
| `@server.list_tools()` | 声明可用工具 | 返回 `list[Tool]` |
| `@server.call_tool()` | 处理工具调用 | 返回 `list[TextContent]` |
| `@server.list_resources()` | 声明可用资源 | 返回 `list[Resource]` |
| `@server.read_resource()` | 读取资源内容 | 返回 `str` |
| `@server.list_prompts()` | 声明提示模板 | 返回 `list[Prompt]` |
| `@server.get_prompt()` | 获取提示内容 | 返回 `GetPromptResult` |
| `server.create_initialization_options()` | 创建协商选项 | 传入 `server.run()` |
| `server.run(read, write, init)` | 启动 Server | 在 stdio_server 中调用 |

### Client 端 API（mcp.client）

| API | 用途 | 示例 |
|-----|------|------|
| `StdioServerParameters(command, args, env)` | Server 启动参数 | `params = StdioServerParameters(...)` |
| `stdio_client(params)` | 建立 stdio 连接 | `async with stdio_client(params) as (r, w)` |
| `ClientSession(read, write)` | 创建 Client 会话 | `async with ClientSession(r, w) as s` |
| `session.initialize()` | 握手初始化 | 必须在其他操作前调用 |
| `session.list_tools()` | 发现工具 | 返回 `ListToolsResult` |
| `session.call_tool(name, args)` | 调用工具 | 返回 `CallToolResult` |
| `session.list_resources()` | 发现资源 | 返回 `ListResourcesResult` |
| `session.read_resource(uri)` | 读取资源 | 返回 `ResourceResult` |
| `session.list_prompts()` | 发现提示模板 | 返回 `ListPromptsResult` |
| `session.get_prompt(name, args)` | 获取提示内容 | 返回 `GetPromptResult` |

---

## 核心数据结构

| 结构 | 字段 | 说明 |
|------|------|------|
| `Tool` | name, description, inputSchema | 工具声明 |
| `Resource` | uri, name, description, mimeType | 资源声明 |
| `Prompt` | name, description, arguments | 提示模板声明 |
| `TextContent` | type="text", text | 工具返回的文本内容 |
| `CallToolResult` | content: list[TextContent] | 工具调用结果 |
| `ResourceResult` | contents: list | 资源读取结果 |
