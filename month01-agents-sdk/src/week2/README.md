# 📚 第 1 月 - Week 2：Tool 与结构化

**日期**: 2026-04-10 至 2026-04-17

**主题**: 从单一 Tool 到多 Tool 协作，掌握结构化输出、Guardrails 安全边界、Tracing 调试

---

## 🎯 周目标（4 个核心）

1. [x] **多 Tool 协作**: 设计 7 个业务 Tool，理解优先级和路由
2. [x] **结构化输出**: 用 Pydantic 模型定义 Agent 返回格式
3. [x] **Guardrails**: 输入/输出安全边界控制
4. [x] **Tracing 调试**: 追踪 Agent 执行流程，定位性能瓶颈

---

## 📁 目录结构

```
week2/
├── README.md                          # 本周学习说明（本文件）
├── ecommerce_support_agent.py         # Day 11-12: 电商客服 Agent 实战（7 个 Tool）
├── structured_output.py               # Day 13: 结构化输出（Pydantic 模型）
├── guardrails_example.py              # Day 14: 输入/输出安全边界
├── tracing_debug_example.py           # Day 14: Tracing 调试
├── handoff_example.py                 # Day 12: Handoff 基础示例
└── multi_tool_agent.py                # Day 11: 多 Tool 设计原型
```

---

## 📋 每日任务清单

### Day 11-12: 电商客服 Agent 实战 ✅ 已完成

**核心文件**: `ecommerce_support_agent.py`

**7 个业务 Tool**:

| Tool 名称 | 功能 | 参数 |
|-----------|------|------|
| `query_order_status` | 查询订单状态和物流 | order_id |
| `query_refund_policy` | 查询退款政策 | order_status |
| `process_refund_apply` | 提交退款申请 | order_id, reason |
| `query_logistics` | 查询物流轨迹 | logistics_no |
| `query_coupons` | 查询用户优惠券 | user_id |
| `query_product_info` | 产品咨询（保修/特性） | product_name |
| `escalate_to_human` | 转接人工客服 | issue_type, summary |

**关键设计决策**:
1. **模拟数据库** — 用 Python dict 模拟 ORDERS_DB、REFUND_RULES、COUPONS_DB、PRODUCT_KB
2. **模糊匹配** — 退款政策和产品查询支持关键词模糊匹配
3. **参数校验** — 缺少必要参数时（如订单号），Agent 先询问而非直接调用
4. **阿里云百炼** — 使用 `qwen3.5-plus` 模型，通过 `OpenAIChatCompletionsModel` 兼容接口接入
5. **交互 + 测试双模式** — 支持命令行交互和 `--test` 批量测试

**Instructions 设计要点**:
- 明确的工具选择指南（什么场景调用哪个 Tool）
- 回复规范（emoji 使用、参数缺失处理、边界情况）
- 职责边界定义（不能处理的转人工）

---

### Day 13: 结构化输出 ✅ 已完成

**核心文件**: `structured_output.py`

**核心概念**: 自由文本适合人类阅读，但结构化输出（JSON/Pydantic 模型）适合程序化处理。

**3 个场景**:

1. **单个订单查询** — `Order` 模型（含 OrderStatus 枚举）
2. **订单列表** — `OrderListResponse` 模型（嵌套 `OrderSummary` 列表）
3. **销售统计报告** — `SalesStatistics` 模型（聚合计算）

**Pydantic 的优势**:
- 类型注解 → IDE 自动补全
- 字段描述 → 作为 Agent instructions 的一部分
- 自动验证 → 数据类型和格式检查
- 序列化 → `.model_dump()` 直接转 JSON

**关键认知**:
> Instructions 中必须强调"始终返回纯 JSON 格式"，否则 Agent 可能混入解释性文字。

---

### Day 14: Guardrails 安全边界 ✅ 已完成

**核心文件**: `guardrails_example.py`

**Guardrails 的作用**: 在 Agent 处理用户输入和输出之前，添加验证和过滤层。

**4 种 Guardrail**:

| 类型 | 作用 | 示例 |
|------|------|------|
| **Input Guardrail** | 验证用户输入合法性 | 长度限制、敏感词过滤 |
| **Output Guardrail** | 验证 Agent 输出安全 | 不泄露内部信息、格式校验 |
| **Tool Guardrail** | 验证 Tool 调用参数 | 订单号格式校验、参数范围 |
| **Prompt Injection** | 防御提示词注入 | 检测"忽略之前的指令"等攻击 |

**设计模式**:
```python
@input_guardrail
def check_input_length(ctx, input):
    if len(input) > 500:
        return GuardrailFunctionOutput(
            output_info="输入过长",
            tripwire_triggered=True
        )
    return GuardrailFunctionOutput(output_info="OK", tripwire_triggered=False)
```

---

### Day 14: Tracing 调试 ✅ 已完成

**核心文件**: `tracing_debug_example.py`

**Tracing 核心概念**:
- **Trace** = 完整工作流（如"订单查询"）
- **Span** = 工作流中的单个操作（如"调用 LLM"、"执行 Tool"）
- **Trace Tree** = Span 的层级关系（父子结构）

**4 个调试场景**:
1. 基础 Tracing — 单订单查询工作流
2. 多步骤工作流 — 订单 + 物流组合查询
3. 错误调试 — 模拟数据库异常、订单不存在
4. 性能分析 — 识别最慢的 Span（Tool 延迟 vs LLM 调用）

**最佳实践**:
- 开发阶段始终启用 Tracing
- 用 `group_id` 关联相关 Trace
- 生产环境采样记录（如 10% 请求）
- 注意隐私：避免记录敏感数据

---

## 💡 关键认知（本周要理解）

1. **多 Tool 设计的核心不是数量，而是职责边界清晰**
   - 每个 Tool 只做一件事，参数明确
   - Instructions 中必须说明"什么场景用什么 Tool"

2. **结构化输出是 Agent 走向生产化的关键一步**
   - 自由文本 → 只能给人看
   - Pydantic 模型 → 可以对接 API、数据库、下游 Agent

3. **Guardrails 是安全网，不是装饰**
   - 没有 Guardrails 的 Agent 就像没有输入验证的 Web 服务
   - 必须在开发早期就设计，不能事后补

4. **Tracing 是 Agent 开发最重要的调试工具**
   - Agent 的决策过程不透明，Tracing 是唯一的"窗口"
   - Week 3 的一致性测试就依赖 Tracing 数据分析

5. **百炼（DashScope）兼容方案**
   - `set_use_responses_by_default(False)` 禁用 Responses API
   - 用 `OpenAIChatCompletionsModel` + `AsyncOpenAI` 客户端
   - `base_url="https://coding.dashscope.aliyuncs.com/v1"`

---

## 📊 进度追踪

| 时间段 | 任务 | 状态 | 用时 |
|--------|------|------|------|
| Day 11-12 | 电商客服 Agent（7 Tool） | ✅ 已完成 | ~3h |
| Day 13 | 结构化输出（Pydantic） | ✅ 已完成 | ~1.5h |
| Day 14 | Guardrails + Tracing | ✅ 已完成 | ~2h |

**总用时**: 预计 7 小时 | 实际：~6.5h

---

## 🚀 前置知识

- 已完成 Week 1（Hello Agent、Run Loop、基础 Tool 调用）
- 理解 `Agent`、`Runner`、`function_tool` 的基本用法
- 安装了 `openai-agents` SDK

---

## 🔗 后续学习

- **Week 3**: 基于 Week 2 的代码进行一致性测试、Token 分析、错误优化
- **Week 4**: 多 Agent 协作（Handoff 模式、旅行规划、知识管理助手）
- **Month 2**: LangGraph — 用 Graph 思维替代 Agent 脚本思维
