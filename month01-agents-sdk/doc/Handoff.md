🔄 什么是 Handoff？
Handoff = 职责转交，即一个 Agent 把对话转交给另一个更专业的 Agent 处理。

类比：
公司前台（Triage）→ 转接给技术客服（Support）
医院分诊台 → 转诊给专科医生
电话客服 → "我帮您转接相关部门"
📚 Handoff 的核心概念
1. 角色分工
角色
职责
特点
TriageAgent
接待员/分类员
只负责理解和转交，不处理具体问题
SupportAgent
专家/处理员
处理特定领域的问题（如订单、退款）
FAQAgent
客服
处理常见问题（支付、发货等）
2. Handoff 的时机
需要转交：
✅ 问题超出当前 Agent 的职责范围
✅ 需要更专业的知识
✅ 需要调用其他 Agent 的专属 tools
不需要转交：
❌ 当前 Agent 能直接回答
❌ 简单问候/闲聊
❌ 问题不明确，需要先澄清
💻 Handoff 代码实现
基础示例
from agents import Agent, Runner, handoff

# 1. 创建 SupportAgent（处理订单问题）
support_agent = Agent(
    name="SupportAgent",
    instructions="""你是客服专家，处理订单相关问题。
    - 查询订单状态
    - 处理订单修改
    - 解答订单疑问
    """,
    tools=[query_order_status, modify_order]
)

# 2. 创建 TriageAgent（接待员）
triage_agent = Agent(
    name="TriageAgent",
    instructions="""你是接待员，负责理解用户问题并转交给合适的专家。
    - 订单问题 → 转交给 SupportAgent
    - 其他问题 → 直接回答
    """,
    handoffs=[
        handoff(support_agent)
    ]
)

# 3. 运行
async def main():
    result = await Runner.run(triage_agent, "我的订单到哪了？")
    print(result.final_output)
🔄 完整 Handoff 流程详解
场景：用户询问退款
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
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: SupportAgent 接手处理                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ SupportAgent 思考：                               │  │
│  │ - 用户要退款                                      │  │
│  │ - 我需要调用 refund_policy tool                   │  │
│  │ - 查询退款政策                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 调用 Tool：                                       │  │
│  │ query_refund_policy(product_type="电子产品")       │  │
│  │ → 返回："7 天内可无理由退货"                       │  │
│  └───────────────────────────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 生成回复：                                        │  │
│  │ "您好，根据我们的退款政策，电子产品在 7 天内可      │  │
│  │  以无理由退货。请问您的订单号是多少？"            │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: 输出给用户                                     │
│  "您好，根据我们的退款政策，电子产品在 7 天内可以        │
│   无理由退货。请问您的订单号是多少？"                   │
└─────────────────────────────────────────────────────────┘
🎯 多 Handoff 场景
3 个 Agent 协作
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
Handoff 决策流程
用户问题："网站打不开了"
    ↓
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
📊 Handoff 的 Tracing
打开 Tracing 后，你可以看到完整的转交过程：
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
💡 Handoff 最佳实践
✅ 推荐做法
清晰的职责边界
# ✅ 好：职责明确
support_agent = Agent(
    instructions="处理订单和退款问题"
)

faq_agent = Agent(
    instructions="处理常见问题：支付、发货、配送"
)
Triage 只负责分类
# ✅ 好：Triage 不处理具体问题
triage_agent = Agent(
    instructions="你是接待员，负责转交，不直接回答问题"
)
提供转交原因
# ✅ 好：说明为什么转交
handoff(support_agent, on="订单或退款问题")
❌ 避免的做法
职责重叠
# ❌ 不好：两个 Agent 都能处理订单
agent1 = Agent(instructions="处理订单问题")
agent2 = Agent(instructions="处理订单查询")  # 重复！
Triage 也处理问题
# ❌ 不好：Triage 既分类又处理
triage_agent = Agent(
    instructions="分类问题，也回答简单问题"  # 混乱！
)
过多 Handoff 层级
# ❌ 不好：转交太多次
Triage → Agent1 → Agent2 → Agent3  # 复杂！
🎓 Handoff 代码示例（完整版）
from agents import Agent, Runner, handoff, function_tool

# 定义 Tools
@function_tool
def query_order_status(order_id: str) -> str:
    """查询订单状态"""
    return f"订单 {order_id} 已发货"

@function_tool
def process_refund(order_id: str) -> str:
    """处理退款"""
    return f"订单 {order_id} 退款已受理"

# 创建 SupportAgent
support_agent = Agent(
    name="SupportAgent",
    instructions="""你是客服专家，处理订单和退款问题。
    - 查询订单状态用 query_order_status
    - 处理退款用 process_refund
    """,
    tools=[query_order_status, process_refund]
)

# 创建 FAQAgent
faq_agent = Agent(
    name="FAQAgent",
    instructions="处理常见问题：支付方式、发货时间、配送范围",
    tools=[]  # 没有工具，直接回答
)

# 创建 TriageAgent
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

# 测试
async def main():
    # 测试 1：订单问题
    result1 = await Runner.run(
        triage_agent,
        "我的订单 ORD123 到哪了？"
    )
    print("测试 1:", result1.final_output)
    
    # 测试 2：退款问题
    result2 = await Runner.run(
        triage_agent,
        "我要退款"
    )
    print("测试 2:", result2.final_output)
    
    # 测试 3：常见问题
    result3 = await Runner.run(
        triage_agent,
        "支持哪些支付方式？"
    )
    print("测试 3:", result3.final_output)

import asyncio
asyncio.run(main())
📝 关键认知总结
问题
答案
什么时候需要 Handoff？
问题超出当前 Agent 职责范围
如何设计清晰的 Handoff？
每个 Agent 职责明确，不重叠
Triage 的职责是什么？
只分类和转交，不处理具体问题
最多可以有多少个 Handoff？
理论上不限，建议 ≤ 5 个
Handoff 会影响性能吗？
会稍微增加延迟，但更专业
🔗 相关资源
Handoffs 官方文档
[Week 4：Handoffs 与整合](./第 1 月 - Week 4：Handoffs 与整合)
[第 4 月：Multi-Agent 协作](./第 4 月 - Week 1：角色拆分原则)