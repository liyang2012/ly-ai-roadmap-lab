# 📚 第 3 月 - RAG 与 Context Engineering

**日期**：2026-06-07 至 2026-07-06

**主题**：从「聪明的大脑」到「有记忆的大脑」—— 让 Agent 拥有自己的知识库

---

## 🎯 月目标

- 理解 RAG（检索增强生成）的完整流程
- 掌握向量数据库、Embedding、文档分块的核心技术
- 学会 Reranking、Hybrid Search 等进阶检索策略
- 做出一个可用的知识库问答系统

---

## 🤔 开始之前：你需要知道什么？

### 前置知识

如果你是**完全的小白**，建议先花 20 分钟了解以下概念：

| 概念 | 一句话解释 | 为什么需要知道 |
|------|-----------|---------------|
| LLM（大语言模型） | 如 ChatGPT、GLM 等 AI 对话系统 | RAG 的核心就是给 LLM "加外挂" |
| Prompt（提示词） | 给 AI 的指令文本 | RAG 的关键步骤就是构造好的 Prompt |
| API（接口） | 程序之间通信的方式 | 调用 LLM 和 Embedding 模型都通过 API |
| Python 基础 | 变量、函数、类、pip 安装 | 所有代码都是 Python |
| JSON | 一种数据格式 `{"key": "value"}` | 配置文件和文档格式 |

### 前置条件

```bash
# 1. 确保 Ollama 正在运行（本地 Embedding 模型）
ollama serve

# 2. 下载中文 Embedding 模型（首次）
ollama pull qwen3-embedding:4b

# 3. 安装 Python 依赖
pip install chromadb numpy requests ollama
pip install langchain langchain-text-splitters langchain-community
pip install pymupdf rank_bm25 python-dotenv
```

### 推荐学习路径

```
第 1 步：先读科普文档（doc/ 目录），建立整体认知
  └── doc/RAG-Fundamentals.md        ← 从这里开始！
  └── doc/Embedding-VectorDB.md      ← 理解"语义变数字"

第 2 步：按 Week 顺序动手实践
  └── Week 1：跑通第一个 RAG（硬编码小数据）
  └── Week 2：处理真实文件 + 分块
  └── Week 3：高级检索 + 评估
  └── Week 4：整合成完整系统

第 3 步：每周完成后读复盘笔记（week*_notes.md），加深理解
```

---

## 📁 目录结构

```
month03-rag/
├── README.md                    # 本月学习说明（本文件）
├── doc/                         # 📖 科普文档（小白友好）
│   ├── RAG-Fundamentals.md      #   RAG 入门科普 ← 从这里开始
│   ├── Embedding-VectorDB.md    #   Embedding 和向量数据库
│   ├── Document-Processing.md   #   文档处理和分块策略
│   ├── Advanced-Retrieval.md    #   高级检索策略
│   └── Build-RAG-System.md      #   搭建完整 RAG 系统
├── src/
│   ├── week1/                   # Week 1: RAG 基础与向量检索
│   ├── week2/                   # Week 2: 文档处理与分块策略
│   ├── week3/                   # Week 3: 高级检索策略
│   └── week4/                   # Week 4: 知识库问答系统实战
├── eval/                        # 评测
└── results/                     # 运行结果
```

## 📋 周计划

### Week 1：RAG 基础与向量检索
- 理解 RAG 架构：Query → Retrieve → Augment → Generate
- 向量数据库入门（ChromaDB）
- Embedding 模型使用（本地 qwen3-embedding:4b / OpenAI text-embedding-3-small）
- 第一个 RAG Pipeline 跑通

### Week 2：文档处理与分块策略
- 文档加载器（PDF、Markdown、HTML）
- 分块策略：固定长度 vs 语义分块 vs 递归分块
- 元数据管理：来源、页码、章节
- 多格式文档处理实战

### Week 3：高级检索策略
- Hybrid Search：向量检索 + BM25 关键词检索
- Reranking：Cross-Encoder 重排序
- Query 改写与扩展
- 检索效果评估指标：Hit Rate、MRR、nDCG

### Week 4：知识库问答系统实战
- 结合 LangGraph + RAG 构建完整问答系统
- 对话记忆与多轮检索
- 引用溯源（answer with sources）
- 月度复盘

## 🛠 技术栈

- 向量数据库：ChromaDB
- Embedding：qwen3-embedding:4b (Ollama 本地) / text-embedding-3-small (API)
- 框架：LangChain + LangGraph（复用第 2 月基础）
- 文档处理：LangChain Document Loaders
- 分块：LangChain Text Splitters

## 📊 进度追踪

| 周 | 任务 | 状态 | 用时 |
|----|------|------|------|
| Week 1 | RAG 基础与向量检索 | ✅ 已完成 | ~3h |
| Week 2 | 文档处理与分块策略 | ✅ 已完成 | ~3h |
| Week 3 | 高级检索策略 | ⬜ 未开始 | __h |
| Week 4 | 知识库问答系统实战 | ⬜ 未开始 | __h |

**总用时**: 预计 12 小时 | 实际：6h（Week 1 + Week 2）

---

## 🔗 与前两月的衔接

**第 1 月**学会了让 Agent 调用 Tool
**第 2 月**学会了用 Graph 编排复杂流程
**第 3 月**学会给 Agent 注入外部知识

三者结合 → 第 4 月 Multi-Agent 就有了真正的知识底座
