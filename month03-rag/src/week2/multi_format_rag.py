"""
Day 5-6: 多格式文档 RAG 实战

目标：组合 Week 2 所有知识，构建一个能真实处理多格式文件的 RAG 系统

=== 本脚本做什么 ===
1. 从 sample_files/ 加载多种格式文档（MD、HTML、TXT、PDF、JSON）
2. 用匹配的分块策略处理每种文档
3. 存入 ChromaDB（带丰富的 metadata）
4. 支持语义检索和按来源/格式过滤
5. 完整 RAG 问答

=== 与 Week 1 simple_rag.py 的关键差异 ===
| 特性          | Week 1 (simple_rag)    | Week 2 (本脚本)       |
|--------------|----------------------|---------------------|
| 文档来源      | 硬编码字符串           | 真实文件（多格式）     |
| 文档处理      | 整篇存入，不分块       | 按策略分块            |
| 元数据        | 简单（source + category） | 丰富（格式/路径/章节/日期） |
| 检索          | 语义检索              | 语义 + metadata 过滤   |
| 引用溯源      | 简单来源名            | 文件名+章节+页码       |

=== 运行方式 ===
    python multi_format_rag.py            # 自动问答演示
    python multi_format_rag.py --reindex  # 强制重建索引
"""

import os
import sys
import json
import re

from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件中的环境变量

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

from openai import OpenAI


# ============================================================
# 配置
# ============================================================

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_files")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"

LLM_MODEL = "glm-5.2"


def get_llm_client():
    """获取 LLM 客户端（使用 GLM5.2"""
    return OpenAI(
        # 智谱 AI API Key，从环境变量读取
        api_key=os.getenv("ZHIPUAI_API_KEY"),
        # 智谱 AI API 地址
        base_url="https://open.bigmodel.cn/api/coding/paas/v4",
    )


# ============================================================
# Part 1: 文档加载器 —— 统一接口
# ============================================================

def load_and_chunk_text(filepath: str) -> list[Document]:
    """
    加载 .txt / .log 纯文本文件，用递归分块

    metadata 包含：
    - source: 文件名
    - format: "text"
    - path: 完整路径
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    chunks = splitter.create_documents(
        texts=[content],
        metadatas=[{"source": os.path.basename(filepath), "format": "text",
                     "path": filepath}],
    )
    return chunks


def load_and_chunk_markdown(filepath: str) -> list[Document]:
    """
    加载 .md 文件，用分步策略：
    1. 先按标题切分（保留章节结构）
    2. 正文过长的章节，再用递归分块细化

    metadata 包含标题层级信息，用于溯源。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 第一步：按 Markdown 标题分块
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "chapter"),     # H1 = 章
            ("##", "section"),    # H2 = 节
            ("###", "subsection"),  # H3 = 子节
        ],
        return_each_line=False,
    )
    md_chunks = md_splitter.split_text(content)

    # 第二步：对过长的块进行递归细化
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    final_chunks = []
    for chunk in md_chunks:
        # 给所有块加上基础 metadata
        chunk.metadata.update({
            "source": os.path.basename(filepath),
            "format": "markdown",
            "path": filepath,
        })
        if len(chunk.page_content) > 400:
            sub_chunks = recursive_splitter.split_documents([chunk])
            for sc in sub_chunks:
                sc.metadata.update(chunk.metadata)
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk)

    return final_chunks


def load_and_chunk_html(filepath: str) -> list[Document]:
    """
    加载 .html 文件

    使用标准库 html.parser 去除 HTML 标签，保留纯文本。
    然后用递归分块。
    """
    import html as html_lib

    with open(filepath, "r", encoding="utf-8") as f:
        html_text = f.read()

    # 去除 HTML 标签
    text = html_lib.unescape(html_text)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    doc = Document(page_content=text, metadata={
        "source": os.path.basename(filepath),
        "format": "html",
        "path": filepath,
    })

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    chunks = splitter.split_documents([doc])
    return chunks


def load_and_chunk_pdf(filepath: str) -> list[Document]:
    """
    加载 .pdf 文件

    PyMuPDFLoader 按页加载，每页自动拆成单独的 Document。
    我们在此基础上用递归分块，让每页内容更均匀。
    """
    try:
        from langchain_community.document_loaders import PyMuPDFLoader
    except ImportError:
        print(f"   ⚠️ PyMuPDFLoader 不可用，安装: pip install pymupdf")
        return []

    loader = PyMuPDFLoader(filepath)
    pdf_docs = loader.load()

    if not pdf_docs:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    chunks = splitter.split_documents(pdf_docs)

    for chunk in chunks:
        chunk.metadata.update({
            "source": os.path.basename(filepath),
            "format": "pdf",
            "path": filepath,
        })

    return chunks


def load_and_chunk_json(filepath: str) -> list[Document]:
    """
    从 JSON 文件加载文档

    假设 JSON 结构为 {"articles": [{"title": ..., "content": ..., "author": ...}, ...]}
    每篇文章作为一个 Document（短内容不分块，长内容再分块）
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for article in data.get("articles", []):
        doc = Document(
            page_content=article.get("content", ""),
            metadata={
                "source": os.path.basename(filepath),
                "format": "json",
                "path": filepath,
                "title": article.get("title", ""),
                "author": article.get("author", ""),
                "tags": article.get("tags", []),
            },
        )
        docs.append(doc)

    # 对过长的文章分块
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    all_chunks = []
    for doc in docs:
        if len(doc.page_content) > 400:
            sub_chunks = splitter.split_documents([doc])
            for sc in sub_chunks:
                sc.metadata.update(doc.metadata)
            all_chunks.extend(sub_chunks)
        else:
            all_chunks.append(doc)

    return all_chunks


# 加载器注册表：根据文件后缀选择加载策略
LOADER_REGISTRY = {
    ".txt": load_and_chunk_text,
    ".md": load_and_chunk_markdown,
    ".html": load_and_chunk_html,
    ".pdf": load_and_chunk_pdf,
    ".json": load_and_chunk_json,
}


def load_all_documents() -> list[Document]:
    """
    统一入口：扫描 sample_files/ 目录，按后缀调用对应加载器

    返回所有文件的切分后的 Document 列表。
    每个 Document 包含丰富的 metadata。
    """
    if not os.path.exists(SAMPLE_DIR):
        print(f"   ⚠️ sample_files 目录不存在: {SAMPLE_DIR}")
        return []

    all_chunks = []
    for filename in sorted(os.listdir(SAMPLE_DIR)):
        filepath = os.path.join(SAMPLE_DIR, filename)
        if os.path.isdir(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        loader = LOADER_REGISTRY.get(ext)

        if loader is None:
            print(f"   ⚠️ 跳过未知格式: {filename}")
            continue

        print(f"   📂 {filename} ({ext})")
        chunks = loader(filepath)
        print(f"      → {len(chunks)} 个块")
        all_chunks.extend(chunks)

    print(f"\n   📊 总计: {len(all_chunks)} 个文档块")
    return all_chunks


# ============================================================
# Part 2: MultiFormatRAG —— 完整 Pipeline
# ============================================================

class MultiFormatRAG:
    """
    多格式文档 RAG 系统

    相比 Week 1 的 SimpleRAG，有两处关键提升：
    1. 文档来源是真实文件，加载后自动分块
    2. 检索支持按格式/来源筛选 (metadata filtering)

    架构：
    ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
    │  MD │ HTML   │    │  分块 +      │    │  ChromaDB    │
    │  TXT│  PDF  │────│  Embedding   │────│  (metadata)  │
    │  JSON        │     │              │     │              │
    └─────────────┘     └──────────────┘     └──────────────┘
                                                      │
    ┌─────────────┐     ┌──────────────┐             │
    │  用户回答    │◄────│  LLM 生成    │◄────  语义检索  │
    │              │     │  (带引用溯源) │     │+ 过滤     │
    └─────────────┘     └──────────────┘     └──────────────┘
    """

    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        self.llm = get_llm_client()
        self.vectorstore = None
        self._indexed = False

    def index(self, chunks: list[Document], force_reindex: bool = False):
        """
        Indexing 阶段

        参数：
            chunks: 已经切分好的文档块列表
            force_reindex: 是否强制重建索引
        """
        if force_reindex and os.path.exists(PERSIST_DIR):
            import shutil
            shutil.rmtree(PERSIST_DIR)
            print("   🧹 已清除旧索引")

        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=PERSIST_DIR,
            collection_name="multi_format_kb",
        )
        self.vectorstore.persist()
        self._indexed = True
        print(f"   ✅ 索引完成，共 {len(chunks)} 个块")

    def retrieve(self, query: str, top_k: int = 3, filter_dict: dict = None) -> list[Document]:
        """
        Retrieval 阶段 — 支持 metadata 过滤

        参数：
            query: 用户问题
            top_k: 返回结果数
            filter_dict: ChromaDB metadata 过滤条件
                        例如 {"format": "markdown"} 只检索 Markdown
                        例如 {"source": "product_faq.md"} 只检索该文件

        返回：
            按相似度降序排列的 Document 列表
        """
        if not self._indexed:
            raise RuntimeError("请先调用 index() 方法")

        search_kwargs = {"k": top_k}
        if filter_dict:
            search_kwargs["filter"] = filter_dict
        retriever = self.vectorstore.as_retriever(
            search_kwargs=search_kwargs,
        )
        docs = retriever.invoke(query)
        return docs

    def generate(self, query: str, context_docs: list[Document]) -> str:
        """
        Generation 阶段 — 带引用溯源的回答

        在 Prompt 中标注每个引用的来源（文件名+章节+页码），
        LLM 会引用这些信息。
        """
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            meta = doc.metadata
            source_info = meta.get("source", "unknown")

            # 拼引入溯源信息
            if meta.get("chapter"):
                source_info += f" → {meta['chapter']}"
            if meta.get("section"):
                source_info += f" → {meta['section']}"
            if meta.get("subsection"):
                source_info += f" → {meta['subsection']}"

            context_parts.append(f"[{i}] 来源: {source_info}\n{doc.page_content}")

        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""你是一个智能知识库问答助手。请根据以下参考资料回答用户问题。

要求：
1. 只根据参考资料回答，不要编造信息
2. 如果参考资料中没有答案，明确告诉用户
3. 回答时引用具体来源（标注 [1]、[2] 等编号）
4. 用中文回答

参考资料：
{context}

用户问题：{query}

请回答："""

        response = self.llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )

        return response.choices[0].message.content

    def query(self, question: str, top_k: int = 3, filter_dict: dict = None) -> dict:
        """完整 Pipeline：Retrieve → Generate"""
        print(f"\n{'='*60}")
        print(f"❓ {question}")
        print(f"{'='*60}")

        # Step 1: 检索
        docs = self.retrieve(question, top_k=top_k, filter_dict=filter_dict)
        print(f"\n🔍 检索到 {len(docs)} 个相关块:")
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "?")
            score = doc.metadata.get("_score", "?")
            print(f"   [{i}] ({source}) {doc.page_content[:80]}...")

        # Step 2: 生成
        print(f"\n🤖 生成回答中...")
        answer = self.generate(question, docs)
        print(f"\n💬 {answer}")

        return {
            "question": question,
            "retrieved_docs": docs,
            "answer": answer,
        }


# ============================================================
# Part 3: 演示
# ============================================================

def demo():
    """运行完整演示"""
    print("=" * 60)
    print("📚 Week 2 - 多格式文档 RAG 实战演示")
    print("=" * 60)

    force_reindex = "--reindex" in sys.argv

    # ─── Step 1: 创建测试文档 ───
    print("\n🚀 Step 1: 准备测试文档...")
    if not os.path.exists(SAMPLE_DIR):
        # 调用 doc_loader.py 中的函数来创建
        from doc_loader import ensure_sample_files
        ensure_sample_files()

    # 创建 knowledge_articles.json（如果不存在）
    json_path = os.path.join(SAMPLE_DIR, "knowledge_articles.json")
    if not os.path.exists(json_path):
        json_content = {
            "articles": [
                {
                    "title": "如何搭建 RAG 系统",
                    "content": "RAG（检索增强生成）是当前最流行的知识库问答方案。"
                               "核心思路是：将文档分割成块，转成向量存入向量数据库，"
                               "查询时找到最相关的文档块，拼接到 Prompt 中让 LLM 回答。",
                    "author": "张三",
                    "date": "2026-03-01",
                    "tags": ["RAG", "Tutorial"],
                },
                {
                    "title": "LangChain 入门指南",
                    "content": "LangChain 是一个强大的 LLM 应用开发框架。它提供了 Document "
                               "Loaders、Text Splitters、Vector Stores 等一系列工具，"
                               "让开发者能快速构建 RAG 应用。",
                    "author": "李四",
                    "date": "2026-03-15",
                    "tags": ["LangChain", "Tutorial"],
                },
            ]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_content, f, ensure_ascii=False, indent=2)

    print(f"   样本文件目录: {SAMPLE_DIR}")
    for f in sorted(os.listdir(SAMPLE_DIR)):
        print(f"   - {f}")

    # ─── Step 2: 加载并分块 ───
    print("\n🚀 Step 2: 加载并分块...")
    all_chunks = load_all_documents()

    # ─── Step 3: 索引到 ChromaDB ───
    print("\n🚀 Step 3: 索引到 ChromaDB...")
    rag = MultiFormatRAG()
    rag.index(all_chunks, force_reindex=force_reindex)

    # ─── Step 4: 测试查询 ───
    print("\n🚀 Step 4: 测试查询...")

    test_questions = [
        "X100 智能手表的防水等级是多少？能戴着游泳吗？",
        "智能家居系统的回家模式有哪些功能？",
        "智能网关无法连接怎么办？",
        "RAG 系统的核心思路是什么？",
        "2026 年 AI 行业有哪些趋势？",
    ]

    for q in test_questions:
        rag.query(q, top_k=2)

    # ─── Step 5: 测试 metadata 过滤 ───
    print("\n" + "=" * 60)
    print("🔍 进阶测试: metadata 过滤检索")
    print("=" * 60)

    print("\n📋 只检索 Markdown 格式...")
    rag.query("智能手表有什么功能？", top_k=2, filter_dict={"format": "markdown"})

    print("\n📋 只检索 HTML 格式...")
    rag.query("AI 行业的趋势", top_k=2, filter_dict={"format": "html"})

    print("\n📋 只检索 PDF 格式...")
    rag.query("充电需要多长时间？", top_k=2, filter_dict={"format": "pdf"})

    # ─── 总结 ───
    print("\n" + "=" * 60)
    print("📊 Week 2 实战总结")
    print("=" * 60)
    print(f"""
    文档格式:     MD / HTML / TXT / PDF / JSON
    分块策略:
        - Markdown: 按标题分块 + 递归细化
        - 其他: 递归分块
    chunk_size:    300 (字符)
    chunk_overlap: 50 (字符)
    检索方式:      语义检索 + metadata 过滤
    LLM:          {LLM_MODEL}
    Embedding:    {EMBEDDING_MODEL}

    ChromaDB 持久化目录: {PERSIST_DIR}
    样本文件目录:        {SAMPLE_DIR}

    ✅ Week 2 知识点串联完成！
    ⏭  下一步: 查看 week2_notes.md 复盘
    """)


if __name__ == "__main__":
    demo()
