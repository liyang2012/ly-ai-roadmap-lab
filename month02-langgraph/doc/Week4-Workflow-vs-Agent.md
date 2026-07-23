# 📙 Week 4 详解 - Workflow vs Agent 选型对比

> **适合人群**：已学完 Week 1-3 的 LangGraph 使用者
> **前置知识**：了解 StateGraph、条件路由、Checkpoint
> **预计时间**：1.5-2 小时

---

## 🎯 学习目标

学完 Week 4，你将掌握：

1. ✅ **Workflow 和 Agent 的区别** — 两种 AI 系统的根本差异
2. ✅ **量化对比** — 用实验数据说话，不是凭感觉
3. ✅ **选型判断力** — 什么场景用什么方案
4. ✅ **混合架构** — 工业界的最佳实践

---

## 📚 一、为什么需要这个对比？

在前面三周，我们用 LangGraph 写了各种 Graph。但始终有一个问题没回答：

> **"LangGraph 这种'你手动设计流程'的方式，和直接让 LLM 自己决定做什么（Agent 模式），到底哪个好？"**

Week 4 就是用**数据**来回答这个问题。

### 实验方法

用**同一个需求**（电商客服），分别写两个版本，然后用 10 个测试用例跑数据：

| 版本 | 文件名 | 核心思路 | 类比 |
|------|--------|---------|------|
| **Workflow 版** | `workflow_version.py` | 你写好规则，程序按流程走 | 自动售货机：按哪个按钮出哪个货 |
| **Agent 版** | `agent_version.py` | LLM 理解你的话，自己决定做什么 | 真人客服：听你说话，自己判断怎么处理 |

---

## 📖 二、先搞懂两个核心概念

### 2.1 Workflow（工作流）= 确定性流程

```
用户说话 → 关键词匹配 → 确定走哪条路 → 执行对应逻辑 → 返回结果
```

**生活类比**：你去银行办业务
1. 取号机问你办什么业务（存款/取款/开户/挂失）
2. 你按了一个按钮（比如"存款"）
3. 系统分配你到存款窗口
4. 柜员按固定流程帮你存款

每一步都是**预设好的**，不会因为你说话方式不同而走不同窗口。

**代码中的体现**：
```python
# 关键词匹配 → 确定意图
if "退款" in user_input or "退货" in user_input:
    intent = "refund"        # 100% 确定走退款流程
elif "物流" in user_input or "快递" in user_input:
    intent = "logistics"     # 100% 确定走物流查询
```

### 2.2 Agent（智能体）= LLM 驱动决策

```
用户说话 → LLM 理解语义 → LLM 选择工具 → 执行工具 → LLM 生成回复
```

**生活类比**：你去找一个万能助手
1. 你用自然语言描述需求："我的手机到了但想退掉"
2. 助手**理解**你的意思（虽然你没说"退款"两个字）
3. 助手自己判断应该调用"退款查询"功能
4. 助手把结果用自然语言回复给你

**代码中的体现**：
```python
# LLM 理解语义 → 即使没说"退款"也能识别
# "这个手机能退吗" → LLM 理解 = 退款意图
intent = llm_classify("这个手机能退吗")  # → "refund"
```

### 2.3 一张图看懂区别

```
              Workflow 版                          Agent 版
          ┌──────────────┐                  ┌──────────────┐
          │  关键词规则    │                  │   LLM 大脑    │
          │  "退款"→退款  │                  │  理解语义     │
          │  "物流"→物流  │                  │  自主选择     │
          └──────┬───────┘                  └──────┬───────┘
                 │                                  │
     ┌───────────┼───────────┐          ┌──────────┼──────────┐
     ↓           ↓           ↓          ↓          ↓          ↓
 [订单节点]  [退款节点]  [物流节点]    [Tool A]   [Tool B]   [Tool C]
     ↓           ↓           ↓          ↓          ↓          ↓
          ┌──────────────┐                  ┌──────────────┐
          │   直接返回    │                  │  LLM 润色回复  │
          └──────────────┘                  └──────────────┘

特点：                              特点：
✅ 快（毫秒级）                     ❌ 慢（1-5秒）
✅ 免费（0 Token）                  ❌ 花钱（每次消耗 Token）
✅ 确定（同样输入=同样结果）          ❌ 不确定（LLM 有随机性）
❌ 死板（关键词匹配不到就废了）       ✅ 灵活（能理解模糊表述）
```

---

## 💻 三、Workflow 版详解

**文件**：`src/week4/workflow_version.py`

### 3.1 整体架构

```
__start__
    ↓
intent_router（关键词匹配 + 提取订单号）
    ↓
[条件边]
    ├─ order_query / refund / logistics / coupon / product / escalate / greeting
    ↓
finalize（拼接流程记录，输出最终结果）
    ↓
__end__
```

### 3.2 意图识别：纯规则

这是 Workflow 版的**核心**——不用 LLM，全靠关键词：

```python
def classify_intent_rules(user_input: str) -> str:
    q = user_input.lower()

    # 按优先级从高到低排列
    if any(k in q for k in ["投诉", "举报", "转人工"]):
        return "escalate"          # 投诉最优先
    if any(k in q for k in ["物流", "快递", "到哪了"]):
        return "logistics"
    if any(k in q for k in ["退款", "退货", "退钱"]):
        return "refund"
    if any(k in q for k in ["优惠", "券", "折扣"]):
        return "coupon"
    if any(k in q for k in ["保修", "什么价格", "多少钱"]):
        return "product"
    if any(k in q for k in ["订单", "状态", "发货了吗"]):
        return "order_query"
    return "greeting"              # 兜底
```

**小白须知**：
- `any(k in q for k in [...])` = 检查用户输入里有没有这些关键词
- 排在前面的先匹配，匹配到就返回，后面的不再检查
- 所以"投诉"优先级最高，"greeting"优先级最低

### 3.3 工厂模式：避免重复代码

为了避免每个节点都写重复的"记录日志 + 统计指标"代码，用了**工厂函数**：

```python
def make_business_node(name: str, handler):
    """
    工厂函数：传入名字和处理函数，自动生成一个完整的节点。

    类比：你不是要开 10 家奶茶店吗？每家店流程一样（接单→做茶→打包），
    只是卖的奶茶不一样。这个函数就是"开奶茶店模板"。
    """
    def node(state):
        resp = handler(state)                          # 执行具体业务逻辑
        history = state["history"] + [f"{name} → 完成"]  # 记录流程
        metrics = state["metrics"].copy()
        metrics["nodes_visited"] += 1                  # 统计经过的节点数
        return {"response": resp, "history": history, "metrics": metrics}
    return node

# 使用：一行创建一个节点
graph.add_node("order_query", make_business_node("order_query", handle_order_query))
graph.add_node("refund", make_business_node("refund", handle_refund))
```

### 3.4 Workflow 版的优缺点

| 优点 | 缺点 |
|------|------|
| ✅ 延迟极低（0.02ms） | ❌ "我的东西什么时候到" → 没命中关键词 |
| ✅ 0 Token 消耗 | ❌ 用户必须说"标准话"才能匹配 |
| ✅ 100% 确定性 | ❌ 新增意图要改代码加关键词 |
| ✅ 每次结果完全一致 | ❌ 无法处理模糊、口语化表达 |

---

## 💻 四、Agent 版详解

**文件**：`src/week4/agent_version.py`

### 4.1 整体架构

```
用户输入
    ↓
[第 1 次 LLM 调用] 意图识别 + 选择 Tool
    ↓
[执行 Tool] 调用对应业务函数
    ↓
[第 2 次 LLM 调用] 基于 Tool 结果生成最终回复
    ↓
（10% 概率）[第 3 次 LLM 调用] 自我纠错检查
    ↓
返回结果
```

### 4.2 模拟 LLM 调用

为了**公平对比**（不让网络延迟影响实验），Agent 版的 LLM 是模拟的：

```python
def simulate_llm_call(prompt: str, estimated_tokens: int = 200) -> dict:
    """
    模拟一次 LLM API 调用。

    真实环境会调用 OpenAI / 阿里云百炼 API，
    模拟版只做两件事：
    1. 模拟延迟（200-800ms）
    2. 返回模拟的 Token 消耗
    """
    latency = random.uniform(200, 800)   # 随机 200-800ms
    time.sleep(latency / 1000)           # 真的等这么久
    return {"latency_ms": latency, "tokens_used": estimated_tokens, "llm_calls": 1}
```

**小白须知**：
- 真实 LLM 调用需要网络请求，通常 200ms-5s
- 每次调用消耗 Token（"字数计费单位"）
- 这里用 `time.sleep` 模拟等待

### 4.3 Tool 注册表

Agent 模式把每个功能封装成"工具"，让 LLM 来选择：

```python
TOOLS = [
    {
        "name": "query_order",
        "description": "查询订单状态，需要提供订单号",  # LLM 看描述来决定用不用
        "handler": tool_query_order,                    # 实际执行的函数
    },
    {
        "name": "query_refund",
        "description": "查询退款政策，需要提供订单号",
        "handler": tool_query_refund,
    },
    # ... 更多工具
]
```

**类比**：就像手机里装了很多 App，Agent 模式下是 **LLM** 帮你选 App，而不是你自己按按钮。

### 4.4 Agent 版的"智能"体现

| 用户说的话 | Workflow 版理解 | Agent 版理解 |
|-----------|---------------|-------------|
| "帮我查物流" | ✅ 命中"物流"关键词 | ✅ LLM 理解 |
| "我的东西什么时候到" | ❌ 没命中关键词 → 走 greeting | ✅ LLM 理解"东西什么时候到"=物流 |
| "这个手机能退吗" | ❌ 没命中"退款"关键词 | ✅ LLM 理解"能退吗"=退款 |
| "手机" | ❌ 不知道指什么 | ✅ LLM 推断"手机"= iPhone 15 Pro |

---

## 📊 五、对比实验详解

**文件**：`src/week4/comparison.py`

### 5.1 实验设计

```
10 个测试用例
    ├── 7 个标准意图（关键词明确）
    ├── 2 个模糊意图（口语化）
    └── 1 个混合意图（多个意图重叠）

每个用例跑 5 次取平均值（消除随机性）

对比维度：延迟、Token 消耗、准确率、一致率
```

### 5.2 测试用例一览

| ID | 输入 | 预期意图 | 类型 |
|----|------|---------|------|
| 1 | 帮我查一下订单 ORD... 的状态 | order_query | 标准 |
| 2 | 退款需要什么条件？ | refund | 标准 |
| 3 | 帮我查一下物流 SF... | logistics | 标准 |
| 4 | USER001 有哪些优惠券？ | coupon | 标准 |
| 5 | iPhone 15 Pro 多少钱？ | product | 标准 |
| 6 | 我要投诉！转人工！ | escalate | 标准 |
| 7 | 你好 | greeting | 标准 |
| 8 | **我的东西什么时候到** | logistics | **模糊** |
| 9 | **这个手机能退吗** | refund | **模糊** |
| 10 | **已发货的订单能退款吗？** | refund | **混合** |

### 5.3 数据汇总

| 评估维度 | Workflow 版 | Agent 版 | 谁赢了？ |
|---------|------------|---------|---------|
| **标准意图 - 延迟** | **0.03ms** | 1082ms | Workflow（快 3 万倍） |
| **标准意图 - 准确率** | 100% | 100% | 平手 |
| **标准意图 - 一致率** | **100%** | 91% | Workflow |
| **标准意图 - Token** | **0** | ~1284/次 | Workflow（免费） |
| **模糊意图 - 准确率** | 100% | 100% | 平手* |
| **混合意图 - 准确率** | **100%** | 0% | Workflow |

> *注：模糊意图的 Workflow 准确率 100% 是因为关键词恰好覆盖了。真实场景中不会这么理想。

### 5.4 关键发现

#### 发现 1：Workflow 快到飞起

```
Workflow 平均延迟：0.03ms（万分之三秒）
Agent 平均延迟：1000ms（1 秒）
差距：约 30000 倍
```

**现实影响**：如果你的系统每秒处理 10000 个请求，Workflow 毫无压力；Agent 版 1000 个请求就要排队 1 秒。

#### 发现 2：混合意图是 Agent 的噩梦

```
输入："已发货的订单能退款吗？订单 ORD20260417001"

Workflow：✅ 正确识别为"退款"（规则优先级：退款关键词 > 订单关键词）
Agent：  ❌ 误判为"订单查询"（LLM 先看到"订单""发货"，截断了"退款"意图）
```

**这叫"意图重叠冲突"（Intent Collision）**：
- 一句话里包含多个意图关键词
- Workflow 靠**人工定义的优先级**解决
- Agent 靠 LLM 自己判断，但可能被前面的关键词"带偏"

#### 发现 3：Token 消耗的隐性成本

```
1300 Token/次 × 10000 用户/天 × 30 天 = 3.9 亿 Token/月

按 GPT-4 价格 = $11,700/月 ≈ ¥85,000/月
按 Qwen 价格 = ¥3,120/月

而 Workflow 版：¥0/月
```

---

## 🎯 六、选型决策树

```
                    你的场景需要 LLM 动态规划步骤吗？
                         /                \
                       是                  否
                      /                    \
            用 Agent 模式              步骤固定，只是分支动态？
         （自由对话、代码生成）              /          \
                                         是            否
                                        /              \
                                  用 Workflow         用纯流程引擎
                                （LangGraph）      （Spring/Airflow）
```

### 用 Workflow 的场景

| 场景 | 原因 |
|------|------|
| 财务审批 | 金额、权限必须精确，不能让 LLM 自由发挥 |
| 订单处理 | 流程固定（验证→扣款→发货），步骤不能乱 |
| 合规审查 | 每一步都要可追溯、可审计 |
| 客服标准问答 | 高频问题用规则覆盖，成本极低 |

### 用 Agent 的场景

| 场景 | 原因 |
|------|------|
| 自由对话 | 用户说什么无法预测，需要 LLM 理解 |
| 代码生成 | 输入千变万化，规则覆盖不了 |
| 数据分析 | 需要根据数据动态决定分析步骤 |
| 创意写作 | 没有固定流程，需要 LLM 发挥 |

### 最佳实践：混合架构（Hybrid）

```
              ┌─────────────────────┐
              │    Workflow 骨架     │
              │  （确定性的主流程）    │
              └──────┬──────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ 规则节点  │ │ Agent 节点│ │ 规则节点  │
  │ 意图路由  │ │ 模糊理解  │ │ 结果校验  │
  └──────────┘ └──────────┘ └──────────┘
```

**核心思想**：
- 用 Workflow 搭骨架（保证流程可控、可追踪）
- 在特定节点嵌入 Agent（处理需要灵活理解的部分）
- 这是目前工业界最推荐的架构

---

## ⚠️ 七、踩坑记录

### 坑 1：意图优先级顺序很重要

```python
# ❌ 错误顺序
if any(k in q for k in ["订单", "状态"]):     # "订单" 先命中！
    return "order_query"
if any(k in q for k in ["退款", "退货"]):     # 永远走不到
    return "refund"

# ✅ 正确顺序：高优先级放前面
if any(k in q for k in ["退款", "退货"]):
    return "refund"
if any(k in q for k in ["订单", "状态"]):
    return "order_query"
```

**教训**：`if-elif` 链的顺序 = 业务优先级，必须仔细设计。

### 坑 2：Agent 的一致性问题

同一个输入跑 5 次，Agent 回复不完全一样（因为 LLM 有随机性）。

**教训**：真实 Agent 系统需要通过**结构化输出**（如 Pydantic）来约束。

---

## 🔑 八、如何运行

```bash
cd month02-langgraph/src/week4

# 单独运行 Workflow 版
python workflow_version.py

# 单独运行 Agent 版
python agent_version.py

# 运行对比实验
python comparison.py
```

---

## 📊 九、与前几周知识的串联

```
Week 1: Graph API 入门 ✅
  └── 学会用 StateGraph + 节点 + 边构建流程

Week 2: 持久化 ✅
  └── 学会用 Checkpoint 保存状态、时间旅行、人工审核

Week 3: 子图模块化 ✅
  └── 学会把大 Graph 拆成独立可复用的子图

Week 4: Workflow vs Agent 对比 ✅
  └── 学会用数据量化两种模式的优劣，建立选型判断力
```

---

## 🎓 十、核心收获总结

> **没有最好的方案，只有最合适的方案。**

| 你的需求 | 推荐方案 | 理由 |
|---------|---------|------|
| 快速 MVP | Workflow | 开发快，不依赖 LLM API |
| 生产级客服 | Hybrid | 主流程用 Workflow，模糊意图交给 Agent |
| 聊天机器人 | Agent | 用户表述千变万化，规则覆盖不了 |
| 内部工具 | Workflow | 用户少，确定性比灵活性重要 |
| 高并发系统 | Workflow | 延迟和成本都是数量级差距 |

---

> 💡 **记住**：能用规则解决的就别用 LLM，把 LLM 留给真正需要"理解"的地方。这不仅是技术选型，更是成本意识。好的工程师不是"什么都会用"，而是"知道什么时候不该用"。
