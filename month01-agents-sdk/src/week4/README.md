# 📚 第 1 月 - Week 4：多 Agent 协作与综合实战

**日期**: 2026-05-05 至 2026-05-11

**主题**: 从「单兵作战」到「团队协作」—— 掌握多 Agent 编排模式，完成综合实战项目

---

## 🎯 周目标（3 个核心）

1. [ ] **掌握 Handoff 模式**: 多 Agent 协作的工作流程
2. [ ] **理解 Agent 生命周期**: 状态管理、上下文传递、错误恢复
3. [ ] **完成综合实战**: 用多个 Agent 协作完成一个实际场景

---

## 📁 目录结构

```
week4/
├── README.md                          # 本周学习说明（本文件）
├── docs/
│   ├── handoff_patterns.md            # Handoff 模式总结
│   └── multi_agent_design.md          # 多 Agent 设计原则
├── src/
│   ├── simple_handoff.py              # Day 24-25: 简单 Handoff 示例
│   ├── multi_agent_collab.py          # Day 26-27: 多 Agent 协作
│   └── capstone_project.py            # Day 28-30: 综合实战项目
├── results/                           # 运行结果输出目录
└── eval/
    └── multi_agent_eval.csv           # 多 Agent 场景评测表
```

---

## 📋 每日任务清单

### Day 24-25: 简单 Handoff 示例 ✅ 待进行

**目标**: 理解 Agent 之间的手动交接模式

**任务**:
1. 创建两个 Agent：一个负责意图识别，一个负责具体执行
2. 使用 `handoff()` 实现 Agent 间的任务交接
3. 验证上下文（context）能否正确传递
4. 记录 Handoff 的触发条件和注意事项

**输出文件**:
- `src/simple_handoff.py`
- `docs/handoff_patterns.md`

---

### Day 26-27: 多 Agent 协作 ✅ 待进行

**目标**: 构建多个 Agent 协同工作的场景

**任务**:
1. 设计一个多 Agent 场景（如：旅行规划助手）
   - Agent A: 意图分析 & 路由
   - Agent B: 机票查询
   - Agent C: 酒店推荐
   - Agent D: 行程汇总
2. 实现 Agent 之间的数据传递
3. 处理异常情况（某个 Agent 失败怎么办）
4. 对比单 Agent vs 多 Agent 的优劣

**输出文件**:
- `src/multi_agent_collab.py`
- `docs/multi_agent_design.md`

---

### Day 28-30: 综合实战项目 ✅ 待进行

**目标**: 用所学构建一个完整的实际应用

**任务**:
1. 选择实战场景（建议：个人知识管理助手）
2. 设计 Agent 架构（至少 3 个 Agent）
3. 实现 Tool 定义、Handoff、Guardrails
4. 编写测试用例
5. 运行评测，记录性能指标

**输出文件**:
- `src/capstone_project.py`
- `eval/multi_agent_eval.csv`

---

## 💡 关键认知（本周要理解）

1. **什么时候用单 Agent，什么时候用多 Agent？**
   - 单 Agent：简单场景、低成本、快速迭代
   - 多 Agent：复杂场景、职责分离、可复用

2. **Handoff vs Tool 调用的区别？**
   - Tool 调用：Agent 调用函数，控制权不转移
   - Handoff：Agent 把控制权交给另一个 Agent

3. **如何设计 Agent 的边界？**
   - 按领域划分（如：客服 Agent / 技术 Agent）
   - 按能力划分（如：检索 Agent / 生成 Agent）
   - 按阶段划分（如：分析 Agent / 执行 Agent）

---

## 📊 进度追踪

| 时间段 | 任务 | 状态 | 用时 |
|--------|------|------|------|
| Day 24-25 | 简单 Handoff 示例 | ⬜ 待进行 | __h |
| Day 26-27 | 多 Agent 协作 | ⬜ 待进行 | __h |
| Day 28-30 | 综合实战项目 | ⬜ 待进行 | __h |

**总用时**: 预计 8 小时 | 实际：__h

---

## 🚀 前置知识

- 已完成 Week 1-3 的学习
- 理解 Tool 的定义和使用
- 理解 Run Loop 的执行流程
- 了解基本的调试和优化方法

---

## 📝 学习笔记

在 `docs/` 目录下记录你的学习心得和遇到的问题。

---

**下一步**: 开始 Day 24-25: 简单 Handoff 示例
