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

### Day 17-18: Token Usage 日志 ⬜ 待进行

**目标**: 记录并分析 10 次调用的 token 消耗

**任务**:
1. 读取 usage 数据（prompt_tokens, completion_tokens, total_tokens）
2. 创建 `usage_log.csv`
3. 记录 10 个问题的 token 消耗
4. 分析哪个问题最费 token

**输出文件**:
- `results/usage_log.csv`

---

### Day 19-20: 错误样本集 ⬜ 待进行

**目标**: 收集 10 条典型错误案例并分类

**任务**:
1. 从测试中找出 10 个错误
2. 分类：prompt 问题 / schema 问题 / 其他
3. 编写 `docs/error_cases.md`
4. 每个错误加原因分析和修复方案

**输出文件**:
- `docs/error_cases.md`

---

### Day 21-22: 优化 Instructions 和 Schema ⬜ 待进行

**目标**: 针对性优化，提升准确率

**任务**:
1. 只改 instructions（不改 tool），测试 10 条
2. 只改 schema（不改 instructions），测试 10 条
3. 对比优化前后的准确率差异
4. 记录优化技巧

**输出文件**:
- `docs/optimization_log.md`

---

### Day 23: 创建 Mini Eval ⬜ 待进行

**目标**: 建立可重复使用的评测表

**任务**:
1. 设计 `eval/mini_eval.csv` 格式
2. 编写 20 个问题（覆盖 4 类意图）
3. 运行评测，统计 pass/fail
4. 计算准确率（目标 > 80%）

**输出文件**:
- `eval/mini_eval.csv`

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

**总用时**: 预计 7.5 小时 | 实际：__h

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

**下一步**: 继续 Day 17-18: Token Usage 日志分析
