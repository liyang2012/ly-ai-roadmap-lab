# 🤖 Agents SDK 完整入门指南

> 本文档专为编程新手设计，从零基础开始，带你理解 AI Agent 的核心概念和实战应用。

---

## 📚 目录

1. [什么是 AI Agent？](#什么是-ai-agent)
2. [环境准备](#环境准备)
3. [Week 1：第一个 Agent](#week-1第一个-agent)
4. [Week 2：Tool 工具系统](#week-2tool-工具系统)
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

然后输入你的问题，例如：
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
