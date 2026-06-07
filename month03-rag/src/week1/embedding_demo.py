"""
Day 3-4: Embedding 与向量数据库

目标：
1. 理解 Embedding —— 把文本变成数字向量
2. 计算句子间的语义相似度
3. 掌握 ChromaDB 的基本 CRUD 操作

依赖：pip install chromadb
"""

import numpy as np
from chromadb import Client
from chromadb.config import Settings

# ============================================================
# Part 1: Embedding 概念演示（不依赖任何 API）
# ============================================================

def cosine_similarity(a: list, b: list) -> float:
    """计算两个向量的余弦相似度"""
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def demo_embedding_concept():
    """
    用简化示例解释 Embedding 的核心思想
    
    真实的 Embedding 模型会把文本映射到高维空间（如 768/1536 维）
    这里用 4 维简化演示
    """
    print("=" * 60)
    print("📐 Part 1: Embedding 概念")
    print("=" * 60)
    
    # 模拟的 Embedding 向量（4 维简化版）
    # 在真实场景中，这些向量由模型生成
    simulated_embeddings = {
        "猫": [0.9, 0.1, 0.8, 0.2],
        "狗": [0.85, 0.15, 0.75, 0.25],    # 和"猫"接近（都是宠物）
        "汽车": [0.1, 0.9, 0.1, 0.8],       # 和"猫""狗"远（交通工具）
        "自行车": [0.15, 0.85, 0.1, 0.75],   # 和"汽车"接近（交通工具）
        "鱼": [0.7, 0.2, 0.7, 0.3],         # 和"猫"有点接近（动物）
    }
    
    print("\n📊 模拟 Embedding 向量（4 维简化）：")
    for word, vec in simulated_embeddings.items():
        print(f"   {word}: {vec}")
    
    print("\n📏 语义相似度（余弦相似度）：")
    words = list(simulated_embeddings.keys())
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            sim = cosine_similarity(
                simulated_embeddings[words[i]],
                simulated_embeddings[words[j]]
            )
            bar = "█" * int(sim * 20)
            print(f"   {words[i]} ↔ {words[j]}: {sim:.3f} {bar}")
    
    print("\n💡 洞察：")
    print("   猫↔狗 (0.99+) → 语义非常接近（都是宠物）")
    print("   汽车↔自行车 (0.99+) → 语义非常接近（都是交通工具）")
    print("   猫↔汽车 (0.2-) → 语义很远（不同类别）")


# ============================================================
# Part 2: 用 Ollama 本地模型生成真实 Embedding
# ============================================================

def get_embedding_ollama(text: str, model: str = "qwen3-embedding:4b") -> list:
    """调用本地 Ollama 获取 Embedding 向量"""
    import requests
    response = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": model, "input": text},
        timeout=30
    )
    result = response.json()
    return result["embeddings"][0]


def demo_real_embedding():
    """用本地 Embedding 模型计算真实语义相似度"""
    print("\n" + "=" * 60)
    print("🧠 Part 2: 真实 Embedding（qwen3-embedding:4b 本地模型）")
    print("=" * 60)
    
    # 测试句子
    sentences = [
        "Python 怎么创建字典？",
        "如何使用 Python 的 dict 类型？",
        "Python 的列表怎么用？",
        "今天天气怎么样？",
        "Python 怎么创建字典？",  # 和第 1 句完全相同
    ]
    
    try:
        print("\n生成 Embedding 中...")
        embeddings = [get_embedding_ollama(s) for s in sentences]
        print(f"向量维度: {len(embeddings[0])}")
        
        print("\n📏 语义相似度矩阵：")
        labels = [f"Q{i+1}" for i in range(len(sentences))]
        
        # 打印表头
        print(f"{'':>20}", end="")
        for label in labels:
            print(f"{label:>8}", end="")
        print()
        
        for i in range(len(sentences)):
            print(f"Q{i+1}: {sentences[i][:15]:>15}", end="")
            for j in range(len(sentences)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"{sim:>8.3f}", end="")
            print()
        
        print("\n💡 关键发现：")
        print("   Q1↔Q2 应该很高（都是问 Python 字典）")
        print("   Q1↔Q3 应该中等（都是 Python 但不同类型）")
        print("   Q1↔Q4 应该很低（完全不同话题）")
        print("   Q1↔Q5 应该是 1.0（完全相同）")
        
    except Exception as e:
        print(f"\n⚠️ 无法连接 Ollama: {e}")
        print("   请确保 Ollama 正在运行: ollama serve")
        print("   跳过真实 Embedding 演示，继续使用 ChromaDB 部分...")


# ============================================================
# Part 3: ChromaDB 基本操作
# ============================================================

def demo_chromadb():
    """ChromaDB CRUD 操作演示"""
    print("\n" + "=" * 60)
    print("🗄️ Part 3: ChromaDB 基本操作")
    print("=" * 60)
    
    # 使用内存模式（不持久化到磁盘）
    client = Client(Settings(anonymized_telemetry=False))
    
    # 1. 创建 Collection
    print("\n1️⃣ 创建 Collection")
    collection = client.get_or_create_collection(
        name="python_docs",
        metadata={"description": "Python 基础知识文档"}
    )
    print(f"   Collection: {collection.name}")
    
    # 2. 添加文档 (CREATE)
    print("\n2️⃣ 添加文档 (CREATE)")
    docs = [
        "Python 的列表（list）是一种有序的可变序列。用方括号 [] 创建。",
        "Python 的字典（dict）是键值对的集合。用花括号 {} 创建。",
        "Python 的元组（tuple）是不可变序列。用圆括号 () 创建。",
        "Python 的集合（set）是无序且不重复的元素集合。",
        "Python 的字符串是不可变的文本序列。",
    ]
    
    collection.add(
        documents=docs,
        ids=["doc1", "doc2", "doc3", "doc4", "doc5"],
        metadatas=[
            {"topic": "list", "difficulty": "basic"},
            {"topic": "dict", "difficulty": "basic"},
            {"topic": "tuple", "difficulty": "basic"},
            {"topic": "set", "difficulty": "basic"},
            {"topic": "string", "difficulty": "basic"},
        ]
    )
    print(f"   添加了 {len(docs)} 篇文档")
    print(f"   Collection 总数: {collection.count()}")
    
    # 3. 查询 (READ/QUERY) —— 这是最核心的操作
    print("\n3️⃣ 语义查询 (QUERY)")
    
    queries = [
        "怎么创建键值对？",
        "什么是不可变的序列？",
        "怎么去除重复元素？",
    ]
    
    for query in queries:
        print(f"\n   ❓ {query}")
        results = collection.query(
            query_texts=[query],
            n_results=2,
        )
        for i, (doc, dist) in enumerate(zip(results["documents"][0], results["distances"][0])):
            print(f"   {i+1}. [距离: {dist:.4f}] {doc[:50]}...")
    
    # 4. 条件查询（过滤 metadata）
    print("\n4️⃣ 条件过滤查询")
    results = collection.query(
        query_texts=["有序的数据结构"],
        n_results=3,
        where={"topic": {"$in": ["list", "tuple"]}},
    )
    print(f"   过滤 topic in [list, tuple]:")
    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        print(f"   [距离: {dist:.4f}] {doc[:50]}...")
    
    # 5. 更新文档 (UPDATE)
    print("\n5️⃣ 更新文档 (UPDATE)")
    collection.update(
        ids=["doc1"],
        documents=["Python 的列表（list）是一种有序的可变序列。支持增删改查操作。用方括号 [] 创建，如 [1, 2, 3]。"],
    )
    print("   更新了 doc1")
    
    # 6. 删除文档 (DELETE)
    print("\n6️⃣ 删除文档 (DELETE)")
    collection.delete(ids=["doc5"])
    print(f"   删除了 doc5")
    print(f"   Collection 总数: {collection.count()}")
    
    # 7. 按 ID 获取 (GET)
    print("\n7️⃣ 按 ID 获取 (GET)")
    result = collection.get(ids=["doc1", "doc2"])
    for doc_id, doc in zip(result["ids"], result["documents"]):
        print(f"   [{doc_id}] {doc[:60]}...")


# ============================================================
# Part 4: 关键词匹配 vs 语义检索对比
# ============================================================

def demo_comparison():
    """对比关键词匹配和语义检索的效果差异"""
    print("\n" + "=" * 60)
    print("⚔️ Part 4: 关键词匹配 vs 语义检索")
    print("=" * 60)
    
    client = Client(Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(name="comparison_test")
    
    # 知识库
    docs = [
        "Python 的列表（list）是一种有序的可变序列。可以用方括号 [] 创建。",
        "Python 的字典（dict）是键值对的集合。用花括号 {} 创建。",
        "Python 的元组（tuple）是不可变序列。用圆括号 () 创建。",
        "Python 的集合（set）是无序且不重复的元素集合。",
        "Python 的字符串是不可变的文本序列。",
    ]
    collection.add(
        documents=docs,
        ids=["d1", "d2", "d3", "d4", "d5"],
    )
    
    # 测试问题
    test_queries = [
        ("什么是不可变的序列？", "d3"),    # 关键词"不可变"在 d3 和 d5 都出现
        ("怎么去除重复？", "d4"),          # "重复" → set
        ("键值对怎么用？", "d2"),          # "键值对" → dict
    ]
    
    print()
    for query, expected in test_queries:
        results = collection.query(query_texts=[query], n_results=1)
        top_id = results["ids"][0][0]
        top_dist = results["distances"][0][0]
        match = "✅" if top_id == expected else "❌"
        print(f"   {match} Q: {query}")
        print(f"      期望: {expected} | 实际: {top_id} (距离: {top_dist:.4f})")
    
    print("\n💡 语义检索能理解'去除重复'='集合去重'，关键词匹配做不到！")


if __name__ == "__main__":
    demo_embedding_concept()
    demo_real_embedding()
    demo_chromadb()
    demo_comparison()
    
    print("\n" + "=" * 60)
    print("✅ Day 3-4 完成！")
    print("学到了：")
    print("  1. Embedding 把文本变成向量，语义相近 → 向量接近")
    print("  2. 余弦相似度衡量向量接近程度（0~1）")
    print("  3. ChromaDB: add / query / get / update / delete")
    print("  4. 语义检索 >> 关键词匹配（理解同义词和语义）")
    print("=" * 60)
