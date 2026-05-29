# 📚 第 1 月 - Week 1：基础入门

**日期**: 2026-04-08 至 2026-04-09

**主题**: 搭建开发环境，理解 Agent 的基本概念，掌握 Run Loop 和 Tool 调用机制

---

## 🎯 周目标（3 个核心）

1. [x] **环境搭建**: Python 虚拟环境 + openai-agents SDK 安装
2. [x] **Hello Agent**: 第一个 Agent 程序跑通
3. [x] **Run Loop 理解**: 掌握 Agent 的执行循环和 Tool 调用流程

---

## 📁 目录结构

```
week1/
├── hello_agent.py              # Day 1-2: 最简 Agent 示例
├── loop_agent_tools.py         # Day 3-4: Run Loop + Tool 调用
└── ../doc/
    ├── RunLoop.md              # Run Loop 流程图详解
    └── Handoff.md              # Handoff 概念文档（提前学习）
```

---

## 📋 每日任务清单

### Day 1-2: Hello Agent ✅ 已完成

**核心文件**: `hello_agent.py`（27 行）

**学习内容**:
1. 创建 Python 虚拟环境：`python3 -m venv venv`
2. 激活环境：`source venv/bin/activate`
3. 安装依赖：`pip install openai-agents`
4. 配置阿里云百炼环境变量（DASHSCOPE_API_KEY）

**Hello Agent 代码拆解**:

```python
from agents import Agent, Runner

# 1. 创建 Agent
agent = Agent(
    name="Helper",
    instructions="You are a helpful assistant."
)

# 2. 运行 Agent
result = await Runner.run(agent, "Hello!")
print(result.final_output)
```

**关键认知**:
- `Agent` = 角色定义（name + instructions）
- `Runner.run()` = 执行引擎（驱动 Agent 处理输入）
- `result.final_output` = Agent 的最终回复

---

### Day 3-4: Run Loop 与 Tool 调用 ✅ 已完成

**核心文件**: `loop_agent_tools.py`（94 行）

**学习内容**:
1. 理解 Run Loop 的完整执行流程
2. 使用原始 OpenAI API 手动实现 Tool 调用循环
3. 理解 `tool_calls` → `tool` → `assistant` 的消息传递机制

**Run Loop 核心流程**（手写版）:

```python
# 第 1 步：用户输入
messages = [{"role": "user", "content": "北京天气咋样"}]

# 第 2 步：调用模型
response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=messages,
    tools=tools  # 告诉模型有哪些工具可用
)

# 第 3 步：检查是否需要调用工具
if response.tool_calls is not None:
    # 第 4 步：执行工具
    tool_result = get_current_weather(arguments)
    
    # 第 5 步：把工具结果加回消息列表
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": tool_result
    })
    
    # 第 6 步：再次调用模型，让模型整合工具结果
    response = client.chat.completions.create(...)
```

**完整 Run Loop 流程图**（见 `../doc/RunLoop.md`）:

```
用户输入 → Agent 理解 → 判断是否需要 Tool
  ├─ 否 → 直接生成回复 → 输出
  └─ 是 → 提取参数 → 执行 Tool → 整合结果 → 生成回复 → 输出
```

**关键认知**:
- `tools` 定义告诉模型**能做什么**
- `tool_calls` 是模型**决定做什么**
- `role: "tool"` 消息把结果**反馈给模型**
- 循环直到模型不再需要调用工具

---

## 💡 关键认知（本周要理解）

1. **Agent 的本质 = System Prompt + Tools**
   - instructions 就是 System Prompt，决定 Agent 的行为风格
   - tools 是 Agent 的能力边界

2. **Run Loop 是 Agent 的"心跳"**
   - 每次循环：理解 → 决策 → 执行 → 整合
   - 多轮对话就是多轮 Run Loop

3. **Tool 描述比 Tool 实现更重要**
   - 模型通过 function description 和 parameters 决定是否调用
   - 描述不清晰 → 模型不知道什么时候用 → 永远不调用

4. **阿里云百炼兼容方案**
   - 使用 OpenAI 兼容接口：`base_url="https://coding.dashscope.aliyuncs.com/v1"`
   - 模型名称：`qwen3.5-plus`（后续也可用 `qwen3.6-plus`）

---

## 📊 进度追踪

| 时间段 | 任务 | 状态 | 用时 |
|--------|------|------|------|
| Day 1-2 | 环境搭建 + Hello Agent | ✅ 已完成 | ~1h |
| Day 3-4 | Run Loop 理解 + Tool 调用 | ✅ 已完成 | ~1.5h |

**总用时**: 预计 2.5 小时 | 实际：~2.5h

---

## 🚀 前置要求

- Python 3.9+
- 阿里云百炼 API Key（DASHSCOPE_API_KEY）

---

## 🔗 后续学习

- **Week 2**: 多 Tool 协作、结构化输出、Guardrails、Tracing
- **Week 3**: 基于 Week 2 的代码进行调试和优化

---

**下一步**: 开始 Week 2 - Tool 与结构化
