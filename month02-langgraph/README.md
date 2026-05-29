# 📚 第 2 月 - LangGraph 与编排

**日期**：2026-05-13 至 2026-06-08

**主题**：从「单兵作战」到「团队协作」—— 建立 workflow vs agent 判断力，掌握 Graph API、State、Node、Edge

---

## 🎯 月目标

- 理解 LangGraph 的 Graph API 基本结构
- 掌握 Persistence / Checkpoints（状态持久化、时间旅行、Human-in-the-loop）
- 学会 Subgraph 与模块化设计
- 建立 Workflow vs Agent 的选型判断力

## 📁 目录结构

```
month02-langgraph/
├── README.md                          # 本月学习说明（本文件）
├── src/
│   ├── week1/                         # Week 1: Graph API 入门
│   │   ├── simple_graph.py
│   │   └── customer_support_graph.py
│   ├── week2/                         # Week 2: Persistence / Checkpoints
│   │   └── checkpoint_demo.py
│   ├── week3/                         # Week 3: Subgraph 与模块化 ✅
│   │   ├── order_subgraph.py
│   │   ├── faq_subgraph.py
│   │   ├── master_graph.py
│   │   └── week3_comprehensive_notes.md
│   └── week4/                         # Week 4: Workflow vs Agent 选型
├── docs/
│   ├── graph_design.md
│   ├── workflow_vs_agent.md
│   └── month2_review.md
├── eval/                              # 评测
│   └── golden_cases.csv
└── results/                           # 运行结果
```

---

## 📋 周计划

### Week 1：Graph API 入门
- 理解 StateGraph 基本结构
- 画结构图、实现第一个 graph
- 把 month01 客服流程翻译成 graph
- 增加条件分支 edge

### Week 2：Persistence / Checkpoints
- 理解持久化机制、线程、checkpoint、time travel
- 做 checkpoint_demo.py
- 模拟失败恢复、Human-in-the-loop

### Week 3：Subgraph 与模块化
- 理解 subgraph 概念
- 设计订单处理子图、FAQ 子图
- 主图组合两个子图

### Week 4：Workflow vs Agent 选型
- 总结判定标准
- 同需求分别做 workflow 版和 agent 版
- 对比：成本、延迟、稳定性、调试难度
- 月度复盘

---

## 📊 进度追踪

| 周 | 任务 | 状态 | 用时 |
|----|------|------|------|
| Week 1 | Graph API 入门 | ✅ 已完成 | ~1.5h |
| Week 2 | Persistence / Checkpoints | ✅ 已完成 (3 个文件全通) | ~3h |
| Week 3 | Subgraph 与模块化 | ✅ 已完成 (3 个文件全通，11 个测试用例) | ~3h |
| Week 4 | Workflow vs Agent 选型 | ⬜ 待开始 | __h |

**总用时**: 预计 12 小时 | 实际：~7.5h

---

## 🚀 快速开始

```bash
cd /Users/liyang/dev/python_project/ly-ai-roadmap-lab
source venv/bin/activate
pip install langgraph langchain-openai
```

---

## 📝 Week 3 补充说明 (2026-05-24)

**已完成的代码文件**：
- `src/week3/order_subgraph.py` — 订单处理子图（5 个节点）
- `src/week3/faq_subgraph.py` — FAQ 子图（置信度路由）
- `src/week3/master_graph.py` — 主图组合（11 个测试用例）
- `src/week3/week3_comprehensive_notes.md` — 详细学习笔记

**关键设计**：
- 子图 = 编译后的 graph 作为节点添加到主图
- State 共享：主图 State 是所有子图 State 的超集
- 适配器模式：解决主图/子图字段不一致问题

**下周**：Week 4 — Workflow vs Agent 选型对比
