# Week 2 复盘笔记：文档处理与分块策略

## 📊 本周完成情况

| Day | 任务 | 产出 | 状态 |
|-----|------|------|------|
| Day 1-2 | 文档加载器 | `doc_loader.py` + sample_files/ | ✅ |
| Day 3-5 | 分块策略对比 | `chunking_strategies.py` | ✅ |
| Day 5-6 | 多格式文档 RAG 实战 | `multi_format_rag.py` | ✅ |
| Day 7 | 复盘笔记 | 本文件 | ✅ |

**实际用时**: ~3 小时

---

## 🔑 核心知识点

### 1. 文档加载器：RAG 的输入管道

```
文档文件 ──→ 加载器 ──→ Document(page_content, metadata) ──→ 分块 ──→ 索引
```

**四种核心加载器对比**：

| 加载器 | 处理格式 | 输出方式 | 关键依赖 |
|--------|---------|---------|---------|
| TextLoader | .txt, .log | 整体加载，1 个 Document | 无 |
| 自制 Markdown 解析 | .md | 整体加载，但保留结构 | 无（标准库） |
| 自制 HTML 解析 | .html | 整体加载，去标签 | 无（标准库） |
| PyMuPDFLoader | .pdf | 按页拆分，每页 1 个 Document | pymupdf |

**实践中发现**：LangChain 内置的 `UnstructuredMDLoader` 和 `UnstructuredHTMLLoader` 依赖 spaCy + en_core_web_sm 模型，安装很麻烦。我们使用 Python 标准库（`re` + `html.parser`）实现了等价的轻量替代方案。

**JSON/结构化数据**：需要手动构建 `Document` 对象，但可以精确控制 metadata（标题、作者、标签等）。

### 2. 分块策略：最关键的工程决策

**为什么分块很重要**：
- 分块太短 → 信息碎片化，检索不完整
- 分块太长 → 多个主题混在一起，检索不精确
- 分块质量 → 直接影响 RAG 回答质量

**四种策略详细对比**：

| 策略 | 实现类 | 原理 | 适用场景 | 推荐度 |
|------|-------|------|---------|-------|
| 固定长度 | `CharacterTextSplitter` | 按字符数硬切 | 代码、日志 | ⭐⭐ |
| 递归分块 | `RecursiveCharacterTextSplitter` | 按分隔符优先级递归 | 通用文本 | ⭐⭐⭐⭐ |
| Markdown 分块 | `MarkdownHeaderTextSplitter` | 按标题切分 | 结构化文档 | ⭐⭐⭐ |
| 组合策略 | 两者结合 | 先标题再递归 | 长文档 | ⭐⭐⭐⭐⭐ |

**关键参数**：

```python
RecursiveCharacterTextSplitter(
    chunk_size=300,          # 块目标大小（字符数）
    chunk_overlap=50,         # 重叠部分（10-20%）
    separators=["\n\n", "\n", "。", "！", "？", " ", ""],  # 中文适配
)
```

**组合策略的核心思想**：
1. 先用 `MarkdownHeaderTextSplitter` 按章节切分（保留结构）
2. 如果某个章节正文 > 400 字符，再用递归分块细化

这样既保留了章节上下文，又避免了单个块过大的问题。

### 3. 元数据管理：让检索更智能

**好的 metadata 设计**：
```python
chunk.metadata = {
    "source": "product_faq.md",          # 来源文件名
    "format": "markdown",               # 文档格式
    "path": "/full/path/...",           # 完整路径
    "chapter": "基础信息",               # 章节（MD 分块自动生成）
    "section": "产品规格",               # 小节
}
```

**metadata 的三大用途**：
1. **溯源**：回答时引用来源文件和章节
2. **过滤**：按格式/来源只检索特定文档
3. **调试**：快速定位问题文档块

### 4. 多格式文档 RAG Pipeline

```
sample_files/                    ChromaDB (持久化)
├── product_faq.md  ──→ MarkdownSplitter ──→ 5 chunks ──┐
├── ai_trends.html  ──→ HTML Parser ──→ 3 chunks ──────┤
├── python_notes.txt──→ RecursiveSplitter ──→ 2 chunks ─┼──→ Embedding → VectorStore
├── user_manual.pdf ──→ PyMuPDFLoader ──→ 3 chunks ────┤
└── knowledge.json  ──→ Manual Doc ──→ 2 chunks ──────┘
                              │
                              ▼
                      MultiFormatRAG
                     ├── retrieve(query, filter)
                     └── generate(query, docs)
```

---

## 🔍 关键发现

### 发现 1：分块策略对检索结果影响显著

在 `multi_format_rag.py` 的测试中：

| 问题 | 正确检索？ | 正确回答？ | 备注 |
|------|-----------|-----------|------|
| "X100 防水等级？" | ✅ (product_faq.md) | ✅ IP68，可游泳 | 语义匹配完美 |
| "回家模式有哪些功能？" | ❌ (没命中 smart_home) | ✅ 诚实说不知道 | 知识库中没有智能家居文档 |
| "智能网关无法连接" | ❌ (命中 pdf) | ✅ 诚实说不知道 | 同上 |
| "RAG 核心思路" | ✅ (knowledge_articles.json) | ✅ 准确回答 | JSON 结构化数据检索成功 |
| "AI 行业趋势" | ✅ (ai_trends.html) | ✅ 多条趋势准确回答 | HTML 表格类数据检索成功 |

**结论**：
- 检索准确率取决于知识库覆盖度（"回家模式"没命中是因为没放相关文档）
- 语义检索理解中文口语/缩写效果很好
- 当检索不到时，LLM 能诚实回答"不知道"（prompt 设计的功劳）

### 发现 2：metadata 过滤很强大

**测试结果**：
- `filter={"format": "markdown"}` → 只从 product_faq.md 检索 ✅
- `filter={"format": "html"}` → 只从 ai_trends.html 检索 ✅
- `filter={"format": "pdf"}` → 只从 user_manual.pdf 检索 ✅

这在大规模知识库中非常有用——可以按文档来源、格式、时间等维度精确控制检索范围。

### 发现 3：LangChain 生态的兼容性挑战

- `langchain-community` 已被标记为 deprecated，但 `langchain-ollama`（新替代品）还没成熟
- `Unstructured` 系列加载器依赖复杂（spaCy 模型下载需要写权限）
- ChromaDB 从 0.4.x 开始不再需要手动 `persist()`
- 实践中，用标准库替代外部依赖更稳定

### 发现 4：Week 1 vs Week 2 的关键差异

| 维度 | Week 1 | Week 2 |
|------|--------|--------|
| 文档来源 | 硬编码字符串（5 篇） | 真实文件（5 个文件，15 个块） |
| 分块 | 整篇存入，不分块 | 按策略分块（组合策略） |
| 元数据 | 简单（source + category） | 丰富（格式/路径/章节/来源） |
| 检索 | 仅语义检索 | 语义 + metadata 过滤 |
| 溯源 | 简单来源名 | 文件名 + 章节引用 |
| 可扩展性 | 固定文档，不能增减 | 扫描目录，增减文件自动加载 |

---

## ⚠️ 踩坑记录

### 1. unstructured 加载器的 spaCy 依赖

**问题**：`UnstructuredMarkdownLoader` 和 `UnstructuredHTMLLoader` 运行时自动下载 `en_core_web_sm` 到系统目录，但 `/Library/Frameworks/Python.framework/` 目录不可写，导致 PermissionError。

**解决**：用 Python 标准库（`re.sub` + `html.unescape`）自行实现轻量级格式剥离。

### 2. ChromaDB filter 空字典异常

**问题**：`Chroma.as_retriever(search_kwargs={"filter": {}})` 传递空字典时，ChromaDB 抛出 `ValueError: Expected where to have exactly one operator, got {}`。

**解决**：只在有过滤条件时才添加 filter 参数。

### 3. 中文分句的 separator 配置

**问题**：默认的 `RecursiveCharacterTextSplitter` separator 列表 `["\n\n", "\n", " ", ""]` 对中文效果不好——中文句子用句号 `。` 分隔，而不是空格。

**解决**：添加中文字号分隔符：`["\n\n", "\n", "。", "！", "？", " ", ""]`

---

## 📝 自检清单

- [x] 能说出 4 种文档加载器及其适用场景
- [x] 知道如何用 Python 标准库解析 Markdown 和 HTML
- [x] 能解释为什么分块对 RAG 如此重要
- [x] 能说出 4 种分块策略的原理和优缺点
- [x] 知道 chunk_size 和 chunk_overlap 的参数含义和经验值
- [x] 理解组合策略：Markdown 标题分块 + 递归细化
- [x] 能设计 metadata 结构并用于过滤检索
- [x] 能构建多格式文档的 RAG Pipeline
- [x] 理解 Week 2 和 Week 1 的关键差异

---

## 🎯 Week 3 预告

| 主题 | 内容 |
|------|------|
| Hybrid Search | 向量检索 + BM25 关键词检索 |
| Reranking | Cross-Encoder 重排序 |
| Query 改写 | 用户问题改写与扩展 |
| 效果评估 | Hit Rate、MRR、nDCG |

Week 2 解决了"文档从哪里来"和"怎么切"的问题。
Week 3 要解决"怎么检索得更准"——引入 Hybrid Search + Reranking。
