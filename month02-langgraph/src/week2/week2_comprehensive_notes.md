# 📚 第 2 月 - Week 2：Persistence / Checkpoints / Human-in-the-Loop

> 学习日期：2026-05-18 至 2026-05-22
> 代码位置：`month02-langgraph/src/week2/`
> 状态：3 个 demo 文件全部跑通 ✅

---

## 一、Week 1 → Week 2：为什么需要持久化？

### 回顾 Week 1 的问题

Week 1 写的 graph，每次调用 `app.invoke(state)` 都是**独立的一次性运行**：

```python
# 第 1 次调用
app.invoke({"user_input": "你好"})  # → "你好！我是客服"

# 第 2 次调用
app.invoke({"user_input": "查订单 ORD123"})  # → ❌ Graph 不记得第 1 次
```

**这就像一个失忆的人**：每次跟你说完话就忘了你是谁。

### Week 2 解决三个问题

| 问题 | 场景 | Week 2 方案 |
|------|------|------------|
| 失忆 | 用户连续对话，Graph 记不住上下文 | MemorySaver + Thread ID |
| 无法暂停 | 退款需要人工审批，但 graph 一口气跑完 | interrupt_before |
| 无法回滚 | 执行错了想回到之前的状态 | get_state_history + Fork |

---

## 二、MemorySaver：让 Graph "有记忆"

### 2.1 一句话理解

> MemorySaver 就是给 Graph 装了个**笔记本**，每次执行完都记录当前状态。下次用同一个 thread_id 调用时，能"翻看笔记本"继续对话。

### 2.2 对比：有 vs 没有

**❌ 没有 checkpointer（失忆模式）**：
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ChatState(TypedDict):
    messages: list[str]
    last_response: str

graph = StateGraph(ChatState)
graph.add_node("reply", lambda s: {"last_response": f"回复: {s['messages'][-1]}"})
graph.set_entry_point("reply")
graph.add_edge("reply", END)

app = graph.compile()  # ← 没有 checkpointer

# 第 1 轮
r1 = app.invoke({"messages": ["你好"], "last_response": ""})
print(r1["last_response"])  # → "回复: 你好"

# 第 2 轮（新调用，Graph 完全不知道第 1 轮）
r2 = app.invoke({"messages": ["你刚才说了啥？"], "last_response": ""})
# ↑ messages 里没有 "你好"，Graph 失忆了
```

**✅ 有 checkpointer（有记忆模式）**：
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()  # ← 创建笔记本

# 关键：编译时传入 checkpointer
app = graph.compile(checkpointer=checkpointer)

# 关键：每次调用传入 thread_id（会话标识）
config = {"configurable": {"thread_id": "user-alice-001"}}

# 第 1 轮
r1 = app.invoke({"messages": ["你好"], "last_response": ""}, config)
print(r1["last_response"])  # → "回复: 你好"

# 第 2 轮（同一个 thread_id，Graph "记得" 第 1 轮！）
r2 = app.invoke({"messages": ["你刚才说了啥？"], "last_response": ""}, config)
# ↑ checkpoint 里有上一轮的 messages，Graph 能接着聊
```

### 2.3 三个关键代码行

```python
# 1. 创建 checkpointer
checkpointer = MemorySaver()

# 2. 编译时传入
app = graph.compile(checkpointer=checkpointer)

# 3. 调用时带 thread_id
config = {"configurable": {"thread_id": "会话标识"}}
result = app.invoke(state, config)
```

**缺一不可**。少一行，Graph 就失忆。

### 2.4 实际运行效果

`checkpoint_demo.py` 中的 demo_1 运行结果：

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

messages 列表自动累积，不用手动拼接！

---

## 三、Thread ID：会话隔离

### 3.1 一句话理解

> thread_id 就是**聊天室编号**。不同 thread_id = 不同聊天室，互不干扰。

### 3.2 类比理解

想象一家咖啡店：
- thread_id = 桌号（1号桌、2号桌...）
- MemorySaver = 服务员的小本子
- 每个桌的点单记录独立存在本子上

```python
config_alice = {"configurable": {"thread_id": "user-alice-001"}}
config_bob = {"configurable": {"thread_id": "user-bob-002"}}

# Alice 查自己的订单
app.invoke({"user_input": "查我的订单"}, config_alice)
# → 返回 Alice 的订单信息

# Bob 查自己的订单（同一个 Graph，不同会话）
app.invoke({"user_input": "查我的订单"}, config_bob)
# → 返回 Bob 的订单信息

# 两边完全不串！
```

### 3.3 Thread ID 命名建议

```
{业务类型}-{用户/实体}-{序号}

user-alice-001          # 用户 Alice 的第 1 个会话
refund-approval-003     # 第 3 个退款审批流程
order-tracking-042      # 第 42 个订单跟踪
```

---

## 四、Checkpoint 机制：状态的"快照"

### 4.1 什么是 Checkpoint？

> 每个 checkpoint 就是 Graph 执行到某个时刻时，**完整状态的快照**。

就像游戏的存档点，随时可以读档回去。

### 4.2 什么时候创建 Checkpoint？

- 每个节点执行**前**后（取决于 interrupt 配置）
- 每次状态变更后

### 4.3 如何查看历史？

```python
history = list(app.get_state_history(config))

# history 是一个列表，从新到旧排列
for i, cp in enumerate(history):
    print(f"[{i}] next={cp.next} | values={cp.values}")
```

### 4.4 每个 Checkpoint 包含什么？

| 属性 | 类型 | 说明 |
|------|------|------|
| `cp.next` | tuple | 下一个待执行的节点名，如 `('order_query',)` |
| `cp.values` | dict | 当时的完整 state，如 `{'intent': 'greeting', 'response': '...'}` |
| `cp.config` | dict | 包含 checkpoint_id 的配置信息 |

> ⚠️ **重要**：`StateSnapshot` 是 `NamedTuple`，**必须用属性访问**（`cp.next`），**不能用字典方式**（`cp["next"]` ❌）

### 4.5 实际输出

`checkpoint_demo.py` 的 demo_2 运行结果：

```
--- 📋 所有 Checkpoint ---
  共 8 个 checkpoint
  [0] 1f155c60... | intent=order_query | response=📦 订单 ORD20260417003...
  [1] 1f155c60... | intent=order_query | response=👋 你好！...
  [2] 1f155c60... | intent=greeting | response=👋 你好！...
  [3] 1f155c60... | intent=greeting | response=👋 你好！...
  ...
  [7] 1f155c60... | intent=? | response=N/A...
```

8 个 checkpoint 记录了从初始状态到最终结果的完整执行轨迹。

---

## 五、Human-in-the-Loop：人工审核

### 5.1 一句话理解

> 让 Graph 在**关键步骤暂停**，等人类审批/决策后再继续。

### 5.2 为什么需要？

有些业务场景不能全自动：
- 退款审批 → 需要主管签字
- 大额转账 → 需要财务确认
- 内容发布 → 需要编辑审核

没有 Human-in-the-Loop，这些流程要么全自动化（不安全），要么绕开 Graph 做（复杂）。

### 5.3 两种中断方式

| 方式 | 语法 | 类比 | 场景 |
|------|------|------|------|
| `interrupt_before` | `interrupt_before=["approve_refund"]` | 在"批准"按钮**前**暂停 | 需要人工**决策** |
| `interrupt_after` | `interrupt_after=["process_payment"]` | 在"扣款"按钮**后**暂停 | 需要人工**检查结果** |

**90% 的场景用 `interrupt_before`**。

### 5.4 完整操作流程（4 步）

**步骤 1：Graph 编译时配置 interrupt**
```python
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["approve_refund"],  # ← 在这个节点前暂停
)
```

**步骤 2：第一次 invoke，Graph 会自动暂停**
```python
result = app.invoke({
    "user_input": "我要退款，订单 ORD20260417001",
    "approved": False,
}, config)

# result["response"] = "💰 退款审核请求... ⏸️ 等待人工审核..."
# Graph 停在了 approve_refund 之前
```

**步骤 3：查看暂停状态，人工注入决策**
```python
# 查看当前状态
current = app.get_state(config)
print(current.next)  # → ('approve_refund',) ← 下一个要执行的节点

# 人工决策：批准退款
app.update_state(config, {"approved": True})
# ↑ 注意：直接 patch state，不要用 as_node 参数！
```

**步骤 4：从断点继续**
```python
result = app.invoke(None, config)  # ← None 表示"从断点继续"
# result["response"] = "✅ 退款已批准，1-3 工作日到账。"
```

### 5.5 多步骤审批流实战（双审核）

`human_in_the_loop.py` 实现了一个完整的多步骤退款审批：

```
创建申请 → 等待主管审核 → 主管批准 → 等待财务审核 → 财务批准 → 退款完成
                                     ↓                    ↓
                                  主管拒绝              财务拒绝
                                     ↓                    ↓
                                 通知用户              通知用户
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

### 5.6 三种场景验证

| 场景 | 主管 | 财务 | 结果 |
|------|------|------|------|
| 完整通过 | ✅ | ✅ | refund_completed |
| 主管拒绝 | ❌ | 不执行 | rejected_by_manager |
| 财务拒绝 | ✅ | ❌ | rejected_by_finance |

实际运行结果：

```
🟢 场景 1：完整审批通过
  ✅ 主管审核通过
  ✅ 财务审核通过，退款 ¥7999.00 已执行
  📢 通知用户: 🎉 退款已完成...

🔴 场景 2：主管拒绝
  ❌ 主管审核拒绝
  📢 通知用户: 退款申请已被主管拒绝

🟡 场景 3：主管通过但财务拒绝
  ✅ 主管审核通过
  ❌ 财务审核拒绝
  📢 通知用户: 退款申请已被财务拒绝
```

### 5.7 ⚠️ 关键踩坑：as_node 参数的 bug

**错误写法**（网上教程和旧文档常见）：
```python
app.update_state(config, {"approved": True}, as_node="approve_refund")
# ❌ 决策节点不会重新执行，状态改了但逻辑没触发！
```

**正确写法**：
```python
app.update_state(config, {"approved": True})
# ✅ 直接 patch state，然后 invoke(None) 时下一个节点会读取到更新后的值
```

**原因**：新版 LangGraph 中，`as_node` 的行为有 bug，会导致状态已更新但决策节点的逻辑不会被触发。

---

## 六、Time Travel：时间旅行

### 6.1 一句话理解

> 回到 Graph 执行的某个历史状态，从那里用不同的输入重新执行。

### 6.2 类比

就像游戏的"存档/读档"：
1. 玩到某个位置 → 自动存档（checkpoint）
2. 发现选错分支 → 查看存档列表
3. 加载某个存档 → 从那里重新玩

### 6.3 场景：修改折扣码后重新计算

**问题**：用户下单时折扣码填错了（INVALID → 无折扣），想改成 SAVE10 重新算。

**❌ 错误做法**：直接在当前 thread 上 update_state
```python
app.update_state(config, {"discount_code": "SAVE10"})
result = app.invoke(None, config)
# 问题：discount 节点已经执行过了，不会重跑
# 结果：总价还是没打折
```

**✅ 正确做法**：从历史 checkpoint fork 新 thread
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

### 6.4 场景：Fork 分支探索

同一初始状态，探索不同方案（配送方式对比）：

```python
for method in ["standard", "express", "overnight"]:
    thread = f"order-fork-{method}"
    config = {"configurable": {"thread_id": thread}}
    
    result = app.invoke(initial_state, config)
    app.update_state(config, {})
    final = app.invoke(None, config)
    
    print(f"{method}: ¥{final['total']:.2f}")
```

结果：
```
standard  : ¥7,599.20 (基准)
express   : ¥7,614.20 (+¥15.00)
overnight : ¥7,629.20 (+¥30.00)
```

---

## 七、三大核心知识点总结

| 知识点 | 一句话 | 核心代码 |
|--------|--------|----------|
| MemorySaver | 给 Graph 装笔记本 | `graph.compile(checkpointer=MemorySaver())` |
| Thread ID | 聊天室编号隔离 | `{"configurable": {"thread_id": "xxx"}}` |
| Checkpoint | 状态快照/游戏存档 | `app.get_state_history(config)` |
| Interrupt | 关键步骤暂停等人工 | `interrupt_before=["node_name"]` |
| Time Travel | 读档重新玩 | fork 新 thread + `update_state` |

---

## 八、生产环境建议

### 8.1 Checkpointer 选型

| 方案 | 适用场景 | 备注 |
|------|----------|------|
| **MemorySaver** | 开发/测试 | 内存存储，重启丢失 |
| **SqliteSaver** | 小型生产 | 本地文件，单进程 |
| **PostgresSaver** | 中大型生产 | 支持并发，持久化 ⭐推荐 |
| **RedisSaver** | 高吞吐场景 | 内存数据库，可集群 |

### 8.2 最佳实践

1. **Thread ID 命名规范**：`{业务类型}-{用户/实体}-{序号}`
2. **最小化 State**：只存必要字段，减少 checkpoint 大小
3. **interrupt_before vs interrupt_after**：
   - 需要人工**决策** → `interrupt_before`（决策后再执行）
   - 需要人工**检查结果** → `interrupt_after`（执行完再审核）
4. **错误处理**：`update_state` 注入前验证数据格式
5. **审计日志**：把每次人工操作记录到 `state.notes` 中

---

## 九、与 Week 1 的对比

| 维度 | Week 1 (无持久化) | Week 2 (有持久化) |
|------|-------------------|-------------------|
| 多轮对话 | ❌ 不支持 | ✅ thread_id + MemorySaver |
| 人工审核 | ❌ 一次性跑完 | ✅ interrupt + update_state |
| 状态回滚 | ❌ 不可逆 | ✅ get_state_history + fork |
| 生产就绪 | ❌ 仅演示 | ✅ PostgresSaver 即可上线 |
| 调试能力 | 看最终输出 | 查看每个 checkpoint |

---

## 十、完整 API 速查表

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

# ========== 1. 定义 State ==========
class MyState(TypedDict, total=False):
    user_input: str
    response: str
    approved: bool
    messages: list[str]

# ========== 2. 定义节点 ==========
def my_node(state: MyState) -> dict:
    return {"response": f"处理了: {state['user_input']}"}

# ========== 3. 构建 Graph（带持久化 + 中断） ==========
graph = StateGraph(MyState)
graph.add_node("my_node", my_node)
graph.set_entry_point("my_node")
graph.add_edge("my_node", END)

app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["my_node"],  # 可选：在某个节点前暂停
)

# ========== 4. 运行（带 thread_id） ==========
config = {"configurable": {"thread_id": "session-001"}}
result = app.invoke({"user_input": "你好", "messages": []}, config)

# ========== 5. 查看状态 ==========
current = app.get_state(config)
print(current.next)      # tuple: 下一个待执行节点
print(current.values)    # dict: 当前完整状态
print(current.tasks)     # list: 待执行任务

# ========== 6. 查看历史 ==========
history = list(app.get_state_history(config))
for cp in history:
    print(cp.values, cp.next)

# ========== 7. 人工决策（interrupt 场景） ==========
app.update_state(config, {"approved": True})  # ← 直接 patch，不用 as_node
result = app.invoke(None, config)  # ← None = 从断点继续

# ========== 8. Time Travel（Fork） ==========
target_cp = next(cp for cp in history if cp.values.get("status") == "target")
fork_config = {"configurable": {"thread_id": "fork-001"}}
app.update_state(fork_config, {**target_cp.values, "field": "new_value"})
result = app.invoke(None, fork_config)
```

---

## 十一、学习路径回顾

```
Week 1: Graph API 入门 ✅
  ├── Day 1-2: 简单线性 graph（3 节点）
  ├── Day 3-4: 客服 graph（8 节点 + 条件路由）
  └── Day 5-6: 测试优化 + 思维对比笔记

Week 2: Persistence / Checkpoints ✅
  ├── Day 1: MemorySaver + Thread ID + Time Travel 基础
  ├── Day 2: Human-in-the-Loop + 多步骤审批流
  └── Day 3: API 兼容性 bug 修复（3 个文件全通）

Week 3: Subgraph 与模块化 ⬜ 下一步
Week 4: Workflow vs Agent 选型对比 ⬜
```

---

## 十二、本周踩坑记录（重点！）

### 踩坑 1：StateSnapshot API 变化

**现象**：`current.get("next")` 报错 `AttributeError: 'StateSnapshot' object has no attribute 'get'`

**原因**：新版 LangGraph 中 `StateSnapshot` 从 dict-like 变成了 `NamedTuple`

**解决**：
```python
# ❌ 旧写法
current.get("next", [])
cp["values"].get("status")

# ✅ 新写法
current.next           # tuple
cp.values.get("status")  # values 是 dict，可以用 .get()
cp.tasks               # list of Task
```

### 踩坑 2：as_node 参数的坑

**现象**：`update_state` 后 `invoke(None)` 返回的不是决策结果，而是原状态

**原因**：`as_node` 在新版 LangGraph 中有 bug，会阻止决策节点重新执行

**解决**：
```python
# ❌ 错误（网上教程常见）
app.update_state(config, {"approved": True}, as_node="approve_refund")

# ✅ 正确
app.update_state(config, {"approved": True})
```

### 踩坑 3：Time Travel 不生效

**现象**：`update_state` 修改字段后，节点不重跑，结果不变

**原因**：`update_state` 只 patch 当前 state，不会重跑已执行过的节点

**解决**：从目标 checkpoint fork 新 thread，在新 thread 上注入状态后继续

---

> 📝 **写在最后**：Week 2 的核心就一句话 — **让 Graph 能记住、能暂停、能回滚**。
> 这三个能力加起来，就把 LangGraph 从"一次性脚本工具"变成了"生产级流程引擎"。
