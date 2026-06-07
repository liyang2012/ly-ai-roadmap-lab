# Week 1：RAG 基础与向量检索

**日期**：2026-06-07 至 2026-06-13
**预计用时**：3-4 小时

---

## 🎯 本周目标

1. 理解 RAG 的完整流程（为什么需要 RAG）
2. 跑通第一个向量检索 demo
3. 理解 Embedding 的概念和用法
4. 用 ChromaDB 构建一个简单的文档检索系统

---

## 📅 Day 1-2：RAG 概念与环境搭建（今天开始）

### 理论（30 分钟）
- [ ] 理解 RAG 架构：`Query → Embed → Retrieve → Augment → Generate`
- [ ] 为什么 LLM 需要 RAG？（知识截止、幻觉、私有数据）
- [ ] Naive RAG vs Advanced RAG 的区别

### 动手（30 分钟）
- [ ] 安装依赖：`pip install chromadb langchain langchain-openai`
- [ ] 验证 ChromaDB 安装
- [ ] 验证本地 Embedding 模型（qwen3-embedding:4b）

### 产出
- `rag_basics.py` — RAG 概念演示（硬编码的小例子）

---

## 📅 Day 3-4：Embedding 与向量数据库

### 理论（30 分钟）
- [ ] 什么是 Embedding？把文本变成数字向量
- [ ] 余弦相似度：怎么衡量两个向量的"接近程度"
- [ ] 向量数据库 vs 传统数据库

### 动手（45 分钟）
- [ ] `embedding_demo.py` — 用本地模型把文本转成向量
- [ ] 计算几个句子的相似度
- [ ] ChromaDB CRUD 操作：add / query / delete / update

### 产出
- `embedding_demo.py` — Embedding 和相似度计算
- `chroma_basics.py` — ChromaDB 基本操作

---

## 📅 Day 5-6：第一个 RAG Pipeline

### 理论（20 分钟）
- [ ] RAG Pipeline 的三个核心环节：Indexing → Retrieval → Generation
- [ ] Top-K 检索的含义
- [ ] Context Window 限制与检索数量

### 动手（60 分钟）
- [ ] `simple_rag.py` — 完整的 RAG Pipeline
  - 加载一组文档（硬编码的小知识库）
  - 存入 ChromaDB
  - 用户提问 → 检索相关文档 → 拼接 prompt → LLM 回答
- [ ] 测试不同问题的检索效果
- [ ] 观察：检索到的文档质量如何影响最终回答

### 产出
- `simple_rag.py` — 第一个完整的 RAG 系统

---

## 📅 Day 7：复盘与笔记

- [ ] 写 `week1_notes.md` 总结本周知识点
- [ ] 记录踩坑和关键概念
- [ ] 准备 Week 2 的数据集（找 3-5 篇技术文档）

---

## 🔑 关键概念清单

| 概念 | 一句话解释 |
|------|-----------|
| RAG | 给 LLM 外接一个"搜索引擎" |
| Embedding | 把文本变成一串数字（向量） |
| 向量数据库 | 专门存储和检索向量的数据库 |
| 余弦相似度 | 两个向量方向越接近，值越接近 1 |
| Top-K | 检索最相似的 K 个结果 |
| Context Window | LLM 一次能"看到"的最大 token 数 |

---

## 🧪 检验标准

本周结束时，你应该能回答：
1. ❓ 为什么不能直接把所有文档塞给 LLM？
2. ❓ Embedding 是怎么把"语义相似"变成"数值接近"的？
3. ❓ RAG 的检索质量主要取决于什么？
4. ❓ ChromaDB 的 query 返回的 distance 是什么含义？
