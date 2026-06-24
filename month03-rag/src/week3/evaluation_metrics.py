"""
Week 3 Day 5-6: 检索效果评估指标

目标：建立可量化的评估体系，用数据对比不同检索策略的优劣

=== 为什么需要评估指标？ ===

之前我们都是"凭感觉"判断检索好不好。但真正的工程需要量化：
- "这个新策略比旧的好" → 好多少？
- "调整了 alpha 参数" → 对效果有什么影响？
- "加了 Reranker" → 到底提升多大？

评估指标就是用数字回答这些问题。

=== 核心指标 ===

1. Hit Rate (命中率)
   相关文档是否出现在 Top-K 中？
   公式: HR@K = (至少命中1篇相关文档的查询数) / 总查询数
   简单直观，但只看"有没有"，不看"排第几"

2. MRR (Mean Reciprocal Rank，平均倒数排名)
   第一个相关文档排在哪里？
   公式: MRR = (1/N) * Σ(1/rank_of_first_relevant)
   考虑了排名位置，越靠前越好

3. nDCG (Normalized Discounted Cumulative Gain)
   综合考虑所有相关文档的排名和相关性程度
   公式: nDCG@K = DCG@K / IDCG@K
   最全面的评估指标，工业标准

=== 评估流程 ===

1. 准备测试集：查询 + 人工标注的相关文档
2. 对每个查询运行检索
3. 计算各项指标
4. 对比不同策略的指标差异

=== 运行方式 ===
    python evaluation_metrics.py                # 完整评估对比
    python evaluation_metrics.py --quick        # 仅快速评估（不用 LLM Reranker）
"""

import os
import sys
import json
import math
import time
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from advanced_retrieval import (
    ALL_DOCS,
    HybridSearcher,
    Reranker,
)


# ═══════════════════════════════════════════════════════════
# 1. 测试集：人工标注的相关文档
# ═══════════════════════════════════════════════════════════

@dataclass
class EvalQuery:
    """评估用的单条查询"""
    query: str                      # 用户问题
    relevant_docs: list[str]        # 人工标注的相关文档 ID（按重要性排序）
    relevant_scores: Optional[list[int]] = None  # 相关性打分（3=高度相关, 2=相关, 1=有点相关）
    description: str = ""           # 说明


# 测试集 —— 人工标注哪些文档应该被检索到
TEST_QUERIES = [
    EvalQuery(
        query="X100防水吗？",
        relevant_docs=["product_x100_manual"],
        relevant_scores=[3],
        description="精确型号查询",
    ),
    EvalQuery(
        query="手机坏了怎么修",
        relevant_docs=["product_warranty", "troubleshooting_guide"],
        relevant_scores=[3, 2],
        description="口语化故障查询",
    ),
    EvalQuery(
        query="退款政策是什么",
        relevant_docs=["refund_policy"],
        relevant_scores=[3],
        description="政策查询",
    ),
    EvalQuery(
        query="怎么免运费",
        relevant_docs=["shipping_info", "vip_benefits"],
        relevant_scores=[3, 2],
        description="物流查询 + 会员权益",
    ),
    EvalQuery(
        query="员工看病怎么报销",
        relevant_docs=["company_benefits"],
        relevant_scores=[3],
        description="HR 政策查询",
    ),
    EvalQuery(
        query="屏幕不亮了",
        relevant_docs=["troubleshooting_guide"],
        relevant_scores=[3],
        description="故障排查",
    ),
    EvalQuery(
        query="新用户有什么优惠",
        relevant_docs=["coupon_rules"],
        relevant_scores=[3],
        description="优惠查询",
    ),
    EvalQuery(
        query="R50的电池多大",
        relevant_docs=["product_r50_spec"],
        relevant_scores=[3],
        description="规格查询",
    ),
    EvalQuery(
        query="充电慢怎么办",
        relevant_docs=["troubleshooting_guide", "product_x100_manual"],
        relevant_scores=[3, 2],
        description="多文档覆盖",
    ),
    EvalQuery(
        query="怎么成为钻石会员",
        relevant_docs=["vip_benefits"],
        relevant_scores=[3],
        description="会员查询",
    ),
]


# ═══════════════════════════════════════════════════════════
# 2. 评估指标计算
# ═══════════════════════════════════════════════════════════

class RetrievalEvaluator:
    """
    检索评估器
    
    Usage:
        evaluator = RetrievalEvaluator(test_queries)
        metrics = evaluator.evaluate(search_fn, strategy_name="Hybrid", k=5)
        print(metrics)
    """
    
    def __init__(self, test_queries: list[EvalQuery]):
        self.test_queries = test_queries
    
    def hit_rate(self, results_per_query: list[list[str]], k: int) -> float:
        """
        Hit Rate @ K
        
        计算有多少查询在 Top-K 结果中至少命中了一篇相关文档
        
        Parameters
        ----------
        results_per_query : [[doc_id, ...], ...]  每个查询的检索结果（按排名排列的 doc_id 列表）
        k : 评估的 Top-K
        
        Returns
        -------
        float : 0.0 ~ 1.0
        """
        hits = 0
        for i, results in enumerate(results_per_query):
            relevant_set = set(self.test_queries[i].relevant_docs)
            if any(doc_id in relevant_set for doc_id in results[:k]):
                hits += 1
        return hits / len(results_per_query)
    
    def mrr(self, results_per_query: list[list[str]]) -> float:
        """
        MRR (Mean Reciprocal Rank)
        
        第一个相关文档排名的倒数的平均值
        排名越靠前，MRR 越高
        
        例：
        - 第 1 名命中 → 1/1 = 1.0
        - 第 3 名命中 → 1/3 = 0.33
        - 没命中 → 0
        """
        reciprocals = []
        for i, results in enumerate(results_per_query):
            relevant_set = set(self.test_queries[i].relevant_docs)
            
            found = False
            for rank, doc_id in enumerate(results, 1):
                if doc_id in relevant_set:
                    reciprocals.append(1.0 / rank)
                    found = True
                    break
            
            if not found:
                reciprocals.append(0.0)
        
        return sum(reciprocals) / len(reciprocals)
    
    def ndcg(
        self,
        results_per_query: list[list[str]],
        k: int,
    ) -> float:
        """
        nDCG @ K (Normalized Discounted Cumulative Gain)
        
        最全面的检索评估指标
        
        步骤：
        1. 对每个查询，计算 DCG@K
        2. 计算 IDCG@K（理想排序下的 DCG）
        3. nDCG = DCG / IDCG
        
        公式：
        DCG@k = Σ(rel_i / log2(i+1))  for i = 1..k
        IDCG@k = 理想排序下的 DCG
        nDCG@k = DCG@k / IDCG@k
        """
        ndcg_scores = []
        
        for i, results in enumerate(results_per_query):
            eq = self.test_queries[i]
            
            # 构建 doc_id → relevance_score 映射
            relevance_map = {}
            if eq.relevant_scores:
                for doc_id, score in zip(eq.relevant_docs, eq.relevant_scores):
                    relevance_map[doc_id] = score
            else:
                for doc_id in eq.relevant_docs:
                    relevance_map[doc_id] = 1  # 默认相关性为 1
            
            # DCG@k
            dcg = 0.0
            for rank, doc_id in enumerate(results[:k], 1):
                rel = relevance_map.get(doc_id, 0)
                dcg += rel / math.log2(rank + 1)
            
            # IDCG@k (按相关性降序排列的理想 DCG)
            ideal_rels = sorted(relevance_map.values(), reverse=True)[:k]
            idcg = 0.0
            for rank, rel in enumerate(ideal_rels, 1):
                idcg += rel / math.log2(rank + 1)
            
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcg_scores.append(ndcg)
        
        return sum(ndcg_scores) / len(ndcg_scores)
    
    def evaluate(
        self,
        search_fn,
        strategy_name: str = "Unknown",
        k: int = 5,
    ) -> dict:
        """
        对搜索策略进行完整评估
        
        Parameters
        ----------
        search_fn : callable(query) → list[dict]
            搜索函数，接收查询字符串，返回文档列表（每个文档有 metadata.source）
        strategy_name : str
            策略名称，用于输出
        k : int
            评估的 Top-K
        
        Returns
        -------
        dict with keys: strategy, k, hit_rate, mrr, ndcg, avg_latency_ms
        """
        print(f"\n📊 评估: {strategy_name}")
        
        results_per_query = []
        latencies = []
        
        for eq in self.test_queries:
            t0 = time.time()
            retrieved_docs = search_fn(eq.query)
            latency = (time.time() - t0) * 1000  # ms
            latencies.append(latency)
            
            # 提取 doc_id 列表
            doc_ids = [doc["metadata"]["source"] for doc in retrieved_docs[:k]]
            results_per_query.append(doc_ids)
            
            # 打印每个查询的结果（调试用）
            relevant_set = set(eq.relevant_docs)
            matched = [did for did in doc_ids if did in relevant_set]
            status = "✅" if matched else "❌"
            print(f"   {status} \"{eq.query[:30]}...\" → {matched if matched else 'miss'} ({latency:.0f}ms)")
        
        hr = self.hit_rate(results_per_query, k)
        reciprocal = self.mrr(results_per_query)
        ndcg_score = self.ndcg(results_per_query, k)
        avg_latency = sum(latencies) / len(latencies)
        
        metrics = {
            "strategy": strategy_name,
            "k": k,
            "hit_rate": hr,
            "mrr": reciprocal,
            "ndcg": ndcg_score,
            "avg_latency_ms": avg_latency,
        }
        
        print(f"\n   📈 Hit Rate@{k}:  {hr:.2%}")
        print(f"   📈 MRR:          {reciprocal:.4f}")
        print(f"   📈 nDCG@{k}:      {ndcg_score:.4f}")
        print(f"   ⏱️  Avg Latency:  {avg_latency:.0f}ms")
        
        return metrics


# ═══════════════════════════════════════════════════════════
# 3. 对比实验：4 种检索策略
# ═══════════════════════════════════════════════════════════

def make_search_fn(alpha, use_rerank=False, name=""):
    """
    工厂函数：创建不同配置的搜索函数
    统一接口：search(query) → list[dict]
    """
    import uuid
    # 每个 searcher 用不同 collection name 避免 ChromaDB 冲突
    coll_name = f"eval_{name}_{uuid.uuid4().hex[:8]}"
    searcher = HybridSearcher(alpha=alpha, collection_name=coll_name)
    searcher.index(ALL_DOCS)
    
    if use_rerank:
        reranker = Reranker()
        
        def search_with_rerank(query: str) -> list[dict]:
            candidates = searcher.search(query, top_k=10)
            return reranker.rerank(query, candidates, top_k=5)
        
        return search_with_rerank
    else:
        def search_simple(query: str) -> list[dict]:
            return searcher.search(query, top_k=5)
        
        return search_simple


def run_full_evaluation():
    """对比 4 种策略的评估结果"""
    evaluator = RetrievalEvaluator(TEST_QUERIES)
    
    strategies = [
        ("纯向量检索 (α=1.0)", make_search_fn(alpha=1.0, use_rerank=False, name="vec")),
        ("Hybrid (α=0.5)", make_search_fn(alpha=0.5, use_rerank=False, name="hyb")),
        ("Hybrid + Rerank", make_search_fn(alpha=0.5, use_rerank=True, name="rrk")),
        ("纯 BM25 (α=0.0)", make_search_fn(alpha=0.0, use_rerank=False, name="bm25")),
    ]
    
    all_metrics = []
    for name, fn in strategies:
        metrics = evaluator.evaluate(fn, strategy_name=name, k=5)
        all_metrics.append(metrics)
        print()
    
    # ─── 汇总对比表 ───
    print("=" * 80)
    print("📊 策略对比汇总")
    print("=" * 80)
    print(f"{'策略':<25} {'Hit Rate':>8} {'MRR':>8} {'nDCG@5':>8} {'延迟':>8}")
    print("-" * 60)
    
    best = max(all_metrics, key=lambda m: m["ndcg"])
    
    for m in all_metrics:
        marker = " ⭐" if m["strategy"] == best["strategy"] else ""
        print(f"{m['strategy']:<25} {m['hit_rate']:>7.1%} {m['mrr']:>8.4f} "
              f"{m['ndcg']:>8.4f} {m['avg_latency_ms']:>6.0f}ms{marker}")
    
    print(f"\n🏆 最佳策略: {best['strategy']} (nDCG@5 = {best['ndcg']:.4f})")
    
    # ─── 逐查询详细 ───
    print("\n" + "=" * 80)
    print("📋 逐查询详细结果")
    print("=" * 80)
    
    hybrid_fn = make_search_fn(alpha=0.5, use_rerank=True)
    for eq in TEST_QUERIES:
        results = hybrid_fn(eq.query)
        doc_ids = [doc["metadata"]["source"] for doc in results[:5]]
        hits = [did for did in doc_ids if did in eq.relevant_docs]
        print(f"\n❓ {eq.query} ({eq.description})")
        print(f"   期望: {eq.relevant_docs}")
        print(f"   检索: {doc_ids}")
        print(f"   命中: {hits if hits else '❌ 未命中'}")
    
    return all_metrics


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    quick = "--quick" in sys.argv
    
    if quick:
        # 快速模式：不用 LLM Reranker，只测三种简单策略
        print("⚡ 快速评估模式（跳过 Reranker）")
        evaluator = RetrievalEvaluator(TEST_QUERIES)
        
        for name, alpha in [("纯向量", 1.0), ("Hybrid", 0.5), ("纯 BM25", 0.0)]:
            evaluator.evaluate(
                make_search_fn(alpha=alpha, use_rerank=False),
                strategy_name=name,
                k=5,
            )
    else:
        run_full_evaluation()
