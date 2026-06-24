"""
Day 1-2: 文档加载器 — PDF / Markdown / HTML 文件读取

目标：掌握 LangChain Document Loaders 处理不同格式的文档

核心概念：
1. 文档加载器 (Document Loaders) 是 RAG Pipeline 的输入入口
2. 不同格式需要不同的加载器
3. 加载后的文档统一为 List[Document] 格式，方便后续处理

LangChain Document 格式：
    Document(page_content="文档内容", metadata={"source": "xxx.md", ...})

支持的格式：
    - Markdown: Notion、GitHub Wiki、技术文档等
    - HTML: 网页内容
    - PDF: 产品手册、合同、研究报告等
    - 其他：CSV、JSON、Word、PowerPoint（扩展学习）

=== 运行方式 ===
    python doc_loader.py               # 自动演示
    python doc_loader.py --interactive  # 交互模式

=== 文件说明 ===
    本脚本会自动创建测试文档（sample_file.md, sample_article.html, sample_report.pdf）
    演示后自动清理

=== 重点对比 ===
    | 加载器          | 输出格式        | 中文支持 | 适用场景         |
    |-----------------|----------------|---------|----------------|
    | TextLoader      | 纯文本          | ✅      | 任意纯文本文件   |
    | UnstructuredMDLoader | Markdown 文本 | ✅   | .md 文件        |
    | UnstructuredHTMLLoader | HTML 文本   | ✅   | .html 文件      |
    | PyMuPDFLoader   | PDF 文本+元数据  | ✅      | .pdf 文件       |
"""

import os
import sys
import tempfile
import json

# LangChain 文档加载器
from langchain_community.document_loaders import (
    TextLoader,                    # 纯文本加载器（最通用）
    # PyMuPDFLoader 需要单独安装: pip install pymupdf
)

# 轻量级替代方案 — 不使用 Unstructured 的 spacy 依赖链
# UnstructuredMarkdownLoader 依赖 spacy 和 en_core_web_sm
# UnstructuredHTMLLoader 也有同样的依赖
# 下面用 Python 标准库实现等同功能
import html as html_lib
import re


# ============================================================
# Part 1: 创建测试文档
# ============================================================
#
# 为了演示文档加载，我们创建几种不同格式的测试文件。
# 文件名用一个唯一的目录前缀，避免冲突。

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_files")


def ensure_sample_files():
    """在 sample_files/ 下创建测试文档"""
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    # ─── 1. Markdown 示例：产品 FAQ ───
    md_content = """# 智能手表 X100 - 产品 FAQ

## 基础信息

### 产品规格
- 屏幕：1.5英寸 AMOLED，分辨率 480×480
- 电池：400mAh，续航 14 天（典型使用）
- 防水：IP68 级（50米防水）
- 系统：兼容 iOS 14+ / Android 8.0+

### 主要功能
- 心率监测、血氧检测、睡眠分析
- GPS 运动追踪（支持 100+ 运动模式）
- 消息通知（微信、短信、电话）
- 支付宝离线支付

## 常见问题

### Q: 续航多久？
A: 典型使用场景下 14 天，重度使用 7 天。

### Q: 支持游泳佩戴吗？
A: 支持，IP68 级防水可在 50 米水深下正常工作。但注意：
- 不支持热水澡（蒸汽会损坏密封圈）
- 海水使用后需用淡水冲洗

### Q: 能接电话吗？
A: 支持蓝牙通话功能。手表有内置扬声器和麦克风，可以直接接听和拨打电话，无需掏出手机。
"""

    with open(os.path.join(SAMPLE_DIR, "product_faq.md"), "w", encoding="utf-8") as f:
        f.write(md_content)

    # ─── 2. HTML 示例：新闻文章 ───
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>2026 年 AI 行业十大趋势</title>
    <meta name="author" content="科技日报">
    <meta name="date" content="2026-01-15">
</head>
<body>
    <h1>2026 年 AI 行业十大趋势</h1>
    <p class="subtitle">人工智能正在重塑每一个行业</p>
    
    <div class="content">
        <h2>1. 多模态 AI 成为主流</h2>
        <p>2026 年，多模态 AI 模型将全面超越单模态模型。GPT-5、Gemini 3 等大模型
        已实现文本、图像、音频、视频的深度协同理解。企业不再需要为不同任务训练
        不同的模型。</p>
        
        <h2>2. Agentic AI 从概念走向落地</h2>
        <p>AI Agent 不再是实验室玩具。在电商、客服、代码审查等领域，Agent 已经
        开始独立完成端到端任务，人类只需监督和干预异常情况。</p>
        
        <h2>3. 本地模型崛起</h2>
        <p>Qwen3、Llama 4 等开源模型在多数场景已逼近闭源模型。配合量化技术和
        NPU 硬件加速，更多企业选择在本地部署 AI 模型以保护数据隐私。</p>
        
        <h2>4. RAG 技术趋于成熟</h2>
        <p>Graph RAG、Agentic RAG 等新范式解决了传统 RAG 的多跳推理和长文档
        理解难题。知识库问答系统在金融、医疗、法律行业的采纳率超过 60%。</p>
    </div>
    
    <footer>
        <p>来源：科技日报 | 2026年1月15日</p>
    </footer>
</body>
</html>"""

    with open(os.path.join(SAMPLE_DIR, "ai_trends.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    # ─── 3. 纯文本示例：简单笔记 ───
    txt_content = """Python 学习笔记 - 2026年3月

基础：
1. 变量命名：小写+下划线，如 user_name
2. 字符串操作：f-string 是最推荐的格式化方式
3. 列表推导式：[x*2 for x in [1,2,3]] → [2,4,6]

函数进阶：
1. 默认参数：def greet(name, msg="你好"): ...
2. *args / **kwargs：可变参数
3. lambda 表达式：lambda x: x*2

常用内置函数：
- map(), filter(), reduce()
- enumerate(), zip()
- sorted(), reversed()

文件操作：
- with open('file.txt', 'r') as f:
- 支持 r/w/a/rb/wb 等模式
"""

    with open(os.path.join(SAMPLE_DIR, "python_notes.txt"), "w", encoding="utf-8") as f:
        f.write(txt_content)

    # ─── 4. PDF 示例 ───
    # 创建一个简单的 PDF 文件用 fpdf2 库
    # 如果没有安装，提示用户安装
    try:
        from fpdf import FPDF

        class PDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 16)
                self.cell(0, 10, "X100 Smart Watch User Manual", ln=True, align="C")
                self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font("Helvetica", "I", 8)
                self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, "Chapter 1: Getting Started", ln=True)
        pdf.ln(5)
        pdf.multi_cell(0, 8, "Thank you for purchasing the X100 Smart Watch. "
                     "This manual will help you set up and use your device.")
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "1.1 Package Contents", ln=True)
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, "The package includes:\n"
                     "- X100 Smart Watch\n"
                     "- Magnetic charging cable\n"
                     "- User manual\n"
                     "- Warranty card")
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Chapter 2: Charging", ln=True)
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, "To charge your X100, use the included magnetic charging "
                     "cable. The charging contacts are on the back of the watch. "
                     "A full charge takes approximately 2 hours.")
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Chapter 3: Health Monitoring", ln=True)
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, "The X100 features advanced health monitoring sensors. "
                     "It can track heart rate 24/7, monitor blood oxygen levels, "
                     "and analyze sleep patterns. For best results, wear the watch "
                     "snugly on your wrist.")

        pdf.output(os.path.join(SAMPLE_DIR, "user_manual.pdf"))
        print(f"   ✅ PDF created: {os.path.join(SAMPLE_DIR, 'user_manual.pdf')}")

    except ImportError:
        print("   ⚠️  fpdf2 not installed, skip PDF test file. Run: pip install fpdf2")

    print(f"   ✅ Sample files created in: {SAMPLE_DIR}")


# ============================================================
# Part 2: 逐个加载文档
# ============================================================

def demo_text_loader():
    """
    TextLoader — 最通用的纯文本加载器
    
    适用场景：
    - .txt 文件
    - .log 文件
    - 任意纯文本文件
    
    特点：
    - 最简单，不做任何格式解析
    - 一行就是一个字符串
    - 自动检测编码（可指定 encoding 参数）
    """
    print("\n" + "-" * 60)
    print("📄 TextLoader — 纯文本加载")
    print("-" * 60)

    file_path = os.path.join(SAMPLE_DIR, "python_notes.txt")
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()

    print(f"\n   加载文件: {file_path}")
    print(f"   文档数量: {len(docs)}")
    print(f"   文档长度: {len(docs[0].page_content)} 字符")
    print(f"   元数据: {docs[0].metadata}")
    print(f"\n  内容预览 (前200字):")
    print(f"   {docs[0].page_content[:200]}")
    return docs


def demo_markdown_loader():
    """
    UnstructuredMarkdownLoader — Markdown 加载器
    
    适用场景：
    - .md 文件（Notion 导出、GitHub Wiki、技术文档）
    - README.md
    
    特点：
    - 保留章节标题结构
    - 去除 Markdown 标记（##, **, - 等）
    - 输出纯文本，但保留了文本的逻辑顺序
    - metadata 中记录 source
    """
    print("\n" + "-" * 60)
    print("📄 MarkdownLoader — Markdown 加载")
    print("-" * 60)

    from langchain_core.documents import Document

    file_path = os.path.join(SAMPLE_DIR, "product_faq.md")
    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    # 去除 Markdown 语法标记，保留纯文本
    plain_text = _strip_markdown(md_text)
    doc = Document(page_content=plain_text, metadata={"source": file_path})

    print(f"\n   加载文件: {file_path}")
    print(f"   文档数量: 1")
    print(f"   文档长度: {len(doc.page_content)} 字符")
    print(f"   元数据: {doc.metadata}")
    print(f"\n  内容预览 (前300字):")
    print(f"   {doc.page_content[:300]}")
    return [doc]
    return docs


def demo_html_loader():
    """
    UnstructuredHTMLLoader — HTML 加载器
    
    适用场景：
    - .html 页面内容
    - 网页抓取后的离线文件
    
    特点：
    - 去除 HTML 标签（<h1>, <p>, <div> 等）
    - 保留文本内容的顺序
    - metadata 自动记录 source
    - 不会保留 CSS 样式、脚本等无关内容
    """
    print("\n" + "-" * 60)
    print("📄 HTMLLoader — HTML 加载")
    print("-" * 60)

    from langchain_core.documents import Document

    file_path = os.path.join(SAMPLE_DIR, "ai_trends.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html_text = f.read()
    # 去除 HTML 标签，保留纯文本
    plain_text = _strip_html(html_text)
    doc = Document(page_content=plain_text, metadata={"source": file_path})

    print(f"\n   加载文件: {file_path}")
    print(f"   文档数量: 1")
    print(f"   文档长度: {len(doc.page_content)} 字符")
    print(f"   元数据: {doc.metadata}")
    print(f"\n  内容预览 (前300字):")
    print(f"   {doc.page_content[:300]}")
    return [doc]
    return docs


def demo_pdf_loader():
    """
    PyMuPDFLoader — PDF 加载器
    
    适用场景：
    - 产品手册、合同、研究报告、论文
    - 任何 PDF 格式的文档
    
    特点：
    - 按页拆分文档（每页一个 Document）
    - 保留页面文本和基本排版
    - metadata 记录 source + page 信息
    - 中文 PDF 支持良好
    
    注意：
    - 扫描版 PDF（图片格式）需要 OCR，PyMuPDFLoader 不支持
    - 扫描版需要 OCR 方案：pytesseract / Azure Document Intelligence
    """
    print("\n" + "-" * 60)
    print("📄 PDFLoader — PDF 加载")
    print("-" * 60)

    file_path = os.path.join(SAMPLE_DIR, "user_manual.pdf")
    
    if not os.path.exists(file_path):
        print("   ⚠️  PDF 文件不存在（可能 fpdf2 未安装），跳过演示")
        return []

    try:
        from langchain_community.document_loaders import PyMuPDFLoader
    except ImportError:
        print("   ⚠️  PyMuPDFLoader 不可用，安装: pip install pymupdf")
        return []

    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    print(f"\n   加载文件: {file_path}")
    print(f"   文档数量: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"\n   📄 第 {i+1} 页:")
        print(f"      长度: {len(doc.page_content)} 字符")
        print(f"      元数据: {doc.metadata}")
        print(f"      内容预览: {doc.page_content[:150]}")
    return docs


# ============================================================
# Part 3: 批量加载并附加元数据
# ============================================================

def demo_json_loader():
    """
    JSONLoader + TextLoader 结合演示
    
    前面演示了三种文本类加载器，但实际项目中我们可能还需要：
    - 从 JSON 文件加载结构化数据
    - 给文档附加自定义 metadata（来源、日期、分类等）
    
    这里演示如何用 TextLoader + 手动 metadata 实现灵活的加载。
    """
    print("\n" + "-" * 60)
    print("📄 自定义元数据加载演示")
    print("-" * 60)

    # 模拟一个 JSON 格式的知识库
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

    import json
    json_path = os.path.join(SAMPLE_DIR, "knowledge_articles.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_content, f, ensure_ascii=False, indent=2)

    # 手动构建 Document 列表
    from langchain_core.documents import Document

    docs = []
    for article in json_content["articles"]:
        doc = Document(
            page_content=article["content"],
            metadata={
                "source": json_path,
                "title": article["title"],
                "author": article["author"],
                "date": article["date"],
                "tags": ", ".join(article["tags"]),
                "format": "json_article",
            },
        )
        docs.append(doc)

    print(f"\n   从 JSON 文件加载 {len(docs)} 篇文章:")
    for doc in docs:
        print(f"   📝 [{doc.metadata['title']}]")
        print(f"      作者: {doc.metadata['author']}, 日期: {doc.metadata['date']}")
        print(f"      标签: {doc.metadata['tags']}")
        print(f"      内容: {doc.page_content[:80]}...")

    return docs


# ============================================================
# 辅助函数：轻量级格式剥离
# ============================================================


def _strip_markdown(text: str) -> str:
    """
    去除 Markdown 语法标记，保留纯文本
    
    处理内容：
    - 标题标记 # ## ### 等
    - 加粗 **text** 和 *斜体*
    - 列表 - 和 1.
    - 链接 [text](url)
    - 引用 >
    
    注意：这只是轻量实现，不处理代码块、表格等复杂结构
    生产环境建议使用 mistune / markdown-it＋BeautifulSoup
    """
    # 先处理链接 [text](url) → text
    text = re.sub(r'\[(\\.|[^\]])\]\([^)]+\)', r'\1', text)
    # 去除标题标记
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 去除加粗/斜体
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # 去除列表序号
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    # 去除列表符号
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    # 去除引用符号
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    return text.strip()


def _strip_html(text: str) -> str:
    """
    去除 HTML 标签，保留纯文本
    
    使用 Python 标准库 html.parser 的 unescape 和解码
    然后用正则去除 HTML/XML 标签
    """
    # 解码 HTML 实体
    text = html_lib.unescape(text)
    # 去除 <script> 和 <style> 块
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 去除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 压缩多余空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


# ============================================================
# Part 4: 统一演示
# ============================================================

def demo():
    """穷尽演示所有加载器"""
    print("=" * 60)
    print("📂 Week 2 - 文档加载器演示")
    print("=" * 60)

    print("\n🚀 第1步: 创建测试文档...")
    ensure_sample_files()

    all_docs = []

    # 各加载器演示
    all_docs.extend(demo_text_loader())
    all_docs.extend(demo_markdown_loader())
    all_docs.extend(demo_html_loader())

    pdf_docs = demo_pdf_loader()
    all_docs.extend(pdf_docs)

    json_docs = demo_json_loader()
    all_docs.extend(json_docs)

    # ─── 总结 ───
    print("\n" + "=" * 60)
    print("📊 加载器对比总结")
    print("=" * 60)
    print(f"\n   成功加载 {len(all_docs)} 个文档:")
    print(f"   - TextLoader:      纯文本 (.txt)")
    print(f"   - MarkdownLoader:  Markdown (.md)")
    print(f"   - HTMLLoader:      HTML (.html)")
    print(f"   - PyMuPDFLoader:   PDF (.pdf, 按页)")
    print(f"   - 自定义 JSON 加载: 结构化数据")

    print(f"\n   所有文档统一为 Document(page_content, metadata) 格式")
    print(f"   这是 RAG Pipeline 的标准输入格式。")
    print(f"\n   ⏭  下一步: 文档分块 (chunking_strategies.py)")


def interactive_mode():
    """交互模式：手动指定文件路径进行加载"""
    print("=" * 60)
    print("📂 文档加载器 — 交互模式")
    print("输入文件路径，查看加载效果。输入 'quit' 退出。")
    print("=" * 60)

    while True:
        path = input("\n📁 请输入文件路径: ").strip()
        if path.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not path:
            continue
        if not os.path.exists(path):
            print("   ❌ 文件不存在，请重新输入")
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext == ".txt":
            loader = TextLoader(path, encoding="utf-8")
        elif ext == ".md":
            with open(path, "r", encoding="utf-8") as f:
                content = _strip_markdown(f.read())
            docs = [{"page_content": content, "metadata": {"source": path}}]
            print(f"   ✅ 加载成功: 1 个文档")
            for doc in docs:
                print(f"\n   📄 文档")
                print(f"      长度: {len(doc['page_content'])} 字符")
                print(f"      元数据: {doc['metadata']}")
                print(f"      内容预览: {doc['page_content'][:200]}")
            continue
        elif ext == ".html":
            with open(path, "r", encoding="utf-8") as f:
                content = _strip_html(f.read())
            docs = [{"page_content": content, "metadata": {"source": path}}]
            print(f"   ✅ 加载成功: 1 个文档")
            for doc in docs:
                print(f"\n   📄 文档")
                print(f"      长度: {len(doc['page_content'])} 字符")
                print(f"      元数据: {doc['metadata']}")
                print(f"      内容预览: {doc['page_content'][:200]}")
            continue
        elif ext == ".pdf":
            try:
                from langchain_community.document_loaders import PyMuPDFLoader
            except ImportError:
                print("   ⚠️  PyMuPDFLoader 不可用")
                continue
            loader = PyMuPDFLoader(path)
        else:
            print(f"   ⚠️ 不支持的格式: {ext}，仍在尝试 TextLoader")
            loader = TextLoader(path, encoding="utf-8")

        try:
            docs = loader.load()
            print(f"   ✅ 加载成功: {len(docs)} 个文档")
            for i, doc in enumerate(docs):
                print(f"\n   📄 文档 #{i+1}")
                print(f"      长度: {len(doc.page_content)} 字符")
                print(f"      元数据: {doc.metadata}")
                print(f"      内容预览: {doc.page_content[:200]}")
        except Exception as e:
            print(f"   ❌ 加载失败: {e}")


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        interactive_mode()
    else:
        demo()
