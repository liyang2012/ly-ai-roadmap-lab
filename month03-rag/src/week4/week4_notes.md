# 第 3 月 Week 4：RAG 实战 — 智能知识库问答系统

**日期**：2026-06-29  
**状态**：✅ 已完成  
**用时**：~3h

---

## 💡 小白科普：本周在学什么？

这是第 3 月的最后一周。前 3 周你分别学了：
- Week 1：Embedding + 向量数据库（“语义指纹” + “图书馆”）
- Week 2：文档加载 + 分块（“真实文档怎么喂给 AI”）
- Week 3：高级检索（“怎么检索得更准”）

本周的任务是：**把前 3 周的所有技术组合起来，做一个能用的知识库问答系统**。

就像一个汽车工厂：
- Week 1 学了发动机（Embedding + 向量检索）
- Week 2 学了车身和底盘（文档处理 + 分块）
- Week 3 学了变速箱和悬挂（Hybrid Search + Reranking）
- Week 4 把它们组装成一辆能开的车🚗

本周你会看到一个完整的系统架构，包含：
- 多格式文档加载（MD/HTML/TXT/PDF/JSON）
- 智能分块（Markdown 标题感知 + 递归分块）
- 混合检索（向量 + BM25 + RRF 融合）
- 查询改写（关键词提取 + 子问题拆解）
- LLM 生成回答（DeepSeek API）

> 📖 更详细的科普请阅读 `doc/Build-RAG-System.md`

---

## 📋 学习目标

将 Week 1-3 学到的技术整合为一个完整的知识库问答系统：
- 多格式文档加载（MD/HTML/TXT/PDF/JSON）
- 智能分块（Markdown 标题感知 + 递归分块）
- Hybrid Search（向量 + BM25 + RRF 融合）
- Query Rewriting（查询改写 + 多查询搜索）
- LLM 生成（DeepSeek API）

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   KnowledgeBaseRAG                    │
├─────────────────────────────────────────────────────┤
│  Indexing (离线)          Query (在线)                │
│  ┌──────────┐             ┌──────────┐              │
│  │Document  │             │  User    │              │
│  │ Loader   │             │  Query   │              │
│  └────┬─────┘             └────┬─────┘              │
│       ↓                        ↓                     │
│  ┌──────────┐             ┌──────────┐              │
│  │ Chunker  │             │  Query   │              │
│  │ (结构+递归)│            │ Rewriter │              │
│  └────┬─────┘             └────┬─────┘              │
│       ↓                        ↓                     │
│  ┌──────────┐             ┌──────────┐              │
│  │Embedding │             │ Hybrid   │              │
│  │ (Ollama) │             │ Searcher │              │
│  └────┬─────┘             │(向量+BM25)│              │
│       ↓                   └────┬─────┘              │
│  ┌──────────┐                  ↓                     │
│  │ ChromaDB │             ┌──────────┐              │
│  │ + BM25   │             │   RRF    │              │
│  └──────────┘             │  Fusion  │              │
│                           └────┬─────┘              │
│                                ↓                     │
│                           ┌──────────┐              │
│                           │   LLM    │              │
│                           │Generator │              │
│                           └────┬─────┘              │
│                                ↓                     │
│                           ┌──────────┐              │
│                           │  Answer  │              │
│                           └──────────┘              │
└─────────────────────────────────────────────────────┘
```

---

## 📁 产出文件

```
src/week4/
├── knowledge_base_rag.py    # 主程序（~550 行）
├── week4_notes.md           # 本复盘笔记
└── docs/                    # 测试文档集
    ├── info.json            # 系统配置（JSON 格式测试）
    ├── ai/
    │   └── rag_overview.md  # RAG 概述（MD 格式）
    ├── tech/
    │   ├── vector_databases.md  # 向量数据库对比
    │   └── chunking_guide.md    # 分块策略指南
    └── python/
        └── python_basics.md     # Python 基础笔记
```

---

## 🔑 核心设计决策

### 1. 为什么是 ChromaDB 而不是 FAISS？
- ChromaDB 自带持久化，FAISS 需要手动序列化
- ChromaDB API 更友好，内置元数据过滤
- 学习项目规模不大，ChromaDB 性能足够

### 2. 为什么 Hybrid Search 而不是纯向量？
- 精确查询（如 "ChromaDB"）向量检索可能召回语义相关但不精确的内容
- BM25 对精确匹配有天然优势
- RRF 融合两者取长补短

### 3. 为什么 Query Rewriting 在搜索前？
- 用户口语化查询可能用词不同
- 子问题拆解帮助处理复杂多意图查询
- 多查询 + 合并去重提高召回率

### 4. 为什么 Markdown 标题感知分块？
- 保留文档逻辑结构
- 元数据中记录标题便于来源追溯
- 结合递归分块兜底处理超长段落

---

## 🧪 测试验证

### 测试文档集
5 个文档，涵盖 3 种格式（MD, JSON），分布在 3 个目录

### 使用方式
```bash
# 索引文档 + 交互模式
cd src/week4
python knowledge_base_rag.py --index --interactive

# 单次查询
python knowledge_base_rag.py --index -q "什么是 RAG？"

# 查看统计
python knowledge_base_rag.py --index --stats
```

---

## 💡 关键领悟

1. **工程化 > 炫技**：一个完整的系统不在于用了多少花哨技术，而在于每个环节都可靠
2. **分块是 RAG 的灵魂**：分块策略直接决定检索质量，比模型选择更重要
3. **错误处理不可忽视**：PDF 解析失败、LLM 超时、API Key 缺失，每个都要优雅降级
4. **元数据是宝藏**：记录来源、标题、格式，用户才能信任回答
5. **渐进式设计**：先跑通基础流程，再叠加 Hybrid Search、Query Rewriting 等优化

---

## 📚 第 3 月总结

| Week | 主题 | 状态 | 用时 |
|------|------|------|------|
| Week 1 | RAG 基础与向量检索 | ✅ | ~3h |
| Week 2 | 文档处理与分块策略 | ✅ | ~3h |
| Week 3 | 高级检索策略 | ✅ | ~3h |
| Week 4 | RAG 实战：知识库问答系统 | ✅ | ~3h |
| **合计** | | | **~12h** |

### 技术栈全景
- **Embedding**: Ollama qwen3-embedding:4b
- **向量数据库**: ChromaDB
- **关键词检索**: BM25（自实现）
- **融合算法**: RRF
- **LLM**: DeepSeek API（换过智谱→DeepSeek）
- **文档处理**: 标准库 + PyMuPDF

### 达到的能力
- ✅ 能独立搭建完整的 RAG 知识库问答系统
- ✅ 理解并实现 Hybrid Search
- ✅ 掌握分块策略选择和调优
- ✅ 能设计评估体系并做 A/B 比较
- ✅ 知道何时用关键词、何时用向量、何时混合

---

## 🚀 下一步

第 4 月：Agent 与 Multi-Agent 系统
- Agent 框架对比（OpenAI Agents SDK vs LangGraph Agent）
- 多 Agent 协作模式
- Tool 设计与调用优化
- 实际业务场景 Agent 开发
