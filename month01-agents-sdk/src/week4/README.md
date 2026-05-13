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

### Day 26-27: 多 Agent 协作 ✅ 已完成

**目标**: 构建多个 Agent 协同工作的场景

**任务**:
1. 设计一个多 Agent 场景（旅行规划助手）
   - Agent A: 意图分析 & 路由
   - Agent B: 机票查询
   - Agent C: 酒店推荐
   - Agent D: 景点推荐
   - Agent E: 行程汇总
2. 实现 Agent 之间的数据传递
3. 处理异常情况（某个 Agent 失败怎么办）
4. 对比单 Agent vs 多 Agent 的优劣

**输出文件**:
- `src/multi_agent_collab.py`
- `docs/multi_agent_design.md`

**测试结果**:
- ✅ 测试 1：单 Agent 工作（2,845 tokens）
- ✅ 测试 2：Handoff 路由（3,290 tokens）
- ✅ 测试 3：多 Agent 协作（14,655 tokens）- 生成完整的 3 天旅行计划
- ✅ 测试 4：单 Agent vs 多 Agent对比

**关键发现**:
- 单 Agent：耗时 78.79 秒，6,063 tokens，1,657 字符
- 多 Agent：更专业的回答，更详细的规划，但消耗更多 tokens
- Handoff 模式适合意图明确的路由场景
- 手动串联模式适合需要多步骤数据收集的场景

---

### Day 28-30: 综合实战项目 ✅ 已完成

**目标**: 用所学构建一个完整的实际应用

**任务**:
1. 选择实战场景：个人知识管理助手
2. 设计 Agent 架构（5 个 Agent）
   - Router Agent：意图识别和路由
   - Search Agent：知识库检索
   - Summarize Agent：内容总结
   - Organize Agent：知识整理和分类
   - Q&A Agent：问答助手
3. 实现 Tool 定义（4 个核心工具）
   - search_knowledge：搜索知识库
   - add_note：添加新笔记
   - get_category_stats：获取统计信息
   - generate_study_plan：生成学习计划
4. 实现 Handoff、Guardrails
5. 编写测试用例（7 个测试场景，24 个测试用例）
6. 运行评测，记录性能指标

**输出文件**:
- `src/capstone_project.py`
- `eval/multi_agent_eval.csv`

**测试场景**:
1. ✅ 知识检索（简单搜索、分类搜索、标签搜索）
2. ✅ 内容总结（Python、机器学习、系统设计）
3. ✅ 知识整理（添加笔记、查看统计、生成学习计划）
4. ✅ 问答系统（4 个知识问题）
5. ✅ Handoff 路由（4 个场景测试）
6. ✅ Guardrails 安全防护（正常、超长、敏感词）
7. ✅ 异常处理（不存在的分类、模糊搜索、空查询）

**技术亮点**:
- 模块化设计：每个 Agent 职责单一、边界清晰
- 可扩展性：易于添加新的 Agent 和 Tool
- 安全性：多层 Guardrails 保护
- 可观测性：详细的日志和 Token 统计
- 知识库：10 条笔记，3 个分类（Python、机器学习、系统设计）

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
| Day 24-25 | 简单 Handoff 示例 | ✅ 已完成 | ~2h |
| Day 26-27 | 多 Agent 协作 | ✅ 已完成 | ~3h |
| Day 28-30 | 综合实战项目 | ✅ 已完成 | ~4h |

**总用时**: 预计 8 小时 | 实际：~9h

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
