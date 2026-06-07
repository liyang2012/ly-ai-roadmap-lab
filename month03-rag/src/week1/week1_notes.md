# Week 1 复盘笔记

## 📊 本周完成情况

| Day | 任务 | 产出 | 状态 |
|-----|------|------|------|
| Day 1-2 | RAG 概念与环境搭建 | `rag_basics.py` | ✅ |
| Day 3-4 | Embedding 与向量数据库 | `embedding_demo.py`, `chroma_basics.py` | ✅ |
| Day 5-6 | 第一个完整 RAG Pipeline | `simple_rag.py` | ✅ |
| Day 7 | 复盘笔记 | 本文件 | ✅ |

**实际用时**: ~3 小时（预计 3-4 小时）

---

## 🔑 核心知识点总结

### 1. RAG 的三个阶段

```
Indexing: 文档 → Embedding → 向量数据库
Retrieval: 用户查询 → 语义检索 Top-K 相关文档
Generation: 检索结果 + 问题 → LLM 生成回答
```

### 2. 为什么需要 RAG？

| 问题 | RAG 的解决方案 |
|------|---------------|
| LLM 知识截止 | 知识库可随时更新 |
| LLM 幻觉 | 基于真实文档回答 |
| 企业私有数据 | 数据不出本地 |

### 3. Embedding 核心概念

- **是什么**：把文本映射到高维向量空间（qwen3-embedding:4b 输出 2560 维）
- **关键性质**：语义相近的文本 → 向量距离近
- **相似度计算**：余弦相似度（0~1，越大越相似）

### 4. ChromaDB 基本操作

```python
# CRUD
collection.add(documents=[], ids=[], metadatas=[])  # Create
collection.query(query_texts=[], n_results=2)        # Query
collection.get(ids=[])                                # Read
collection.update(ids=[], documents=[])               # Update
collection.delete(ids=[])                             # Delete
```

### 5. 关键参数

| 参数 | 含义 | 经验值 |
|------|------|--------|
| top_k | 检索返回的文档数 | 2-5 |
| distance | 向量距离（越小越相似） | < 0.6 相关性高 |
| temperature | LLM 生成温度 | RAG 场景用 0.3（更确定） |

---

## 🔍 关键发现

### 1. 关键词匹配 vs 语义检索

**关键词匹配的问题**（rag_basics.py 暴露）：
- "什么是不可变的序列？" → 相关度全部为 0
- 因为 query 里没有"元组""tuple"这些关键词

**语义检索的优势**（simple_rag.py 验证）：
- "买了手机用了一个月坏了怎么办？" → 正确检索到 `product_warranty`
- "怎么才能免运费？" → 正确检索到 `shipping_info`
- 同义词、近义词、口语表达都能理解

### 2. ChromaDB 默认 Embedding 的问题

- ChromaDB 内置 `all-MiniLM-L6-v2` 是英文模型
- 对中文效果差：所有测试都返回错误结果
- **解决方案**：用 Ollama 本地中文 Embedding（qwen3-embedding:4b）

### 3. RAG Pipeline 的检索质量决定回答质量

- 检索到了正确文档 → 回答准确（6/6 全对）
- 如果检索到了错误文档 → LLM 也会基于错误文档"一本正经地胡说"
- **结论**：Retrieval 是 RAG 的核心瓶颈

---

## ⚠️ 踩坑记录

1. **API Key 切换**：阿里云百炼 → 智谱 AI，.env 文件需要对应更新
2. **chromadb 需要 `pip install ollama`**：OllamaEmbeddingFunction 依赖 ollama python 包
3. **ChromaDB 首次运行会下载 ONNX 模型**（all-MiniLM-L6-v2，79MB），需要网络

---

## 🎯 Week 2 预告

- 文档加载器（PDF、Markdown、HTML）
- 分块策略：固定长度 vs 语义分块 vs 递归分块
- 元数据管理
- 用真实文档构建更大的知识库

---

## 📝 自检清单

- [x] 能解释 RAG 的三个阶段（Indexing / Retrieval / Generation）
- [x] 能解释 Embedding 的作用和原理
- [x] 能解释余弦相似度的含义
- [x] 能使用 ChromaDB 进行 CRUD 操作
- [x] 能构建一个完整的 RAG Pipeline
- [x] 理解关键词匹配 vs 语义检索的区别
- [x] 理解 top_k、distance、temperature 的含义
