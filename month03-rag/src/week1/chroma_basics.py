"""
Day 3-4 补充: ChromaDB 持久化存储

目标：理解内存模式 vs 持久化模式的区别
"""

from chromadb import PersistentClient


def demo_persistent_chroma():
    """
    持久化 ChromaDB —— 数据保存到磁盘
    
    内存模式：程序结束 → 数据消失
    持久化模式：数据保存到指定目录，下次还能读取
    """
    import tempfile
    import os
    
    # 使用临时目录演示
    persist_dir = os.path.join(tempfile.gettempdir(), "rag_demo_chroma")
    print(f"持久化目录: {persist_dir}")
    
    # 1. 创建持久化 Client
    client = PersistentClient(path=persist_dir)
    
    # 2. 创建或获取 Collection
    collection = client.get_or_create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )
    
    # 3. 添加文档（如果为空）
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
        print(f"✅ 添加了 {len(docs)} 篇文档")
    else:
        print(f"📦 已有 {collection.count()} 篇文档（持久化数据）")
    
    # 4. 查询
    print("\n🔍 查询测试：")
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
    
    # 5. 清理（演示用）
    print(f"\n💡 数据已持久化到: {persist_dir}")
    print("   下次运行时，数据依然存在（不需要重新添加）")
    
    # 展示距离空间的含义
    print("\n📏 距离空间说明：")
    print("   cosine: 0 = 完全相同, 2 = 完全相反")
    print("   l2: 欧氏距离，越小越相似")
    print("   ip: 内积，越大越相似")


if __name__ == "__main__":
    demo_persistent_chroma()
