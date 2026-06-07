# 📚 第 2 月 - Week 4：Workflow vs Agent 对比实验

> 学习日期：2026-05-26 至 2026-05-28
> 代码位置：`month02-langgraph/src/week4/`
> 状态：3 个文件全部跑通 ✅

---

## 一、Week 4 到底在干什么？

### 一句话总结

> **用同一个需求（电商客服），分别写两个版本，然后跑数据对比，看看哪种方案更适合什么场景。**

### 为什么要做这个对比？

在前面三周的学习中，我们已经用 LangGraph 写了各种 Graph：
- Week 1：基础 Graph（节点 + 边 + 条件路由）
- Week 2：持久化（Checkpoint、时间旅行、人工审核）
- Week 3：子图模块化（拆分子图、适配器模式）

但始终有一个问题没回答：

> **"LangGraph 这种'你手动设计流程'的方式，和直接让 LLM 自己决定做什么（Agent 模式），到底哪个好？"**

Week 4 就是用**数据**来回答这个问题。

### 两个版本是什么？

| 版本 | 文件名 | 核心思路 | 类比 |
|------|--------|---------|------|
| **Workflow 版** | `workflow_version.py` | 你写好规则，程序按流程走 | 自动售货机：按哪个按钮出哪个货 |
| **Agent 版** | `agent_version.py` | LLM 理解你的话，自己决定做什么 | 真人客服：听你说话，自己判断怎么处理 |

---

## 二、先搞懂两个核心概念

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

每一步都有 **LLM 参与**，灵活但有代价。

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

## 三、Workflow 版详解 (`workflow_version.py`)

### 3.1 整体架构

```
__start__
    ↓
intent_router（关键词匹配意图 + 提取订单号等信息）
    ↓
[条件边：根据意图路由]
    ├─ order_query  → 查订单
    ├─ refund       → 查退款
    ├─ logistics    → 查物流
    ├─ coupon       → 查优惠券
    ├─ product      → 查产品
    ├─ escalate     → 转人工
    └─ greeting     → 问候
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
        return "escalate"
    if any(k in q for k in ["物流", "快递", "到哪了", "包裹"]):
        return "logistics"
    if any(k in q for k in ["退款", "退货", "退钱"]):
        return "refund"
    if any(k in q for k in ["优惠", "券", "折扣"]):
        return "coupon"
    if any(k in q for k in ["保修", "什么价格", "多少钱"]):
        return "product"
    if any(k in q for k in ["订单", "状态", "发货了吗"]):
        return "order_query"
    return "greeting"  # 兜底：啥都没匹配到就当问候
```

**小白须知**：
- `any(k in q for k in [...])` 就是检查用户输入里有没有这些关键词
- 比如用户说"帮我查一下物流 SF1234567890"，里面有"物流"，所以返回 `"logistics"`
- **优先级**：排在前面的先匹配到就先返回，所以"投诉"优先级最高

### 3.3 信息提取：正则表达式

```python
def extract_info(user_input: str) -> dict:
    # 用正则从用户输入中提取结构化信息
    order_id = re.search(r"ORD\d+", user_input)     # 提取订单号
    tracking = re.search(r"(SF|JD)\d+", user_input) # 提取物流单号
    user_id = re.search(r"USER\d+", user_input)      # 提取用户ID
```

**小白须知**：
- `re.search(r"ORD\d+", ...)` 就是找 "ORD" 开头后面跟数字的字符串
- 比如 "帮我查订单 ORD20260417001" → 提取出 `"ORD20260417001"`
- 这比 LLM 快得多，但也死板得多——格式不对就提取不到

### 3.4 业务节点：工厂模式

为了避免每个节点都写重复的"记录日志 + 统计指标"代码，用了**工厂函数**：

```python
def make_business_node(name: str, handler):
    """
    工厂函数：传入名字和处理函数，自动生成一个完整的节点。

    类比：你不是要开10家奶茶店吗？每家店流程一样（接单→做茶→打包），
    只是卖的奶茶不一样。这个函数就是"开奶茶店模板"。
    """
    def node(state: WorkflowState) -> dict:
        resp = handler(state)              # 执行具体业务逻辑
        history = state["history"] + [f"{name} → 完成"]  # 记录流程
        metrics = state["metrics"].copy()
        metrics["nodes_visited"] += 1      # 统计经过了几个节点
        return {"response": resp, "history": history, "metrics": metrics}
    return node

# 使用：一行创建一个节点
graph.add_node("order_query", make_business_node("order_query", handle_order_query))
graph.add_node("refund", make_business_node("refund", handle_refund))
```

### 3.5 Workflow 版的优缺点

| 优点 | 缺点 |
|------|------|
| ✅ 延迟极低（0.02ms） | ❌ "我的东西什么时候到" → 没命中"物流/快递"关键词 |
| ✅ 0 Token 消耗 | ❌ 用户必须说"标准话"才能匹配 |
| ✅ 100% 确定性 | ❌ 新增意图要改代码加关键词 |
| ✅ 每次结果完全一致 | ❌ 无法处理模糊、口语化表达 |

---

## 四、Agent 版详解 (`agent_version.py`)

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

    真实环境这里会调用 OpenAI / 阿里云百炼 API，
    模拟版只做两件事：
    1. 模拟延迟（200-800ms）
    2. 返回模拟的 Token 消耗
    """
    latency = random.uniform(200, 800)  # 随机 200-800ms
    time.sleep(latency / 1000)          # 真的等这么久

    return {
        "latency_ms": latency,
        "tokens_used": estimated_tokens,
        "llm_calls": 1,
    }
```

**小白须知**：
- 真实 LLM 调用需要网络请求，通常 200ms-5s 不等
- 每次调用会消耗 Token（可以理解为"字数计费单位"）
- 这里用 `time.sleep` 模拟等待，用随机数模拟 Token 消耗

### 4.3 Tool 注册表

Agent 模式把每个功能封装成"工具"，让 LLM 来选择：

```python
TOOLS = [
    {
        "name": "query_order",
        "description": "查询订单状态，需要提供订单号",  # LLM 看这个描述来决定用不用
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

**小白须知**：
- 就像你手机里装了很多 App（工具），你根据需求选择打开哪个
- Agent 模式下，是 **LLM** 帮你选 App，而不是你自己按按钮
- `description` 就是告诉 LLM "这个工具能干什么"，LLM 据此判断是否调用

### 4.4 Agent 执行循环（核心）

```python
def run_agent(user_input: str) -> dict:
    """
    Agent 的完整执行流程，类比真人客服的工作过程：
    """
    # Step 1: 理解用户说什么（第 1 次 LLM 调用）
    # 类比：客服听你说话，判断你要办什么业务
    intent_result = agent_classify_intent(user_input)

    # Step 2: 执行具体操作（调用 Tool）
    # 类比：客服在电脑上点"查询订单"按钮
    tool_result = tool_def["handler"](**tool_args)

    # Step 3: 组织语言回复你（第 2 次 LLM 调用）
    # 类比：客服查到结果后，用礼貌的话术告诉你
    llm_result2 = simulate_llm_call(f"基于工具结果生成回复: {tool_result}")

    # （可选）Step 4: 10% 概率自我检查
    # 类比：客服想了一下"我是不是回答错了？"
    if random.random() < 0.1:
        simulate_llm_call("自我纠错检查")
```

### 4.5 Agent 版的"智能"体现

Agent 版能理解更模糊的表述：

| 用户说的话 | Workflow 版理解 | Agent 版理解 |
|-----------|---------------|-------------|
| "帮我查物流" | ✅ 命中"物流"关键词 | ✅ LLM 理解 |
| "我的东西什么时候到" | ❌ 没命中任何关键词 → 走 greeting | ✅ LLM 理解"东西什么时候到"=物流 |
| "这个手机能退吗" | ❌ 没命中"退款"关键词 → 走 greeting | ✅ LLM 理解"能退吗"=退款，"手机"=iPhone |
| "手机" | ❌ 不知道指什么 | ✅ LLM 推断"手机"= iPhone 15 Pro |

### 4.6 Agent 版的优缺点

| 优点 | 缺点 |
|------|------|
| ✅ 能理解模糊、口语化表达 | ❌ 延迟高（~1000ms vs 0.02ms） |
| ✅ 不需要穷举关键词 | ❌ 每次消耗 ~1300 Token |
| ✅ 能处理没见过的表述 | ❌ 结果不确定（同样输入可能不同输出） |
| ✅ 回复更自然 | ❌ 10% 概率多余一次 LLM 调用（自我纠错） |

---

## 五、对比实验详解 (`comparison.py`)

### 5.1 实验设计

```
10 个测试用例
    ├── 7 个标准意图（关键词明确，如"帮我查订单 ORD..."）
    ├── 2 个模糊意图（口语化，如"我的东西什么时候到"）
    └── 1 个混合意图（多个意图重叠，如"已发货的订单能退款吗"）

每个用例跑 5 次取平均值（消除随机性）

对比维度：
    ├── 延迟（latency）：从输入到输出花了多长时间
    ├── Token 消耗：花了多少"字数费"
    ├── 准确率（accuracy）：回复是否正确
    └── 一致率（consistency）：5 次结果是否一样
```

### 5.2 测试用例一览

| ID | 输入 | 预期意图 | 类型 | 说明 |
|----|------|---------|------|------|
| 1 | 帮我查一下订单 ORD20260417001 的状态 | order_query | 标准 | 有明确"订单"关键词 |
| 2 | 退款需要什么条件？ | refund | 标准 | 有明确"退款"关键词 |
| 3 | 帮我查一下物流 SF1234567890 | logistics | 标准 | 有明确"物流"关键词 |
| 4 | USER001 有哪些优惠券？ | coupon | 标准 | 有明确"优惠券"关键词 |
| 5 | iPhone 15 Pro 多少钱？ | product | 标准 | 有明确产品名 |
| 6 | 我要投诉！转人工！ | escalate | 标准 | 有明确"投诉""转人工" |
| 7 | 你好 | greeting | 标准 | 简单问候 |
| 8 | 我的东西什么时候到 | logistics | **模糊** | 没有"物流""快递"关键词 |
| 9 | 这个手机能退吗 | refund | **模糊** | 没有"退款"关键词 |
| 10 | 已发货的订单能退款吗？订单 ORD... | refund | **混合** | 同时含"订单""发货""退款" |

### 5.3 一致率怎么算？

```python
# 同一个输入跑 5 次，看回复有几种
responses = ["回复A", "回复A", "回复A", "回复B", "回复A"]  # 2 种不同回复
unique = len(set(responses))  # = 2
consistency = (5 - 2 + 1) / 5 * 100  # = 80%
```

- Workflow 版：5 次结果**完全一样** → 一致率 100%
- Agent 版：因为有随机性（模拟 LLM 的 self-correction），可能产生不同结果 → 一致率 ~80-90%

---

## 六、实验结果分析

### 6.1 数据汇总表

| 评估维度 | Workflow 版 | Agent 版 | 谁赢了？ |
|---------|------------|---------|---------|
| **标准意图 - 延迟** | **0.03ms** | 1082ms | ✅ Workflow（快 3 万倍） |
| **标准意图 - 准确率** | 100% | 100% | 🤝 平手 |
| **标准意图 - 一致率** | **100%** | 91% | ✅ Workflow |
| **标准意图 - Token** | **0** | ~1284/次 | ✅ Workflow（免费） |
| **模糊意图 - 延迟** | **0.02ms** | 1064ms | ✅ Workflow |
| **模糊意图 - 准确率** | 100% | 100% | 🤝 平手 |
| **模糊意图 - 一致率** | **100%** | 90% | ✅ Workflow |
| **混合意图 - 准确率** | **100%** | **0%** | ✅ Workflow |

### 6.2 逐条解读关键发现

#### 发现 1：Workflow 快到飞起

```
Workflow 平均延迟：0.03ms（万分之三秒）
Agent 平均延迟：1000ms（1 秒）

差距：约 30000 倍
```

**为什么？**
- Workflow 只做字符串匹配（`"退款" in user_input`），CPU 几个时钟周期就搞定
- Agent 要模拟网络请求 + LLM 推理，每次至少 200ms

**现实影响**：
- 如果你的系统每秒处理 10000 个请求，Workflow 毫无压力
- Agent 版？1000 个请求就要排队 1 秒，10000 个要排 10 秒

#### 发现 2：混合意图是 Agent 的噩梦

```
输入："已发货的订单能退款吗？订单 ORD20260417001"

Workflow：✅ 正确识别为"退款"（因为规则优先级：退款关键词 > 订单关键词）
Agent：  ❌ 误判为"订单查询"（LLM 先看到"订单""发货"，截断了"退款"意图）
```

**这叫"意图重叠冲突"（Intent Collision）**：
- 一句话里包含多个意图关键词
- Workflow 靠**人工定义的优先级**解决（代码里 if-elif 的顺序）
- Agent 靠 LLM 自己判断，但 LLM 可能被前面的关键词"带偏"

#### 发现 3：Agent 并非一无是处

虽然数据表上 Workflow 全赢，但这是因为：
1. 我们的模拟 LLM 不够智能（真实 LLM 会更灵活）
2. 测试用例有限（真实场景更复杂）
3. Workflow 版的关键词**恰好覆盖了**所有模糊用例

**Agent 的真正价值**在于面对**没见过的表述**时的泛化能力。

---

## 七、选型决策树（什么时候用哪个？）

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

### 7.1 用 Workflow 的场景

| 场景 | 原因 |
|------|------|
| 财务审批 | 金额、权限必须精确，不能让 LLM 自由发挥 |
| 订单处理 | 流程固定（验证→扣款→发货），步骤不能乱 |
| 合规审查 | 每一步都要可追溯、可审计 |
| 客服标准问答 | 高频问题用规则覆盖，成本极低 |

### 7.2 用 Agent 的场景

| 场景 | 原因 |
|------|------|
| 自由对话 | 用户说什么无法预测，需要 LLM 理解 |
| 代码生成 | 输入千变万化，规则覆盖不了 |
| 数据分析 | 需要根据数据动态决定分析步骤 |
| 创意写作 | 没有固定流程，需要 LLM 发挥 |

### 7.3 最佳实践：混合架构（Hybrid）

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

## 八、代码结构速览

### 8.1 文件关系

```
week4/
├── workflow_version.py    # Workflow 版实现（纯规则路由）
├── agent_version.py       # Agent 版实现（模拟 LLM 驱动）
├── comparison.py          # 对比实验脚本
├── comparison_results.json # 实验结果数据（自动生成）
└── subgraphs/             # 子图目录（预留扩展）
```

### 8.2 数据流对比

**Workflow 版数据流**：
```
用户输入 "帮我查订单 ORD20260417001"
    ↓
intent_router_node:
    classify_intent_rules() → "order_query"（关键词"订单"命中）
    extract_info() → {order_id: "ORD20260417001"}
    ↓
order_query 节点:
    handle_order_query() → "📦 订单 ORD20260417001：..."
    ↓
finalize_node:
    拼接流程记录 → 最终输出
```

**Agent 版数据流**：
```
用户输入 "帮我查订单 ORD20260417001"
    ↓
agent_classify_intent():
    simulate_llm_call() → 200-800ms 延迟，150 Token
    识别意图 → "order_query"
    选择 Tool → "query_order"
    ↓
执行 Tool:
    tool_query_order("ORD20260417001") → "📦 订单..."
    ↓
simulate_llm_call():
    基于 Tool 结果生成回复 → 200-800ms 延迟，100 Token
    ↓
（10%概率）自我纠错:
    simulate_llm_call() → 额外 80 Token
    ↓
最终输出
```

### 8.3 如何运行

```bash
# 单独运行 Workflow 版
cd month02-langgraph/src/week4
python workflow_version.py

# 单独运行 Agent 版
python agent_version.py

# 运行对比实验（自动调用上面两个版本）
python comparison.py
```

---

## 九、本周踩坑记录

### 踩坑 1：意图优先级顺序很重要

**现象**：输入"已发货的订单能退款吗"，被识别为"订单查询"而不是"退款"。

**原因**：代码里 `order_query` 的关键词 `"订单"` 排在 `refund` 的 `"退款"` 前面，先匹配到了。

```python
# ❌ 错误顺序：订单关键词先匹配
if any(k in q for k in ["订单", "状态"]):     # "订单" 命中！直接返回
    return "order_query"
if any(k in q for k in ["退款", "退货"]):     # 永远走不到这里
    return "refund"

# ✅ 正确顺序：高优先级意图放前面
if any(k in q for k in ["退款", "退货"]):     # 先检查退款
    return "refund"
if any(k in q for k in ["订单", "状态"]):     # 再检查订单
    return "order_query"
```

**教训**：if-elif 链的顺序 = 业务优先级，必须仔细设计。

### 踩坑 2：模拟 LLM 的随机性影响一致率

**现象**：Agent 版同一个输入跑 5 次，回复不完全一样，一致率只有 80%。

**原因**：
- `simulate_llm_call` 有随机延迟（200-800ms）
- 10% 概率触发"自我纠错"（额外一次 LLM 调用）
- 导致回复文本中 `[流程]` 部分可能多出"LLM自我纠错 → 完成"

**教训**：真实 Agent 系统的一致性问题更严重，需要通过结构化输出（如 Pydantic）来约束。

### 踩坑 3：Token 消耗的隐性成本

**现象**：Agent 版每次请求消耗 ~1300 Token，看起来不多。

**算一笔账**：
```
1300 Token/次 × 10000 用户/天 × 30 天 = 3.9 亿 Token/月

按 GPT-4 价格（$30/百万 Token）= $11,700/月 ≈ ¥85,000/月
按 Qwen 价格（¥0.008/千 Token）= ¥3,120/月

而 Workflow 版：¥0/月
```

**教训**：Token 单价虽低，但乘以用户量后差距巨大。

---

## 十、与前几周知识的串联

### 10.1 学习路径回顾

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

### 10.2 知识图谱

```
                    ┌───────────────────┐
                    │   你的 AI 系统     │
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 ↓            ↓            ↓
          ┌───────────┐ ┌──────────┐ ┌───────────┐
          │ Workflow  │ │  Agent   │ │  Hybrid   │
          │ (Week 1-3)│ │ (Month 1)│ │ (Week 4)  │
          │           │ │          │ │           │
          │ 确定流程   │ │ LLM驱动  │ │ 两者结合  │
          │ 规则路由   │ │ 动态决策  │ │ 骨架+智能 │
          │ 零成本    │ │ 灵活但贵 │ │ 最佳实践  │
          └───────────┘ └──────────┘ └───────────┘
```

### 10.3 核心收获

> **没有最好的方案，只有最合适的方案。**

| 你的需求 | 推荐方案 | 理由 |
|---------|---------|------|
| 快速 MVP | Workflow | 开发快，不依赖 LLM API |
| 生产级客服 | Hybrid | 主流程用 Workflow，模糊意图交给 Agent |
| 聊天机器人 | Agent | 用户表述千变万化，规则覆盖不了 |
| 内部工具 | Workflow | 用户少，确定性比灵活性重要 |
| 高并发系统 | Workflow | 延迟和成本都是数量级差距 |

---

> 📝 **写在最后**：Week 4 的核心就一句话 — **能用规则解决的就别用 LLM，把 LLM 留给真正需要"理解"的地方**。
> 这不仅是技术选型，更是成本意识。每多一次 LLM 调用，就多一份延迟和费用。
> 好的工程师不是"什么都会用"，而是"知道什么时候不该用"。
