# 多 Agent 设计原则

## 1. 职责单一原则

每个 Agent 应该专注于一个明确的领域或任务。

```
✅ 好：TravelAgent (只负责旅行规划)
❌ 差：EverythingAgent (什么都会，什么都不精)
```

## 2. 边界清晰原则

Agent 之间的交接条件应该明确且无歧义。

```python
# 清晰的边界
support_agent = Agent(
    instructions="Handle product returns and refunds only.",
)

tech_agent = Agent(
    instructions="Handle technical troubleshooting only.",
)
```

## 3. 上下文传递原则

Handoff 时，显式传递必要的上下文信息。

```python
def on_handoff(ctx):
    # 提取关键信息传递给下一个 Agent
    return {"order_id": ctx.order_id, "issue": ctx.issue}

handoff(support_agent, on_handoff=on_handoff)
```

## 4. 容错原则

设计时要考虑某个 Agent 失败时的降级策略。

- 超时处理
- 空结果处理
- 错误信息反馈

## 5. 可观测性原则

每个 Agent 应该有清晰的日志和 Tracing，便于调试。
