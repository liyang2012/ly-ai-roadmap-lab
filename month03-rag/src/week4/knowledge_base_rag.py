"""
Week 4: RAG 实战 — 智能知识库问答系统
=========================================
将 Week 1-3 学到的技术整合为一个完整可用的知识库问答系统：
- Week 1: Embedding + ChromaDB
- Week 2: 多格式文档加载 + 分块策略
- Week 3: Hybrid Search + RRF + Query Rewriting

功能：
1. 支持多种文档格式 (MD/HTML/TXT/PDF/JSON)
2. 智能分块 (Markdown 标题 + 递归分块)
3. Hybrid Search (向量 + BM25 + RRF)
4. Query Rewriting（查询优化）
5. 交互式问答 + Web UI (gradio 可选)

作者: 大懒
日期: 2026-06-29
"""

import os
import json
import hashlib
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings as ChromaSettings
import requests  # for Ollama embedding API

# ============================================================
# 0. 配置
# ============================================================

@dataclass
class RAGConfig:
    """RAG 系统全局配置"""
    # 文档目录
    doc_dir: str = "./docs"
    # ChromaDB 持久化目录
    chroma_dir: str = "./chroma_db"
    collection_name: str = "knowledge_base"
    # Embedding 模型 (Ollama)
    embedding_model: str = "qwen3-embedding:4b"
    # LLM (DeepSeek API)
    llm_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    llm_api_base: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    # 分块参数
    chunk_size: int = 512
    chunk_overlap: int = 50
    # 检索参数
    top_k: int = 5
    # Hybrid Search 权重
    vector_weight: float = 0.7
    bm25_weight: float = 0.3


# ============================================================
# 1. 文档加载器 (from Week 2)
# ============================================================

class DocumentLoader:
    """多格式文档加载器"""

    @staticmethod
    def load_markdown(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def load_txt(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def load_json(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def load_html(filepath: str) -> str:
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip_tags = {"script", "style", "meta", "link"}

            def handle_data(self, data):
                stripped = data.strip()
                if stripped:
                    self.text.append(stripped)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        extractor = TextExtractor()
        extractor.feed(content)
        return "\n".join(extractor.text)

    @staticmethod
    def load_pdf(filepath: str) -> str:
        """使用 PyMuPDF (fitz) 加载 PDF"""
        try:
            import fitz
            doc = fitz.open(filepath)
            text = []
            for page in doc:
                text.append(page.get_text())
            doc.close()
            return "\n".join(text)
        except ImportError:
            raise ImportError("请安装 PyMuPDF: pip install PyMuPDF")

    @classmethod
    def load(cls, filepath: str) -> str:
        """自动识别格式并加载"""
        ext = Path(filepath).suffix.lower()
        loaders = {
            ".md": cls.load_markdown,
            ".txt": cls.load_txt,
            ".json": cls.load_json,
            ".html": cls.load_html,
            ".htm": cls.load_html,
            ".pdf": cls.load_pdf,
        }
        loader = loaders.get(ext)
        if not loader:
            raise ValueError(f"不支持的文档格式: {ext}")
        return loader(filepath)


# ============================================================
# 2. 智能分块器 (from Week 2)
# ============================================================

class Chunker:
    """Markdown 标题感知的递归分块器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_by_headings(self, text: str) -> list[tuple[str, str]]:
        """按 Markdown 标题分割，返回 (标题, 内容) 列表"""
        pattern = r"^(#{1,6})\s+(.+)$"
        lines = text.split("\n")
        sections = []
        current_heading = ""
        current_content = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                if current_content:
                    sections.append((current_heading, "\n".join(current_content).strip()))
                current_heading = match.group(2)
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections.append((current_heading, "\n".join(current_content).strip()))

        return sections

    def _recursive_split(self, text: str) -> list[str]:
        """递归分块：先按段落，再按句子，再强制切割"""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # 先按双换行（段落）
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        for para in paragraphs:
            if len(para) <= self.chunk_size:
                if para.strip():
                    chunks.append(para.strip())
            else:
                # 按句子分
                sentences = re.split(r"(?<=[。！？.!?])\s*", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) > self.chunk_size and current:
                        chunks.append(current.strip())
                        current = sent[-self.chunk_overlap:] + sent if self.chunk_overlap > 0 else sent
                    else:
                        current += sent
                if current.strip():
                    chunks.append(current.strip())

        # 如果还有超长块，强制切割
        final = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final.append(chunk)
            else:
                for i in range(0, len(chunk), self.chunk_size - self.chunk_overlap):
                    final.append(chunk[i:i + self.chunk_size])

        return final

    def chunk_document(self, filepath: str) -> list[dict]:
        """加载并分块文档，返回带元数据的块列表"""
        content = DocumentLoader.load(filepath)
        filename = Path(filepath).name
        ext = Path(filepath).suffix.lower()

        sections = self._split_by_headings(content)
        chunks = []

        for heading, section_text in sections:
            sub_chunks = self._recursive_split(section_text)
            for i, sub in enumerate(sub_chunks):
                chunk_id = hashlib.md5(f"{filepath}:{heading}:{i}".encode()).hexdigest()
                chunks.append({
                    "id": chunk_id,
                    "text": sub,
                    "metadata": {
                        "source": filepath,
                        "filename": filename,
                        "format": ext,
                        "heading": heading,
                        "chunk_index": i,
                    }
                })

        return chunks


# ============================================================
# 3. Embedding 服务 (from Week 1)
# ============================================================

class EmbeddingService:
    """Ollama Embedding 服务封装"""

    def __init__(self, model: str = "qwen3-embedding:4b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def embed(self, text: str | list[str]) -> list[list[float]]:
        """生成 embedding，支持单个文本或批量"""
        texts = [text] if isinstance(text, str) else text
        embeddings = []
        for t in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": t},
                timeout=30,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)[0]


# ============================================================
# 4. BM25 检索器 (from Week 3)
# ============================================================

class BM25Retriever:
    """BM25 关键词检索器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[str] = []
        self.doc_ids: list[str] = []
        self.doc_lengths: list[int] = []
        self.avg_dl: float = 0.0
        self.term_freqs: dict[str, list[int]] = {}  # term -> [doc_freq1, doc_freq2, ...]
        self.idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        """中文分词（简单字符级）"""
        # 简单的中文混合分词
        tokens = []
        for char in text:
            if char.isalnum() or '\u4e00' <= char <= '\u9fff':
                if tokens and tokens[-1] and (
                    (tokens[-1][-1].isalpha() and char.isalpha()) or
                    (tokens[-1][-1].isdigit() and char.isdigit()) or
                    ('\u4e00' <= tokens[-1][-1] <= '\u9fff' and '\u4e00' <= char <= '\u9fff')
                ):
                    tokens[-1] += char
                else:
                    tokens.append(char)
            elif char.strip():
                tokens.append(char)
        return [t.lower() for t in tokens if t.strip()]

    def index(self, documents: list[dict]):
        """建立 BM25 索引"""
        self.documents = []
        self.doc_ids = []
        self.doc_lengths = []
        self.term_freqs = {}
        N = len(documents)

        for i, doc in enumerate(documents):
            text = doc["text"]
            doc_id = doc["id"]
            self.documents.append(text)
            self.doc_ids.append(doc_id)
            tokens = self._tokenize(text)
            self.doc_lengths.append(len(tokens))

            # 统计词频
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            for token, freq in tf.items():
                if token not in self.term_freqs:
                    self.term_freqs[token] = [0] * N
                self.term_freqs[token][i] = freq

        # 计算平均文档长度
        self.avg_dl = sum(self.doc_lengths) / N if N > 0 else 0

        # 计算 IDF
        for term, freqs in self.term_freqs.items():
            df = sum(1 for f in freqs if f > 0)
            self.idf[term] = max(0, ((N - df + 0.5) / (df + 0.5)) + 1)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """BM25 检索"""
        query_tokens = self._tokenize(query)
        N = len(self.documents)
        scores = [0.0] * N

        for token in query_tokens:
            idf = self.idf.get(token, 0)
            if token not in self.term_freqs:
                continue
            for i, tf in enumerate(self.term_freqs[token]):
                if tf > 0:
                    dl = self.doc_lengths[i]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                    scores[i] += idf * numerator / denominator

        # 排序取 top_k
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(self.doc_ids[i], score) for i, score in ranked[:top_k] if score > 0]


# ============================================================
# 5. RRF 融合 + Hybrid Search (from Week 3)
# ============================================================

class HybridSearcher:
    """混合检索：向量 + BM25 + RRF 融合"""

    def __init__(
        self,
        embed_service: EmbeddingService,
        bm25: BM25Retriever,
        collection,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        rrf_k: int = 60,
    ):
        self.embed_service = embed_service
        self.bm25 = bm25
        self.collection = collection
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k

    def _vector_search(self, query: str, top_k: int) -> dict[str, float]:
        """向量检索"""
        query_embedding = self.embed_service.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # 多取一些用于融合
        )
        scores = {}
        if results["ids"] and results["ids"][0]:
            for doc_id, distance in zip(results["ids"][0], results["distances"][0]):
                # ChromaDB 返回距离，转相似度
                scores[doc_id] = 1.0 / (1.0 + distance)
        return scores

    def _rrf_fusion(self, ranked_lists: list[list[tuple[str, float]]], weights: list[float] = None) -> list[tuple[str, float]]:
        """RRF (Reciprocal Rank Fusion) 融合多个排序列表"""
        if weights is None:
            weights = [1.0] * len(ranked_lists)

        scores: dict[str, float] = {}
        for rank_list, weight in zip(ranked_lists, weights):
            for rank, (doc_id, _) in enumerate(rank_list, 1):
                scores[doc_id] = scores.get(doc_id, 0) + weight / (self.rrf_k + rank)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """混合检索"""
        # 向量检索 + 排序
        vector_scores = self._vector_search(query, top_k)
        vector_ranked = sorted(vector_scores.items(), key=lambda x: x[1], reverse=True)

        # BM25 检索 + 排序
        bm25_results = self.bm25.search(query, top_k=top_k * 2)

        # RRF 融合
        rrf_results = self._rrf_fusion(
            [vector_ranked, bm25_results],
            weights=[self.vector_weight, self.bm25_weight],
        )

        # 取 top_k，并组装完整文档信息
        final = []
        for doc_id, rrf_score in rrf_results[:top_k]:
            result = self.collection.get(ids=[doc_id])
            if result["documents"]:
                final.append({
                    "id": doc_id,
                    "text": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                    "rrf_score": rrf_score,
                })

        return final


# ============================================================
# 6. Query Rewriting (from Week 3)
# ============================================================

class QueryRewriter:
    """查询改写：关键词提取 + 同义词扩展 + 子问题拆解"""

    @staticmethod
    def extract_keywords(query: str) -> str:
        """提取关键词"""
        # 简单规则：去停用词，保留核心词
        stopwords = {"的", "是", "了", "在", "和", "与", "或", "不", "也",
                     "都", "就", "要", "有", "对", "把", "被", "让", "从",
                     "到", "为", "以", "而", "能", "会", "可以", "这个", "那个",
                     "一个", "什么", "怎么", "如何", "为什么", "怎么样"}
        words = [w for w in re.split(r"[\s，。！？、]+", query) if w and w not in stopwords]
        return " ".join(words)

    @staticmethod
    def decompose(query: str) -> list[str]:
        """拆解复杂查询为子问题"""
        # 简单拆解：按问号、逗号、分号分割
        parts = re.split(r"[？?，,；;]+", query)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) <= 1:
            return [query]
        return parts

    def rewrite(self, query: str) -> dict:
        """返回原始查询 + 改写后的多个查询"""
        return {
            "original": query,
            "keywords": self.extract_keywords(query),
            "sub_queries": self.decompose(query),
        }

    def multi_query_search(self, query: str, searcher: HybridSearcher, top_k: int = 5) -> list[dict]:
        """多查询搜索：对原始查询和子查询分别搜索，合并去重"""
        rewritten = self.rewrite(query)
        all_results = {}
        seen = set()

        # 对原始查询和子查询分别检索
        queries = [rewritten["original"]] + rewritten["sub_queries"]
        for q in queries:
            results = searcher.search(q, top_k=top_k)
            for r in results:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    all_results[r["id"]] = r

        # 按 RRF score 排序
        return sorted(all_results.values(), key=lambda x: x.get("rrf_score", 0), reverse=True)[:top_k]


# ============================================================
# 7. LLM 生成回答
# ============================================================

class LLMGenerator:
    """基于检索结果生成回答"""

    def __init__(self, config: RAGConfig):
        self.config = config

    def _build_prompt(self, query: str, contexts: list[dict]) -> str:
        context_text = "\n\n---\n\n".join([
            f"[来源: {c['metadata'].get('filename', 'unknown')}]\n{c['text']}"
            for c in contexts
        ])
        return f"""你是一个知识库问答助手。请基于以下检索到的文档内容回答用户的问题。
如果文档内容不足以回答问题，请如实说明"文档中没有相关信息"。

## 检索到的文档内容
{context_text}

## 用户问题
{query}

## 回答要求
1. 基于文档内容回答，不要编造
2. 如果信息不完整，说明缺失了什么
3. 语言简洁清晰
4. 如引用了具体文档，标注来源

## 回答"""

    def generate(self, query: str, contexts: list[dict]) -> str:
        """调用 LLM 生成回答"""
        prompt = self._build_prompt(query, contexts)

        headers = {
            "Authorization": f"Bearer {self.config.llm_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        try:
            resp = requests.post(
                f"{self.config.llm_api_base}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            return f"LLM 调用失败: {e}"


# ============================================================
# 8. 知识库问答系统（主类）
# ============================================================

class KnowledgeBaseRAG:
    """智能知识库问答系统"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.embed_service = EmbeddingService(model=self.config.embedding_model)
        self.chunker = Chunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.rewriter = QueryRewriter()
        self.bm25 = BM25Retriever()
        self.searcher: Optional[HybridSearcher] = None
        self.generator: Optional[LLMGenerator] = None

        # 初始化 ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # 获取或创建 collection
        try:
            self.collection = self.chroma_client.get_collection(self.config.collection_name)
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    def index_documents(self, doc_dir: str = None):
        """索引文档目录中的所有文档"""
        doc_dir = doc_dir or self.config.doc_dir
        doc_path = Path(doc_dir)

        if not doc_path.exists():
            print(f"文档目录不存在: {doc_dir}")
            return

        all_files = list(doc_path.rglob("*"))
        supported = [f for f in all_files if f.suffix.lower() in {".md", ".txt", ".json", ".html", ".htm", ".pdf"}]

        if not supported:
            print(f"文档目录中没有支持的文件: {doc_dir}")
            return

        print(f"发现 {len(supported)} 个文档，开始分块和索引...")

        all_chunks = []
        for filepath in supported:
            try:
                chunks = self.chunker.chunk_document(str(filepath))
                all_chunks.extend(chunks)
                print(f"  ✓ {filepath.name}: {len(chunks)} 个块")
            except Exception as e:
                print(f"  ✗ {filepath.name}: {e}")

        if not all_chunks:
            print("没有生成任何块！")
            return

        print(f"\n共生成 {len(all_chunks)} 个文本块")

        # 生成 embeddings 并存入 ChromaDB
        texts = [c["text"] for c in all_chunks]
        ids = [c["id"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]

        print("生成 Embeddings...")
        embeddings = self.embed_service.embed(texts)

        # 清除旧数据后添加
        try:
            self.collection.delete(ids=self.collection.get()["ids"])
        except Exception:
            pass

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"已索引 {len(ids)} 个文档块到 ChromaDB")

        # 建立 BM25 索引
        print("建立 BM25 索引...")
        self.bm25.index(all_chunks)
        print("BM25 索引建立完成")

        # 初始化混合检索器
        self.searcher = HybridSearcher(
            embed_service=self.embed_service,
            bm25=self.bm25,
            collection=self.collection,
            vector_weight=self.config.vector_weight,
            bm25_weight=self.config.bm25_weight,
        )

        # 初始化 LLM 生成器
        if self.config.llm_api_key:
            self.generator = LLMGenerator(self.config)

        print("\n✅ 知识库索引完成！")

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """搜索知识库"""
        if not self.searcher:
            raise RuntimeError("请先调用 index_documents() 建立索引")
        top_k = top_k or self.config.top_k
        return self.rewriter.multi_query_search(query, self.searcher, top_k=top_k)

    def ask(self, query: str, top_k: int = None) -> dict:
        """问答：检索 + 生成"""
        results = self.search(query, top_k=top_k)

        if not self.generator:
            return {
                "query": query,
                "contexts": results,
                "answer": "LLM 未配置（需要 DEEPSEEK_API_KEY），仅返回检索结果。",
            }

        if not results:
            return {
                "query": query,
                "contexts": [],
                "answer": "知识库中没有找到相关信息。",
            }

        answer = self.generator.generate(query, results)
        return {
            "query": query,
            "contexts": results,
            "answer": answer,
        }

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        try:
            count = len(self.collection.get()["ids"])
        except Exception:
            count = 0
        return {
            "collection": self.config.collection_name,
            "chunks": count,
            "embedding_model": self.config.embedding_model,
            "llm_model": self.config.llm_model if self.config.llm_api_key else "未配置",
        }


# ============================================================
# 9. CLI 交互入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="智能知识库问答系统")
    parser.add_argument("--doc-dir", default="./docs", help="文档目录")
    parser.add_argument("--index", action="store_true", help="重新索引文档")
    parser.add_argument("--query", "-q", type=str, help="单次查询")
    parser.add_argument("--top-k", type=int, default=5, help="检索结果数量")
    parser.add_argument("--stats", action="store_true", help="显示知识库统计")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()

    config = RAGConfig(doc_dir=args.doc_dir)

    rag = KnowledgeBaseRAG(config)

    # 索引
    if args.index or args.query or args.interactive:
        rag.index_documents(args.doc_dir)

    # 统计
    if args.stats:
        stats = rag.get_stats()
        print("\n📊 知识库统计:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    # 单次查询
    if args.query and not args.interactive:
        print(f"\n🔍 查询: {args.query}\n")
        result = rag.ask(args.query, top_k=args.top_k)
        print(f"📝 回答:\n{result['answer']}\n")
        if result["contexts"]:
            print("📚 参考来源:")
            for i, ctx in enumerate(result["contexts"], 1):
                source = ctx["metadata"].get("filename", "unknown")
                print(f"  [{i}] {source} (score: {ctx['rrf_score']:.4f})")
        return

    # 交互模式
    if args.interactive:
        print("\n" + "=" * 50)
        print("🤖 智能知识库问答系统")
        print("=" * 50)
        print(f"📊 已加载 {rag.get_stats()['chunks']} 个文档块")
        print("输入 'quit' 或 'exit' 退出, 'stats' 查看统计\n")

        while True:
            try:
                query = input("\n🔍 请输入问题: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("👋 再见！")
                break
            if query.lower() == "stats":
                stats = rag.get_stats()
                for k, v in stats.items():
                    print(f"  {k}: {v}")
                continue

            result = rag.ask(query, top_k=args.top_k)
            print(f"\n📝 {result['answer']}")

            if result["contexts"]:
                print("\n📚 参考来源:")
                for i, ctx in enumerate(result["contexts"], 1):
                    source = ctx["metadata"].get("filename", "unknown")
                    heading = ctx["metadata"].get("heading", "")
                    info = f"{source}"
                    if heading:
                        info += f" → {heading}"
                    print(f"  [{i}] {info}")


if __name__ == "__main__":
    main()
