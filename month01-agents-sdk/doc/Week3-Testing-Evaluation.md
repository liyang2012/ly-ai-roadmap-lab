# 📊 Week 3 详解 - 测试、评估与优化

> **小白必看**：本文档教你如何测试和优化 AI Agent，让它更稳定、更省钱、更准确

---

## 🎯 本周目标

学完 Week 3，你将掌握：

1. ✅ **一致性测试** - 确保 Agent 对同样问题给出稳定回答
2. ✅ **Token 分析** - 了解 Agent 消耗了多少 Token，如何省钱
3. ✅ **错误收集** - 建立错误样本集，知道哪里需要改进
4. ✅ **优化方法** - 优化 instructions 和 tools，降低误调率

---

## 📚 核心概念

### 什么是 Agent 测试？

**测试 Agent 就像测试软件一样**，确保它：
- 回答稳定（不是每次都不一样）
- 调用正确的工具（不要查订单却调用了查天气）
- 性价比高（不要一个问题花几块钱）

### 为什么需要测试？

| 不测试的后果 | 测试的好处 |
|------------|----------|
| ❌ 用户每次问同样问题，答案不同 | ✅ 回答稳定，用户信任 |
| ❌ Agent 调错工具，浪费时间 | ✅ 工具选择准确，效率高 |
| ❌ Token 消耗大，成本高 | ✅ 成本可控，效益高 |
| ❌ 不知道哪里不好，无法改进 | ✅ 知道问题所在，针对性优化 |

---

## 📋 核心任务详解

### Day 15-16：一致性测试

**文件**：`day15_16_consistency_test.py`

#### 什么是一致性测试？

**一致性测试 = 用同样的问题多次运行，看回答是否一致**

比如问"我的订单到哪了？"，运行 5 次：
- 第 1 次："您的订单已发货"
- 第 2 次："您的订单已发货"
- 第 3 次："您的订单处理中" ← **不一致！**
- 第 4 次："您的订单已发货"
- 第 5 次："您的订单已发货"

**一致率 = 4/5 = 80%**

#### 测试流程

```
1. 准备 10 个测试问题
2. 每个问题运行 5 次
3. 比较 5 次回答是否一致
4. 计算一致率（>80% 算优秀）
5. 分析不一致的原因
```

#### 代码示例

```python
from agents import Agent, Runner

# 1. 准备测试问题
test_questions = [
    "帮我查一下订单 ORD20260417001 的状态",
    "ORD20260417002 发货了吗？",
    "已发货的订单能退款吗？",
    # ... 更多问题
]

# 2. 每个问题运行 5 次
for question in test_questions:
    results = []
    for i in range(5):  # 运行 5 次
        result = await Runner.run(agent, question)
        results.append(result.final_output)
    
    # 3. 检查一致性
    # 如果 5 次回答完全相同，一致率 = 100%
    # 如果有不同，一致率 < 100%
    unique_answers = len(set(results))  # 去重后的答案数量
    if unique_answers == 1:
        print(f"✅ 一致：{results[0]}")
    else:
        print(f"❌ 不一致：有 {unique_answers} 种不同回答")
```

#### 运行方式

```bash
cd src/week3
./run_test.sh
```

#### 测试结果示例

```
📊 一致性测试报告
━━━━━━━━━━━━━━━━
总问题：10
一致：7 个 (70%)
不一致：3 个 (30%)

不一致问题：
1. "订单 ORD20260417001 的状态"
   - 第 1 次：订单已发货，物流顺丰
   - 第 2 次：订单状态：已发货
   - 第 3 次：您的订单 ORD20260417001 已发货

2. "怎么退款？"
   - 第 1 次：调用 query_refund_policy
   - 第 2 次：直接回答（不调用工具）
   ...
```

#### 为什么会不一致？

**原因 1：AI 的表达方式不同**
- 同一个意思，可以用不同的句子表达
- 这其实是"假不一致"，Agent 行为是正确的

**原因 2：工具选择不同**
- 有时调用工具，有时直接回答
- 这才是真正的问题

**原因 3：参数提取错误**
- 应该提取 `order_id="ORD001"`
- 却提取了 `order_id="订单 ORD001"`

---

### Day 17-18：Token 使用分析

**文件**：`day17_18_token_usage.py`

#### 什么是 Token？

**Token = AI 的文字计量单位**

- 1 个 Token ≈ 0.5 个中文字符
- "你好世界" ≈ 4-6 个 Token
- "Hello World" ≈ 2-3 个 Token

#### 为什么要分析 Token？

**Token 直接影响成本！**

| 指标 | 影响 |
|------|------|
| Prompt Tokens（输入） | 你的问题 + 历史记录 + instructions |
| Completion Tokens（输出） | AI 的回答 |
| Total Tokens（总计） | 总消耗，影响费用 |

**示例**：
- 输入：1000 tokens × 0.0001 元/token = 0.1 元
- 输出：200 tokens × 0.0002 元/token = 0.04 元
- **一次对话 = 0.14 元**

如果有 10000 个用户，每人问 10 个问题：
- 10000 × 10 × 0.14 = **14000 元**

#### 测试流程

```python
from agents import Agent, Runner

async def analyze_token_usage():
    """分析 Token 使用情况"""
    questions = [
        "我的订单到哪了？",
        "怎么退款？",
        "iPhone 保修多久？",
    ]
    
    total_prompt = 0
    total_completion = 0
    
    for question in questions:
        result = await Runner.run(agent, question)
        
        # 获取 Token 使用数据
        for response in result.raw_responses:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            
            total_prompt += prompt_tokens
            total_completion += completion_tokens
            
            print(f"问题：{question}")
            print(f"  Prompt: {prompt_tokens} tokens")
            print(f"  Completion: {completion_tokens} tokens")
            print(f"  Total: {prompt_tokens + completion_tokens} tokens")
            print()
    
    # 汇总
    print("=" * 50)
    print(f"总计：{total_prompt + total_completion} tokens")
    print(f"  Prompt: {total_prompt}")
    print(f"  Completion: {total_completion}")
```

#### 测试结果示例

```
📊 Token 使用分析报告
━━━━━━━━━━━━━━━━━━━━
问题                    Prompt   Completion   Total
────────────────────────────────────────────────────
订单 ORD20260417001     2,450      180       2,630
物流 SF1234567890       2,800      368       3,168  ← 最费 Token
怎么退款？              2,350      184       2,534
iPhone 保修多久？       2,380      145       2,525
你好                    2,320       24       2,344  ← 最省 Token
────────────────────────────────────────────────────
总计                   25,495    3,114      28,609
平均每题                2,550      311       2,861
```

#### 如何降低 Token 消耗？

**方法 1：精简 Instructions**

```python
# ❌ 冗长的 Instructions（浪费 Token）
instructions="""
你是一个非常专业的电商客服助手，你的工作就是帮助用户解决他们的问题。
当用户问你关于订单的问题时，你应该调用 query_order_status 工具。
当用户问你关于退款的问题时，你应该调用 query_refund_policy 工具。
...
"""  # 500+ tokens

# ✅ 简洁的 Instructions（节省 Token）
instructions="""
电商客服助手。
- 订单问题 → query_order_status
- 退款问题 → query_refund_policy
...
"""  # 100 tokens，节省 80%
```

**方法 2：减少历史记录**

```python
# ❌ 保留所有历史（越来越贵）
messages = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好，请问有什么可以帮您？"},
    {"role": "user", "content": "我的订单..."},
    {"role": "assistant", "content": "您的订单..."},
    # ... 100 条历史记录
]

# ✅ 只保留最近的历史（控制成本）
messages = [
    # 只保留最近 5 条
    {"role": "user", "content": "最近的问题 1"},
    {"role": "assistant", "content": "最近的回答 1"},
    # ...
]
```

**方法 3：优化工具返回格式**

```python
# ❌ 工具返回冗长格式
def query_order(order_id):
    return f"""
📦 订单详情
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
订单号：{order_id}
商品：iPhone 15 Pro Max 256GB 深空黑色
金额：¥7,999.00
状态：已发货
物流：顺丰 SF1234567890
预计送达：2026年4月19日
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""  # 150 tokens

# ✅ 工具返回简洁格式
def query_order(order_id):
    return f"订单 {order_id}：iPhone，¥7999，已发货，顺丰 SF123，预计 4/19"  # 30 tokens
```

---

### Day 19-20：错误样本集

**文件**：`day19_20_error_cases.py`、`docs/error_cases.md`

#### 什么是错误样本集？

**错误样本集 = 收集 Agent 犯的错误，分类整理**

就像错题本一样，知道哪里错了，才能改进。

#### 错误分类

| 类型 | 说明 | 示例 |
|------|------|------|
| **Prompt 问题** | Agent 不理解该不该调用工具 | 问"怎么退款"，Agent 不调用工具，直接回答 |
| **Schema 问题** | Agent 调用了工具但参数错了 | 应该传 `order_id="ORD001"`，却传了 `order_id="订单001"` |
| **工具选择错误** | Agent 调用了错误的工具 | 问"订单状态"，却调用了"退款政策"工具 |
| **回答错误** | 回答内容不正确 | 明明订单已发货，却说"未发货" |

#### 收集流程

```
1. 准备 20 条测试用例（eval/mini_eval.csv）
2. 每条用例运行 3 次
3. 记录所有错误
4. 分类错误类型
5. 分析根本原因
6. 制定优化方案
```

#### 错误示例

**错误 1：Prompt 问题**

```
用户问："怎么退款？"
期望行为：调用 query_refund_policy(order_status="通用")
实际行为：Agent 直接回答，没有调用工具

原因分析：
- Instructions 没有说明"退款政策咨询"需要调用工具
- Tool 描述不够清晰

优化方案：
- 在 Instructions 中添加：
  "遇到退款相关问题（包括怎么退款、退款条件等），使用 query_refund_policy"
- 优化 Tool 描述：
  """查询退款政策。适用于：
  - 查询某个订单状态的退款规则
  - 一般性退款咨询（不针对具体订单）
  """
```

**错误 2：Schema 问题**

```
用户问："订单 ORD001 的状态"
期望行为：调用 query_order_status(order_id="ORD001")
实际行为：调用 query_order_status(order_id="订单 ORD001")  ← 多了"订单"两字

原因分析：
- Agent 从用户输入中提取参数时，没有正确解析
- 用户说"订单 ORD001"，Agent 把"订单"也当成 order_id 的一部分

优化方案：
- 在 Tool 的参数描述中明确：
  "order_id: 订单号，如 ORD001（不包含'订单'两字）"
- 在 Instructions 中添加：
  "提取订单号时，只提取字母+数字，不要包含'订单'等关键词"
```

---

### Day 21-22：优化 Instructions 和 Schema

**文件**：`day21_22_optimization.py`

#### 优化策略

**策略 1：改进 Tool 描述**

```python
# 优化前
@function_tool
def query_refund_policy(order_status: str) -> str:
    """查询退款政策"""
    ...

# 优化后
@function_tool
def query_refund_policy(order_status: str) -> str:
    """查询商城的退款/退货政策。适用于以下场景：
    - 用户询问退款条件、退款流程、退款规则
    - 用户提供订单状态查询对应政策（如"未发货"、"已发货"、"已签收"）
    - 一般性退款咨询（不针对具体订单）时，传入"通用"或"一般"作为参数
    
    Args:
        order_status: 订单状态（未发货/已发货/已签收/超过7天）或"通用"
    
    Returns:
        退款政策说明
    """
    ...
```

**策略 2：改进 Instructions**

```python
# 优化前
instructions = "你是客服助手，帮用户查询订单和退款"

# 优化后
instructions = """你是电商客服助手。

【工具使用规则】
1. 订单查询（含订单号）→ query_order_status
2. 退款政策咨询（任何退款相关问题）→ query_refund_policy
3. 物流查询（含物流单号）→ query_logistics

【参数提取规则】
- 订单号：只提取字母+数字，如 "ORD001"
- 物流单号：只提取字母+数字，如 "SF123"
- 不要包含"订单"、"物流"等关键词

【示例】
用户："订单 ORD001 到哪了？"
  ✓ 正确：query_order_status(order_id="ORD001")
  ✗ 错误：query_order_status(order_id="订单 ORD001")
"""
```

#### A/B 测试（对比优化效果）

```python
# 优化前
agent_v1 = Agent(
    instructions=old_instructions,
    tools=old_tools
)

# 优化后
agent_v2 = Agent(
    instructions=new_instructions,
    tools=new_tools
)

# 用同样的 20 条测试用例对比
test_cases = load_eval_cases()  # 20 条

results_v1 = []
results_v2 = []

for case in test_cases:
    # 测试 V1
    result_v1 = await Runner.run(agent_v1, case.query)
    results_v1.append(check_correct(result_v1, case.expected))
    
    # 测试 V2
    result_v2 = await Runner.run(agent_v2, case.query)
    results_v2.append(check_correct(result_v2, case.expected))

# 对比结果
print(f"V1 通过率：{sum(results_v1)/len(results_v1):.1%}")
print(f"V2 通过率：{sum(results_v2)/len(results_v2):.1%}")
print(f"提升：{(sum(results_v2)-sum(results_v1))/len(results_v1):.1%}")
```

#### 测试结果示例

```
📊 优化效果对比
━━━━━━━━━━━━━━
指标          V1 (优化前)   V2 (优化后)   提升
─────────────────────────────────────────────
通过率          65%          85%        +20%
误调率          25%          10%        -15%
平均 Token      2,860        2,650      -210
─────────────────────────────────────────────
```

---

### Day 23：创建 Mini Eval（评测集）

**文件**：`eval/mini_eval.csv`

#### 什么是 Mini Eval？

**Mini Eval = 小型评测集**，用于快速测试 Agent 的质量。

就像一个"考卷"，每次优化后都考一遍，看分数有没有提高。

#### Eval 格式

```csv
id,query,expected_tool,expected_params,note
1,"帮我查一下订单 ORD001",query_order_status,"{""order_id"":""ORD001""}",基础订单查询
2,"ORD002 发货了吗",query_order_status,"{""order_id"":""ORD002""}",简短问法
3,"怎么退款？",query_refund_policy,"{""order_status"":""通用""}",一般性政策咨询
4,"已发货的订单能退吗",query_refund_policy,"{""order_status"":""已发货""}",特定状态咨询
...
```

#### 使用方法

```python
import csv

# 1. 加载评测集
with open("eval/mini_eval.csv") as f:
    reader = csv.DictReader(f)
    test_cases = list(reader)

# 2. 运行评测
correct = 0
for case in test_cases:
    result = await Runner.run(agent, case["query"])
    
    # 检查是否调用了正确的工具
    # 检查参数是否正确
    if is_correct(result, case):
        correct += 1

# 3. 计算通过率
pass_rate = correct / len(test_cases)
print(f"通过率：{pass_rate:.1%}")
```

---

## 💡 核心认知总结

### 1. 测试是优化的基础

```
没有测试 = 盲目优化
有了测试 = 知道哪里不好，针对性改进
```

### 2. 错误分类很重要

| 错误类型 | 优化方法 |
|---------|---------|
| Prompt 问题 | 改 Instructions，说明什么时候调用工具 |
| Schema 问题 | 改 Tool 描述，明确参数格式 |
| 工具选择错误 | 优化 Instructions 的"工具使用规则" |
| 回答错误 | 检查工具返回值，确保数据准确 |

### 3. Token 消耗要关注

- 每天统计 Token 消耗
- 找到最费 Token 的场景
- 优化 Instructions 和 Tool 返回格式

### 4. 迭代优化流程

```
1. 测试 → 2. 发现错误 → 3. 分析原因 → 4. 优化 → 5. 再测试
   ↑                                              ↓
   └──────────────────────────────────────────────┘
            持续改进，直到达到目标
```

---

## 🎓 实践建议

### 1. 从小规模开始

- 先准备 10 条测试用例
- 跑 3 次看一致性
- 不要一开始就搞 100 条

### 2. 关注关键指标

- 一致率 > 80%（稳定性）
- 通过率 > 85%（准确性）
- Token 成本可控（经济性）

### 3. 记录优化过程

```
日期：2026-04-23
优化内容：改进 query_refund_policy 的描述
优化前通过率：65%
优化后通过率：75%
提升：+10%
```

### 4. 不要过度优化

- 达到 85% 通过率就很好了
- 不要追求 100%（不现实）
- 有些"不一致"其实是可接受的（表达方式不同但意思相同）

---

## 🔗 相关资源

- [完整入门指南](../doc/README.md) - Week 3 在整体中的位置
- [Day 15-16 代码](./day15_16_consistency_test.py) - 一致性测试
- [Day 17-18 代码](./day17_18_token_usage.py) - Token 分析
- [Day 19-20 代码](./day19_20_error_cases.py) - 错误收集
- [Day 21-22 代码](./day21_22_optimization.py) - 优化对比
- [评测集示例](./eval/mini_eval.csv) - Mini Eval 模板

---

> 💡 **记住**：测试、评估、优化是一个循环过程。每次优化后都要测试，用数据说话，不要凭感觉！
