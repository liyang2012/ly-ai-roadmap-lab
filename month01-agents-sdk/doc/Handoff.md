# 🔄 Handoff 详解 - 多 Agent 协作机制

> **小白必看**：本文档用最通俗的方式解释 Handoff（职责转交）是如何工作的

---

## 📚 什么是 Handoff？

### 简单理解

**Handoff = 职责转交**，就是一个 Agent 把对话转交给另一个更专业的 Agent 处理。

### 生活类比

**场景 1：医院就诊**

```
你去医院
    ↓
分诊台护士："您哪里不舒服？"
你："我眼睛疼"
    ↓
分诊台判断：这是眼科问题
    ↓
转交 → 眼科医生
    ↓
眼科医生专业诊断和治疗
```

**场景 2：电话客服**

```
你拨打 10086
    ↓
语音助手："请问您要办理什么业务？"
你："我要查话费"
    ↓
语音助手判断：这是账单查询
    ↓
转交 → 账单专员
    ↓
账单专员帮你查询详细账单
```

**Agent 的 Handoff 完全一样！**

---

## 🎯 核心概念

### 角色分工

| 角色 | 职责 | 特点 | 类比 |
|------|------|------|------|
| **TriageAgent** | 接待员/分类员 | 只负责理解和转交，不处理具体问题 | 医院分诊台 |
| **SupportAgent** | 专家/处理员 | 处理特定领域的问题（如订单、退款） | 专科医生 |
| **FAQAgent** | 客服 | 处理常见问题（支付、发货等） | 咨询台 |

### Handoff 的时机

**需要转交的情况**：

✅ 问题超出当前 Agent 的职责范围  
✅ 需要更专业的知识  
✅ 需要调用其他 Agent 的专属 tools  

**不需要转交的情况**：

❌ 当前 Agent 能直接回答  
❌ 简单问候/闲聊  
❌ 问题不明确，需要先澄清  

---

## 💻 Handoff 代码实现

### 基础示例

**场景**：用户询问订单，TriageAgent 转交给 SupportAgent

```python
from agents import Agent, Runner, handoff

# 第 1 步：创建 SupportAgent（处理订单问题）
support_agent = Agent(
    name="SupportAgent",
    instructions="""你是客服专家，处理订单相关问题。
    - 查询订单状态
    - 处理订单修改
    - 解答订单疑问
    """,
    tools=[query_order_status, modify_order]  # 专属工具
)

# 第 2 步：创建 TriageAgent（接待员）
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是接待员，负责理解用户问题并转交给合适的专家。
    - 订单问题 → 转交给 SupportAgent
    - 其他问题 → 直接回答
    """,
    handoffs=[
        handoff(support_agent)  # 添加转交选项
    ]
)

# 第 3 步：运行
async def main():
    result = await Runner.run(triage_agent, "我的订单到哪了？")
    print(result.final_output)
```

**运行流程**：

```
用户："我的订单到哪了？"
    ↓
TriageAgent 分析：
  - 关键词："订单"
  - 意图：查询订单状态
  - 判断：这超出了我的职责范围
  - 决策：需要转交给 SupportAgent
    ↓
Handoff 转交 → SupportAgent
    ↓
SupportAgent 处理：
  - 调用 query_order_status 工具
  - 查询订单信息
  - 生成回复
    ↓
输出："您的订单 ORD123 已发货，预计明天到达"
```

---

## 🔄 完整 Handoff 流程详解

### 场景：用户询问退款

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 用户输入                                       │
│  "我要退款"                                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: TriageAgent 理解意图                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 分析：                                            │  │
│  │ - 关键词："退款"                                  │  │
│  │ - 意图：申请退款                                  │  │
│  │ - 判断：这超出了我的职责范围                      │  │
│  │ - 决策：需要转交                                  │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 匹配 Handoff                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 可用的 handoffs：                                 │  │
│  │ - SupportAgent（处理订单/退款）← 匹配！          │  │
│  │ - FAQAgent（处理常见问题）                        │  │
│  │                                                   │  │
│  │ 选择：SupportAgent                                │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: 执行 Handoff 转交                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 转交信息：                                        │  │
│  │ - From: TriageAgent                               │  │
│  │ - To: SupportAgent                                │  │
│  │ - Context: 用户要退款                             │  │
│  │ - Messages: 完整对话历史                          │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: SupportAgent 接手处理                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ SupportAgent 思考：                               │  │
│  │ - 用户要退款                                      │  │
│  │ - 我需要调用 query_refund_policy tool             │  │
│  │ - 查询退款政策                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 调用 Tool：                                       │  │
│  │ query_refund_policy(order_status="已发货")         │  │
│  │ → 返回："支持退款，运费自理"                       │  │
│  └───────────────────────────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 生成回复：                                        │  │
│  │ "您好，根据我们的退款政策，已发货的订单可以        │  │
│  │  申请退款，但需要您承担运费。请问您的订单号        │  │
│  │  是多少？"                                        │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: 输出给用户                                     │
│  "您好，根据我们的退款政策，已发货的订单可以申请        │
│   退款，但需要您承担运费。请问您的订单号是多少？"       │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 多 Handoff 场景

### 3 个 Agent 协作

**场景**：电商客服系统，有多个专业 Agent

```python
from agents import Agent, handoff

# 1. FAQAgent - 处理常见问题
faq_agent = Agent(
    name="FAQAgent",
    instructions="处理常见问题：支付方式、发货时间、配送范围",
    tools=[query_payment_methods, query_shipping_info]
)

# 2. SupportAgent - 处理订单/退款
support_agent = Agent(
    name="SupportAgent",
    instructions="处理订单和退款问题",
    tools=[query_order_status, process_refund]
)

# 3. TechnicalAgent - 处理技术问题
technical_agent = Agent(
    name="TechnicalAgent",
    instructions="处理技术问题：账号登录、APP 故障、网站错误",
    tools=[troubleshoot_login, report_bug]
)

# 4. TriageAgent - 接待员（可以转交给 3 个专家）
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是接待员，根据问题类型转交：
    - 常见问题（支付/发货）→ FAQAgent
    - 订单/退款 → SupportAgent
    - 技术问题 → TechnicalAgent
    """,
    handoffs=[
        handoff(faq_agent),
        handoff(support_agent),
        handoff(technical_agent)
    ]
)
```

### Handoff 决策流程

**用户问题**："网站打不开了"

```
TriageAgent 分析
    ↓
┌──────────────────────────────────────┐
│ 问题分类判断：                       │
│ - 是订单问题吗？→ 否                 │
│ - 是常见问题吗？→ 否                 │
│ - 是技术问题吗？→ 是！✓              │
└──────────────────────────────────────┘
    ↓
Handoff → TechnicalAgent
    ↓
TechnicalAgent 处理
    ↓
输出："请问您看到什么错误提示？"
```

**真实测试用例**：

```python
# 测试 1：订单问题
result1 = await Runner.run(triage_agent, "我的订单 ORD123 到哪了？")
# → 转交 SupportAgent → 查询订单 → 回复

# 测试 2：退款问题
result2 = await Runner.run(triage_agent, "我要退款")
# → 转交 SupportAgent → 查询退款政策 → 回复

# 测试 3：常见问题
result3 = await Runner.run(triage_agent, "支持哪些支付方式？")
# → 转交 FAQAgent → 查询支付方式 → 回复

# 测试 4：技术问题
result4 = await Runner.run(triage_agent, "网站打不开了")
# → 转交 TechnicalAgent → 排查问题 → 回复
```

---

## 📊 Handoff 的 Tracing（追踪）

### 什么是 Tracing？

**Tracing = 追踪记录**，就是把 Agent 的完整决策过程记录下来，方便调试和分析。

### 开启 Tracing

```python
from agents import set_tracing_disabled

# 启用追踪（默认可能是关闭的）
set_tracing_disabled(False)
```

### 查看 Tracing 结果

打开 Tracing 后，你可以看到完整的转交过程：

```
Run Trace:
├── Agent: TriageAgent
│   ├── Input: "我要退款"
│   ├── Intent Detection
│   │   └── Identified: refund_request
│   ├── Handoff Decision
│   │   ├── Available: [SupportAgent, FAQAgent]
│   │   ├── Selected: SupportAgent
│   │   └── Reason: "退款问题需要 SupportAgent 处理"
│   └── Handoff Executed
│       └── Transferred to: SupportAgent
│
├── Agent: SupportAgent
│   ├── Received Context: "用户要退款"
│   ├── Tool Call
│   │   ├── Function: query_refund_policy
│   │   └── Result: "7 天内可退货"
│   └── Response Generation
│       └── Output: "您好，根据我们的退款政策..."
│
└── Final Output
    └── "您好，根据我们的退款政策..."
```

**Tracing 能帮你**：
- 看到 Agent 是如何决策的
- 了解为什么选择了某个 Handoff
- 调试工具调用问题
- 分析性能瓶颈

---

## 💡 Handoff 最佳实践

### ✅ 推荐做法

#### 1. 清晰的职责边界

```python
# ✅ 好：职责明确
support_agent = Agent(
    instructions="处理订单和退款问题"
)

faq_agent = Agent(
    instructions="处理常见问题：支付、发货、配送"
)
```

**为什么好？**  
- AI 能清楚知道什么时候该转交
- 避免多个 Agent 都能处理同一个问题

#### 2. Triage 只负责分类

```python
# ✅ 好：Triage 不处理具体问题
triage_agent = Agent(
    instructions="你是接待员，负责转交，不直接回答问题"
)
```

**为什么好？**  
- 职责单一，不容易混乱
- 提高转交准确率

#### 3. 提供转交原因

```python
# ✅ 好：说明为什么转交
handoff(support_agent, on="订单或退款问题")
```

**为什么好？**  
- 帮助 TriageAgent 更准确地判断
- 便于调试和理解

---

### ❌ 避免的做法

#### 1. 职责重叠

```python
# ❌ 不好：两个 Agent 都能处理订单
agent1 = Agent(instructions="处理订单问题")
agent2 = Agent(instructions="处理订单查询")  # 重复！
```

**问题**：
- TriageAgent 不知道应该转交给谁
- 可能导致随机选择，体验差

**解决方法**：

```python
# ✅ 明确分工
agent1 = Agent(instructions="处理订单查询和状态")
agent2 = Agent(instructions="处理订单修改和取消")
```

#### 2. Triage 也处理问题

```python
# ❌ 不好：Triage 既分类又处理
triage_agent = Agent(
    instructions="分类问题，也回答简单问题"  # 混乱！
)
```

**问题**：
- 职责不清晰
- 可能该转交却没转交

**解决方法**：

```python
# ✅ 分离职责
triage_agent = Agent(
    instructions="只负责分类和转交，不处理具体问题"
)
```

#### 3. 过多 Handoff 层级

```python
# ❌ 不好：转交太多次
Triage → Agent1 → Agent2 → Agent3  # 复杂！
```

**问题**：
- 延迟增加（每次转交都要调用 AI）
- 容易丢失上下文
- 难以调试

**解决方法**：

```python
# ✅ 扁平化设计
Triage → SupportAgent
Triage → FAQAgent
Triage → TechnicalAgent
# 最多 2 层：Triage → Expert
```

---

## 🎓 Handoff 代码示例（完整版）

**文件位置**：参考 `src/week4/src/simple_handoff.py`

```python
from agents import Agent, Runner, handoff, function_tool

# ============ 定义 Tools ============

@function_tool
def query_order_status(order_id: str) -> str:
    """查询订单状态"""
    return f"订单 {order_id} 已发货"

@function_tool
def process_refund(order_id: str) -> str:
    """处理退款"""
    return f"订单 {order_id} 退款已受理"

# ============ 创建 Agents ============

# 1. 创建 SupportAgent
support_agent = Agent(
    name="SupportAgent",
    instructions="""你是客服专家，处理订单和退款问题。
    - 查询订单状态用 query_order_status
    - 处理退款用 process_refund
    """,
    tools=[query_order_status, process_refund]
)

# 2. 创建 FAQAgent
faq_agent = Agent(
    name="FAQAgent",
    instructions="处理常见问题：支付方式、发货时间、配送范围",
    tools=[]  # 没有工具，直接回答
)

# 3. 创建 TriageAgent
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是接待员，根据问题类型转交：
    - 订单/退款 → SupportAgent
    - 常见问题（支付/发货）→ FAQAgent
    - 其他 → 直接回答
    """,
    handoffs=[
        handoff(support_agent),
        handoff(faq_agent)
    ]
)

# ============ 测试 ============

async def main():
    # 测试 1：订单问题
    result1 = await Runner.run(
        triage_agent,
        "我的订单 ORD123 到哪了？"
    )
    print("测试 1:", result1.final_output)
    # 预期：转交 SupportAgent → 查询订单 → 回复
    
    # 测试 2：退款问题
    result2 = await Runner.run(
        triage_agent,
        "我要退款"
    )
    print("测试 2:", result2.final_output)
    # 预期：转交 SupportAgent → 处理退款 → 回复
    
    # 测试 3：常见问题
    result3 = await Runner.run(
        triage_agent,
        "支持哪些支付方式？"
    )
    print("测试 3:", result3.final_output)
    # 预期：转交 FAQAgent → 回答支付方式

import asyncio
asyncio.run(main())
```

---

## 📝 关键认知总结

### 常见问题 Q&A

| 问题 | 答案 |
|------|------|
| **什么时候需要 Handoff？** | 问题超出当前 Agent 职责范围 |
| **如何设计清晰的 Handoff？** | 每个 Agent 职责明确，不重叠 |
| **Triage 的职责是什么？** | 只分类和转交，不处理具体问题 |
| **最多可以有多少个 Handoff？** | 理论上不限，建议 ≤ 5 个 |
| **Handoff 会影响性能吗？** | 会稍微增加延迟，但更专业 |
| **转交时会丢失上下文吗？** | 不会，完整对话历史会传递 |
| **用户能感知到转交吗？** | 不能，感觉像在和同一个 Agent 对话 |

---

## 🔍 Handoff 调试技巧

### 1. 打印决策过程

```python
async def debug_handoff():
    result = await Runner.run(triage_agent, "我要退款")
    
    # 查看最终回复
    print(f"最终输出：{result.final_output}")
    
    # 查看最终是哪个 Agent 处理的（重要！）
    print(f"最终处理 Agent：{result.last_agent.name}")
    # 可能的输出：
    # - "TriageAgent" → 没有发生转交，TriageAgent 自己回答了
    # - "SupportAgent" → 转交给了 SupportAgent
    # - "FAQAgent" → 转交给了 FAQAgent
```

### 2. 检查 Handoff 配置

```python
# 打印 TriageAgent 的 handoffs
print("可用的 Handoff：")
for handoff in triage_agent.handoffs:
    print(f"  - {handoff.agent.name}")
```

### 3. 测试边界情况

```python
test_cases = [
    "我要退款",              # 明确 → 应该转交
    "订单到哪了",            # 明确 → 应该转交
    "你好",                  # 模糊 → 不应该转交
    "我想问一下",            # 不完整 → 不应该转交
    "退款和订单是什么？",    # 混合 → 看 Triage 判断
]

for query in test_cases:
    result = await Runner.run(triage_agent, query)
    print(f"问题：{query}")
    print(f"回答：{result.final_output}")
    print(f"处理 Agent：{result.last_agent.name}")  # 查看谁处理的
    print()
```

---

## 🔁 单 Agent vs 多 Agent：两种方式解决同一个问题

### 问题：我该用哪种方式？

项目中有一个对比学习的例子：
- `ecommerce_support_agent.py` = 单 Agent + 7 个工具（集中式）
- `handoff_example.py` = 多 Agent + Handoff（分布式）

### 对比图解

```
方式 A：单 Agent + 多 Tool（集中式）
┌───────────────────────────────────┐
│  一个"全能"客服 Agent              │
│  带 7 个工具                      │
│  Instructions 很长（什么都要会） │
│  AI 要从 7 个工具中选择          │
└───────────────────────────────────┘

方式 B：多 Agent + Handoff（分布式）
┌──────────────┐
│  TriageAgent │ ← 只负责分类，不处理问题
└──────┬───────┘
       │
       ├──→ SupportAgent（订单/退款专家，3 个工具）
       ├──→ FAQAgent（常见问题，1 个工具）
       └──→ EscalationAgent（人工转接，1 个工具）
```

### 详细对比

| 对比维度 | 单 Agent（方式 A） | 多 Agent（方式 B） |
|---------|-------------------|-------------------|
| Instructions 长度 | 很长（什么都要写） | 每个都很短（只写自己的） |
| 工具数量 | 7 个（AI 可能选错） | 1-3 个（选择更少更准） |
| 职责清晰度 | 低（全挤在一起） | 高（各管各的） |
| 维护难度 | 高（改一处影响全部） | 低（改一个不影响其他） |
| 延迟 | 低（只有一次 LLM 调用） | 较高（需要两次调用：分类 + 处理） |
| 适用场景 | 简单场景、快速原型 | 生产环境、复杂业务 |

### 什么时候用哪种？

**用单 Agent 当：**
- 工具数量 ≤ 3 个
- 业务逻辑简单
- 快速原型验证
- 对延迟要求高

**用多 Agent 当：**
- 工具数量 > 5 个
- 业务逻辑复杂，需要多个专家
- 需要清晰的职责划分
- 团队协作开发（每人负责一个 Agent）

### 验证 Handoff 是否成功

```python
# 用 result.last_agent.name 检查最终处理 Agent
result = await Runner.run(triage_agent, "我的订单 ORD1001 到哪了？")
print(result.last_agent.name)  # 输出：SupportAgent

# 如果输出是 TriageAgent，说明没有发生 Handoff
# 如果输出是 SupportAgent/FAQAgent/EscalationAgent，说明 Handoff 成功
```

---

## 🎯 实际应用场景

### 场景 1：电商客服

```
TriageAgent
    ├─ 订单问题 → OrderAgent
    ├─ 退款问题 → RefundAgent
    ├─ 物流问题 → LogisticsAgent
    └─ 产品咨询 → ProductAgent
```

### 场景 2：技术支持

```
TriageAgent
    ├─ 登录问题 → LoginAgent
    ├─ 支付问题 → PaymentAgent
    ├─ Bug 报告 → BugAgent
    └─ 功能咨询 → FeatureAgent
```

### 场景 3：旅游规划

```
TriageAgent
    ├─ 酒店预订 → HotelAgent
    ├─ 机票查询 → FlightAgent
    ├─ 旅游攻略 → GuideAgent
    └─ 签证咨询 → VisaAgent
```

---

## 🔗 相关资源

- [完整入门指南](./README.md) - 从零开始的完整教程
- [RunLoop 运行机制](./RunLoop.md) - Agent 如何工作
- [实际代码示例](../src/week4/) - 可运行的完整项目
- [官方文档 - Handoffs](https://openai.github.io/openai-agents-python/handoffs/)

---

> 💡 **记住**：Handoff 就是"识别问题 → 找对的人 → 转交上下文 → 专家处理"的过程。设计时记住"职责明确、层级扁平、上下文完整"三个原则！
