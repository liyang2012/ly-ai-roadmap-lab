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
│   ├── week3/                         # Week 3: Subgraph 与模块化
│   │   └── subgraphs/
│   │       ├── order_subgraph.py
│   │       └── faq_subgraph.py
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
| Week 1 | Graph API 入门 | ⬜ 待开始 | __h |
| Week 2 | Persistence / Checkpoints | ⬜ 待开始 | __h |
| Week 3 | Subgraph 与模块化 | ⬜ 待开始 | __h |
| Week 4 | Workflow vs Agent 选型 | ⬜ 待开始 | __h |

**总用时**: 预计 12 小时 | 实际：__h

---

## 🚀 快速开始

```bash
cd /Users/liyang/dev/python_project/ly-ai-roadmap-lab
source venv/bin/activate
pip install langgraph langchain-openai
```
