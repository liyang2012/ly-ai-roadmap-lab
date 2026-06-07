"""
Day 3-4 补充: ChromaDB 持久化存储

目标：理解内存模式 vs 持久化模式的区别

=== 两种模式对比 ===

内存模式 (Client):
  - 数据只在程序运行时存在
  - 程序结束 → 数据消失
  - 适合：测试、演示
  - 用法：client = chromadb.Client()

持久化模式 (PersistentClient):
  - 数据保存到指定目录
  - 程序重启 → 数据还在
  - 适合：生产环境
  - 用法：client = chromadb.PersistentClient(path="./chroma_data")

=== 什么时候需要持久化？ ===

知识库文档很大（几百上千篇）时，每次启动都重新索引很慢：
  - 5 篇文档：索引 ~1 秒
  - 100 篇文档：索引 ~10 秒
  - 1000 篇文档：索引 ~100 秒
  → 持久化后，启动时直接加载，秒级就绪

=== 距离空间说明 ===

ChromaDB 支持三种距离计算方式（在创建 Collection 时通过 metadata 指定）：

1. cosine（余弦相似度，我们用的）
   metadata={"hnsw:space": "cosine"}
   distance 范围: 0 ~ 2
   0 = 完全相同，越小越相似

2. l2（欧氏距离）
   metadata={"hnsw:space": "l2"}
   distance 范围: 0 ~ ∞
   0 = 完全相同，越小越相似

3. ip（内积）
   metadata={"hnsw:space": "ip"}
   distance 范围: -∞ ~ ∞
   越大越相似（和前两个相反！）
"""

import os
import tempfile
from chromadb import PersistentClient


def demo_persistent_chroma():
    """
    持久化 ChromaDB 完整演示
    
    展示：
    1. 创建持久化 Client
    2. 文档入库（首次）
    3. 数据持久化（下次启动自动加载）
    4. 语义查询
    """
    # 使用临时目录演示（实际生产中用固定路径）
    persist_dir = os.path.join(tempfile.gettempdir(), "rag_demo_chroma")
    print(f"持久化目录: {persist_dir}")
    
    # ─── 1. 创建持久化 Client ───
    # 数据会保存到 persist_dir 目录下
    # 目录结构：
    #   chroma.sqlite3          — 元数据数据库
    #   {collection_id}/        — 每个 Collection 的向量数据
    client = PersistentClient(path=persist_dir)
    
    # ─── 2. 创建或获取 Collection ───
    # get_or_create_collection:
    #   如果已存在 → 直接获取（不会重复创建）
    #   如果不存在 → 创建新的
    # 这是持久化模式的标准用法（vs 内存模式每次都 delete + create）
    collection = client.get_or_create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )
    
    # ─── 3. 添加文档（如果为空） ───
    # 持久化模式下，只需要首次添加
    # 后续启动时 collection.count() > 0，跳过添加
    if collection.count() == 0:
        docs = [
            "Agents SDK 是 OpenAI 推出的 Agent 开发框架，支持 Tool 调用和 Handoff。",
            "LangGraph 是 LangChain 团队推出的图编排框架，支持状态机和条件路由。",
            "RAG（检索增强生成）通过检索外部知识来增强 LLM 的回答质量。",
            "Embedding 模型将文本转换为高维向量，用于语义相似度计算。",
            "ChromaDB 是一个开源向量数据库，专为 AI 应用设计。",
        ]
        collection.add(
            documents=docs,
            ids=["kb1", "kb2", "kb3", "kb4", "kb5"],
            metadatas=[
                {"topic": "agents", "month": "1"},
                {"topic": "langgraph", "month": "2"},
                {"topic": "rag", "month": "3"},
                {"topic": "embedding", "month": "3"},
                {"topic": "vectordb", "month": "3"},
            ]
        )
        print(f"✅ 首次：添加了 {len(docs)} 篇文档")
    else:
        print(f"📦 已有 {collection.count()} 篇文档（从磁盘加载，无需重新索引）")
    
    # ─── 4. 语义查询 ───
    print("\n🔍 查询测试（注意：这里用的是 ChromaDB 默认英文 Embedding）：")
    queries = [
        "第 3 月学什么？",
        "怎么编排 Agent 的流程？",
        "向量数据库是什么？",
    ]
    
    for query in queries:
        results = collection.query(query_texts=[query], n_results=2)
        print(f"\n   ❓ {query}")
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        ):
            print(f"   [{meta['topic']}] (距离: {dist:.4f}) {doc[:50]}...")
    
    # ─── 5. 持久化说明 ───
    print(f"\n💡 数据已持久化到: {persist_dir}")
    print("   下次运行本程序时：")
    print("   - 不需要重新添加文档（直接从磁盘加载）")
    print("   - 向量索引也已保存（不需要重新计算）")
    print("   - 这就是持久化的意义：节省启动时间")


if __name__ == "__main__":
    demo_persistent_chroma()
