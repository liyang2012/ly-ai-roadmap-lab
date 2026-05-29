# 📚 LangGraph 文档索引

> 本目录包含 LangGraph 学习文档，适合从基础到进阶的完整学习路径

---

## 🎯 快速开始

### 我是 LangGraph 新手，从哪里开始？

👉 **先看对应 Week 的源码和笔记**

每个 Week 都有详细的笔记和可运行的代码：

| Week | 主题 | 文件位置 |
|------|------|---------|
| Week 1 | Graph API 入门 | `src/week1/` |
| Week 2 | Persistence / Checkpoints | `src/week2/` |
| Week 3 | Subgraph 与模块化 | `src/week3/` |
| Week 4 | Workflow vs Agent 选型 | `src/week4/`（待完成） |

---

## 📖 核心文档

### 1. [Week3-Subgraph-Modular.md - Subgraph 与模块化设计](./Week3-Subgraph-Modular.md)

**适合人群**：想学习 LangGraph 子图设计的人

**你将学到**：
- ✅ 为什么要拆子图（从"大杂烩"到"模块化"）
- ✅ Subgraph 核心概念（用公司组织架构类比）
- ✅ State 共享机制（主图和子图如何通信）
- ✅ 三种架构模式（扁平、适配器、隔离）
- ✅ 实战实现（订单子图 + FAQ 子图 + 主图编排）
- ✅ 常见踩坑与解决方案
- ✅ 设计原则总结

**预计时间**：1.5 小时

---

## 🗺️ 学习路径

### 路径 1：快速上手（30 分钟）

```
1. 阅读 Week 1 源码和笔记
   └─ 理解 StateGraph 基本概念
   └─ 运行简单 graph

2. 阅读 Week 2 源码和笔记
   └─ 理解 Checkpoint 和 MemorySaver
   └─ 运行带持久化的 graph

3. 阅读 Week 3 源码和笔记
   └─ 理解 Subgraph 概念
   └─ 运行子图示例
```

### 路径 2：系统学习（3-4 小时）

```
1. 完整学习 Week 1
   └─ 阅读笔记
   └─ 运行代码
   └─ 修改参数观察变化

2. 完整学习 Week 2
   └─ 理解 Checkpoint 机制
   └─ 掌握 Time Travel
   └─ 实践 Human-in-the-Loop

3. 完整学习 Week 3
   └─ 深入阅读 Week3-Subgraph-Modular.md
   └─ 理解三种架构模式
   └─ 尝试自己设计子图

4. 动手实践
   └─ 设计一个包含子图的系统
   └─ 实现并测试
```

---

## 📂 代码目录对照

| 文档章节 | 对应代码 | 难度 |
|---------|---------|------|
| Week 1：Graph API 入门 | `src/week1/simple_graph.py` | ⭐ |
| Week 1：客服 graph | `src/week1/customer_support_graph.py` | ⭐⭐ |
| Week 2：Checkpoint 演示 | `src/week2/checkpoint_demo.py` | ⭐⭐ |
| Week 2：Human-in-the-Loop | `src/week2/human_in_the_loop.py` | ⭐⭐⭐ |
| Week 2：Time Travel | `src/week2/time_travel_demo.py` | ⭐⭐⭐ |
| Week 3：订单子图 | `src/week3/order_subgraph.py` | ⭐⭐⭐ |
| Week 3：FAQ 子图 | `src/week3/faq_subgraph.py` | ⭐⭐⭐ |
| Week 3：主图编排 | `src/week3/master_graph.py` | ⭐⭐⭐⭐ |

---

## 🔍 按主题查找

### 想了解"StateGraph 基础"
→ Week 1 源码和笔记

### 想了解"Checkpoint 和持久化"
→ Week 2 源码和笔记

### 想了解"Subgraph 子图"
→ [Week3-Subgraph-Modular.md](./Week3-Subgraph-Modular.md)
→ Week 3 源码

### 想了解"State 共享机制"
→ [Week3-Subgraph-Modular.md - State 共享机制](./Week3-Subgraph-Modular.md#2-state-共享机制)

### 想了解"三种架构模式"
→ [Week3-Subgraph-Modular.md - 三种架构模式](./Week3-Subgraph-Modular.md#3-三种架构模式)

### 想了解"常见踩坑"
→ [Week3-Subgraph-Modular.md - 常见踩坑与解决方案](./Week3-Subgraph-Modular.md#️-常见踩坑与解决方案)

---

## 💡 学习建议

### ✅ 推荐做法

1. **先运行，再阅读**
   ```bash
   # 先运行看输出
   cd src/week3
   python order_subgraph.py
   
   # 再看代码理解
   # 最后看文档深化理解
   ```

2. **边学边改**
   - 改 `State` 字段，看数据如何流动
   - 改路由逻辑，看条件如何变化
   - 改子图结构，看编排如何工作

3. **做笔记**
   - 记录关键概念
   - 记录常见错误
   - 记录自己的理解

4. **动手实践**
   - 不要只看文档
   - 不要只读代码
   - 一定要自己运行、修改、调试

### ❌ 避免的做法

1. **只看不动手**
   - ❌ 只看文档不运行代码
   - ✅ 边看边运行

2. **一次性全看完**
   - ❌ 试图一天看完所有文档
   - ✅ 分阶段学习，循序渐进

3. **不调试就放弃**
   - ❌ 遇到错误直接放弃
   - ✅ 看错误信息、查文档、问 AI

---

## 🎓 知识体系

```
LangGraph 知识体系
│
├─ 基础概念
│  ├─ StateGraph（状态图）
│  ├─ Nodes（节点）
│  ├─ Edges（边）
│  └─ State（状态）
│
├─ 核心机制
│  ├─ Conditional Edges（条件边）
│  ├─ Entry Point（入口点）
│  ├─ END（结束节点）
│  └─ Compiled Graph（编译后的图）
│
├─ 持久化
│  ├─ Checkpoint（检查点）
│  ├─ MemorySaver（内存保存）
│  ├─ Thread ID（线程 ID）
│  └─ Time Travel（时间旅行）
│
├─ 子图与模块化
│  ├─ Subgraph（子图）
│  ├─ State 共享机制
│  ├─ 适配器模式
│  ├─ 扁平模式
│  └─ 隔离模式
│
├─ 高级特性
│  ├─ Human-in-the-Loop
│  ├─ Interrupt（中断）
│  ├─ Resume（恢复）
│  └─ Streaming（流式输出）
│
└─ 最佳实践
   ├─ 职责划分
   ├─ State 设计
   ├─ 路由策略
   └─ 错误处理
```

---

## 🔗 外部资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph 教程](https://langchain-ai.github.io/langgraph/tutorials/)
- [LangGraph API 参考](https://langchain-ai.github.io/langgraph/reference/)

---

## 📝 文档更新记录

| 日期 | 更新内容 | 更新人 |
|------|---------|--------|
| 2026-05-23 | 创建 Week3-Subgraph-Modular.md | AI Assistant |
| 2026-05-23 | 创建 LangGraph INDEX.md | AI Assistant |

---

## 💬 反馈与建议

如果你发现文档有问题，或者想补充内容，请：

1. 检查代码是否与文档一致
2. 确认示例可以正常运行
3. 提出具体的改进建议

---

> 💡 **学习提示**：LangGraph 的核心是理解 State 如何流动、节点如何执行、边如何路由。多运行代码、看 State 变化，比看 10 遍文档都有效！
