# 📗 Week 2 详解 - Persistence / Checkpoints / Human-in-the-Loop

> **适合人群**：已经掌握 Week 1（会写基本 Graph）的新手
> **前置知识**：了解 StateGraph、Node、Edge 基本概念
> **预计时间**：2-2.5 小时

---

## 🎯 学习目标

学完 Week 2，你将掌握：

1. ✅ **MemorySaver** — 让 Graph "记住" 状态，支持多轮对话
2. ✅ **Thread ID** — 隔离不同用户/会话
3. ✅ **Checkpoint** — 状态快照，像游戏存档一样
4. ✅ **Human-in-the-Loop** — 关键步骤暂停，等人类审批
5. ✅ **Time Travel** — 回到过去的状态重新执行

---

## 📚 一、为什么需要持久化？

### Week 1 的痛点

Week 1 写的 Graph，每次调用 `app.invoke()` 都是**独立的一次性运行**：

```python
# 第 1 次
result = app.invoke({"user_input": "你好"})
# → "你好！我是客服助手"

# 第 2 次（Graph 完全不知道第 1 次发生了什么）
result = app.invoke({"user_input": "帮我查一下刚才说的订单"})
# → ❌ Graph 不知道"刚才说的订单"是什么
```

**类比**：这就像一个**失忆的客服**——你每说一句话，他就忘了你之前说过的所有话。

### Week 2 解决三个问题

| 问题 | 生活场景 | Week 2 方案 |
|------|---------|------------|
| **失忆** | 用户连续对话，客服记不住上下文 | MemorySaver + Thread ID |
| **无法暂停** | 退款需要主管签字，但系统一口气跑完了 | interrupt_before |
| **无法回滚** | 操作错了想撤销，但没有"撤销"按钮 | Checkpoint + Time Travel |

---

## 📖 二、MemorySaver：让 Graph "有记忆"

### 一句话理解

> MemorySaver 就是给 Graph 装了一个**笔记本**，每次执行完都记录当前状态。下次用同一个 `thread_id` 调用时，Graph 能"翻看笔记本"继续对话。

### 三行代码搞定

```python
from langgraph.checkpoint.memory import MemorySaver

# 第 1 行：创建笔记本
checkpointer = MemorySaver()

# 第 2 行：编译时把笔记本装上去
app = graph.compile(checkpointer=checkpointer)

# 第 3 行：调用时告诉 Graph 用哪个"聊天室"
config = {"configurable": {"thread_id": "user-alice-001"}}
result = app.invoke(state, config)
```

**缺一不可**。少了任何一行，Graph 就失忆。

### 对比：有 vs 没有

```python
# ❌ 没有 checkpointer（失忆模式）
app = graph.compile()
r1 = app.invoke({"messages": ["你好"], "response": ""})
r2 = app.invoke({"messages": ["你刚才说了啥"], "response": ""})
# → messages 里没有"你好"，Graph 失忆了

# ✅ 有 checkpointer（有记忆模式）
app = graph.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "session-001"}}
r1 = app.invoke({"messages": ["你好"], "response": ""}, config)
r2 = app.invoke({"messages": ["你刚才说了啥"], "response": ""}, config)
# → checkpoint 里有上一轮的 messages，Graph 记得！
```

### 实际效果

运行 `checkpoint_demo.py` 的 demo_1，你会看到：

```
--- 第 1 轮 ---
用户: 你好
助手: 👋 你好！我是智能客服...

--- 第 2 轮 ---
用户: 帮我查一下订单 ORD20260417001
助手: 📦 订单 ORD20260417001，商品：iPhone 15 Pro...

--- 📜 完整对话历史 ---
👤 你好
⚙️ 意图: greeting
🤖 👋 你好！我是智能客服...
👤 帮我查一下订单 ORD20260417001
⚙️ 意图: order_query
🤖 📦 订单 ORD20260417001...
```

`messages` 列表自动累积，不用手动拼接！

---

## 📖 三、Thread ID：会话隔离

### 一句话理解

> `thread_id` 就是**聊天室编号**。不同的 `thread_id` = 不同的聊天室，互不干扰。

### 类比理解

想象一家咖啡店：
- `thread_id` = 桌号（1号桌、2号桌...）
- `MemorySaver` = 服务员的小本子
- 每个桌的点单记录独立存在本子上

```python
config_alice = {"configurable": {"thread_id": "user-alice-001"}}
config_bob   = {"configurable": {"thread_id": "user-bob-002"}}

# Alice 查自己的订单
app.invoke({"user_input": "查我的订单"}, config_alice)

# Bob 查自己的订单（同一个 Graph，不同会话）
app.invoke({"user_input": "查我的订单"}, config_bob)

# 两边完全不串！Alice 看不到 Bob 的记录
```

### Thread ID 命名建议

```
{业务类型}-{用户/实体}-{序号}

user-alice-001          # 用户 Alice 的第 1 个会话
refund-approval-003     # 第 3 个退款审批流程
order-tracking-042      # 第 42 个订单跟踪
```

---

## 📖 四、Checkpoint：状态的"游戏存档"

### 一句话理解

> 每个 Checkpoint 就是 Graph 执行到某个时刻时，**完整状态的快照**。就像游戏的存档点，随时可以读档回去。

### 什么时候创建 Checkpoint？

- 每个节点执行前/后
- 每次状态变更后

### 如何查看历史？

```python
history = list(app.get_state_history(config))

# history 是一个列表，从新到旧排列
for i, cp in enumerate(history):
    print(f"[{i}] next={cp.next} | values={cp.values}")
```

### 每个 Checkpoint 包含什么？

| 属性 | 类型 | 说明 |
|------|------|------|
| `cp.next` | tuple | 下一个待执行的节点名，如 `('order_query',)` |
| `cp.values` | dict | 当时的完整 state |
| `cp.config` | dict | 包含 checkpoint_id 的配置信息 |

> ⚠️ **重要**：`StateSnapshot` 是 `NamedTuple`，**必须用属性访问**（`cp.next`），**不能用字典方式**（`cp["next"]` ❌）

### 实际输出

运行 `checkpoint_demo.py` 的 demo_2：

```
--- 📋 所有 Checkpoint ---
  共 8 个 checkpoint
  [0] 1f155c60... | intent=order_query | response=📦 订单 ORD20260417003...
  [1] 1f155c60... | intent=order_query | response=👋 你好！...
  [2] 1f155c60... | intent=greeting | response=👋 你好！...
  ...
```

8 个 checkpoint 记录了从初始状态到最终结果的**完整执行轨迹**。

---

## 📖 五、Human-in-the-Loop：人工审核

### 一句话理解

> 让 Graph 在**关键步骤暂停**，等人类审批/决策后再继续。

### 为什么需要？

有些业务场景不能全自动：
- **退款审批** → 需要主管签字
- **大额转账** → 需要财务确认
- **内容发布** → 需要编辑审核

### 两种中断方式

| 方式 | 代码 | 类比 | 什么时候用 |
|------|------|------|----------|
| `interrupt_before` | `interrupt_before=["approve"]` | 在"批准"按钮**前**暂停 | 需要人工**做决策** |
| `interrupt_after` | `interrupt_after=["process"]` | 在"扣款"按钮**后**暂停 | 需要人工**检查结果** |

> 💡 **90% 的场景用 `interrupt_before`**。

### 完整操作流程（4 步）

**步骤 1：编译时配置 interrupt**

```python
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["approve_refund"],  # ← 在 approve_refund 节点前暂停
)
```

**步骤 2：第一次 invoke，Graph 自动暂停**

```python
result = app.invoke({
    "user_input": "我要退款，订单 ORD20260417001",
    "approved": False,  # 默认未批准
}, config)

# Graph 停在了 approve_refund 之前
# result["response"] = "💰 退款审核请求... ⏸️ 等待人工审核..."
```

**步骤 3：查看暂停状态，人工注入决策**

```python
# 查看当前状态
current = app.get_state(config)
print(current.next)  # → ('approve_refund',) ← 下一个要执行的节点

# 人工决策：批准退款
app.update_state(config, {"approved": True})
```

> ⚠️ **关键**：直接 patch state，**不要用 `as_node` 参数**！后面会解释为什么。

**步骤 4：从断点继续**

```python
result = app.invoke(None, config)  # ← None 表示"从断点继续"
# result["response"] = "✅ 退款已批准，1-3 工作日到账。"
```

### 多步骤审批实战（双审核）

`human_in_the_loop.py` 实现了一个完整的多步骤退款审批：

```
创建申请 → 等待主管审核 → ⏸️ → 主管批准 → 等待财务审核 → ⏸️ → 财务批准 → 退款完成
                                     ↓                              ↓
                                  主管拒绝                       财务拒绝
                                     ↓                              ↓
                                 通知用户                       通知用户
```

**关键代码**：

```python
# 在两个决策节点前都暂停
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["manager_decision", "finance_decision"],
)

# 第 1 次暂停：主管审核
app.update_state(config, {"manager_approved": True})
app.invoke(None, config)

# 第 2 次暂停：财务审核
app.update_state(config, {"finance_approved": True})
app.invoke(None, config)
```

### 三种场景验证

| 场景 | 主管 | 财务 | 结果 |
|------|------|------|------|
| 完整通过 | ✅ 批准 | ✅ 批准 | 退款完成 |
| 主管拒绝 | ❌ 拒绝 | 不执行 | 主管拒绝，直接通知用户 |
| 财务拒绝 | ✅ 批准 | ❌ 拒绝 | 财务拒绝，通知用户 |

---

## 📖 六、Time Travel：时间旅行

### 一句话理解

> 回到 Graph 执行的某个历史状态，从那里用不同的输入重新执行。

### 类比

就像游戏的"存档/读档"：
1. 玩到某个位置 → 自动存档（checkpoint）
2. 发现选错分支 → 查看存档列表
3. 加载某个存档 → 从那里重新玩

### 场景：修改折扣码后重新计算

**问题**：用户下单时折扣码填错了（`INVALID` → 无折扣），想改成 `SAVE10` 重新算。

**❌ 错误做法**：直接在当前 thread 上 `update_state`

```python
app.update_state(config, {"discount_code": "SAVE10"})
result = app.invoke(None, config)
# 问题：discount 节点已经执行过了，不会重跑
# 结果：总价还是没打折
```

**✅ 正确做法**：从历史 checkpoint **fork** 新 thread

```python
# 1. 找到目标 checkpoint（刚计算完总价，还没应用折扣）
history = list(app.get_state_history(config))
calc_cp = next(cp for cp in history if cp.values.get("status") == "calculated")

# 2. 创建新 thread，注入修改后的状态
fork_config = {"configurable": {"thread_id": "fork-001"}}
app.update_state(fork_config, {
    **calc_cp.values,           # 继承 checkpoint 的状态
    "discount_code": "SAVE10",  # 修改关键字段
})

# 3. 从 fork 点继续（会重新执行 discount 及之后的节点）
result = app.invoke(None, fork_config)
```

**实际效果**：
```
原始总价: ¥7999.00（INVALID 折扣码，无折扣）
修改后:   ¥7199.10（SAVE10 折扣码，-¥799.90，10% off）
```

### 场景：Fork 分支探索

同一初始状态，探索不同配送方案：

```python
for method in ["standard", "express", "overnight"]:
    thread = f"order-fork-{method}"
    config = {"configurable": {"thread_id": thread}}
    result = app.invoke(initial_state, config)
    print(f"{method}: ¥{result['total']:.2f}")
```

结果：
```
standard  : ¥7,599.20 (基准)
express   : ¥7,614.20 (+¥15.00)
overnight : ¥7,629.20 (+¥30.00)
```

---

## ⚠️ 七、踩坑记录（非常重要！）

### 坑 1：StateSnapshot API 变化

**现象**：`current.get("next")` 报错 `AttributeError`

**原因**：新版 LangGraph 中 `StateSnapshot` 从 dict-like 变成了 `NamedTuple`

```python
# ❌ 旧写法
current.get("next", [])
cp["values"].get("status")

# ✅ 新写法
current.next              # tuple
cp.values.get("status")   # values 是 dict，可以用 .get()
cp.tasks                  # list of pending tasks
```

### 坑 2：as_node 参数的 bug

**现象**：`update_state` 后 `invoke(None)` 返回的不是决策结果

**原因**：`as_node` 在新版 LangGraph 中有 bug，会阻止决策节点重新执行

```python
# ❌ 错误（网上教程常见）
app.update_state(config, {"approved": True}, as_node="approve_refund")

# ✅ 正确
app.update_state(config, {"approved": True})
```

### 坑 3：Time Travel 不生效

**现象**：`update_state` 修改字段后，节点不重跑，结果不变

**原因**：`update_state` 只 patch 当前 state，不会重跑已执行过的节点

**解决**：从目标 checkpoint **fork 新 thread**，在新 thread 上注入状态后继续

---

## 📊 八、Checkpointer 选型指南

| 方案 | 适用场景 | 特点 |
|------|---------|------|
| **MemorySaver** | 开发/测试 | 内存存储，重启丢失，但速度快 |
| **SqliteSaver** | 小型生产 | 本地文件持久化，单进程 |
| **PostgresSaver** | 中大型生产 | 支持并发，真正的持久化 |
| **RedisSaver** | 高吞吐场景 | 内存数据库，可集群 |

---

## 🔑 九、API 速查表

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 1. 构建带持久化的 Graph
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["node_name"],  # 可选
)

# 2. 运行（带 thread_id）
config = {"configurable": {"thread_id": "session-001"}}
result = app.invoke({"user_input": "你好", "messages": []}, config)

# 3. 查看当前状态
current = app.get_state(config)
print(current.next)      # tuple: 下一个待执行节点
print(current.values)    # dict: 当前完整状态
print(current.tasks)     # list: 待执行任务

# 4. 查看历史
history = list(app.get_state_history(config))
for cp in history:
    print(cp.values, cp.next)

# 5. 人工决策（interrupt 场景）
app.update_state(config, {"approved": True})   # 直接 patch，不用 as_node
result = app.invoke(None, config)              # None = 从断点继续

# 6. Time Travel（Fork）
target_cp = next(cp for cp in history if cp.values.get("status") == "target")
fork_config = {"configurable": {"thread_id": "fork-001"}}
app.update_state(fork_config, {**target_cp.values, "field": "new_value"})
result = app.invoke(None, fork_config)
```

---

## 📝 十、与 Week 1 的对比

| 维度 | Week 1 (无持久化) | Week 2 (有持久化) |
|------|-------------------|-------------------|
| 多轮对话 | ❌ 不支持 | ✅ thread_id + MemorySaver |
| 人工审核 | ❌ 一次性跑完 | ✅ interrupt + update_state |
| 状态回滚 | ❌ 不可逆 | ✅ get_state_history + fork |
| 生产就绪 | ❌ 仅演示 | ✅ PostgresSaver 即可上线 |
| 调试能力 | 只能看最终输出 | 查看每个 checkpoint |

---

> 💡 **记住**：Week 2 的核心就一句话 — **让 Graph 能记住、能暂停、能回滚**。这三个能力加起来，就把 LangGraph 从"一次性脚本工具"变成了"生产级流程引擎"。
