"""
Week 3 Day 4: Query 改写与扩展

目标：在检索之前改写用户问题，提高检索命中率

=== 为什么需要 Query 改写？ ===

用户的自然提问和文档的表述方式往往不一致：
- 用户："手机摔了怎么办"  → 文档："意外损坏维修流程"
- 用户："退款"           → 文档："退货退款政策"
- 用户："免邮"           → 文档："免运费条件"
- 用户："X100"           → 文档："X100 Pro Max"

Query Expansion（查询扩展）解决这个 gap：
1. 同义词扩展：把口语化表达映射到文档用词
2. 缩写扩展：X100 → X100 Pro Max
3. 多角度查询：从不同角度改写问题
4. 关键词提取：提取最关键的名词用于检索

=== 方法对比 ===

┌──────────────────┬────────────────┬──────────┬──────────┐
│ 方法              │ 实现            │ 延迟      │ 效果      │
├──────────────────┼────────────────┼──────────┼──────────┤
│ 人工同义词典       │ 硬编码映射      │ ~0ms     │ 中等      │
│ LLM 改写           │ GPT/GLM 生成   │ ~500ms   │ 好        │
│ 历史查询映射       │ embedding 聚类  │ ~50ms    │ 需要数据  │
│ 子问题拆解         │ LLM 分解        │ ~500ms   │ 复杂查询  │
└──────────────────┴────────────────┴──────────┴──────────┘

=== 在本脚本中 ===
我们使用 LLM 进行 Query 改写，教学目的：
1. 理解改写对检索的影响
2. 对比改写前后检索结果差异
3. 学会把改写集成到 RAG Pipeline
"""

import os
import sys
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from week1.simple_rag import get_llm_client
from advanced_retrieval import ALL_DOCS, HybridSearcher

# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"
LLM_MODEL = "glm-4-flash"
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db_query_rewrite")


# ═══════════════════════════════════════════════════════════
# 1. LLM-based Query Rewriter
# ═══════════════════════════════════════════════════════════

class QueryRewriter:
    """
    Query 改写器：把用户的自然语言问题改写成更适合检索的形式
    
    三种策略：
    1. keyword_extract: 提取核心关键词
    2. expand: 生成同义词/相关表达（用于扩展检索）
    3. decompose: 把复杂问题拆成多个子问题
    """
    
    def __init__(self):
        self.llm = get_llm_client()
    
    def keyword_extract(self, query: str) -> str:
        """
        提取核心关键词
        
        把自然语言问题压缩成关键词列表
        "X100手机的防水等级是多少？" → "X100 防水等级 IP68"
        """
        prompt = f"""请提取用户问题中的核心关键词，用于检索文档。
关键词应该包含：产品型号、问题类型、关键名词。
只输出关键词列表，用空格分隔。

用户问题：{query}
关键词："""
        
        try:
            response = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"      ⚠️ 关键词提取失败: {e}")
            return query
    
    def expand(self, query: str) -> str:
        """
        扩展查询：生成文档中可能使用的同义表达
        
        "免邮" → "免运费 包邮 免配送费 运费减免"
        "手机坏了" → "手机故障 手机损坏 设备问题 产品异常"
        """
        prompt = f"""用户用口语化的方式提出了问题。请用更正式、更接近产品文档的表述来改写这个问题。
同时加入同义词和相关表达。
直接输出改写后的文本，不要解释。

原始问题：{query}
改写后："""
        
        try:
            response = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"      ⚠️ 查询扩展失败: {e}")
            return query
    
    def decompose(self, query: str) -> list[str]:
        """
        拆解复杂问题为多个子问题
        
        "X100和R50哪个更值得买？" →
        ["X100的规格和价格", "R50的规格和价格", "两款手机对比"]
        """
        prompt = f"""请把以下复杂问题拆解为多个简单的子问题，每个子问题可以独立回答。
每行一个子问题，不超过3个。

复杂问题：{query}
子问题："""
        
        try:
            response = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
            )
            sub_questions = [
                q.strip("- ・1234567890") for q in response.choices[0].message.content.strip().split("\n")
                if q.strip() and not q.strip().startswith("#")
            ]
            return sub_questions[:3]
        except Exception as e:
            print(f"      ⚠️ 问题拆解失败: {e}")
            return [query]


# ═══════════════════════════════════════════════════════════
# 2. QueryRewritingRAG —— 集成改写的 RAG Pipeline
# ═══════════════════════════════════════════════════════════

class QueryRewritingRAG:
    """
    集成 Query 改写的 RAG Pipeline
    
    流程：
    1. Query 改写 → 生成更好的搜索查询
    2. 用改写后的查询进行 Hybrid Search
    3. 合并多个查询结果（去重 + 分数融合）
    4. 用原始问题 + 检索结果生成回答
    
    注意：Generation 阶段仍用原始问题
    - 因为用户期望的回答是针对原始问题的
    - 改写只是为了让检索更准
    """
    
    def __init__(self):
        self.rewriter = QueryRewriter()
        self.searcher = HybridSearcher(alpha=0.5)
        self.llm = get_llm_client()
    
    def index(self, documents: list[dict]):
        self.searcher.index(documents)
        return self
    
    def query(
        self,
        question: str,
        strategy: str = "expand",
        top_k: int = 5,
    ) -> dict:
        """
        Parameters
        ----------
        strategy : "keyword" | "expand" | "decompose" | "none"
            改写策略
        """
        print(f"\n{'='*60}")
        print(f"❓ 原始问题: {question}")
        print(f"🔧 改写策略: {strategy}")
        
        if strategy == "none":
            # 不改写，直接检索
            rewritten_queries = [question]
        elif strategy == "keyword":
            keywords = self.rewriter.keyword_extract(question)
            print(f"   📝 关键词: {keywords}")
            rewritten_queries = [keywords]
        elif strategy == "expand":
            expanded = self.rewriter.expand(question)
            print(f"   📝 扩展后: {expanded}")
            rewritten_queries = [expanded]
        elif strategy == "decompose":
            sub_questions = self.rewriter.decompose(question)
            print(f"   📝 子问题: {sub_questions}")
            rewritten_queries = sub_questions
        else:
            rewritten_queries = [question]
        
        # 用改写后的查询进行检索
        all_results = {}  # doc_id → best_score
        
        for rq in rewritten_queries:
            print(f"\n🔍 检索: \"{rq}\"")
            results = self.searcher.search(rq, top_k=top_k)
            for doc in results:
                doc_id = doc["metadata"]["source"]
                if doc_id not in all_results or doc["hybrid_score"] > all_results[doc_id]["score"]:
                    all_results[doc_id] = {
                        "doc": doc,
                        "score": doc["hybrid_score"],
                    }
        
        # 合并排序
        merged = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)[:top_k]
        final_docs = [item["doc"] for item in merged]
        
        print(f"\n📋 合并结果 (Top-{top_k}):")
        for i, doc in enumerate(final_docs, 1):
            print(f"   {i}. [{doc['metadata']['source']}] score={sum(1 for _ in all_results if all_results[_]['doc']['metadata']['source']==doc['metadata']['source'])} hits")
        
        # 生成回答（用原始问题）
        context = "\n\n---\n\n".join([
            f"[来源: {doc['metadata']['source']}]\n{doc['text']}"
            for doc in final_docs
        ])
        
        prompt = f"""你是一个专业的问答助手。根据参考资料回答用户问题。

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
        
        print(f"\n💬 回答:\n{answer}")
        
        return {
            "question": question,
            "strategy": strategy,
            "rewritten_queries": rewritten_queries,
            "retrieved_docs": final_docs,
            "answer": answer,
        }


# ═══════════════════════════════════════════════════════════
# 3. 对比实验：不同改写策略的效果
# ═══════════════════════════════════════════════════════════

def compare_strategies():
    """
    对比四种改写策略的效果
    """
    print("=" * 60)
    print("📊 Query 改写策略对比实验")
    print("=" * 60)
    
    rag = QueryRewritingRAG()
    rag.index(ALL_DOCS)
    
    # 设计一些故意用口语化、缩写的问题
    test_questions = [
        ("X100能下水不？", "expand"),     # 口语化 → 需要扩展为"防水"
        ("员工看病能报销多少", "expand"),   # 口语化 → 需要扩展为"医疗保险"
        ("手机出毛病了怎么整", "keyword"),  # 口语化 → 需要提取关键词
        ("R50和X100有啥区别", "decompose"), # 对比 → 需要拆解
    ]
    
    for q, strategy in test_questions:
        rag.query(q, strategy=strategy)


def demo_rewrite_only():
    """仅演示改写效果，不检索"""
    rewriter = QueryRewriter()
    
    test_queries = [
        "X100能下水不？",
        "员工生病看医生能报销多少？",
        "手机老是自己关机咋整",
        "这两款手机哪个更适合大学生用？",
    ]
    
    print("=" * 60)
    print("🔧 Query 改写演示")
    print("=" * 60)
    
    for q in test_queries:
        print(f"\n原始问题: {q}")
        print(f"关键词:   {rewriter.keyword_extract(q)}")
        print(f"扩展:     {rewriter.expand(q)}")
        print(f"拆解:     {rewriter.decompose(q)}")
        print("-" * 40)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if "--compare" in sys.argv:
        compare_strategies()
    elif "--demo" in sys.argv:
        demo_rewrite_only()
    else:
        # 默认：先演示改写效果，再对比检索效果
        demo_rewrite_only()
        print("\n")
        compare_strategies()
