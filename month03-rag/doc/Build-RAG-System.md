# 搭建完整 RAG 系统科普

> 配套 Week 4 内容。这篇把 Week 1~3 的所有技术串起来，讲清楚一个完整系统是怎么设计的。

---

## 1. 从"能跑"到"能用"

前三周我们学了 RAG 的各个组件：

| Week | 学到的组件 | 单独能做什么 |
|------|-----------|---------|
| Week 1 | Embedding + ChromaDB | 把文字变向量，语义检索 |
| Week 2 | 文档加载 + 分块 | 处理真实文件 |
| Week 3 | Hybrid Search + Reranking + 评估 | 让检索更准 |

Week 4 的任务是：**把这些组件组合成一个完整的、可用的知识库问答系统**。

### 一个完整系统需要具备什么？

| 能力 | 说明 | Week 几学的 |
|------|------|-----------|
| 多格式文档加载 | 支持 MD/HTML/TXT/PDF/JSON | Week 2 |
| 智能分块 | Markdown 标题感知 + 递归分块 | Week 2 |
| 向量存储 | ChromaDB + Ollama Embedding | Week 1 |
| 混合检索 | 向量 + BM25 + RRF 融合 | Week 3 |
| 查询优化 | 关键词提取 + 子问题拆解 | Week 3 |
| LLM 生成 | 基于检索结果生成回答 | Week 1 |
| CLI 交互 | 命令行参数 + 交互模式 | Week 4 新增 |

---

## 2. 系统架构总览

```
┌──────────────────────────────────────────────────────┐
│                  KnowledgeBaseRAG                      │
├──────────────────────────────────────────────────────┤
│                                                        │
│  ┌─ 离线索引 ─────────────────────────────────────┐  │
│  │                                                  │  │
│  │  docs/ 目录                                      │  │
│  │  ├── ai/rag_overview.md                          │  │
│  │  ├── tech/vector_databases.md                    │  │
│  │  ├── tech/chunking_guide.md                      │  │
│  │  ├── python/python_basics.md                     │  │
│  │  └── info.json                                   │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  DocumentLoader（按格式自动选择加载器）             │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  Chunker（标题感知 + 递归分块）                    │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  EmbeddingService（Ollama qwen3-embedding:4b）    │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  ChromaDB（向量存储）+ BM25Retriever（关键词索引）  │  │
│  │                                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌─ 在线查询 ─────────────────────────────────────┐  │
│  │                                                  │  │
│  │  用户问题                                        │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  QueryRewriter（关键词提取 + 子问题拆解）          │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  HybridSearcher（向量检索 + BM25 + RRF 融合）     │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  LLMGenerator（DeepSeek API 生成回答）            │  │
│  │       │                                          │  │
│  │       ▼                                          │  │
│  │  最终回答 + 引用来源                              │  │
│  │                                                  │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 3. 关键设计决策

### 决策 1：为什么选 ChromaDB 而不是 FAISS？

| 对比项 | ChromaDB | FAISS |
|-------|----------|-------|
| 持久化 | 自带，自动保存 | 需要手动序列化 |
| API 友好度 | 很高，5 行代码搞定 | 中等，需要更多代码 |
| 元数据过滤 | 内置支持 | 不支持 |
| 性能（100万+文档） | 一般 | 极快 |
| 适合规模 | 小到中型（<10 万文档） | 大型（10 万~10 亿） |

**结论**：学习项目和小中型知识库，ChromaDB 更合适。超大规模生产环境再考虑 FAISS。

### 决策 2：为什么用 Hybrid Search？

纯向量检索在以下场景会翻车：
- 精确型号查询："ChromaDB 支持哪些距离计算？"
- 缩写查询："RRF 的全称是什么？"

加入 BM25 后，精确匹配能力大幅提升，代价只是多维护一个内存索引。

### 决策 3：为什么 Query Rewriting 放在搜索前？

用户的口语化表达和文档的正式表达经常不一致。改写查询可以：
- 去噪：去掉"的""吗""呢"等无意义词
- 扩展：加入文档中可能出现的同义词
- 拆解：复杂问题拆成多个子问题

多查询 + 合并去重 = 更高的召回率。

### 决策 4：为什么用 Markdown 标题感知分块？

如果只按固定长度切分，一个章节的内容可能被切到两个不同的块里。标题感知分块能：
- 保留文档逻辑结构
- metadata 中记录标题，便于来源追溯
- 结合递归分块兜底处理超长段落

---

## 4. 核心组件详解

### 4.1 DocumentLoader（文档加载器）

支持 5 种格式，自动识别：

```python
ext = Path(filepath).suffix.lower()
loaders = {
    ".md": load_markdown,      # 直接读取
    ".txt": load_txt,          # 直接读取
    ".json": load_json,        # 解析 JSON 并格式化
    ".html": load_html,        # HTMLParser 去标签
    ".pdf": load_pdf,          # PyMuPDF 按页提取
}
```

### 4.2 Chunker（智能分块器）

两步分块策略：

```
原始文档
    │
    ▼
Step 1: 按 Markdown 标题切分
    │  # 第一章 → (标题="第一章", 内容="...")
    │  ## 1.1 节 → (标题="1.1 节", 内容="...")
    │
    ▼
Step 2: 对过长的块递归细化
    │  段落太长 → 按段落(\n\n)切分
    │  段落还长 → 按句子(。！？)切分
    │  句子还长 → 按 chunk_size 强制切割
    │
    ▼
每个块都有 metadata：{source, filename, format, heading, chunk_index}
```

### 4.3 BM25Retriever（自实现 BM25）

Week 4 没有使用 `rank_bm25` 库，而是自己实现了 BM25 算法：

```python
class BM25Retriever:
    def index(self, documents):
        # 1. 对每个文档分词
        # 2. 统计词频（TF）
        # 3. 计算逆文档频率（IDF）
        # 4. 计算平均文档长度

    def search(self, query, top_k):
        # 1. 对查询分词
        # 2. 对每个文档计算 BM25 分数
        # 3. 排序返回 top_k
```

**BM25 公式**：
```
score(D, Q) = Σ IDF(qi) × (TF(qi,D) × (k1+1)) / (TF(qi,D) + k1 × (1 - b + b × |D|/avgdl))

其中：
  IDF = 词的稀有度（越稀有的词权重越高）
  TF = 词在文档中的出现次数
  k1 = 1.5（控制词频饱和速度）
  b = 0.75（控制文档长度归一化强度）
```

### 4.4 HybridSearcher（混合检索）

使用 RRF（Reciprocal Rank Fusion）融合向量和 BM25 结果：

```python
# 向量检索和 BM25 各返回一个排序列表
vector_ranked = [(doc_id, score), ...]  # 按相似度排序
bm25_ranked = [(doc_id, score), ...]    # 按 BM25 分排序

# RRF 融合
for rank, (doc_id, _) in enumerate(rank_list, 1):
    scores[doc_id] += weight / (k + rank)
    # k=60：平滑参数
    # weight：向量 0.7，BM25 0.3
```

### 4.5 QueryRewriter（查询改写）

Week 4 用了更轻量的规则改写（不依赖 LLM）：

```python
# 关键词提取：去停用词
"什么是 RAG 的核心思路？"
→ 去掉 "什么""的""是" 等停用词
→ "RAG 核心 思路"

# 子问题拆解：按标点分割
"RAG 怎么用？有什么优缺点？"
→ ["RAG 怎么用", "有什么优缺点"]
```

### 4.6 LLMGenerator（LLM 回答生成）

Week 4 切换为 DeepSeek API（之前用智谱 AI）：

```python
prompt = f"""你是一个知识库问答助手。
请基于以下检索到的文档内容回答用户的问题。
如果文档内容不足以回答问题，请如实说明。

## 检索到的文档内容
[来源: rag_overview.md]
RAG 的核心思路是...

## 用户问题
{query}

## 回答要求
1. 基于文档内容回答，不要编造
2. 标注引用来源
"""
```

---

## 5. 使用方式

```bash
# 进入 Week 4 目录
cd src/week4

# 索引文档 + 交互模式（最常用）
python knowledge_base_rag.py --index --interactive

# 单次查询
python knowledge_base_rag.py --index -q "什么是 RAG？"

# 查看知识库统计
python knowledge_base_rag.py --index --stats

# 指定文档目录
python knowledge_base_rag.py --doc-dir /path/to/docs --index -q "向量数据库对比"
```

---

## 6. 配置参数速查

```python
@dataclass
class RAGConfig:
    doc_dir: str = "./docs"              # 文档目录
    chroma_dir: str = "./chroma_db"      # ChromaDB 存储目录
    embedding_model: str = "qwen3-embedding:4b"  # Embedding 模型
    llm_model: str = "deepseek-chat"     # LLM 模型
    chunk_size: int = 512                # 分块大小（字符）
    chunk_overlap: int = 50              # 重叠大小
    top_k: int = 5                       # 检索结果数
    vector_weight: float = 0.7           # 向量检索权重
    bm25_weight: float = 0.3            # BM25 权重
```

---

## 7. 第 3 月技术栈全景

```
┌─────────────────────────────────────────────────┐
│              第 3 月学到的所有技术                 │
├─────────────────────────────────────────────────┤
│                                                   │
│  Embedding 模型                                   │
│    └── Ollama qwen3-embedding:4b（2560 维，中文）  │
│                                                   │
│  向量数据库                                       │
│    └── ChromaDB（持久化，元数据过滤）               │
│                                                   │
│  关键词检索                                       │
│    └── BM25（自实现，支持中文分词）                │
│                                                   │
│  融合算法                                         │
│    └── RRF（Reciprocal Rank Fusion）              │
│                                                   │
│  LLM 生成                                         │
│    └── DeepSeek API / 智谱 AI GLM                 │
│                                                   │
│  文档处理                                         │
│    └── 标准库 + PyMuPDF                           │
│                                                   │
│  分块策略                                         │
│    └── Markdown 标题感知 + 递归分块               │
│                                                   │
│  查询优化                                         │
│    └── 关键词提取 + 子问题拆解                     │
│                                                   │
│  评估指标                                         │
│    └── Hit Rate / MRR / nDCG                      │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## 8. 关键领悟

1. **工程化 > 炫技**：一个完整的系统不在于用了多少花哨技术，而在于每个环节都可靠
2. **分块是 RAG 的灵魂**：分块策略直接决定检索质量，比模型选择更重要
3. **错误处理不可忽视**：PDF 解析失败、LLM 超时、API Key 缺失，每个都要优雅降级
4. **元数据是宝藏**：记录来源、标题、格式，用户才能信任回答
5. **渐进式设计**：先跑通基础流程，再叠加 Hybrid Search、Query Rewriting 等优化

---

## 9. 从学习项目到生产系统的差距

| 维度 | 我们的学习项目 | 生产级系统 |
|------|-------------|-----------|
| 文档规模 | 5~20 篇 | 1000~100000 篇 |
| 更新频率 | 手动重建索引 | 自动增量更新 |
| 并发处理 | 单线程 | 异步 + 连接池 |
| 监控 | print 日志 | 结构化日志 + 指标 |
| 安全 | 无 | API 鉴权 + 数据隔离 |
| 评测 | 10 个查询 | 100+ 查询 + 自动回归 |

学习项目不需要做这些，但知道"生产需要什么"很重要。

---

## 10. 下一步

第 3 月结束后，你已经具备了搭建完整 RAG 系统的能力。

第 4 月的方向：
- **Agent 与 Multi-Agent 系统**：让 AI 不只是"回答问题"，还能"主动做事"
- 结合第 1 月的 Tool 调用 + 第 2 月的 Graph 编排 + 第 3 月的 RAG 知识 = 全能 Agent

---

## 自检清单

- [ ] 能画出完整 RAG 系统的架构图
- [ ] 知道每个组件用了什么技术
- [ ] 理解为什么选 ChromaDB 而不是 FAISS
- [ ] 理解为什么用 Hybrid Search 而不是纯向量
- [ ] 知道系统从"学习"到"生产"还需要做什么
- [ ] 能独立运行 `knowledge_base_rag.py` 并测试
