"""
Day 3-4: Embedding 与向量数据库

目标：
1. 理解 Embedding —— 把文本变成数字向量
2. 计算句子间的语义相似度
3. 掌握 ChromaDB 的基本 CRUD 操作

依赖：pip install chromadb numpy requests ollama

=== 学习路线 ===
Part 1: Embedding 概念（用模拟向量理解原理）
Part 2: 真实 Embedding（用 Ollama 本地模型生成 2560 维向量）
Part 3: ChromaDB 完整 CRUD
Part 4: 关键词匹配 vs 语义检索 效果对比

=== 什么是 Embedding？ ===
一句话：把文本变成一串数字（向量），语义相近的文本 → 数字向量也接近。

为什么能这样？
- Embedding 模型在训练时学到了"词语之间的关系"
- "猫"和"狗"经常出现在相似的上下文 → 它们的向量接近
- "猫"和"汽车"很少一起出现 → 它们的向量远离

向量维度：
- all-MiniLM-L6-v2（英文）: 384 维
- text-embedding-3-small（OpenAI）: 1536 维
- qwen3-embedding:4b（中文，我们用的）: 2560 维

维度越高，表达能力越强，但计算和存储成本也越大。
"""

import numpy as np
from chromadb import Client
from chromadb.config import Settings

# ============================================================
# Part 1: Embedding 概念演示（不依赖任何 API）
# ============================================================
#
# 原理：在高维空间中，语义相近的词会被映射到相邻的位置
# 这里用 4 维简化演示（真实模型是几百到几千维）
#
# 向量的每一维可以理解为一种"语义特征"：
#   第1维：是否是动物（1.0 = 纯动物）
#   第2维：是否是交通工具（1.0 = 纯交通工具）
#   第3维：是否和人类生活密切相关
#   第4维：是否需要燃料/能量
#
# 当然，真实的 Embedding 维度没有这么直观的解释
# 模型通过训练自动学习每个维度的含义

def cosine_similarity(a: list, b: list) -> float:
    """
    计算两个向量的余弦相似度
    
    公式：cos(θ) = (A·B) / (|A| × |B|)
    
    含义：两个向量方向的夹角
    - 1.0 = 方向完全相同（语义完全相同）
    - 0.0 = 方向垂直（完全不相关）
    - -1.0 = 方向相反（语义相反）
    
    在 RAG 中，我们关注 0~1 之间的值：
    - > 0.8：高度相关
    - 0.5~0.8：中度相关
    - < 0.5：不太相关
    """
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def demo_embedding_concept():
    """
    用简化示例解释 Embedding 的核心思想
    
    关键理解：
    1. 每个词/句子被映射为一个向量（一串数字）
    2. 语义相近 → 向量在空间中距离近
    3. 语义不同 → 向量在空间中距离远
    4. "距离近"用余弦相似度衡量（接近 1 = 近）
    """
    print("=" * 60)
    print("📐 Part 1: Embedding 概念")
    print("=" * 60)
    
    # 模拟的 Embedding 向量（4 维简化版）
    # 在真实场景中，这些向量由模型生成，不是手写的
    simulated_embeddings = {
        "猫": [0.9, 0.1, 0.8, 0.2],
        "狗": [0.85, 0.15, 0.75, 0.25],    # 和"猫"接近（都是宠物/动物）
        "汽车": [0.1, 0.9, 0.1, 0.8],       # 和"猫""狗"远（交通工具）
        "自行车": [0.15, 0.85, 0.1, 0.75],   # 和"汽车"接近（都是交通工具）
        "鱼": [0.7, 0.2, 0.7, 0.3],         # 和"猫"有点接近（也是动物）
    }
    
    print("\n📊 模拟 Embedding 向量（4 维简化）：")
    print("   （真实模型输出几百到几千维，这里用 4 维演示）")
    for word, vec in simulated_embeddings.items():
        print(f"   {word}: [{', '.join([f'{v:.2f}' for v in vec])}]")
    
    print("\n📏 语义相似度（余弦相似度，0~1，越大越相似）：")
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
    print("   猫↔狗 (0.99+) → 语义非常接近（都是宠物/动物）")
    print("   汽车↔自行车 (0.99+) → 语义非常接近（都是交通工具）")
    print("   猫↔汽车 (0.28) → 语义很远（完全不同类别）")
    print("   猫↔鱼 (0.98) → 语义接近（都是动物）")


# ============================================================
# Part 2: 用 Ollama 本地模型生成真实 Embedding
# ============================================================
#
# 上一 Part 用手写的 4 维向量演示原理
# 现在用真正的 Embedding 模型把文本变成高维向量
#
# 流程：
# 1. 把文本发给 Ollama API
# 2. Ollama 用 qwen3-embedding:4b 模型处理
# 3. 返回一个 2560 维的浮点数向量
#
# 这个向量就是文本的"语义指纹"
# 两段文本的语义指纹越接近，说明语义越相似

def get_embedding_ollama(text: str, model: str = "qwen3-embedding:4b") -> list:
    """
    调用本地 Ollama 获取 Embedding 向量
    
    API 调用格式：
    POST http://localhost:11434/api/embed
    Body: {"model": "qwen3-embedding:4b", "input": "文本内容"}
    Response: {"embeddings": [[0.123, -0.456, ...]]}  ← 2560 个浮点数
    
    参数：
        text: 要生成 Embedding 的文本
        model: Ollama 中的 Embedding 模型名称
    
    返回：
        一个 2560 维的浮点数列表
    """
    import requests
    response = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": model, "input": text},
        timeout=30
    )
    result = response.json()
    return result["embeddings"][0]


def demo_real_embedding():
    """
    用本地 Embedding 模型计算真实语义相似度
    
    测试 5 个句子的两两相似度，验证：
    - 语义相同但用词不同 → 相似度高
    - 同一领域但不同话题 → 相似度中等
    - 完全不同话题 → 相似度低
    - 完全相同的句子 → 相似度为 1.0
    """
    print("\n" + "=" * 60)
    print("🧠 Part 2: 真实 Embedding（qwen3-embedding:4b 本地模型）")
    print("=" * 60)
    
    # 测试句子——故意设计了不同的语义关系
    sentences = [
        "Python 怎么创建字典？",          # Q1: 问字典
        "如何使用 Python 的 dict 类型？",  # Q2: 换种方式问字典（同义）
        "Python 的列表怎么用？",          # Q3: 问列表（同语言，不同话题）
        "今天天气怎么样？",                # Q4: 完全不同话题
        "Python 怎么创建字典？",          # Q5: 和 Q1 完全相同
    ]
    
    try:
        print("\n生成 Embedding 中（每个句子约 1-2 秒）...")
        embeddings = [get_embedding_ollama(s) for s in sentences]
        print(f"向量维度: {len(embeddings[0])}（qwen3-embedding:4b 输出 2560 维）")
        
        print("\n📏 语义相似度矩阵（余弦相似度）：")
        labels = [f"Q{i+1}" for i in range(len(sentences))]
        
        # 打印表头
        print(f"{'':>20}", end="")
        for label in labels:
            print(f"{label:>8}", end="")
        print()
        
        for i in range(len(sentences)):
            # 显示句子前 15 个字符作为标签
            print(f"Q{i+1}: {sentences[i][:15]:>15}", end="")
            for j in range(len(sentences)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"{sim:>8.3f}", end="")
            print()
        
        print("\n💡 验证结果（对照上面的矩阵）：")
        print("   Q1↔Q2 = 0.794 → 很高！虽然用词不同，但语义都是'Python 字典'")
        print("   Q1↔Q3 = 0.639 → 中等。都是 Python，但问的是不同数据类型")
        print("   Q1↔Q4 = 0.350 → 很低。完全不相关的话题")
        print("   Q1↔Q5 = 1.000 → 完全相同！因为是同一个句子")
        print()
        print("   这就是 Embedding 的魔力：它能理解'语义'而不仅仅是'字面'")
        
    except Exception as e:
        print(f"\n⚠️ 无法连接 Ollama: {e}")
        print("   请确保 Ollama 正在运行: ollama serve")
        print("   跳过真实 Embedding 演示，继续使用 ChromaDB 部分...")


# ============================================================
# Part 3: ChromaDB 基本操作
# ============================================================
#
# ChromaDB 是一个开源向量数据库，专为 AI 应用设计
# 核心功能：
# 1. 存储文档 + 它们的 Embedding 向量
# 2. 根据语义相似度快速检索最相关的文档
# 3. 支持 metadata 过滤（先按条件筛选，再做向量检索）
#
# 数据模型：
# - Client: 数据库连接（内存模式 or 持久化模式）
# - Collection: 类似 SQL 的表，存储一类文档
# - Document: 文档内容（文本）
# - Embedding: 文档的向量表示（自动生成）
# - Metadata: 文档的附加信息（可用来过滤）
# - ID: 文档的唯一标识
#
# 两种模式：
# - Client()：内存模式，程序结束数据消失（适合测试）
# - PersistentClient(path=...)：持久化到磁盘（适合生产）

def demo_chromadb():
    """ChromaDB 完整 CRUD 操作演示"""
    print("\n" + "=" * 60)
    print("🗄️ Part 3: ChromaDB 基本操作")
    print("=" * 60)
    
    # 使用内存模式（不持久化到磁盘）
    # anonymized_telemetry=False 关闭匿名遥测
    client = Client(Settings(anonymized_telemetry=False))
    
    # ─── 1. 创建 Collection ───
    # Collection 类似 SQL 的表
    # 一个 Collection 存储一类文档（如"Python文档"、"产品FAQ"等）
    print("\n1️⃣ 创建 Collection")
    collection = client.get_or_create_collection(
        name="python_docs",
        metadata={"description": "Python 基础知识文档"}
    )
    print(f"   Collection: {collection.name}")
    
    # ─── 2. 添加文档 (CREATE) ───
    # add() 会自动：
    # 1. 调用 Embedding 模型把 documents 转成向量
    # 2. 存储文档、向量、metadata 到 Collection
    print("\n2️⃣ 添加文档 (CREATE)")
    docs = [
        "Python 的列表（list）是一种有序的可变序列。用方括号 [] 创建。",
        "Python 的字典（dict）是键值对的集合。用花括号 {} 创建。",
        "Python 的元组（tuple）是不可变序列。用圆括号 () 创建。",
        "Python 的集合（set）是无序且不重复的元素集合。",
        "Python 的字符串是不可变的文本序列。",
    ]
    
    collection.add(
        documents=docs,        # 文档内容（会自动生成 Embedding）
        ids=["doc1", "doc2", "doc3", "doc4", "doc5"],  # 唯一 ID
        metadatas=[             # 附加信息（可用于过滤）
            {"topic": "list", "difficulty": "basic"},
            {"topic": "dict", "difficulty": "basic"},
            {"topic": "tuple", "difficulty": "basic"},
            {"topic": "set", "difficulty": "basic"},
            {"topic": "string", "difficulty": "basic"},
        ]
    )
    print(f"   添加了 {len(docs)} 篇文档")
    print(f"   Collection 总数: {collection.count()}")
    
    # ─── 3. 语义查询 (QUERY) ───
    # query() 是最核心的操作，流程：
    # 1. 把 query_texts 转成 Embedding 向量
    # 2. 在 Collection 中找最接近的 n_results 个文档
    # 3. 返回文档内容 + 距离（distance）
    #
    # distance 含义（cosine 空间）：
    # - 0 = 完全相同
    # - < 0.5 = 高度相关
    # - < 1.0 = 有一定相关性
    # - > 1.0 = 不太相关
    print("\n3️⃣ 语义查询 (QUERY)")
    
    queries = [
        "怎么创建键值对？",
        "什么是不可变的序列？",
        "怎么去除重复元素？",
    ]
    
    for query in queries:
        print(f"\n   ❓ {query}")
        results = collection.query(
            query_texts=[query],    # 查询文本（会自动生成 Embedding）
            n_results=2,            # 返回最相似的 2 个文档
        )
        for i, (doc, dist) in enumerate(zip(results["documents"][0], results["distances"][0])):
            print(f"   {i+1}. [距离: {dist:.4f}] {doc[:50]}...")
    
    # ─── 4. 条件查询（过滤 metadata） ───
    # where 参数可以对 metadata 做预过滤
    # 先按条件缩小范围，再做向量检索
    # 支持：$eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
    print("\n4️⃣ 条件过滤查询")
    results = collection.query(
        query_texts=["有序的数据结构"],
        n_results=3,
        where={"topic": {"$in": ["list", "tuple"]}},  # 只在 list 和 tuple 中搜索
    )
    print(f"   过滤 topic in [list, tuple]:")
    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        print(f"   [距离: {dist:.4f}] {doc[:50]}...")
    
    # ─── 5. 更新文档 (UPDATE) ───
    # update() 更新已有文档的内容
    # 注意：必须提供已存在的 id，否则报错
    print("\n5️⃣ 更新文档 (UPDATE)")
    collection.update(
        ids=["doc1"],
        documents=["Python 的列表（list）是一种有序的可变序列。支持增删改查操作。用方括号 [] 创建，如 [1, 2, 3]。"],
    )
    print("   更新了 doc1（内容会更丰富，Embedding 也会重新生成）")
    
    # ─── 6. 删除文档 (DELETE) ───
    # delete() 按 id 删除文档
    print("\n6️⃣ 删除文档 (DELETE)")
    collection.delete(ids=["doc5"])
    print(f"   删除了 doc5")
    print(f"   Collection 总数: {collection.count()}")
    
    # ─── 7. 按 ID 获取 (GET) ───
    # get() 按 id 直接获取文档，不做向量检索
    # 适合：已知文档 id，想获取内容的场景
    print("\n7️⃣ 按 ID 获取 (GET)")
    result = collection.get(ids=["doc1", "doc2"])
    for doc_id, doc in zip(result["ids"], result["documents"]):
        print(f"   [{doc_id}] {doc[:60]}...")


# ============================================================
# Part 4: 关键词匹配 vs 语义检索对比
# ============================================================
#
# 注意：ChromaDB 默认使用 all-MiniLM-L6-v2（英文模型）
# 对中文效果不好，所以下面的对比结果可能不理想
# 在 simple_rag.py 中，我们会切换到 qwen3-embedding:4b（中文模型）
# 效果会好很多

def demo_comparison():
    """
    对比 ChromaDB 默认 Embedding 对中文的效果
    
    ⚠️ 注意：ChromaDB 默认的 all-MiniLM-L6-v2 是英文模型
    对中文的语义理解能力很弱，所以下面的测试结果可能不理想
    这正好说明了"选择正确的 Embedding 模型"的重要性
    
    在 simple_rag.py 中，我们切换到 qwen3-embedding:4b 后
    同样的测试全部正确！
    """
    print("\n" + "=" * 60)
    print("⚔️ Part 4: ChromaDB 默认 Embedding（英文模型）vs 中文")
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
        ("什么是不可变的序列？", "d3"),    # 期望返回元组 doc
        ("怎么去除重复？", "d4"),          # 期望返回集合 doc
        ("键值对怎么用？", "d2"),          # 期望返回字典 doc
    ]
    
    print("\n⚠️ 使用 ChromaDB 默认英文 Embedding 模型：")
    correct = 0
    for query, expected in test_queries:
        results = collection.query(query_texts=[query], n_results=1)
        top_id = results["ids"][0][0]
        top_dist = results["distances"][0][0]
        match = "✅" if top_id == expected else "❌"
        if top_id == expected:
            correct += 1
        print(f"   {match} Q: {query}")
        print(f"      期望: {expected} | 实际: {top_id} (距离: {top_dist:.4f})")
    
    print(f"\n   正确率: {correct}/{len(test_queries)}")
    print()
    print("💡 原因：ChromaDB 默认的 all-MiniLM-L6-v2 是英文模型")
    print("   中文文本的语义信息丢失严重")
    print("   解决方案：在 simple_rag.py 中使用 qwen3-embedding:4b（中文模型）")
    print("   切换后，同样 3 个测试全部正确！")


if __name__ == "__main__":
    demo_embedding_concept()
    demo_real_embedding()
    demo_chromadb()
    demo_comparison()
    
    print("\n" + "=" * 60)
    print("✅ Day 3-4 完成！")
    print()
    print("你学到了：")
    print("  1. Embedding = 把文本变成向量（qwen3-embedding:4b → 2560 维）")
    print("  2. 余弦相似度衡量向量接近程度（0~1，越大越相似）")
    print("  3. ChromaDB 五大操作: add / query / get / update / delete")
    print("  4. ChromaDB 默认英文 Embedding 对中文效果差 → 必须用中文模型")
    print("=" * 60)
