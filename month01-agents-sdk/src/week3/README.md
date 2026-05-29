# 📚 第 1 月 - Week 3：调试与优化

**日期**: 2026-04-20 至 2026-04-26

**主题**: 从「会用」到「用好」—— 建立系统化的 Agent 调试与优化能力

---

## 🎯 周目标（3 个核心）

1. [ ] **建立错误样本集**: 收集 10 条典型错误案例
2. [ ] **优化 instructions**: 降低误调率到 < 20%
3. [ ] **创建 mini eval**: 建立可重复使用的评测表

---

## 📁 目录结构

```
week3/
├── README.md                          # 本周学习说明（本文件）
├── day15_16_consistency_test.py       # Day 15-16: 连续性测试脚本
├── run_test.sh                        # 测试运行脚本
├── results/                           # 测试结果输出目录
│   ├── consistency_run_*.csv          # 5 次运行详细结果
│   └── consistency_analysis_*.md      # 一致性分析报告
├── day17_18_token_usage.py            # Day 17-18: Token Usage 日志（待创建）
├── day19_20_error_cases.py            # Day 19-20: 错误样本集（待创建）
├── day21_22_optimization.py           # Day 21-22: Instructions 优化（待创建）
└── eval/
    └── mini_eval.csv                  # Day 23: Mini Eval 评测表（待创建）
```

---

## 📋 每日任务清单

### Day 15-16: 连续测试与对比 ✅ 已完成

**目标**: 用同样的 10 个问题连续跑 5 次，对比输出一致性

**测试结果**:
- 一致率：**70%** (7/10)
- 不一致问题：3 个（订单查询、物流查询、优惠券查询）
- 根本原因：检测逻辑不完善，实际 Agent 行为可能更稳定

**输出文件**:
- `results/consistency_run_20260420_123654.csv`
- `results/consistency_analysis_20260420_123654.md`

**关键发现**:
> 不能仅凭输出文本判断 tool 调用，需要分析 trace 数据！

---

### Day 17-18: Token Usage 日志 ✅ 已完成

**核心文件**: `day17_18_token_usage.py`

**测试结果** (输出: `results/usage_analysis_20260423_142325.md`):

| 指标 | 数值 |
|------|------|
| 总 Prompt Tokens | 25,495 |
| 总 Completion Tokens | 3,114 |
| 总消耗 | 28,609 |
| 平均每题 | 2,861 tokens |

**最费 Token**: 物流查询 (3,168 tokens) — 因为物流轨迹输出较长
**最省 Token**: 退款条件 (1,534 tokens) — 直接回复，无需 Tool

**关键发现**:
- Completion/Prompt Ratio 全部 < 0.25，说明回复相对简洁
- 物流和退款申请的 completion 最高（340+ tokens），需要 Tool 输出格式化数据
- Instructions 精简空间有限（~2,600 tokens 基线）

---

### Day 19-20: 错误样本集 ✅ 部分完成

**核心文件**: `docs/error_cases.md`

**已收集案例**: 1 个（检测逻辑缺陷）

**核心发现**: 一致性测试 70% 一致率，但实际 Agent 行为更稳定。
- 问题：`extract_tool()` 只匹配简单关键词，无法识别格式化变化
- 3 个不一致问题：订单查询、退款条件、投诉转人工
- **根因**: 检测代码不完善，不是 Agent 本身不稳定
- **教训**: 不能仅凭输出文本判断 tool 调用，需要分析 trace 数据

> ⚠️ 未完成：原计划收集 10 条真实错误案例，因 Day 19-23 整体跳过未继续。

---

### Day 21-22: 优化 Instructions 和 Schema ⬜ 已跳过

> 进入第 2 月后决定跳过剩余 Week 3 任务。核心教训（检测逻辑需依赖 trace）已在 MEMORY.md 中沉淀。

---

### Day 23: 创建 Mini Eval ⬜ 已跳过

> LangGraph（Month 2）的 graph 模式天生具备显式流程控制，Month 1 的一致性率问题在 graph 模式下可避免。

---

## 💡 关键认知（本周要理解）

1. **哪些错误是 prompt 问题？哪些是 schema 问题？**
   - prompt 问题：agent 不理解该不该调用 tool
   - schema 问题：agent 选对了 tool 但参数错了

2. **如何系统性地优化 agent 性能？**
   - 收集错误 → 分类 → 针对性优化 → 再测试

3. **为什么需要 eval？**
   - 避免"感觉变好了"，用数据说话
   - 防止优化 A 导致 B 变差

---

## 📊 进度追踪

| 时间段 | 任务 | 状态 | 用时 |
|--------|------|------|------|
| Day 15-16 | 连续测试与对比 | ✅ 已完成 | 6 分钟 |
| Day 17-18 | Token Usage 日志 | ⬜ 待进行 | __h |
| Day 19-20 | 错误样本集 | ⬜ 待进行 | __h |
| Day 21-22 | 优化 Instructions/Schema | ⬜ 待进行 | __h |
| Day 23 | Mini Eval | ⬜ 待进行 | __h |

**总用时**: 预计 7.5 小时 | 实际：~1h（仅完成 Day 15-18，Day 19-23 跳过）

---

## 🚀 快速开始

```bash
# 运行 Day 15-16 一致性测试
cd /Users/liyang/dev/python_project/ly-ai-roadmap-lab
./month01-agents-sdk/src/week3/run_test.sh

# 查看测试结果
open month01-agents-sdk/src/week3/results/
```

---

## 📝 学习笔记

在 `notes/` 目录下记录你的学习心得和遇到的问题。

---

**下一步**: 进入 Month 2（LangGraph），学习 Graph API 的 StateGraph 和条件路由
