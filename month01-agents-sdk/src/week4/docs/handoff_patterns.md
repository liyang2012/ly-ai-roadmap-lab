# Handoff 模式总结

## Handoff 是什么？

Handoff 是 OpenAI Agents SDK 中实现**多 Agent 协作**的核心机制。
通过 Handoff，一个 Agent 可以将对话控制权交给另一个更专业的 Agent。

## 基本用法

```python
from agents import Agent, handoff

# 定义子 Agent
support_agent = Agent(
    name="Support Agent",
    instructions="You handle customer support queries.",
)

# 在主 Agent 中注册 handoff
router_agent = Agent(
    name="Router Agent",
    instructions="Route queries to the appropriate specialist.",
    handoffs=[handoff(support_agent)],
)
```

## Handoff vs Tool 的区别

| 维度 | Tool 调用 | Handoff |
|------|----------|---------|
| 控制权 | Agent 保留 | 转移给另一个 Agent |
| 适用场景 | 简单函数调用 | 复杂任务、专业领域 |
| 上下文 | 作为参数传递 | 完整对话历史传递 |
| 返回 | 返回值给原 Agent | 可以直接回复用户 |

## 常见模式

1. **路由模式**: 一个 Router Agent 根据意图分发到多个专业 Agent
2. **流水线模式**: Agent A → Agent B → Agent C 顺序处理
3. **监督模式**: 主 Agent 分配任务给子 Agent，汇总结果

## 注意事项

- Handoff 后原 Agent 的 instructions 不再生效
- 上下文传递需要显式指定（on_handoff 参数）
- 多 Agent 场景下调试更复杂，建议用 Tracing
