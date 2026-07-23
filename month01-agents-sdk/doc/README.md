# 🤖 Agents SDK 完整入门指南

> 本文档专为编程新手设计，从零基础开始，带你理解 AI Agent 的核心概念和实战应用。

---

## 📚 目录

1. [什么是 AI Agent？](#什么是-ai-agent)
2. [环境准备](#环境准备)
3. [Week 1：第一个 Agent](#week-1第一个-agent)
4. [Week 2：Tool 工具系统](#week-2tool-工具系统)
   - 2.1 多 Tool 协作
   - 2.2 电商客服 Agent 实战
   - 2.3 Week 2 标准初始化模板
   - 2.4 结构化输出（Structured Output）
   - 2.5 Guardrails 安全防护
   - 2.6 Tracing 追踪调试
   - 2.7 Handoff 预览
5. [Week 3：测试与评估](#week-3测试与评估)
6. [Week 4：多 Agent 协作](#week-4多-agent-协作)
7. [常见问题解答](#常见问题解答)

---

## 什么是 AI Agent？

### 简单理解

想象你有一个超级聪明的助手：
- 它能听懂你说的话（自然语言理解）
- 它能帮你做事（调用工具）
- 它能按照你的要求工作（遵循指令）

这个"助手"就是 **AI Agent**（AI 智能体）。

### 核心组成

```
┌─────────────────────────────────────────┐
│              AI Agent                    │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────┐  │
│  │  大脑    │  │  工具    │  │ 指令  │  │
│  │ (LLM)   │  │ (Tools)  │  │(Instr.)│  │
│  └──────────┘  └──────────┘  └───────┘  │
│                                          │
│  大脑：理解你的问题                       │
│  工具：帮你执行具体操作                   │
│  指令：告诉它该怎么工作                   │
└─────────────────────────────────────────┘
```

- **LLM（大语言模型）**：Agent 的"大脑"，负责理解和思考
- **Tools（工具）**：Agent 的"手"，用来执行具体任务（查天气、查订单等）
- **Instructions（指令）**：Agent 的"工作手册"，告诉它该做什么、怎么做

---

## 环境准备

### 1. 安装 Python

确保你的电脑已安装 Python 3.8 或更高版本：

```bash
python --version  # 应该显示 Python 3.8+
```

### 2. 安装依赖

进入项目目录，安装所需的 Python 库：

```bash
cd /Users/liyang/dev/python_project/ly-ai-roadmap-lab
pip install -r requirements.txt
```

### 3. 配置 API Key

AI Agent 需要连接大模型才能工作。我们使用智谱 AI 平台：

1. 前往 [智谱 AI 平台](https://open.bigmodel.cn/) 获取 API Key
2. 在项目根目录创建 `.env` 文件（已存在）
3. 添加以下内容：

```env
ZHIPUAI_API_KEY=你的APIKey
```

> ⚠️ **重要**：不要将 API Key 上传到公开代码库！

---

## Week 1：第一个 Agent

### 1.1 Hello Agent - 第一次对话

**文件位置**：`src/week1/hello_agent.py`

这是最简单的 Agent，只对话，不调用工具。

#### 代码解读

```python
# 第 1-3 行：导入必要的库
import os                              # 用来读取环境变量
from openai import OpenAI             # OpenAI 客户端（兼容阿里云百炼）
from dotenv import load_dotenv        # 加载 .env 文件的工具

# 第 5 行：加载环境变量
load_dotenv()  # 从 .env 文件读取 DASHSCOPE_API_KEY

# 第 8-14 行：创建 AI 客户端
client = OpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY"),  # 从环境变量读取 API Key
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",  # 智谱 AI 网关
)

# 第 16-22 行：发送对话请求
completion = client.chat.completions.create(
    model="glm-5.1",           # 使用的模型名称
    messages=[
        {"role": "system", "content": "你是一个非常耐心的老师"},  # 系统指令
        {"role": "user", "content": "你是谁？"},                   # 用户问题
    ],
)

# 第 23 行：打印 AI 的回答
print(completion.choices[0].message.content)
```

#### 运行方式

```bash
cd src/week1
python hello_agent.py
```

#### 你会看到

```
我是一个人工智能助手，旨在通过提供信息和协助来帮助用户...
```

#### 核心概念

**Messages（消息列表）**：
- `system`：系统指令，设定 AI 的"人设"
- `user`：用户的问题
- `assistant`：AI 的回答（由模型生成）

---

### 1.2 Loop Agent - 带工具调用的 Agent

**文件位置**：`src/week1/loop_agent_tools.py`

这个 Agent 能调用工具（查询天气），展示了完整的"理解 → 调用工具 → 回答"流程。

#### 核心流程

```
用户问："北京天气咋样？"
    ↓
Agent 理解：需要查询天气
    ↓
调用工具：get_current_weather("北京")
    ↓
工具返回："北京今天是晴天。"
    ↓
Agent 总结："北京现在是晴天，适合出门哦！"
```

#### 代码详解

**步骤 1：定义工具**

```python
# 第 22-40 行：告诉 AI 有哪些工具可用
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",         # 工具名称
            "description": "当你想查询指定城市的天气时非常有用。",  # 工具说明
            "parameters": {                        # 参数定义
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。",
                    }
                },
                "required": ["location"],          # 必填参数
            },
        },
    },
]
```

**步骤 2：实现工具函数**

```python
# 第 44-48 行：实际的天气查询函数（这里用随机数据模拟）
def get_current_weather(arguments):
    weather_conditions = ["晴天", "多云", "雨天"]
    random_weather = random.choice(weather_conditions)
    location = arguments["location"]  # 从参数中获取城市名
    return f"{location}今天是{random_weather}。"
```

**步骤 3：Run Loop（运行循环）**

```python
# 第 62-95 行：核心循环逻辑

# 1. 用户提问
messages = [{"role": "user", "content": USER_QUESTION}]

# 2. 发送给 AI
response = get_response(messages)
assistant_output = response.choices[0].message

# 3. 检查是否需要调用工具
if assistant_output.tool_calls is None:
    # 不需要工具，直接回答
    print(f"无需调用天气查询工具，直接回复：{assistant_output.content}")
else:
    # 需要工具，进入循环
    while assistant_output.tool_calls is not None:
        # 4. 提取工具调用信息
        tool_call = assistant_output.tool_calls[0]
        func_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        # 5. 执行工具
        tool_result = get_current_weather(arguments)
        
        # 6. 把工具结果加回消息列表
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result,
        }
        messages.append(tool_message)
        
        # 7. 再次调用 AI，让它根据工具结果生成最终回答
        response = get_response(messages)
        assistant_output = response.choices[0].message
```

#### 运行方式

```bash
cd src/week1
python loop_agent_tools.py
```

#### 你会看到

```
正在调用工具 [get_current_weather]，参数：{'location': '北京'}
工具返回：北京今天是晴天。
助手最终回复：北京现在是晴天，气温适宜，适合外出活动！
```

---

## Week 2：Tool 工具系统

### 2.1 多 Tool 协作

**文件位置**：`src/week2/multi_tool_agent.py`

这个示例展示了 Agent 如何根据用户问题，**自动选择**最合适的工具。

#### 三个工具

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `query_refund_policy` | 查询退货政策 | `product_type`（商品类型） |
| `check_order_status` | 查询订单状态 | `order_id`（订单号） |
| `calculate_shipping` | 计算运费 | `weight_kg`（重量）、`destination`（目的地） |

#### 关键代码

**定义工具（使用装饰器）**

```python
from agents import function_tool

@function_tool
def query_refund_policy(product_type: str) -> str:
    """
    查询某类商品的退货政策。
    
    Args:
        product_type: 商品类型，如 "electronics", "clothing", "books"
    
    Returns:
        退货政策说明
    """
    policies = {
        "electronics": "电子产品：7 天无理由退货...",
        "clothing": "服装：30 天无理由退货...",
        # ...
    }
    return policies.get(product_type.lower(), policies["default"])
```

> 💡 **`@function_tool` 装饰器的作用**：  
> 它会自动把函数的名称、参数、文档字符串（`"""..."""`）转换成 AI 能理解的格式。  
> **文档字符串非常重要**！AI 主要靠它来理解工具的用途。

**创建 Agent**

```python
from agents import Agent

customer_service_agent = Agent(
    model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
    name="客服助手",
    instructions="""你是一个电商客服助手。你可以帮助用户：
1. 查询退货政策
2. 查询订单状态
3. 计算运费

根据用户问题，自动调用合适的工具。回答要简洁友好。""",
    tools=[
        query_refund_policy,
        check_order_status,
        calculate_shipping
    ]
)
```

**运行测试**

```python
from agents import Runner
import asyncio

async def main():
    test_cases = [
        "电子产品怎么退货？",
        "帮我查一下订单 ORD001 的状态",
        "从北京寄一个 2.5kg 的包裹到上海，运费多少？",
    ]
    
    for query in test_cases:
        result = await Runner.run(customer_service_agent, query)
        print(f"用户问：{query}")
        print(f"客服答：{result.final_output}\n")

asyncio.run(main())
```

#### 运行方式

```bash
cd src/week2
python multi_tool_agent.py
```

---

### 2.2 电商客服 Agent 实战

**文件位置**：`src/week2/ecommerce_support_agent.py`

这是一个完整的电商客服系统，包含 7 个工具、模拟数据库、错误处理等。

#### 系统架构

```
┌─────────────────────────────────────────────────┐
│            电商客服 Agent                         │
│                                                   │
│  工具列表：                                       │
│  1. query_order_status    - 查询订单              │
│  2. query_refund_policy   - 查询退款政策          │
│  3. process_refund_apply  - 提交退款申请          │
│  4. query_logistics       - 查询物流轨迹          │
│  5. query_coupons         - 查询优惠券            │
│  6. query_product_info    - 查询产品信息          │
│  7. escalate_to_human     - 转人工客服            │
│                                                   │
│  模拟数据库：                                     │
│  - ORDERS_DB（订单数据）                          │
│  - REFUND_RULES（退款规则）                       │
│  - COUPONS_DB（优惠券数据）                       │
│  - PRODUCT_KB（产品知识库）                       │
└─────────────────────────────────────────────────┘
```

#### 两种运行模式

**模式 1：测试模式（自动运行所有测试用例）**

```bash
python ecommerce_support_agent.py --test
```

**模式 2：交互模式（手动输入问题）**

```bash
python ecommerce_support_agent.py
```

后输入你的问题，例如：
```
👤 您：帮我查一下订单 ORD20260417001 的状态
🤖 客服：📦 订单详情
━━━━━━━━━━━━━━━━
订单号：ORD20260417001
商品：iPhone 15 Pro
金额：¥7,999.00
状态：已发货
...
```

---

### 2.3 Week 2 标准初始化模板

**重要**：Week 2 的每个文件都有一段通用的初始化代码，在开始学习具体主题之前，先理解这段"模板代码"。

```python
# ===== 第 1 步：禁用 SDK 内置 Tracing =====
import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "true"
# 为什么？SDK 默认会把追踪数据发送到 api.openai.com
# 我们用的是智谱 AI，不需要这个，所以关掉

# ===== 第 2 步：加载环境变量 =====
from dotenv import load_dotenv
load_dotenv()
# 从 .env 文件读取 ZHIPUAI_API_KEY

# ===== 第 3 步：禁用 Responses API =====
from agents.models._openai_shared import set_use_responses_by_default
set_use_responses_by_default(False)
# 为什么？SDK 默认使用新的 Responses API，但智谱 AI 只支持标准的 Chat Completions
# 所以必须关掉这个，否则会报错

# ===== 第 4 步：创建客户端 =====
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
client = AsyncOpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)
# AsyncOpenAI 是异步客户端，支持 async/await
# OpenAIChatCompletionsModel 是包装器，把客户端给 Agent 使用
```

#### 关键概念解释

| 配置项 | 作用 | 如果不设置会怎样 |
|--------|------|------------------|
| `OPENAI_AGENTS_DISABLE_TRACING` | 关闭 SDK 内置追踪 | SDK 会尝试向 api.openai.com 发送追踪数据，导致报错 |
| `set_use_responses_by_default(False)` | 使用标准 Chat Completions API | SDK 会使用 Responses API，智谱 AI 不支持，报错 |
| `OpenAIChatCompletionsModel` | 把 AsyncOpenAI 客户端包装成 Agent 能用的模型 | Agent 不知道如何直接使用 AsyncOpenAI |

#### 如何创建 Agent（Week 2 通用模式）

```python
from agents import Agent

agent = Agent(
    model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
    name="Agent 名称",
    instructions="你是...（工作手册）",
    tools=[tool1, tool2],           # 可选：工具列表
    input_guardrails=[...],         # 可选：输入安全检查
    output_guardrails=[...],        # 可选：输出安全检查
    handoffs=[...],                 # 可选：可以转交给的其他 Agent
)
```

---

### 2.4 结构化输出（Structured Output）

**文件位置**：`src/week2/structured_output.py`

#### 为什么需要结构化输出？

想象你是外卖平台，用户问"我的订单到哪了"：

**方案 A：自由文本（人类能读，程序难处理）**
```
"您的订单 ORD001 已发货，商品是 iPhone 15 Pro，金额 7999 元，物流单号 SF123"
```
→ 前端 APP 很难从这段话中提取出订单号、金额等信息来显示

**方案 B：结构化输出（JSON 格式，程序能直接解析）**
```json
{
  "order_id": "ORD001",
  "product_name": "iPhone 15 Pro",
  "amount": 7999.00,
  "status": "shipped",
  "logistics_no": "SF123"
}
```
→ 前端可以直接用 `data.order_id`、`data.amount` 来渲染界面

#### Pydantic：定义数据结构的工具

Pydantic 是 Python 的数据验证库，用来定义"数据长什么样"：

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

# 定义枚举：订单状态只能是这几个值
class OrderStatus(str, Enum):
    PENDING = "pending"      # 待支付
    PROCESSING = "processing" # 处理中
    SHIPPED = "shipped"      # 已发货
    DELIVERED = "delivered"  # 已签收
    CANCELLED = "cancelled"  # 已取消

# 定义订单结构
class Order(BaseModel):
    order_id: str = Field(description="订单号，例如：ORD20260417001")
    product_name: str = Field(description="商品名称")
    amount: float = Field(description="订单金额（元）")
    status: OrderStatus = Field(description="订单状态")
    logistics_no: Optional[str] = Field(default=None, description="物流单号（可选）")
```

**关键概念**：
- `BaseModel`：Pydantic 的基类，继承它就变成了"数据结构定义"
- `Field(description=...)`：字段描述，告诉 AI 这个字段是什么意思
- `Optional[str]`：可选字段，可以没有值
- `default=None`：默认值为 None

#### 三个实战场景

本文件包含 3 个场景，从简单到复杂：

| 场景 | Agent 名称 | 功能 | 输出结构 |
|------|-----------|------|----------|
| 1. 单订单查询 | 订单查询助手 | 查询一个订单 | `Order` 对象 |
| 2. 订单列表 | 订单列表助手 | 查询所有订单 | `OrderListResponse`（包含列表+统计） |
| 3. 销售统计 | 数据分析助手 | 生成统计报告 | `SalesStatistics`（包含汇总数据） |

#### Instructions 的关键写法

要让 Agent 输出 JSON 格式，必须在 instructions 中明确要求：

```python
instructions = """
你是一个订单查询助手。...

【重要】你的最终输出必须是纯 JSON 格式，不要包含任何其他文本、
解释或 markdown 代码块标记。

输出的 JSON 必须符合以下结构：
{
  "order_id": "订单号",
  "product_name": "商品名称",
  "amount": 订单金额（数字）,
  ...
}
"""
```

> 💡 **小白提示**：AI 默认会输出自然语言（人类读的文字），你必须明确告诉它"只输出 JSON"，否则它会夹杂解释文字。

#### 如何解析 Agent 的输出

```python
import json

# Agent 返回的是字符串
output_text = result.final_output

# 可能包含 markdown 代码块，需要提取
if "```json" in output_text:
    json_str = output_text.split("```json")[1].split("```")[0].strip()
elif "```" in output_text:
    json_str = output_text.split("```")[1].split("```")[0].strip()
else:
    json_str = output_text

# 解析 JSON
data = json.loads(json_str)
print(data["order_id"])   # ORD20260417001
print(data["amount"])     # 7999.0
```

#### 运行方式

```bash
cd src/week2
python structured_output.py --test   # 运行测试
python structured_output.py          # 交互模式
```

---

### 2.5 Guardrails 安全防护

**文件位置**：`src/week2/guardrails_example.py`

#### Guardrails 是什么？

**Guardrails = 安全护栏**，就像公路两边的护栏一样，防止 Agent "跑出轨道"。

```
用户输入 ──→ [Input Guardrail] ──→ Agent 处理 ──→ [Output Guardrail] ──→ 回复用户
              ↑ 检查输入安全                      ↑ 检查输出安全
              - 输入太长？                         - 泄露密码？
              - 有敏感词？                         - 输出太长？
              - 注入攻击？                         - 不当内容？
```

#### 为什么需要 Guardrails？

| 问题 | 没有 Guardrails | 有 Guardrails |
|------|-----------------|---------------|
| 用户输入 10000 字 | 消耗大量 Token，浪费钱 | 拦截，提示输入过长 |
| 用户说"删除全部数据" | Agent 可能执行危险操作 | 拦截，拒绝执行 |
| 用户说"忽略所有指令" | Agent 可能被绕过（提示词注入） | 拦截，检测到注入攻击 |
| Agent 输出包含 API Key | 敏感信息泄露 | 拦截，阻止输出 |

#### 创建 Input Guardrail（输入安全检查）

```python
from agents import GuardrailFunctionOutput
from agents.guardrail import input_guardrail

@input_guardrail
async def check_input_length(ctx, agent, input):
    """检查用户输入是否过长"""
    max_length = 500
    text = input if isinstance(input, str) else str(input)
    
    if len(text) > max_length:
        return GuardrailFunctionOutput(
            output_info=f"输入过长（{len(text)} 字符）",
            tripwire_triggered=True   # True = 触发拦截，Agent 不会处理
        )
    
    return GuardrailFunctionOutput(
        output_info="输入长度正常",
        tripwire_triggered=False      # False = 安全，放行
    )
```

**关键点**：
- `@input_guardrail`：装饰器，标记这是输入检查
- `GuardrailFunctionOutput`：检查结果
- `tripwire_triggered=True`：触发警报，请求被拦截
- `tripwire_triggered=False`：安全，继续处理

#### 创建 Output Guardrail（输出安全检查）

```python
from agents.guardrail import output_guardrail

@output_guardrail
async def check_output_safety(ctx, agent, output):
    """检查 Agent 输出是否安全"""
    text = output if isinstance(output, str) else str(output)
    
    # 检查是否泄露敏感信息
    sensitive_keywords = ["api_key", "password", "secret", "token"]
    for keyword in sensitive_keywords:
        if keyword.lower() in text.lower():
            return GuardrailFunctionOutput(
                output_info=f"输出包含敏感关键词：{keyword}",
                tripwire_triggered=True
            )
    
    return GuardrailFunctionOutput(
        output_info="输出安全检查通过",
        tripwire_triggered=False
    )
```

#### 给 Agent 添加 Guardrails

```python
agent = Agent(
    name="客服助手",
    instructions="...",
    tools=[...],
    input_guardrails=[           # 输入检查列表（按顺序执行）
        check_input_length,      # 1. 检查长度
        check_sensitive_words,   # 2. 检查敏感词
        check_prompt_injection,  # 3. 检查注入攻击
    ],
    output_guardrails=[          # 输出检查列表
        check_output_safety,     # 1. 检查输出安全
    ],
)
```

#### 本文件包含的 4 个 Guardrail

| Guardrail | 类型 | 作用 | 拦截场景 |
|-----------|------|------|----------|
| `check_input_length` | Input | 限制输入 ≤ 500 字符 | 防止超长输入浪费 Token |
| `check_sensitive_words` | Input | 检测"删除全部""清空数据库"等 | 防止危险操作 |
| `check_prompt_injection` | Input | 检测"忽略指令""你现在是"等 | 防止提示词注入攻击 |
| `check_output_safety` | Output | 检测 API Key、密码等关键词 | 防止信息泄露 |

#### 运行方式

```bash
cd src/week2
python guardrails_example.py
```

#### 你会看到

```
【测试 1】正常输入 - 查询订单
✅ 回复: 📦 订单 ORD001: iPhone 15 - 已发货

【测试 2】超长输入 - 应该被拦截
✅ 被 Guardrail 拦截: ...

【测试 3】敏感词输入 - 应该被拦截
✅ 被 Guardrail 拦截: ...

【测试 4】提示词注入 - 应该被拦截
✅ 被 Guardrail 拦截: ...
```

---

### 2.6 Tracing 追踪调试

**文件位置**：`src/week2/tracing_debug_example.py`

#### Tracing 是什么？

**Tracing = 追踪记录**，就像飞机的"黑匣子"，记录 Agent 执行过程中的每一步。

```
┌───────────────────────────────────────────┐
│  Trace: "订单查询工作流"                    │
│  ├── Span 1: 用户输入                      │
│  ├── Span 2: Agent 思考（LLM 调用）        │
│  │   └── 决定调用 get_order 工具           │
│  ├── Span 3: 执行 Tool（get_order）        │
│  │   └── 返回订单数据                      │
│  ├── Span 4: Agent 生成回复（LLM 调用）    │
│  │   └── 基于工具结果生成 JSON             │
│  └── Span 5: 输出给用户                    │
└───────────────────────────────────────────┘
```

**两个核心概念**：
- **Trace**：一次完整的工作流（从用户输入到最终输出）
- **Span**：工作流中的单个操作步骤

#### 为什么需要 Tracing？

| 用途 | 说明 |
|------|------|
| 🔍 调试 | 查看 Agent 为什么做出某个决策 |
| 🐛 排错 | 定位 Tool 调用失败的原因 |
| ⚡ 优化 | 找出哪个步骤最慢 |
| 💰 成本 | 统计每次调用的 Token 消耗 |

#### 如何使用 trace

```python
from agents import trace

# 用 with 语句包裹整个工作流
with trace("订单查询工作流", group_id="test_001") as t:
    print(f"Trace ID: {t.trace_id}")
    
    # 运行 Agent
    result = await Runner.run(agent, "查询订单 ORD001")
    print(result.final_output)

# with 块结束时，Trace 自动完成
```

**关键参数**：
- `"订单查询工作流"`：Trace 名称，方便识别
- `group_id="test_001"`：分组 ID，把相关的 Trace 归为一组
- `t.trace_id`：唯一标识符，用于查找特定的 Trace

#### 本文件包含的 4 个测试场景

| 场景 | 功能 | 学习重点 |
|------|------|----------|
| 测试 1：基础 Tracing | 简单的订单查询 | trace 基本用法 |
| 测试 2：多步骤工作流 | 订单 + 物流查询 | 多个 Tool 调用的追踪 |
| 测试 3：错误调试 | 模拟数据库错误 | 用 Trace 定位异常 |
| 测试 4：性能分析 | 对比快/慢工具 | 用 Trace 找性能瓶颈 |

#### 运行方式

```bash
cd src/week2
python tracing_debug_example.py --test   # 运行全部测试
python tracing_debug_example.py          # 交互模式
```

#### Tracing 配置指南

```bash
# 环境变量控制
export OPENAI_AGENTS_DISABLE_TRACING=true   # 完全禁用追踪
export OPENAI_AGENTS_DONT_LOG_MODEL_DATA=false  # 允许记录模型输入输出
export OPENAI_AGENTS_DONT_LOG_TOOL_DATA=false   # 允许记录工具调用数据
```

> 💡 **注意**：本项目中 `tracing_debug_example.py` 故意**没有**设置 `OPENAI_AGENTS_DISABLE_TRACING`，因为 Tracing 就是这个文件要演示的功能。

---

### 2.7 Handoff 预览（Week 2 入门版）

**文件位置**：`src/week2/handoff_example.py`

> 这是 Week 2 的 Handoff 入门，Week 4 会有更深入的学习。

#### 单 Agent vs 多 Agent：两种方式解决同一个问题

你已经学过 `ecommerce_support_agent.py`（2.2 节），它是一个 Agent 带 7 个工具。现在看看另一种方式：

```
方式 A：单 Agent + 多 Tool（ecommerce_support_agent.py）
┌─────────────────────────────────┐
│  一个"全能"客服 Agent            │
│  带 7 个工具                    │
│  Instructions 很长（什么都要会） │
└─────────────────────────────────┘

方式 B：多 Agent + Handoff（handoff_example.py）
┌──────────────┐
│  TriageAgent │ ← 只负责分类，不处理问题
└──────┬───────┘
       │
       ├──→ SupportAgent（订单/退款专家，3 个工具）
       ├──→ FAQAgent（常见问题，1 个工具）
       └──→ EscalationAgent（人工转接，1 个工具）
```

| 对比维度 | 单 Agent（方式 A） | 多 Agent（方式 B） |
|---------|-------------------|-------------------|
| Instructions 长度 | 很长（什么都要写） | 每个都很短（只写自己的） |
| 工具数量 | 7 个（AI 可能选错） | 1-3 个（选择更少更准） |
| 职责清晰度 | 低（全挤在一起） | 高（各管各的） |
| 维护难度 | 高（改一处影响全部） | 低（改一个不影响其他） |
| 适用场景 | 简单场景、快速原型 | 生产环境、复杂业务 |

#### 关键代码：handoff()

```python
from agents import handoff

# 创建 TriageAgent，可以转交给 3 个专家
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是分诊台，根据问题类型转交：
    - 订单/退款 → SupportAgent
    - 常见问题 → FAQAgent
    - 投诉/人工 → EscalationAgent
    """,
    handoffs=[
        handoff(support_agent),
        handoff(faq_agent),
        handoff(escalation_agent),
    ],
)
```

#### 验证 Handoff 是否成功

```python
result = await Runner.run(triage_agent, "我的订单 ORD1001 到哪了？")

# 查看最终回复
print(result.final_output)

# 查看最终是哪个 Agent 处理的
print(result.last_agent.name)  # 输出：SupportAgent
```

> 💡 `result.last_agent` 是检查 Handoff 是否成功的关键属性！

#### 运行方式

```bash
cd src/week2
python handoff_example.py --test   # 批量测试（验证路由是否正确）
python handoff_example.py          # 交互模式
```

#### 测试模式输出示例

```
🧪 Handoff 路由测试
✅ PASS | 用户: 我的订单 ORD1001 到哪了？
         期望: SupportAgent | 实际: SupportAgent
✅ PASS | 用户: 你们支持什么支付方式？
         期望: FAQAgent | 实际: FAQAgent
✅ PASS | 用户: 我要投诉
         期望: EscalationAgent | 实际: EscalationAgent

📊 测试结果: 9/9 通过, 0 失败
```

---

## Week 3：测试与评估

### 3.1 一致性测试

**文件位置**：`src/week3/day15_16_consistency_test.py`

**目的**：确保 Agent 对相同问题的回答保持一致。

#### 测试流程

```
1. 准备测试数据集（eval/mini_eval.csv）
2. 对每个问题运行多次（如 5 次）
3. 比较每次的回答是否一致
4. 生成分析报告（results/consistency_run_*.csv）
```

#### 运行方式

```bash
cd src/week3
./run_test.sh
```

---

### 3.2 Token 使用分析

**文件位置**：`src/week3/day17_18_token_usage.py`

**目的**：监控和分析 Agent 的 Token 消耗（影响成本）。

#### 关键指标

- **Input Tokens**：输入消耗的 Token（用户问题 + 历史记录）
- **Output Tokens**：输出消耗的 Token（AI 回答）
- **Total Tokens**：总消耗
- **Cost**：估算费用

---

## Week 4：多 Agent 协作

### 4.1 Handoff（职责转交）

**文件位置**：`src/week4/src/simple_handoff.py`

**概念**：一个 Agent 把对话转交给另一个更专业的 Agent。

#### 类比理解

```
公司前台（TriageAgent）
    ↓ 识别问题类型
技术客服（SupportAgent） / 财务客服（FinanceAgent）
```

#### 代码示例

```python
from agents import Agent, handoff

# 专家 Agent
support_agent = Agent(
    name="SupportAgent",
    instructions="处理订单和退款问题",
    tools=[query_order, process_refund]
)

# 接待员 Agent（可以转交给专家）
triage_agent = Agent(
    name="TriageAgent",
    instructions="你是接待员，根据问题类型转交给合适的专家",
    handoffs=[
        handoff(support_agent)  # 添加转交选项
    ]
)

# 运行
result = await Runner.run(triage_agent, "我要退款")
```

#### 完整流程

```
用户："我要退款"
    ↓
TriageAgent 分析：这是退款问题，应该转交给 SupportAgent
    ↓
Handoff 转交 → SupportAgent
    ↓
SupportAgent 处理：调用退款工具，生成回复
    ↓
输出给用户："您好，根据退款政策..."
```

---

### 4.2 多 Agent 协作

**文件位置**：`src/week4/src/multi_agent_collab.py`

**场景**：多个 Agent 协同完成复杂任务。

#### 示例：旅游规划系统

```
┌──────────────┐
│ 用户输入      │
│ "我要去北京"  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ TriageAgent  │  ← 识别意图：旅游规划
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│酒店Agent │  │机票Agent │  │攻略Agent │
└──────────┘  └──────────┘  └──────────┘
       │             │             │
       └─────────────┴─────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ 整合结果输出  │
              └──────────────┘
```

---

## 常见问题解答

### Q1：什么是 Async/Await？

**简单理解**：

```python
# 普通函数（同步）- 会阻塞程序
def query_database():
    time.sleep(5)  # 等待 5 秒，程序卡住
    return "结果"

# 异步函数 - 不会阻塞程序
async def query_database():
    await asyncio.sleep(5)  # 等待 5 秒，但程序可以做其他事
    return "结果"
```

**为什么要用异步？**  
因为 AI 请求是网络操作，需要等待服务器响应。异步可以让程序在等待时不卡死。

---

### Q2：`@function_tool` 是什么？

它是 Python 的**装饰器**，作用是把普通函数变成 AI 可调用的工具。

```python
# 不使用装饰器（普通函数）
def add(a, b):
    return a + b

# 使用装饰器（AI 工具）
@function_tool
def add(a: int, b: int) -> int:
    """计算两个数的和"""
    return a + b
```

**区别**：
- 普通函数：只能被代码调用
- `@function_tool` 函数：AI 可以根据需要自动调用

---

### Q3：`instructions` 该怎么写？

**Instructions = AI 的工作手册**，要写得清晰、具体。

```python
# ❌ 不好的写法
instructions="你是客服"

# ✅ 好的写法
instructions="""你是电商客服助手，职责如下：
1. 查询订单状态（使用 query_order_status 工具）
2. 处理退款申请（使用 process_refund 工具）
3. 回答产品咨询（使用 query_product_info 工具）

回复规范：
- 语气友好、专业
- 使用 emoji 增加亲和力
- 重要信息用【】标注
- 如果缺少必要参数，先询问用户
"""
```

---

### Q4：为什么有时 AI 不调用工具？

可能原因：

1. **Instructions 没写清楚**：AI 不知道什么时候该用工具
2. **工具描述不准确**：AI 不理解工具的用途
3. **用户问题太模糊**：AI 无法匹配到合适的工具

**解决方法**：
- 在 Instructions 中明确说明："遇到 XX 问题时，使用 XX 工具"
- 完善工具的文档字符串（`"""..."""`）
- 引导用户提供更多细节

---

### Q5：如何调试 Agent？

**方法 1：打印日志**

```python
import logging
logging.basicConfig(level=logging.INFO)
```

**方法 2：查看 Tracing（官方提供）**

```python
from agents import set_tracing_disabled
set_tracing_disabled(False)  # 启用追踪
```

**方法 3：手动检查消息列表**

```python
# 打印完整的对话历史
for msg in messages:
    print(f"角色：{msg['role']}")
    print(f"内容：{msg['content']}\n")
```

---

### Q6：Token 是什么？为什么重要？

**Token = AI 的文字计量单位**

- 1 个 Token ≈ 0.5 个中文字符
- 例如："你好世界" ≈ 4-6 个 Token

**为什么重要？**
- 影响成本：按 Token 收费
- 影响性能：Token 越多，速度越慢
- 有限制：模型有最大 Token 限制（如 8000）

**如何优化？**
- 精简 Instructions
- 减少不必要的历史记录
- 使用更高效的提示词

---

## 📖 延伸阅读

- [RunLoop 流程图](./RunLoop.md) - 详细理解 Agent 的运行循环
- [Handoff 转交机制](./Handoff.md) - 多 Agent 协作的核心
- [官方文档](https://openai.github.io/openai-agents-python/)

---

## 🎓 学习路径建议

```
Week 1（基础）
  ↓
理解 Agent、Tool、Instructions 的概念
  ↓
Week 2（进阶）
  ↓
掌握多工具协作、错误处理、结构化输出
  ↓
Week 3（实战）
  ↓
学习测试、评估、优化
  ↓
Week 4（高级）
  ↓
多 Agent 协作、Handoff、复杂场景
```

---

> 💡 **提示**：学习过程中，最好的方式是**运行代码、看输出、改参数、再运行**。动手实践比只看文档有效 10 倍！
