# Week 1 复盘笔记：RAG 基础与向量检索

## 💡 小白科普：本周在学什么？

本周的目标是：**让 AI 拥有“翻书找答案”的能力**。

想象你在参加考试：
- **没有 RAG** = 闭卷考试：只能凭记忆答题，不会的就可能瞎编
- **有 RAG** = 开卷考试：先翻书找答案，再组织语言

本周你会学到 4 个核心概念：

| 概念 | 一句话解释 | 类比 |
|------|-----------|------|
| **RAG** | 给 AI 外接一个“搜索引擎” | 开卷考试的参考书 |
| **Embedding** | 把文字变成一串数字（语义指纹） | 图书馆的索引编号 |
| **向量数据库** | 存储和检索“语义指纹”的数据库 | 图书馆的检索系统 |
| **余弦相似度** | 两个“指纹”有多像（0~1，越大越像） | 两张照片的相似度 |

> 📖 更详细的科普请阅读 `doc/RAG-Fundamentals.md` 和 `doc/Embedding-VectorDB.md`

---

## 📊 本周完成情况

| Day | 任务 | 产出 | 状态 |
|-----|------|------|------|
| Day 1-2 | RAG 概念与环境搭建 | `rag_basics.py` | ✅ |
| Day 3-4 | Embedding 与向量数据库 | `embedding_demo.py`, `chroma_basics.py` | ✅ |
| Day 5-6 | 第一个完整 RAG Pipeline | `simple_rag.py` | ✅ |
| Day 7 | 复盘笔记 | 本文件 | ✅ |

**实际用时**: ~3 小时（预计 3-4 小时）

---

## 🔑 核心知识点

### 1. RAG 的完整架构

RAG = **R**etrieval-**A**ugmented **G**eneration（检索增强生成）

三个阶段：

```
┌──────────────────────────────────────────────────────┐
│                 Indexing（离线，只做一次）              │
│                                                      │
│  文档 ──→ 分块 ──→ Embedding ──→ 存入向量数据库        │
│                                                      │
├──────────────────────────────────────────────────────┤
│                 Query（在线，每次查询时）               │
│                                                      │
│  用户问题 ──→ Embedding ──→ 向量检索 Top-K            │
│                                        ↓             │
│                          拼接到 Prompt（Augmented）    │
│                                        ↓             │
│                          LLM 生成回答（Generation）    │
└──────────────────────────────────────────────────────┘
```

### 2. 为什么需要 RAG？

LLM 的三大痛点及 RAG 的解决方案：

| LLM 痛点 | 具体表现 | RAG 解决方案 |
|----------|---------|-------------|
| **知识截止** | 训练数据有截止日期，不知道最新信息 | 知识库可随时更新，不需要重新训练 |
| **幻觉** | 对不知道的问题"一本正经地胡说" | 基于真实文档回答，有据可查 |
| **私有数据** | 企业内部文档，LLM 训练数据里没有 | 数据不出本地，安全合规 |

类比：
- 没有 RAG = 闭卷考试（只能凭记忆）
- 有了 RAG = 开卷考试（先翻书找答案，再组织语言）

### 3. Embedding 详解

**是什么**：把文本映射到高维向量空间中的一串数字

```
"Python 怎么创建字典？" → [0.123, -0.456, 0.789, ..., 0.012]  ← 2560 个浮点数
"如何使用 dict 类型？"   → [0.118, -0.443, 0.801, ..., 0.015]  ← 语义相近，向量接近
"今天天气怎么样？"       → [0.001, 0.892, -0.234, ..., 0.678]  ← 语义不同，向量远离
```

**关键性质**：语义相近的文本 → 向量在高维空间中距离近

**为什么能这样**：
- Embedding 模型在训练时学习了"词语之间的共现关系"
- "猫"和"狗"经常出现在相似的上下文 → 模型学到它们语义相近 → 向量接近
- "猫"和"汽车"很少一起出现 → 模型学到它们语义不同 → 向量远离

**常用模型对比**：

| 模型 | 维度 | 语言 | 特点 |
|------|------|------|------|
| all-MiniLM-L6-v2 | 384 | 英文 | ChromaDB 默认，对中文效果差 |
| text-embedding-3-small | 1536 | 多语言 | OpenAI，效果好但要 API 费用 |
| qwen3-embedding:4b | 2560 | 中文优化 | Ollama 本地，免费，中文效果好 |

**余弦相似度**：
- 公式：cos(θ) = (A·B) / (|A| × |B|)
- 范围：-1 ~ 1（RAG 中一般 0 ~ 1）
- 1.0 = 完全相同，0.0 = 完全不相关
- 经验值：> 0.8 高度相关，0.5~0.8 中度相关，< 0.5 不太相关

### 4. ChromaDB 详解

**是什么**：开源向量数据库，专为 AI 应用设计

**数据模型**：
```
Client（数据库连接）
  └── Collection（类似 SQL 的表）
        ├── Document（文本内容）
        ├── Embedding（自动生成的向量）
        ├── Metadata（附加信息，可过滤）
        └── ID（唯一标识）
```

**两种模式**：
- `Client()` — 内存模式，程序结束数据消失（适合测试）
- `PersistentClient(path=...)` — 持久化到磁盘（适合生产）

**五大操作**：

```python
# CREATE — 添加文档
collection.add(
    documents=["文档内容"],      # 会自动生成 Embedding
    ids=["doc1"],                # 唯一 ID
    metadatas=[{"topic": "xx"}]  # 可选的附加信息
)

# QUERY — 语义查询（最核心）
results = collection.query(
    query_texts=["用户问题"],    # 会自动生成 Embedding
    n_results=2,                 # 返回最相似的 2 个
    where={"topic": "xx"},       # 可选的 metadata 过滤
)
# 返回：documents, distances, metadatas, ids

# GET — 按 ID 获取
result = collection.get(ids=["doc1", "doc2"])

# UPDATE — 更新文档（Embedding 会重新生成）
collection.update(ids=["doc1"], documents=["新内容"])

# DELETE — 删除文档
collection.delete(ids=["doc1"])
```

**distance 含义**（cosine 空间）：
- 0.0 ~ 0.3: 非常相关（几乎就是同一内容）
- 0.3 ~ 0.6: 高度相关（包含想要的信息）
- 0.6 ~ 1.0: 有一定相关性
- \> 1.0: 不太相关

### 5. SimpleRAG Pipeline 设计

```python
class SimpleRAG:
    def __init__(persist_dir=None)  # 初始化 ChromaDB + Embedding + LLM
    def index(documents)            # Indexing: 文档入库
    def retrieve(query, top_k=2)    # Retrieval: 语义检索
    def generate(query, docs)       # Generation: LLM 回答
    def query(question, top_k=2)    # 完整 Pipeline: retrieve + generate
```

**Prompt 设计要点**：
1. 明确角色（"你是一个专业的电商客服"）
2. 约束行为（"只根据参考资料回答"）
3. 减少幻觉（"不要编造信息"）
4. 可追溯（"引用信息来源"）
5. 诚实回答（"没有答案就说不确定"）

**关键参数**：

| 参数 | 含义 | 经验值 |
|------|------|--------|
| top_k | 检索返回的文档数 | 2~5（太多会引入噪声，太少可能遗漏） |
| temperature | LLM 生成温度 | RAG 场景 0.1~0.3（忠于文档，不要发挥创意） |
| max_tokens | 回答最大长度 | 300~500（RAG 回答通常不需要太长） |

---

## 🔍 关键发现

### 发现 1：关键词匹配 vs 语义检索

**rag_basics.py 暴露的关键词匹配缺陷**：

| 用户问题 | 期望匹配 | 关键词匹配结果 | 原因 |
|---------|---------|--------------|------|
| "Python 怎么创建字典？" | doc2 | doc1, doc2 (得分 1) | ✅ 正好匹配到"字典" |
| "什么是不可变的序列？" | doc3 (元组) | **所有 0 分** | ❌ query 里没有"元组" |
| "Python 有哪些数据类型？" | 全部 | doc1, doc2 (得分 1) | ⚠️ 太模糊 |

核心问题：**关键词匹配不理解"语义"，只匹配"字面"**
- "不可变的序列" = "元组"，但关键词匹配不知道
- "去除重复" = "集合去重"，但关键词匹配不知道

**simple_rag.py 验证的语义检索优势**：

| 用户问题 | 期望文档 | 实际检索 | 结果 |
|---------|---------|---------|------|
| "买了手机用了一个月坏了怎么办？" | product_warranty | product_warranty (0.59) | ✅ |
| "怎么才能免运费？" | shipping_info | shipping_info (0.55) | ✅ |
| "退款多久能到账？" | refund_policy | refund_policy (0.51) | ✅ |
| "钻石会员有什么好处？" | vip_benefits | vip_benefits (0.47) | ✅ |
| "我昨天下的单怎么还没收到？" | shipping_info | shipping_info (0.51) | ✅ |
| "能同时用两张优惠券吗？" | coupon_rules | coupon_rules (0.46) | ✅ |

**6/6 全对！** 语义检索能理解口语、同义词、隐含语义。

### 发现 2：中文场景必须用中文 Embedding 模型

**embedding_demo.py Part 4 的对比实验**：

使用 ChromaDB 默认 `all-MiniLM-L6-v2`（英文模型）：
| 测试问题 | 期望 | 实际 | 结果 |
|---------|------|------|------|
| "什么是不可变的序列？" | d3 | d5 | ❌ |
| "怎么去除重复？" | d4 | d3 | ❌ |
| "键值对怎么用？" | d2 | d3 | ❌ |

**0/3 正确！** 英文模型对中文的语义理解能力极差。

切换到 `qwen3-embedding:4b`（中文模型）后：**6/6 全对！**

**结论**：
- Embedding 模型的语言能力是 RAG 质量的基础
- 中文场景必须用中文优化的 Embedding 模型
- 这也是 Week 3 学习 Hybrid Search 的动机之一

### 发现 3：检索质量决定回答质量

RAG 的核心瓶颈在 **Retrieval** 而非 Generation：

```
检索到了正确文档 → LLM 能基于正确信息回答 → 回答准确 ✅
检索到了错误文档 → LLM 基于错误信息回答 → "一本正经地胡说" ❌
```

LLM 本身是"听话的好学生"——你给它什么参考资料，它就基于什么回答。
如果给错了参考资料，它不会质疑，而是忠实地基于错误资料生成回答。

**这就是为什么 Week 3 要学 Reranking 和 Hybrid Search**——进一步提升检索质量。

---

## ⚠️ 踩坑记录

### 1. API Key 配置

- 阿里云百炼 API Key 已弃用，切换为智谱 AI
- `.env` 文件路径：`/Users/liyang/dev/python_project/ly-ai-roadmap-lab/.env`
- 当前有效配置：`ZHIPUAI_API_KEY="ec5080…NZgk"`

### 2. 依赖安装

- `pip install chromadb` — 向量数据库
- `pip install ollama` — ChromaDB 的 OllamaEmbeddingFunction 依赖
- `pip install numpy` — 余弦相似度计算

### 3. ChromaDB 首次运行

- 首次使用会自动下载 `all-MiniLM-L6-v2` ONNX 模型（79MB）
- 即使你用的是 Ollama Embedding，ChromaDB 也会下载这个默认模型
- 下载路径：`~/.cache/chroma/onnx_models/`

### 4. Ollama 服务

- 确保 Ollama 正在运行：`ollama serve`
- Embedding 模型需要提前拉取：`ollama pull qwen3-embedding:4b`
- 调用 API：`POST http://localhost:11434/api/embed`

---

## 🎯 Week 2 预告

| 主题 | 内容 |
|------|------|
| 文档加载 | PDF、Markdown、HTML 文件的处理 |
| 分块策略 | 固定长度 vs 语义分块 vs 递归分块，不同策略的适用场景 |
| 元数据管理 | 来源、页码、章节等附加信息 |
| 实战 | 用真实文档（而非硬编码文本）构建更大的知识库 |

Week 1 用的是硬编码的小文档集（5 篇），Week 2 要处理真实文档文件。

---

## 📝 自检清单

- [x] 能画出 RAG 的三阶段架构图（Indexing / Retrieval / Generation）
- [x] 能解释为什么 LLM 需要 RAG（知识截止、幻觉、私有数据）
- [x] 能解释 Embedding 的作用：文本 → 向量，语义相近 → 向量接近
- [x] 能解释余弦相似度的含义和范围（-1 ~ 1）
- [x] 能说出 ChromaDB 的五大操作：add / query / get / update / delete
- [x] 能说出 distance 的含义（0 = 完全相同，越大越不相关）
- [x] 能解释 top_k 的作用和经验值（2~5）
- [x] 能解释为什么 RAG 场景 temperature 要设低（忠于文档，不要发挥创意）
- [x] 理解关键词匹配 vs 语义检索的区别和局限性
- [x] 理解中文场景必须用中文 Embedding 模型
- [x] 理解"检索质量决定回答质量"—— Retrieval 是 RAG 的核心瓶颈
