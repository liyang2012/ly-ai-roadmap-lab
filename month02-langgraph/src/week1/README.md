# 📚 第 2 月 - Week 1：Graph API 入门

**日期**：2026-05-11 至 2026-05-17

## 🎯 周目标

- [x] 理解 Graph API 基本结构
- [x] 画出 StateGraph 结构图
- [x] 实现第一个 graph
- [x] 把 month01 客服流程翻译成 graph
- [x] 增加条件分支 edge
- [x] 周笔记：graph 思维 vs agent 脚本思维

## 📋 任务清单

### Day 1-2: Graph API 基础 ✅ 已完成
- [x] 安装 LangGraph
- [x] 阅读官方 overview、graph api 文档
- [x] 画 StateGraph 基本结构图
- [x] 写 `simple_graph.py`（3 个节点）

### Day 3-4: 客服流程 Graph 化 ✅ 已完成
- [x] 把 month01 的电商客服 Agent 流程翻译成 graph
- [x] 定义 state schema
- [x] 定义 nodes：意图识别 → 订单查询 / 退款政策 / 转人工
- [x] 增加条件分支 edge（根据意图路由）

### Day 5-6: 条件分支与优化 ✅ 已完成
- [x] 测试各种输入场景（8 个测试用例，全部通过）
- [x] 记录 graph 思维 vs agent 脚本思维的差异
- [x] 修复杂意图优先级 bug（order_query vs logistics）

## 📝 周输出

- `simple_graph.py` ✅
- `customer_support_graph.py` ✅
- `docs/graph_design.md` ✅（周笔记）

## ⏰ 时间统计

- 工作日：~1.5h（5月13日完成）
- 周末：0h
- 合计：~1.5h

## 📊 周小结

- 完成情况：Day 1-6 全部完成
- 关键收获：Graph 思维 = 显式流程设计，条件边 = 路由表
- 遇到的问题：意图分类优先级需要仔细设计（越具体的意图越先判断）
- 下周调整：Week 2 引入 LLM 做意图识别，替代规则匹配
