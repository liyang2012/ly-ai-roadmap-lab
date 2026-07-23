"""
Week 3 Day 1-3: 高级检索策略 —— Hybrid Search + Reranking

目标：超越单纯的向量检索，引入 BM25 关键词检索和重排序

=== 为什么需要高级检索？ ===

单纯的向量检索（如 Week 1/2 用的 ChromaDB）有局限性：
1. 对专有名词、缩写、精确关键词不敏感
   - 例："X100" 这个型号，向量检索可能找不到
2. 随机性强——每次结果可能不同
3. 只能做语义近似，不能精确匹配

解决方案：Hybrid Search（混合检索）
- 向量检索：覆盖语义相似的文档（理解"坏了" = "故障"）
- BM25 关键词检索：cover 精确关键词匹配（型号、代码、日期）
- 两者结果融合 → 覆盖更全面

=== 架构图 ===

用户问题 "手机X100屏幕坏了怎么办？"
        │
        ├──→ 向量检索 (ChromaDB)         ──→ [保修政策, 物流配送, ...]
        │       语义：理解"坏了"="故障"
        │
        └──→ BM25 关键词检索 (rank_bm25) ──→ [X100说明书, 保修政策, ...]
                关键词：精确匹配"X100"
        │
        ▼
    融合 (Reciprocal Rank Fusion)
        │
        ▼
    Reranking (Cross-Encoder)  ← 最贵的步骤，但最准
        │
        ▼
    Top-K 最终结果

=== 运行方式 ===
    python advanced_retrieval.py                 # 演示 + 对比
    python advanced_retrieval.py --reindex       # 强制重建索引
    python advanced_retrieval.py --interactive   # 交互模式
"""

import os
import sys
import json
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from rank_bm25 import BM25Okapi
import numpy as np

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from week1.simple_rag import get_llm_client, KNOWLEDGE_DOCS

# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db_week3")
LLM_MODEL = "glm-4-flash"


# ═══════════════════════════════════════════════════════════
# 扩展的知识库（比 Week 1/2 更丰富）
# ═══════════════════════════════════════════════════════════

# 在原有 KNOWLEDGE_DOCS 基础上增加一些精确关键词密集的文档
# 这样能更好地展示 BM25 的价值
EXTRA_DOCS = [
    {
        "id": "product_x100_manual",
        "text": """X100 智能旗舰手机 产品规格说明书：
型号：X100 Pro Max
屏幕：6.78英寸 AMOLED 120Hz
处理器：天玑9300+ 八核 3.25GHz
内存：16GB LPDDR5X
存储：512GB UFS 4.0
摄像头：后置三摄 50MP主摄 + 50MP超广角 + 64MP长焦
电池：5400mAh 支持 100W 快充 + 50W 无线快充
防水等级：IP68（可水下 1.5 米 30 分钟）
操作系统：ColorOS 15.0 基于 Android 15
网络：5G NR / Wi-Fi 7 / 蓝牙 5.4
特殊功能：卫星通信、AI 影像引擎、超声波屏下指纹""",
        "metadata": {"source": "product_x100_manual", "category": "product"},
    },
    {
        "id": "product_r50_spec",
        "text": """R50 青春版手机 规格：
型号：R50 Lite
屏幕：6.5英寸 LCD 90Hz
处理器：骁龙7 Gen3 八核 2.4GHz
内存：8GB LPDDR4X
存储：256GB UFS 3.1
摄像头：后置双摄 64MP主摄 + 8MP超广角
电池：5000mAh 支持 67W 快充
防水等级：IP54（防溅水）
操作系统：ColorOS 14.0
网络：5G / Wi-Fi 6 / 蓝牙 5.3""",
        "metadata": {"source": "product_r50_spec", "category": "product"},
    },
    {
        "id": "troubleshooting_guide",
        "text": """常见问题排查指南：

屏幕问题：
- 屏幕不亮：长按电源键 15 秒强制重启
- 触控失灵：检查是否有贴膜气泡，撕掉贴膜重试
- 屏幕闪烁：关闭自动亮度，固定 60% 手动亮度

电池问题：
- 耗电快：检查后台应用，关闭不必要的位置和蓝牙
- 充电慢：使用原装充电器和数据线，检查充电口是否有异物
- 不充电：重启手机，尝试无线充电确认充电口是否损坏

网络问题：
- Wi-Fi 连不上：重启路由器和手机，忘记网络重新连接
- 5G 信号弱：检查所在区域是否覆盖 5G，切换 4G 试试
- 蓝牙连不上：关闭蓝牙再打开，清除已配对设备重试""",
        "metadata": {"source": "troubleshooting_guide", "category": "support"},
    },
    {
        "id": "company_benefits",
        "text": """公司员工福利政策（2025年版）：

医疗保险：
- 门诊报销比例 90%，住院 100%
- 年度体检免费（含家属一次半价）
- 牙科保险覆盖基础治疗

假期政策：
- 年假：入职第一年 10 天，满 3 年 15 天
- 病假：每年 12 天带薪病假
- 产假/陪产假：按国家标准 + 额外 7 天

其他福利：
- 餐补：每月 800 元
- 交通补贴：每月 500 元
- 通讯补贴：每月 200 元
- 学习基金：每年 5000 元（课程/书籍/认证报销）
- 健身房年卡：公司合作健身房免费""",
        "metadata": {"source": "company_benefits", "category": "hr"},
    },
]

# 合并知识库
ALL_DOCS = KNOWLEDGE_DOCS + EXTRA_DOCS


# ═══════════════════════════════════════════════════════════
# 1. 预处理：分词（中文友好）
# ═══════════════════════════════════════════════════════════

def tokenize_chinese(text: str) -> list[str]:
    """
    中文分词函数
    
    BM25 需要分词后的文档，中文没有天然的空格分隔
    最简单的方案：按字符切分（unigram）
    
    更好的方案（生产环境）：
    - jieba 分词：更准确
    - 但如果 tokenized 太粗，关键词匹配会变弱
    
    这里用字符级切分，因为：
    1. 不需要额外依赖
    2. 对中文关键词匹配足够（"X100"不会被打散）
    3. BM25 本来就更擅长精确匹配
    """
    # 字符级切分，但保留连续字母/数字
    import re
    tokens = []
    for chunk in re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]|[^\s]', text.lower()):
        tokens.append(chunk)
    return [t for t in tokens if t.strip()]


# ═══════════════════════════════════════════════════════════
# 2. HybridSearch —— 向量检索 + BM25
# ═══════════════════════════════════════════════════════════

class HybridSearcher:
    """
    混合检索器：向量检索 + BM25 关键词检索
    
    核心思想：取长补短
    - 向量检索：语义理解强（"坏了"="故障"）
    - BM25：精确关键词匹配强（"X100"型号）
    
    融合策略：Reciprocal Rank Fusion (RRF)
    - 两个排序列表按排名倒数加权合并
    - 在两个列表中都靠前的文档得分最高
    
    Parameters
    ----------
    alpha : 向量检索权重（0.0~1.0），默认 0.5
        0.0 = 纯 BM25
        0.5 = 各一半
        1.0 = 纯向量检索
    """
    
    def __init__(self, alpha: float = 0.5, collection_name: str = "hybrid_rag"):
        self.alpha = alpha
        self.collection_name = collection_name
        
        # ChromaDB 向量检索器
        self.embedding_fn = OllamaEmbeddingFunction(
            url=OLLAMA_BASE_URL,
            model_name=EMBEDDING_MODEL,
        )
        
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = None
        
        # BM25 索引（内存中）
        self.bm25 = None
        self.bm25_docs: list[dict] = []  # BM25 对应的文档列表
        
    def index(self, documents: list[dict]):
        """构建双索引：ChromaDB 向量索引 + BM25 关键词索引"""
        print("📥 构建 Hybrid 索引...")
        
        # ─── 1. ChromaDB 向量索引 ───
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        
        self.collection.add(
            documents=[doc["text"] for doc in documents],
            ids=[doc["id"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents],
        )
        
        # ─── 2. BM25 关键词索引 ───
        self.bm25_docs = documents
        
        # BM25Okapi 需要 tokenized 文档
        tokenized = [tokenize_chinese(doc["text"]) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
        
        print(f"   ✅ 向量索引: {len(documents)} 篇文档")
        print(f"   ✅ BM25 索引: {len(documents)} 篇文档")
        return self
    
    def _vector_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """向量检索：返回 [(doc_index, cosine_distance), ...]"""
        results = self.collection.query(query_texts=[query], n_results=top_k)
        
        # 构建 doc_id → index 映射
        id_to_index = {doc["id"]: i for i, doc in enumerate(self.bm25_docs)}
        
        scored = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            distance = results["distances"][0][i]
            doc_index = id_to_index.get(doc_id)
            if doc_index is not None:
                # 转换距离 → 相似度分数（距离越小，相似度越高）
                score = 1.0 / (1.0 + distance)
                scored.append((doc_index, score))
        
        return scored
    
    def _bm25_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """BM25 关键词检索"""
        tokenized_query = tokenize_chinese(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # 取 top_k 并归一化
        top_indices = np.argsort(scores)[::-1][:top_k]
        max_score = scores.max() if scores.max() > 0 else 1.0
        
        return [(int(idx), float(scores[idx] / max_score)) for idx in top_indices]
    
    def _rrf_fusion(
        self,
        vector_results: list[tuple[int, float]],
        bm25_results: list[tuple[int, float]],
    ) -> dict[int, float]:
        """
        Hybrid Score Fusion（归一化线性组合）
        
        公式: hybrid_score(d) = alpha * norm_vec(d) + (1-alpha) * norm_bm25(d)
        
        将两路分数分别归一化到 [0, 1]，再加权融合。
        比 RRF 更直观：分数直接反映相关性，而不是仅依赖排名。
        """
        scores: dict[int, float] = {}
        
        # 向量分数归一化到 [0, 1]
        vec_vals = [s for _, s in vector_results]
        vec_min, vec_max = min(vec_vals, default=0.0), max(vec_vals, default=1.0)
        vec_range = vec_max - vec_min if vec_max - vec_min > 1e-9 else 1.0
        for doc_idx, raw in vector_results:
            norm = (raw - vec_min) / vec_range
            scores[doc_idx] = scores.get(doc_idx, 0.0) + self.alpha * norm
        
        # BM25 分数归一化到 [0, 1]
        bm_vals = [s for _, s in bm25_results]
        bm_min, bm_max = min(bm_vals, default=0.0), max(bm_vals, default=1.0)
        bm_range = bm_max - bm_min if bm_max - bm_min > 1e-9 else 1.0
        for doc_idx, raw in bm25_results:
            norm = (raw - bm_min) / bm_range
            scores[doc_idx] = scores.get(doc_idx, 0.0) + (1 - self.alpha) * norm
        
        return scores
    
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        混合检索主函数
        
        返回: [{"text": ..., "metadata": ..., "hybrid_score": ..., "vector_score": ..., "bm25_score": ...}, ...]
        """
        # 向量检索
        vec_results = self._vector_search(query, top_k * 2)
        
        # BM25 检索
        bm_results = self._bm25_search(query, top_k * 2)
        
        # RRF 融合
        fused = self._rrf_fusion(vec_results, bm_results)
        
        # 创建分数 lookup
        vec_scores = {idx: score for idx, score in vec_results}
        bm_scores = {idx: score for idx, score in bm_results}
        
        # 排序并返回 top_k
        sorted_indices = sorted(fused, key=fused.get, reverse=True)[:top_k]
        
        results = []
        for idx in sorted_indices:
            doc = self.bm25_docs[idx]
            results.append({
                "text": doc["text"],
                "metadata": doc["metadata"],
                "hybrid_score": fused[idx],
                "vector_score": vec_scores.get(idx, 0.0),
                "bm25_score": bm_scores.get(idx, 0.0),
            })
        
        return results


# ═══════════════════════════════════════════════════════════
# 3. Reranking —— 重排序
# ═══════════════════════════════════════════════════════════

class Reranker:
    """
    重排序器：用 Cross-Encoder 对检索结果进行精细排序
    
    为什么需要 Reranking？
    - 向量检索和 BM25 都是「快速初筛」，精度有限
    - Cross-Encoder 把 (query, doc) 成对输入，输出相关性分数
    - 比 Bi-Encoder（向量相似度）准确得多，但更慢
    
    这里用一个简化的 LLM-based Reranker：
    - 生产环境用 Cohere Rerank / BGE-Reranker-v2
    - 我们这里用 LLM 打分（更直观理解原理）
    
    Bi-Encoder vs Cross-Encoder：
    ┌──────────────┬──────────────────┬──────────────────────┐
    │              │   Bi-Encoder      │   Cross-Encoder       │
    ├──────────────┼──────────────────┼──────────────────────┤
    │ 编码方式      │ 分别编码 q 和 d   │ 同时编码 (q, d) 对    │
    │ 速度          │ 快（可预计算 d）  │ 慢（每对都要算）      │
    │ 精度          │ 中等              │ 高                    │
    │ 使用阶段      │ 初筛（Top-K）     │ 精排（Top-K → Top-N） │
    └──────────────┴──────────────────┴──────────────────────┘
    
    流程：
    Hybrid Search → 20 篇候选 → Reranker → 5 篇最终结果
    """
    
    def __init__(self):
        self.llm = get_llm_client()
    
    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 3,
    ) -> list[dict]:
        """
        用 LLM 对候选文档进行重排序
        
        对每个候选文档，让 LLM 评估相关性
        返回 top_k 个最相关的文档
        """
        scored = []
        
        for candidate in candidates:
            relevance = self._score_relevance(query, candidate["text"])
            scored.append({
                **candidate,
                "relevance_score": relevance,
            })
        
        # 按相关性分数降序排列
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:top_k]
    
    def _score_relevance(self, query: str, doc_text: str) -> float:
        """
        用 LLM 评估文档与查询的相关性
        返回 0.0 ~ 1.0 的分数
        
        注意：这是为了教学目的展示 Reranking 原理
        生产环境应使用专门的 Cross-Encoder 模型（如 BGE-Reranker）
        """
        # 截断文档文本（太长浪费 token）
        doc_preview = doc_text[:800]
        
        prompt = f"""请评估以下文档与用户问题的相关性，只返回一个 0 到 1 之间的数字。

用户问题：{query}

文档内容：{doc_preview}

相关性分数（0=完全不相关，1=完美匹配）："""
        
        try:
            response = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            score_text = response.choices[0].message.content.strip()
            # 提取数字
            import re
            numbers = re.findall(r'[\d.]+', score_text)
            if numbers:
                score = float(numbers[0])
                return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"      ⚠️ Reranking 评分失败: {e}")
        
        return 0.5  # 默认中等相关性


# ═══════════════════════════════════════════════════════════
# 4. 完整 Pipeline：Hybrid Search + Rerank
# ═══════════════════════════════════════════════════════════

class AdvancedRAG:
    """
    高级 RAG Pipeline
    
    流程：
    1. Hybrid Search（向量 + BM25）→ 10 篇候选
    2. Reranking（LLM/Cross-Encoder）→ 3 篇最终
    3. LLM Generation（基于最终结果生成回答）
    """
    
    def __init__(self, alpha: float = 0.5):
        self.searcher = HybridSearcher(alpha=alpha)
        self.reranker = Reranker()
        self.llm = get_llm_client()
    
    def index(self, documents: list[dict]):
        self.searcher.index(documents)
        return self
    
    def query(self, question: str, hybrid_top_k: int = 10, final_top_k: int = 3) -> dict:
        print(f"\n{'='*60}")
        print(f"❓ 用户问题: {question}")
        
        # Step 1: Hybrid Search
        print(f"🔍 Step 1: Hybrid Search (向量+BM25) → Top-{hybrid_top_k}")
        candidates = self.searcher.search(question, top_k=hybrid_top_k)
        for i, doc in enumerate(candidates, 1):
            print(f"   {i}. [{doc['metadata']['source']}] "
                  f"vec={doc['vector_score']:.3f} bm25={doc['bm25_score']:.3f} "
                  f"hybrid={doc['hybrid_score']:.3f}")
        
        # Step 2: Reranking
        print(f"🎯 Step 2: Reranking → Top-{final_top_k}")
        reranked = self.reranker.rerank(question, candidates, top_k=final_top_k)
        for i, doc in enumerate(reranked, 1):
            print(f"   {i}. [{doc['metadata']['source']}] relevance={doc['relevance_score']:.2f}")
        
        # Step 3: Generate
        print("🤖 Step 3: LLM 生成回答...")
        context = "\n\n---\n\n".join([
            f"[来源: {doc['metadata']['source']}]\n{doc['text']}"
            for doc in reranked
        ])
        
        prompt = f"""你是一个专业的问答助手。请根据以下参考资料回答用户问题。

要求：
1. 只根据参考资料回答，不要编造
2. 引用来源
3. 如果资料中没有答案，说"根据现有资料无法回答"

参考资料：
{context}

用户问题：{question}

请回答："""
        
        response = self.llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        
        print(f"💬 回答:\n{answer}")
        
        return {
            "question": question,
            "candidates": candidates,
            "reranked": reranked,
            "answer": answer,
        }


# ═══════════════════════════════════════════════════════════
# 5. 对比实验：纯向量 vs Hybrid vs Hybrid+Rerank
# ═══════════════════════════════════════════════════════════

def compare_strategies():
    """
    对比三种检索策略的效果
    
    用同一个问题测试三种策略，观察检索结果差异
    """
    print("=" * 60)
    print("📊 检索策略对比实验")
    print("=" * 60)
    
    test_questions = [
        "X100手机的防水等级是多少？",
        "公司有哪些医疗福利？",
        "手机屏幕不亮了怎么处理？",
    ]
    
    # 1. 纯向量检索（作为 baseline）
    print("\n" + "─" * 60)
    print("策略 A: 纯向量检索 (ChromaDB)")
    print("─" * 60)
    
    vec_searcher = HybridSearcher(alpha=1.0)  # alpha=1.0 = 纯向量
    vec_searcher.index(ALL_DOCS)
    
    for q in test_questions:
        results = vec_searcher.search(q, top_k=3)
        print(f"\n❓ {q}")
        for i, doc in enumerate(results, 1):
            print(f"   {i}. [{doc['metadata']['source']}] "
                  f"score={doc['hybrid_score']:.4f}")
    
    # 2. Hybrid Search
    print("\n" + "─" * 60)
    print("策略 B: Hybrid Search (向量 + BM25, alpha=0.5)")
    print("─" * 60)
    
    hybrid_searcher = HybridSearcher(alpha=0.5)
    hybrid_searcher.index(ALL_DOCS)
    
    for q in test_questions:
        results = hybrid_searcher.search(q, top_k=3)
        print(f"\n❓ {q}")
        for i, doc in enumerate(results, 1):
            print(f"   {i}. [{doc['metadata']['source']}] "
                  f"vec={doc['vector_score']:.3f} bm25={doc['bm25_score']:.3f} "
                  f"hybrid={doc['hybrid_score']:.3f}")
    
    # 3. Hybrid + Rerank
    print("\n" + "─" * 60)
    print("策略 C: Hybrid Search + Reranking (完整 Pipeline)")
    print("─" * 60)
    
    adv_rag = AdvancedRAG(alpha=0.5)
    adv_rag.index(ALL_DOCS)
    
    for q in test_questions:
        result = adv_rag.query(q, hybrid_top_k=5, final_top_k=3)
        # 答案已经在 query() 里打印了，这里不再重复


# ═══════════════════════════════════════════════════════════
# 6. 交互模式
# ═══════════════════════════════════════════════════════════

def interactive_mode():
    print("=" * 60)
    print("🔍 高级 RAG 问答系统 — 交互模式")
    print("Hybrid Search + Reranking")
    print("输入问题进行提问，输入 'quit' 退出")
    print("=" * 60)
    
    adv_rag = AdvancedRAG(alpha=0.5)
    adv_rag.index(ALL_DOCS)
    
    while True:
        question = input("\n❓ 请输入问题: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not question:
            continue
        
        adv_rag.query(question, hybrid_top_k=8, final_top_k=3)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_mode()
    else:
        compare_strategies()
