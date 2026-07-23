# 🔄 Run Loop 详解 - Agent 的运行机制

> **小白必看**：本文档用最通俗的方式解释 Agent 是如何工作的

---

## 📚 什么是 Run Loop？

**Run Loop = 运行循环**，就是 Agent 从"听到问题"到"给出答案"的完整过程。

### 生活类比

想象你去餐厅点餐：

```
1. 你告诉服务员："我要一份宫保鸡丁"     ← 用户输入
2. 服务员理解你的需求                      ← Agent 理解意图
3. 服务员确认：需要辣椒吗？                ← 判断是否需要工具
4. 你说："微辣"                           ← 提供参数
5. 服务员下单给厨房                        ← 调用工具
6. 厨房做好菜                              ← 工具返回结果
7. 服务员端给你                            ← 生成最终回复
```

**Agent 的工作方式完全一样！**

---

## 🎯 核心概念

### Messages（消息列表）

Agent 的"记忆"，保存所有对话历史。

```python
messages = [
    {"role": "user", "content": "北京天气怎么样？"},      # 用户说的话
    {"role": "assistant", "content": "我来帮你查询..."}, # AI 说的话
    {"role": "tool", "content": "晴天，25°C"}            # 工具返回的结果
]
```

**三种角色**：
- `user`：用户
- `assistant`：AI 助手
- `tool`：工具

### Tools（工具）

Agent 的"手"，用来执行具体操作。

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",              # 工具名称
            "description": "查询天气",           # 工具说明（AI 靠这个理解用途）
            "parameters": {                     # 参数定义
                "location": "城市名"             # 需要哪些信息
            }
        }
    }
]
```

---

## 📊 流程图详解

### 场景 1：基础流程（无 Tool）

**例子**：用户打招呼，不需要调用工具

```
┌─────────────┐
│  用户输入   │
│  "Hello!"   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│   Agent 理解意图        │
│   判断：这是问候，      │
│   不需要工具            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   直接生成回复          │
│   基于 instructions     │
│   和对话历史            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│  输出给用户 │
│  "Hi! How   │
│   can I     │
│   help?"    │
└─────────────┘
```

**真实代码示例**（来自 `src/week1/hello_agent.py`）：

```python
# 第 1 步：构建消息
messages = [
    {"role": "system", "content": "你是一个非常耐心的老师"},
    {"role": "user", "content": "你是谁？"},
]

# 第 2 步：发送给 AI
completion = client.chat.completions.create(
    model="glm-5.1",  # 智谱 AI 模型名称
    messages=messages,
)

# 第 3 步：获取回复
print(completion.choices[0].message.content)
# 输出：我是一个人工智能助手...
```

**关键点**：
- 没有 `tools` 参数，AI 直接回答
- 适合简单问答、闲聊、知识咨询等场景

---

### 场景 2：完整流程（带 Tool 调用）

**例子**：用户查询天气，需要调用工具

```
┌─────────────┐
│  用户输入   │
│ "北京天气   │
│  怎么样？"  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│   第 1 轮：Agent 分析   │
│   ┌───────────────────┐ │
│   │ 理解：需要天气    │ │
│   │ 匹配：get_weather │ │
│   │ 决策：调用工具    │ │
│   └───────────────────┘ │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   提取 Tool 参数        │
│   city = "北京"         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   执行 Tool             │
│   get_weather("北京")   │
│   → 返回："晴天，25°C"  │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   第 2 轮：整合结果     │
│   把工具结果加入消息    │
│   再次请求 AI 总结      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│  输出给用户 │
│  "北京现在  │
│   晴朗，    │
│   气温 25   │
│   度。"     │
└─────────────┘
```

**真实代码示例**（来自 `src/week1/loop_agent_tools.py`）：

```python
# 第 1 步：用户提问
messages = [{"role": "user", "content": "北京天气咋样"}]

# 第 2 步：发送给 AI（带 tools 参数）
response = client.chat.completions.create(
    model="glm-5.1",  # 智谱 AI 模型名称
    extra_body={"enable_thinking": False},  # 关闭模型的思考模式
    messages=messages,
    tools=tools  # 告诉 AI 有哪些工具可用
)

# 第 3 步：检查是否需要调用工具
assistant_output = response.choices[0].message

# ❗ 关键细节：assistant 消息也要追加到 messages
messages.append(assistant_output)
# 为什么？因为后续工具调用需要完整的对话上下文
# AI 需要看到自己之前说过什么，才能正确总结工具结果

if assistant_output.tool_calls is None:
    # 不需要工具，直接输出
    print(f"直接回复：{assistant_output.content}")
else:
    # 需要工具，进入循环
    while assistant_output.tool_calls is not None:
        # 第 4 步：提取工具调用信息
        tool_call = assistant_output.tool_calls[0]
        func_name = tool_call.function.name  # "get_current_weather"
        arguments = json.loads(tool_call.function.arguments)  # {"location": "北京"}
        
        # 第 5 步：执行工具
        tool_result = get_current_weather(arguments)
        # tool_result = "北京今天是晴天。"
        
        # 第 6 步：把工具结果加回消息列表
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result,
        }
        messages.append(tool_message)
        
        # 第 7 步：再次调用 AI，让它根据工具结果生成最终回答
        response = client.chat.completions.create(
            model="glm-5.1",  # 智谱 AI 模型名称
            messages=messages,  # 现在消息列表包含了工具结果
            tools=tools
        )
        assistant_output = response.choices[0].message
    
    # 第 8 步：输出最终回答
    print(f"助手最终回复：{assistant_output.content}")
    # 输出：北京现在是晴天，气温适宜，适合外出活动！
```

**关键点**：
- `while` 循环：支持多次工具调用（如先查订单，再查物流）
- `messages.append(assistant_output)`：助手消息也要追加！保持对话上下文完整
- `messages.append(tool_message)`：工具结果也要追加
- 第二次调用 AI 时，它能看到工具结果，从而生成更准确的回答

#### 两个容易忽略的细节

**细节 1：`enable_thinking` 参数**

```python
response = client.chat.completions.create(
    model="glm-5.1",
    extra_body={"enable_thinking": False},  # 关闭思考模式
    messages=messages,
    tools=tools,
)
```

- 智谱 AI 的 `glm-5.1` 模型默认开启"思考模式"，会在回答前先输出一段内部思考
- 关闭它可以避免干扰工具调用解析（思考内容会混入 tool_calls）
- 实际代码在 `src/week1/loop_agent_tools.py` 第 54 行

**细节 2：`messages.append(assistant_output)` 的重要性**

```python
assistant_output = response.choices[0].message
messages.append(assistant_output)  # ← 这行不能忘！
```

很多新手会忘记把 AI 的回复也追加到 messages 中。但实际上：
- 工具调用时，AI 需要看到自己的"决定调用工具"的消息
- 否则对话上下文不完整，可能导致 AI 生成混乱的回复
- 实际代码在 `src/week1/loop_agent_tools.py` 第 66 行和第 93 行（循环内也有一处）

---

### 场景 3：多轮对话循环

**例子**：用户连续问多个问题

```
┌──────────────────────────────────────────────────┐
│                  Run Loop 循环                    │
│                                                   │
│  ┌─────────┐                                     │
│  │ 用户输入 │  "我的订单到哪了？"                 │
│  └────┬────┘                                     │
│       │                                          │
│       ▼                                          │
│  ┌─────────────────┐                             │
│  │ Agent 处理      │                             │
│  │ - 理解意图      │  需要查询订单                │
│  │ - 调用工具      │  query_order_status()        │
│  │ - 生成回复      │  "订单已发货..."             │
│  └────┬────────────┘                             │
│       │                                          │
│       ▼                                          │
│  ┌─────────────┐                                 │
│  │  输出结果   │  "您的订单已发货，预计明天到达"  │
│  └────┬────────┘                                 │
│       │                                          │
│       │ 用户继续提问                              │
│       ▼                                          │
│  ┌─────────┐                                     │
│  │ 用户输入 │  "能退款吗？"                       │
│  └────┬────┘                                     │
│       │                                          │
│       ▼                                          │
│  ┌─────────────────┐                             │
│  │ Agent 处理      │                             │
│  │ - 理解意图      │  需要查询退款政策            │
│  │ - 调用工具      │  query_refund_policy()       │
│  │ - 生成回复      │  "支持 7 天无理由退款..."    │
│  └────┬────────────┘                             │
│       │                                          │
│       ▼                                          │
│  ┌─────────────┐                                 │
│  │  输出结果   │  "根据政策，您可以申请退款..."   │
│  └────┬────────┘                                 │
│       │                                          │
│       │ 用户说："谢谢"                            │
│       ▼                                          │
│  ┌─────────────┐                                 │
│  │  对话结束   │                                 │
│  └─────────────┘                                 │
│                                                   │
└──────────────────────────────────────────────────┘
```

**真实代码示例**（来自 `src/week2/ecommerce_support_agent.py`）：

```python
async def interactive_mode():
    """交互模式 - 用户可以连续提问"""
    agent = create_ecommerce_support_agent()
    
    while True:
        # 第 1 步：获取用户输入
        user_input = input("\n👤 您：").strip()
        
        # 第 2 步：检查退出条件
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 感谢您的使用，再见！")
            break
        
        # 第 3 步：运行 Agent
        result = await Runner.run(agent, user_input)
        
        # 第 4 步：输出结果
        print(f"\n🤖 客服：{result.final_output}")
        
        # 循环继续，等待下一个问题
```

**运行方式**：

```bash
cd src/week2
python ecommerce_support_agent.py
```

**交互示例**：

```
👤 您：帮我查一下订单 ORD20260417001 的状态
🤖 客服：📦 订单详情
━━━━━━━━━━━━━━━━
订单号：ORD20260417001
商品：iPhone 15 Pro
金额：¥7,999.00
状态：已发货
...

👤 您：那能退款吗？
🤖 客服：💰 退款政策
━━━━━━━━━━━━━━━━
订单状态：已发货
✅ 支持退款
时效：拒收或退货后
费用：运费自理
...

👤 您：好的，谢谢
🤖 客服：不客气！如有其他问题，随时联系我 😊

👤 您：quit
👋 感谢您的使用，再见！
```

---

### 场景 4：Handoff 流程（多 Agent 协作）

**例子**：用户询问退款，需要转交给专业 Agent

```
┌─────────────┐
│  用户输入   │
│ "我要退款"  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│   第 1 轮：TriageAgent  │
│   (接待员/分类)         │
│   ┌───────────────────┐ │
│   │ 分析：退款问题    │ │
│   │ 判断：超出我的    │ │
│   │       职责范围    │ │
│   │ 决策：转交        │ │
│   └───────────────────┘ │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Handoff 转交          │
│   TriageAgent →         │
│   SupportAgent          │
│   携带上下文：          │
│   "用户要退款"          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   第 2 轮：SupportAgent │
│   (专家/处理退款)       │
│   ┌───────────────────┐ │
│   │ 接收上下文        │ │
│   │ 调用 refund tool  │ │
│   │ 生成退款方案      │ │
│   └───────────────────┘ │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│  输出给用户 │
│  "您可以... │
│   申请退款" │
└─────────────┘
```

**真实代码示例**（来自 `src/week4/src/simple_handoff.py`）：

```python
from agents import Agent, Runner, handoff

# 第 1 步：创建专家 Agent
support_agent = Agent(
    name="SupportAgent",
    instructions="""你是客服专家，处理订单和退款问题。
    - 查询订单状态用 query_order_status
    - 处理退款用 process_refund
    """,
    tools=[query_order_status, process_refund]
)

# 第 2 步：创建接待员 Agent（带 handoffs）
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是接待员，根据问题类型转交：
    - 订单/退款 → SupportAgent
    - 其他 → 直接回答
    """,
    handoffs=[
        handoff(support_agent)  # 可以转交给 SupportAgent
    ]
)

# 第 3 步：运行
async def main():
    result = await Runner.run(triage_agent, "我要退款")
    print(result.final_output)
    # 输出：您好，根据我们的退款政策...
```

**关键点**：
- `handoffs=[handoff(support_agent)]`：告诉 TriageAgent 可以转交给谁
- 转交时自动携带对话上下文，SupportAgent 知道用户要什么
- 用户无感知，感觉像是在和同一个 Agent 对话

---

## 💡 核心机制总结

### 1. 为什么叫"循环"（Loop）？

因为 Agent 可能多次调用工具：

```
用户："查订单 ORD001 的物流"
    ↓
第 1 次循环：调用 query_order_status → 获得物流单号 SF123
    ↓
第 2 次循环：调用 query_logistics → 获得物流轨迹
    ↓
第 3 次循环：生成最终回复给用户
```

**代码体现**：

```python
while assistant_output.tool_calls is not None:
    # 执行工具
    tool_result = execute_tool(...)
    
    # 把结果加回消息
    messages.append(tool_result)
    
    # 再次调用 AI
    response = get_response(messages)
    assistant_output = response.choices[0].message
    
    # 如果还有工具调用，继续循环
    # 如果没有，退出循环，输出最终结果
```

### 2. Messages 的重要性

Messages 是 Agent 的"记忆"，每次调用都会累积：

```python
# 初始
messages = [
    {"role": "user", "content": "北京天气"}
]

# 第 1 次 AI 回复（说要调用工具）
messages.append({"role": "assistant", "tool_calls": [...]})

# 工具结果
messages.append({"role": "tool", "content": "晴天，25°C"})

# 第 2 次 AI 回复（最终答案）
messages.append({"role": "assistant", "content": "北京现在是晴天..."})

# 现在 messages 包含完整对话历史
# AI 能看到所有上下文
```

### 3. Async/Await 的作用

**为什么要用异步？**

```python
# 同步（会卡住）
def query_ai():
    time.sleep(5)  # 等待 5 秒，程序完全卡住
    return "结果"

# 异步（不会卡住）
async def query_ai():
    await asyncio.sleep(5)  # 等待 5 秒，但程序可以做其他事
    return "结果"
```

**实际场景**：

```python
async def main():
    # 同时发起多个请求
    task1 = asyncio.create_task(Runner.run(agent1, "问题 1"))
    task2 = asyncio.create_task(Runner.run(agent2, "问题 2"))
    
    # 等待所有完成
    results = await asyncio.gather(task1, task2)
    # 总时间 ≈ 最慢的那个，而不是所有时间相加
```

---

## 🎓 学习建议

### 动手实践

1. **运行代码**：

```bash
cd src/week1
python hello_agent.py          # 最简单
python loop_agent_tools.py     # 带工具
```

2. **修改参数**：
   - 改 `messages` 内容
   - 改 `instructions`
   - 添加新工具

3. **观察输出**：
   - 看 AI 如何理解问题
   - 看工具如何被调用
   - 看最终如何生成回答

### 调试技巧

**打印消息列表**：

```python
for i, msg in enumerate(messages):
    print(f"--- 消息 {i+1} ---")
    print(f"角色：{msg['role']}")
    print(f"内容：{msg.get('content', '无')}")
    if 'tool_calls' in msg:
        print(f"工具调用：{msg['tool_calls']}")
    print()
```

**查看工具调用**：

```python
if assistant_output.tool_calls:
    for tool_call in assistant_output.tool_calls:
        print(f"工具名：{tool_call.function.name}")
        print(f"参数：{tool_call.function.arguments}")
```

---

## 🔗 相关资源

- [完整入门指南](./README.md) - 从零开始的完整教程
- [Handoff 转交机制](./Handoff.md) - 多 Agent 协作详解
- [实际代码示例](../src/) - 可运行的完整项目

---

> 💡 **记住**：Run Loop 就是"理解 → 决策 → 执行 → 回复"的循环过程。多运行代码、看输出，比看 10 遍文档都有效！
