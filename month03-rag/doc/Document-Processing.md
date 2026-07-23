# 文档处理与分块策略科普

> 配套 Week 2 内容。如果你想知道"真实文档（PDF/网页/Markdown）怎么喂给 AI"以及"为什么要分块"，看这篇。

---

## 1. 为什么需要文档处理？

### Week 1 vs Week 2 的区别

Week 1 我们用的是"硬编码"的文本：

```python
# Week 1: 直接写在代码里的文档
KNOWLEDGE_DOCS = [
    {"id": "refund_policy", "text": "退款政策：未发货订单支持全额退款..."},
    {"id": "shipping_info", "text": "物流配送说明：默认快递顺丰..."},
]
```

这在真实项目中不可行——你的公司不可能把几百篇文档都写在代码里。

Week 2 解决的是：**从真实文件中读取文档**。

```
sample_files/
├── product_faq.md       ← Markdown 文件（产品 FAQ）
├── ai_trends.html       ← HTML 文件（新闻文章）
├── python_notes.txt     ← 纯文本文件（学习笔记）
├── user_manual.pdf      ← PDF 文件（产品手册）
└── knowledge_articles.json  ← JSON 文件（结构化文章）
```

---

## 2. 文档加载器：把文件变成"统一格式"

### 核心问题

不同格式的文件有不同的结构：
- PDF 有页码、有排版
- HTML 有标签（`<h1>`, `<p>`, `<div>`）
- Markdown 有标题层级（`#`, `##`, `###`）

但 RAG 系统需要统一的格式来处理。这个统一格式就是 LangChain 的 `Document` 对象：

```python
Document(
    page_content="文档的文字内容",
    metadata={"source": "文件名", "format": "格式", ...}
)
```

### 四种加载器对比

| 加载器 | 处理格式 | 特点 | 注意事项 |
|--------|---------|------|---------|
| **TextLoader** | .txt, .log | 最简单，不做任何解析 | 无 |
| **自制 Markdown 解析** | .md | 用正则去掉 #、** 等标记 | 不依赖外部库 |
| **自制 HTML 解析** | .html | 去掉 `<标签>`，保留文字 | 不依赖外部库 |
| **PyMuPDFLoader** | .pdf | 按页拆分，每页一个 Document | 需安装 pymupdf |

### 为什么不直接用 LangChain 内置加载器？

LangChain 的 `UnstructuredMarkdownLoader` 和 `UnstructuredHTMLLoader` 需要安装 spaCy + en_core_web_sm 模型，安装过程很麻烦，还容易出错。

我们用 Python 标准库（`re` + `html.parser`）实现了等价的轻量替代方案，效果一样好，还不需要额外依赖。

### Markdown 加载示例

```python
# 原始 Markdown 内容
"""
# 智能手表 X100

## 产品规格
- 屏幕：1.5英寸 AMOLED
- 防水：IP68 级
"""

# 去掉 Markdown 标记后
"""
智能手表 X100

产品规格
- 屏幕：1.5英寸 AMOLED
- 防水：IP68 级
"""
```

### JSON 加载示例

JSON 文件需要手动构建 Document 对象，但可以精确控制元数据：

```python
doc = Document(
    page_content=article["content"],
    metadata={
        "source": "knowledge_articles.json",
        "title": article["title"],
        "author": article["author"],
        "tags": "RAG, Tutorial",
    }
)
```

---

## 3. 分块：RAG 中最关键的工程决策

### 为什么不能把整篇文档直接存？

假设你有一篇 5000 字的产品手册。如果整篇存入：

**问题 1：检索不精确**
```
用户问："X100 防水吗？"
系统检索到整篇 5000 字的手册 → 里面只有 1 段提到防水
→ LLM 需要从 5000 字里找到那段话，又慢又容易出错
```

**问题 2：上下文窗口浪费**
```
LLM 的上下文窗口有限（比如 128K tokens）
如果把 5 篇 5000 字的文档都塞进去 → 25000 字 ≈ 15000 tokens
→ 大量不相关内容占用了宝贵的上下文空间
```

**问题 3：多主题混杂**
```
一篇文档可能包含 10 个不同主题
整篇存入 → 一个向量代表了 10 个主题的"混合语义"
→ 检索时匹配度下降
```

### 分块的目标

把文档切成"语义完整的小段落"，使得：
- 每个块只包含一个主题
- 每个块的信息是完整的（不是半句话）
- 检索时能精确命中相关段落

---

## 4. 四种分块策略详解

### 策略 1：固定长度分块

**原理**：每 N 个字符切一刀，不管内容是什么。

```python
CharacterTextSplitter(
    separator="\n",
    chunk_size=200,     # 每个块目标 200 字符
    chunk_overlap=30,   # 相邻块重叠 30 字符
)
```

**优点**：简单快速
**缺点**：可能切在句子中间，破坏语义

```
原文：Python 的列表是有序可变序列。可以用方括号创建。
          ↑ 如果正好在这里切一刀 ↓
块 1：Python 的列表是有序可变
块 2：序列。可以用方括号创建。
→ 两半都不完整！
```

**适用场景**：代码文件、日志文件等不需要语义完整性的内容。

### 策略 2：递归分块（推荐首选）

**原理**：按分隔符优先级逐级切分，尽量保持段落完整。

```python
RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=30,
    separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    #           ↑段落    ↑句子   ↑中文句号  ↑最后手段
)
```

**工作流程**：
1. 先按 `\n\n`（段落）切 → 如果每段都 < 200 字 → 完成
2. 某段 > 200 字 → 按 `\n`（换行）切 → 如果每段都 < 200 字 → 完成
3. 某段 > 200 字 → 按 `。`（句号）切 → ...
4. 最后的兜底：按空格或字符硬切

**优点**：保持段落和句子完整性
**缺点**：不考虑文档的章节结构

**适用场景**：通用文本，大多数 RAG 场景首选。

### 策略 3：Markdown 标题分块

**原理**：按 Markdown 标题（`#`, `##`, `###`）切分，保留章节信息。

```python
MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "章节"),     # H1 → metadata["章节"]
        ("##", "小节"),    # H2 → metadata["小节"]
        ("###", "子节"),   # H3 → metadata["子节"]
    ],
)
```

**效果**：
```
块 1: {内容: "...", metadata: {章节: "X100手册", 小节: "产品规格"}}
块 2: {内容: "...", metadata: {章节: "X100手册", 小节: "常见问题"}}
```

**优点**：保留章节结构，metadata 可用于溯源
**缺点**：如果某个章节内容太长，块会过大

**适用场景**：有良好标题结构的 Markdown 文档。

### 策略 4：组合策略（最推荐）

**原理**：先按 Markdown 标题切分，再对过长的章节用递归分块细化。

```python
# 第一步：按标题切分
md_chunks = markdown_splitter.split_text(document)

# 第二步：对过长的块（> 400 字符）递归细化
for chunk in md_chunks:
    if len(chunk.page_content) > 400:
        sub_chunks = recursive_splitter.split_documents([chunk])
        # 保留原来的章节 metadata
        for sc in sub_chunks:
            sc.metadata.update(chunk.metadata)
```

**优点**：兼顾结构完整性和块大小控制
**缺点**：实现稍复杂

**适用场景**：结构化长文档（产品手册、技术文档）。

---

## 5. 分块参数怎么选？

### chunk_size（块大小）

| chunk_size | 适用场景 | 说明 |
|-----------|---------|------|
| 100~200 | FAQ、短问答 | 每块信息量小，检索很精确 |
| 300~500 | 通用文档 | 推荐范围 |
| 500~1000 | 长报告、论文 | 信息量大，但检索精度下降 |

### chunk_overlap（重叠大小）

**为什么需要重叠？**

假设一个话题正好跨越了块的边界：
```
不重叠：
  块 1：...X100 的防水等级是 IP68
  块 2：可以在 50 米水深下工作...
→ 如果用户问"X100 能潜水多深"，块 1 知道型号和等级，块 2 知道深度，但两个块各自不完整

有重叠：
  块 1：...X100 的防水等级是 IP68，可以在 50 米
  块 2：IP68，可以在 50 米水深下工作...
→ 两个块都包含完整信息，检索更可靠
```

**经验值**：chunk_size 的 10%~20%
- chunk_size=300 → overlap=30~60
- chunk_size=500 → overlap=50~100

### 中文分隔符配置

默认的英文分隔符 `["\n\n", "\n", " ", ""]` 对中文效果不好——中文句子用句号分隔，不是空格。

**中文适配版**：
```python
separators=["\n\n", "\n", "。", "！", "？", " ", ""]
```

---

## 6. 元数据（Metadata）：让检索更智能

### 什么是元数据？

元数据是附加在文档块上的"标签"，用来描述文档的属性。

```python
chunk.metadata = {
    "source": "product_faq.md",     # 来自哪个文件
    "format": "markdown",           # 什么格式
    "path": "/full/path/...",       # 完整路径
    "chapter": "基础信息",           # 属于哪个章节
    "section": "产品规格",           # 属于哪个小节
}
```

### 元数据的三大用途

**用途 1：溯源** — 回答时告诉用户信息来源
```
AI 回答：X100 支持 IP68 防水，可在 50 米水深下工作。
来源：product_faq.md → 常见问题 → Q: 支持游泳佩戴吗？
```

**用途 2：过滤** — 只在特定文档中搜索
```python
# 只在 Markdown 格式文档中搜索
results = collection.query(
    query_texts=["X100 防水等级"],
    where={"format": "markdown"}
)
```

**用途 3：调试** — 快速定位问题出在哪个文档块

---

## 7. 多格式文档 RAG 架构

Week 2 的完整 Pipeline：

```
sample_files/ 目录                  ChromaDB (持久化)
├── product_faq.md  ─→ MD标题分块 → 5 chunks ──┐
├── ai_trends.html  ─→ HTML解析  → 3 chunks ──┤
├── python_notes.txt─→ 递归分块  → 2 chunks ──┼──→ Embedding → 向量存储
├── user_manual.pdf ─→ PDF按页   → 3 chunks ──┤
└── knowledge.json  ─→ 手动构建  → 2 chunks ──┘
                                                      │
用户问题 ─→ 语义检索 + metadata 过滤 ←─────────────────┘
    │
    ▼
LLM 生成回答（带引用溯源）
```

---

## 8. 踩坑记录

| 坑 | 原因 | 解决方案 |
|----|------|---------|
| spaCy 依赖安装失败 | Unstructured 加载器需要 spaCy 模型 | 用标准库自建解析器 |
| ChromaDB 空字典过滤报错 | `where={}` 被当作有效过滤条件 | 只在有过滤条件时才传 filter |
| 中文分块效果差 | 默认分隔符是英文的 | 添加 `。！？` 中文字号分隔符 |
| PDF 加载失败 | 没安装 pymupdf | `pip install pymupdf` |
| 扫描版 PDF 无法读取 | PyMuPDFLoader 不支持 OCR | 需要用 pytesseract 等 OCR 方案 |

---

## 9. 自检清单

- [ ] 知道 4 种文档加载器及适用格式
- [ ] 理解为什么分块对 RAG 至关重要
- [ ] 知道 4 种分块策略的原理和优缺点
- [ ] 理解 chunk_size 和 chunk_overlap 的含义
- [ ] 知道组合策略的设计思路
- [ ] 理解 metadata 的三大用途

---

## 下一步

- 动手实践：前往 `src/week2/chunking_strategies.py`
- 进阶学习：阅读 [高级检索科普](Advanced-Retrieval.md)
