# LangGraph Week 2 学习笔记：Persistence / Checkpoints / Human-in-the-Loop

> **Day 1 (2026-05-18)**: 创建 3 个 demo 文件
> **Day 2 (2026-05-22)**: 修复所有 API 兼容性 bug，三个文件全部跑通 ✅

## 核心知识点

### 1. MemorySaver — 让 Graph "有记忆"

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

**关键变化**：
- 没有 checkpointer：每次 invoke 都是独立运行，无状态
- 有 checkpointer：通过 thread_id 关联多次 invoke，实现多轮对话

```python
config = {"configurable": {"thread_id": "user-001"}}

# 第 1 轮
app.invoke({"user_input": "你好"}, config)

# 第 2 轮（同一个 thread_id，Graph "记得" 上一轮）
app.invoke({"user_input": "查订单 ORD123"}, config)
```

### 2. Thread ID — 会话隔离

每个 thread_id 是独立的会话空间：

| thread_id | 用途 |
|-----------|------|
| `user-alice-001` | Alice 的对话 |
| `user-bob-002` | Bob 的对话 |
| `refund-approval-003` | 某个退款审批流程 |

不同 thread_id 之间互不干扰，各自有自己的 checkpoint 序列。

### 3. Checkpoint 机制

**什么时候创建 checkpoint？**
- 每个节点执行前后（取决于 interrupt 配置）
- 每次状态变更后

**查看历史**：
```python
history = list(app.get_state_history(config))
# 返回从最新到最旧的 checkpoint 列表
```

**每个 checkpoint 包含**：
- checkpoint_id（唯一标识）
- values（当时的完整 state）
- next（下一个待执行节点）

### 4. Human-in-the-Loop — 人工审核

**两种中断方式**：

| 方式 | 语法 | 场景 |
|------|------|------|
| interrupt_before | `interrupt_before=["node_name"]` | 在节点执行前暂停，人工注入决策 |
| interrupt_after | `interrupt_after=["node_name"]` | 在节点执行后暂停，人工检查结果 |

**人工操作流程**：

```python
# 1. invoke 会停在 interrupt 点
result = app.invoke(state, config)

# 2. 查看当前状态（StateSnapshot 是 NamedTuple，用属性访问）
current = app.get_state(config)
print(current.next)  # tuple，如 ('approve_refund',)

# 3. 人工注入决策 — 直接 patch state，不要用 as_node
app.update_state(config, {"approved": True})

# 4. 从断点继续
result = app.invoke(None, config)  # None 表示从当前 checkpoint 继续
```

> ⚠️ **API 兼容性注意 (2026-05-22 踩坑)**：
> - `StateSnapshot` 是 `NamedTuple`，**不能用 `.get()`**：
>   - ❌ `current.get("next", [])` → ✅ `current.next`
>   - ❌ `cp["values"]` → ✅ `cp.values`
> - `update_state` **不要用 `as_node`**（新版本的 bug）：
>   - ❌ `app.update_state(config, {"approved": True}, as_node="approve_refund")`
>   - ✅ `app.update_state(config, {"approved": True})`
>   - 原因：`as_node` 会阻止决策节点重新执行，导致状态已更新但节点逻辑没触发

### 5. Time Travel — 时间旅行

**场景 1：Fork 从历史 checkpoint 创建新分支**

单纯 `update_state` 只 patch 当前 state，不会重跑已执行过的节点。
正确的 Time Travel 方式是从目标 checkpoint fork 一个新 thread：

```python
# 1. 找到目标 checkpoint（如刚计算完总价、还没应用折扣）
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

**场景 2：Fork 分支探索**
```python
# 从同一初始状态，创建不同 thread_id 的分支
for method in ["standard", "express", "overnight"]:
    thread = f"order-{method}"
    config = {"configurable": {"thread_id": thread}}
    result = app.invoke(initial_state, config)
```

### 6. 多步骤审批流架构

Week 2 实战的审批流程图：

```
create_request
    ↓
manager_review
    ↓
⏸️ interrupt_before["manager_decision"]
    ↓
manager_decision ──[reject]──→ notify_result → END
    ↓[approve]
finance_review
    ↓
⏸️ interrupt_before["finance_decision"]
    ↓
finance_decision ──[reject]──→ notify_result → END
    ↓[approve]
notify_result → END
```

## 生产环境建议

### Checkpointer 选型

| 方案 | 适用场景 | 备注 |
|------|----------|------|
| MemorySaver | 开发/测试 | 内存存储，重启丢失 |
| SqliteSaver | 小型生产 | 本地文件，单进程 |
| PostgresSaver | 中大型生产 | 支持并发，持久化 |
| RedisSaver | 高吞吐场景 | 内存数据库，可集群 |

### 最佳实践

1. **Thread ID 命名规范**：`{业务类型}-{用户/实体}-{序号}`
2. **最小化 State**：只存必要字段，减少 checkpoint 大小
3. **interrupt_before vs interrupt_after**：
   - 需要人工**决策**：用 interrupt_before（决策后再执行）
   - 需要人工**检查结果**：用 interrupt_after（执行完再审核）
4. **错误处理**：update_state 注入前验证数据格式
5. **审计日志**：把每次人工操作记录到 state.notes 中

## 与 Week 1 的对比

| 维度 | Week 1 (无持久化) | Week 2 (有持久化) |
|------|-------------------|-------------------|
| 多轮对话 | ❌ 不支持 | ✅ thread_id + MemorySaver |
| 人工审核 | ❌ 一次性跑完 | ✅ interrupt + update_state |
| 状态回滚 | ❌ 不可逆 | ✅ get_state_history + fork |
| 生产就绪 | ❌ 仅演示 | ✅ PostgresSaver 即可上线 |
| 调试能力 | 看最终输出 | 查看每个 checkpoint |

## 关键 API 速查

```python
# 编译
app = graph.compile(checkpointer=MemorySaver(), interrupt_before=["node_name"])

# 运行
result = app.invoke(state, {"configurable": {"thread_id": "xxx"}})

# 查看状态（NamedTuple，属性访问）
current = app.get_state(config)
print(current.next)      # tuple of next node names
print(current.values)    # dict of current state
print(current.tasks)     # list of pending tasks

# 查看历史
history = list(app.get_state_history(config))
for cp in history:
    print(cp.values, cp.next)

# 注入人工决策 — 直接 patch，不用 as_node
app.update_state(config, {"approved": True})

# 从断点继续
result = app.invoke(None, config)

# Fork: 从历史 checkpoint 创建新分支
calc_cp = next(cp for cp in history if cp.values.get("status") == "calculated")
fork_config = {"configurable": {"thread_id": "fork-001"}}
app.update_state(fork_config, {**calc_cp.values, "field": "new_value"})
result = app.invoke(None, fork_config)
```
