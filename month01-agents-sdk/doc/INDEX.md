# 📚 Agents SDK 文档索引

> 本目录包含所有学习文档，适合从零基础到进阶的完整学习路径

---

## 🎯 快速开始

### 我是完全新手，从哪里开始？

👉 **[README.md - 完整入门指南](./README.md)**

这是最全面的文档，包含：
- 什么是 AI Agent
- 环境配置步骤
- Week 1-4 完整教程
- 常见问题解答
- 学习路径建议

**预计时间**：2-3 小时

---

## 📖 核心文档

### 1. [RunLoop.md - Agent 运行机制](./RunLoop.md)

**适合人群**：想深入理解 Agent 如何工作的人

**你将学到**：
- ✅ Run Loop 是什么（用餐厅点餐类比）
- ✅ 无 Tool 的基础流程
- ✅ 带 Tool 调用的完整流程
- ✅ 多轮对话循环
- ✅ Handoff 转交流程
- ✅ 真实代码示例对照
- ✅ 调试技巧

**预计时间**：1 小时

---

### 2. [Handoff.md - 多 Agent 协作](./Handoff.md)

**适合人群**：想学习多 Agent 协作的人

**你将学到**：
- ✅ 什么是 Handoff（用医院就诊类比）
- ✅ 角色分工（Triage、Expert）
- ✅ 单 Handoff 实现
- ✅ 多 Handoff 场景
- ✅ 最佳实践（推荐 vs 避免）
- ✅ 调试技巧
- ✅ 实际应用场景

**预计时间**：1 小时

---

### 3. [Week3-Testing-Evaluation.md - 测试、评估与优化](./Week3-Testing-Evaluation.md)

**适合人群**：想优化 Agent 性能、降低成本的人

**你将学到**：
- ✅ 一致性测试 - 确保 Agent 回答稳定
- ✅ Token 分析 - 了解成本构成
- ✅ 错误样本集 - 知道哪里需要改进
- ✅ 优化方法 - 降低误调率和成本
- ✅ A/B 测试 - 对比优化效果
- ✅ Mini Eval - 建立评测体系

**预计时间**：1 小时

---

## 🗺️ 学习路径

### 路径 1：快速上手（30 分钟）

```
1. 阅读 README.md 的"什么是 AI Agent"部分
2. 运行 src/week1/hello_agent.py
3. 运行 src/week1/loop_agent_tools.py
4. 看输出，理解流程
```

### 路径 2：系统学习（4-5 小时）

```
1. 完整阅读 README.md
   └─ 理解核心概念
   └─ 配置环境
   └─ 了解 Week 1-4 全貌

2. 深入阅读 RunLoop.md
   └─ 理解 Agent 运行机制
   └─ 对照代码看流程

3. 深入阅读 Handoff.md
   └─ 理解多 Agent 协作
   └─ 学习设计原则

4. 深入阅读 Week3-Testing-Evaluation.md
   └─ 学习如何测试 Agent
   └─ 了解优化方法

5. 动手实践
   └─ 运行所有示例代码
   └─ 修改参数，观察变化
```

### 路径 3：实战进阶（1-2 天）

```
1. 学习 Week 2 电商客服
   └─ src/week2/multi_tool_agent.py
   └─ src/week2/ecommerce_support_agent.py

2. 学习 Week 3 测试评估
   └─ src/week3/day15_16_consistency_test.py
   └─ src/week3/day17_18_token_usage.py

3. 学习 Week 4 多 Agent 协作
   └─ src/week4/src/simple_handoff.py
   └─ src/week4/src/multi_agent_collab.py
   └─ src/week4/src/capstone_project.py

4. 自己设计一个 Agent 系统
   └─ 定义角色
   └─ 设计工具
   └─ 实现 Handoff
   └─ 测试优化
```

---

## 📂 代码目录对照

| 文档章节 | 对应代码 | 难度 |
|---------|---------|------|
| Week 1：第一个 Agent | `src/week1/hello_agent.py` | ⭐ |
| Week 1：带工具的 Agent | `src/week1/loop_agent_tools.py` | ⭐⭐ |
| Week 2：多 Tool 协作 | `src/week2/multi_tool_agent.py` | ⭐⭐ |
| Week 2：电商客服实战 | `src/week2/ecommerce_support_agent.py` | ⭐⭐⭐ |
| Week 3：一致性测试 | `src/week3/day15_16_consistency_test.py` | ⭐⭐⭐ |
| Week 3：Token 分析 | `src/week3/day17_18_token_usage.py` | ⭐⭐⭐ |
| Week 4：简单 Handoff | `src/week4/src/simple_handoff.py` | ⭐⭐⭐ |
| Week 4：多 Agent 协作 | `src/week4/src/multi_agent_collab.py` | ⭐⭐⭐⭐ |
| Week 4：综合项目 | `src/week4/src/capstone_project.py` | ⭐⭐⭐⭐⭐ |

---

## 🔍 按主题查找

### 想了解"Agent 是什么"
→ [README.md - 什么是 AI Agent](./README.md#什么是-ai-agent)

### 想了解"环境怎么配置"
→ [README.md - 环境准备](./README.md#环境准备)

### 想了解"Tool 怎么用"
→ [README.md - Week 2：Tool 工具系统](./README.md#week-2tool-工具系统)
→ [RunLoop.md - 场景 2：完整流程（带 Tool 调用）](./RunLoop.md#场景-2完整流程带-tool-调用)

### 想了解"Handoff 怎么用"
→ [Handoff.md - 完整教程](./Handoff.md)
→ [RunLoop.md - 场景 4：Handoff 流程](./RunLoop.md#场景-4handoff-流程多-agent-协作)

### 想了解"如何调试"
→ [RunLoop.md - 调试技巧](./RunLoop.md#调试技巧)
→ [Handoff.md - Handoff 调试技巧](./Handoff.md#handoff-调试技巧)

### 想了解"如何测试"
→ [Week3-Testing-Evaluation.md - 一致性测试](./Week3-Testing-Evaluation.md#day-15-16一致性测试)
→ [Week3-Testing-Evaluation.md - Token 分析](./Week3-Testing-Evaluation.md#day-17-18token-使用分析)

### 想了解"如何优化"
→ [Week3-Testing-Evaluation.md - 错误样本集](./Week3-Testing-Evaluation.md#day-19-20错误样本集)
→ [Week3-Testing-Evaluation.md - 优化方法](./Week3-Testing-Evaluation.md#day-21-22优化-instructions-和-schema)

### 想了解"最佳实践"
→ [Handoff.md - 最佳实践](./Handoff.md#handoff-最佳实践)

### 想了解"常见问题"
→ [README.md - 常见问题解答](./README.md#常见问题解答)

---

## 💡 学习建议

### ✅ 推荐做法

1. **先运行，再阅读**
   ```bash
   # 先运行看输出
   cd src/week1
   python hello_agent.py
   
   # 再看代码理解
   # 最后看文档深化理解
   ```

2. **边学边改**
   - 改 `instructions` 看 AI 反应
   - 改 `tools` 看调用变化
   - 改 `messages` 看对话流程

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
AI Agent 知识体系
│
├─ 基础概念
│  ├─ 什么是 Agent
│  ├─ LLM（大语言模型）
│  ├─ Tools（工具）
│  └─ Instructions（指令）
│
├─ 运行机制
│  ├─ Run Loop（运行循环）
│  ├─ Messages（消息列表）
│  ├─ Tool Call（工具调用）
│  └─ Async/Await（异步）
│
├─ 工具系统
│  ├─ @function_tool 装饰器
│  ├─ 工具定义
│  ├─ 工具实现
│  └─ 多工具协作
│
├─ 测试与优化
│  ├─ 一致性测试
│  ├─ Token 分析
│  ├─ 错误样本集
│  ├─ Instructions 优化
│  ├─ Schema 优化
│  └─ Mini Eval（评测集）
│
├─ 多 Agent 协作
│  ├─ Handoff（转交）
│  ├─ TriageAgent（接待员）
│  ├─ ExpertAgent（专家）
│  └─ 上下文传递
│
└─ 最佳实践
   ├─ 职责划分
   ├─ 指令设计
   ├─ 工具设计
   ├─ 调试技巧
   └─ 性能优化
```

---

## 🔗 外部资源

- [OpenAI Agents SDK 官方文档](https://openai.github.io/openai-agents-python/)
- [阿里云百炼平台](https://help.aliyun.com/zh/model-studio/)
- [Python 异步编程教程](https://docs.python.org/3/library/asyncio.html)

---

## 📝 文档更新记录

| 日期 | 更新内容 | 更新人 |
|------|---------|--------|
| 2026-05-23 | 创建完整入门指南（README.md） | AI Assistant |
| 2026-05-23 | 重写 RunLoop.md，增加详细解释和代码对照 | AI Assistant |
| 2026-05-23 | 重写 Handoff.md，增加类比和最佳实践 | AI Assistant |
| 2026-05-23 | 创建文档索引（INDEX.md） | AI Assistant |
| 2026-05-23 | 创建 Week3-Testing-Evaluation.md，测试与优化详解 | AI Assistant |

---

## 💬 反馈与建议

如果你发现文档有问题，或者想补充内容，请：

1. 检查代码是否与文档一致
2. 确认示例可以正常运行
3. 提出具体的改进建议

---

> 💡 **学习提示**：最好的学习方式是"运行代码 → 看输出 → 改参数 → 再运行 → 看变化"。动手实践比只看文档有效 10 倍！
