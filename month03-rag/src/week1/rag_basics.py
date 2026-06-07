"""
Day 1-2: RAG 基础概念演示

目标：理解 RAG 的完整流程，用硬编码的方式体验"检索增强生成"
不需要向量数据库，纯粹理解概念
"""

# ============================================================
# Part 1: 为什么需要 RAG？
# ============================================================

# 假设我们有一个"知识库"——关于 Python 基础的小文档集
KNOWLEDGE_BASE = {
    "doc1": "Python 的列表（list）是一种有序的可变序列。可以用方括号 [] 创建，如 [1, 2, 3]。",
    "doc2": "Python 的字典（dict）是键值对的集合。用花括号 {} 创建，如 {'name': 'Alice', 'age': 30}。",
    "doc3": "Python 的元组（tuple）是不可变序列。用圆括号 () 创建，如 (1, 2, 3)。一旦创建不能修改。",
    "doc4": "Python 的集合（set）是无序且不重复的元素集合。用 set() 或 {} 创建，自动去重。",
    "doc5": "Python 的字符串可以用单引号或双引号。三引号 ''' 或 \"\"\" 可以跨行。字符串是不可变的。",
}


def naive_retrieve(query: str, docs: dict, top_k: int = 2) -> list:
    """
    最简单的"检索"——关键词匹配
    这就是 Naive RAG 的检索阶段
    
    真正的 RAG 会用向量检索（后面会学）
    """
    results = []
    query_words = set(query.lower().split())
    
    for doc_id, content in docs.items():
        content_words = set(content.lower().split())
        # 简单的关键词重叠度
        overlap = len(query_words & content_words)
        results.append((doc_id, content, overlap))
    
    # 按重叠度排序，取 top_k
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]


def augment_prompt(query: str, retrieved_docs: list) -> str:
    """
    RAG 的"增强"阶段——把检索到的文档拼到 prompt 里
    
    这就是 RAG 的核心思想：
    不是让 LLM 凭记忆回答，而是给它参考资料
    """
    context = "\n\n".join([f"[{doc_id}]: {content}" for doc_id, content, _ in retrieved_docs])
    
    prompt = f"""请根据以下参考资料回答用户问题。如果参考资料中没有答案，请说"我不确定"。

参考资料：
{context}

用户问题：{query}

请回答："""
    return prompt


# ============================================================
# Part 2: 对比演示——有 RAG vs 无 RAG
# ============================================================

def demo():
    print("=" * 60)
    print("📚 RAG 基础概念演示")
    print("=" * 60)
    
    # 场景：用户问一个 LLM 训练数据里可能没有的问题
    query = "Python 怎么创建字典？"
    
    print(f"\n❓ 用户问题: {query}")
    
    # Step 1: 检索
    print("\n🔍 Step 1: 检索相关文档...")
    retrieved = naive_retrieve(query, KNOWLEDGE_BASE, top_k=2)
    for doc_id, content, score in retrieved:
        print(f"   [{doc_id}] (相关度: {score}) → {content[:50]}...")
    
    # Step 2: 增强
    print("\n📝 Step 2: 构建 Augmented Prompt...")
    augmented = augment_prompt(query, retrieved)
    print(f"   Prompt 长度: {len(augmented)} 字符")
    print(f"   Preview: {augmented[:100]}...")
    
    # Step 3: 对比
    print("\n" + "=" * 60)
    print("📊 对比：有 RAG vs 无 RAG")
    print("=" * 60)
    
    print("\n🔸 无 RAG 的 prompt:")
    print(f"   '{query}'")
    print("   → LLM 只能靠训练数据回答，可能过时或不准确")
    
    print("\n🔹 有 RAG 的 prompt:")
    print(f"   参考资料长度: {len(augmented)} 字符")
    print(f"   引用了 {len(retrieved)} 篇文档")
    print("   → LLM 基于真实文档回答，准确且有据可查")
    
    # 关键洞察
    print("\n" + "=" * 60)
    print("💡 RAG 的三大价值")
    print("=" * 60)
    print("1. 🎯 准确性：基于真实文档，减少幻觉")
    print("2. 🔄 时效性：可以随时更新知识库，不需要重新训练")
    print("3. 🔒 私有性：企业内部数据不进训练集，安全合规")


# ============================================================
# Part 3: RAG 的关键参数
# ============================================================

def demo_parameters():
    print("\n" + "=" * 60)
    print("⚙️ RAG 的关键参数")
    print("=" * 60)
    
    queries = [
        "Python 怎么创建字典？",
        "什么是不可变的序列？",
        "Python 有哪些数据类型？",
    ]
    
    for query in queries:
        print(f"\n❓ {query}")
        retrieved = naive_retrieve(query, KNOWLEDGE_BASE, top_k=3)
        
        print(f"   Top-3 检索结果:")
        for i, (doc_id, content, score) in enumerate(retrieved, 1):
            print(f"   {i}. [{doc_id}] 相关度={score} → {content[:40]}...")


if __name__ == "__main__":
    demo()
    demo_parameters()
    
    print("\n" + "=" * 60)
    print("✅ Day 1 完成！")
    print("下一步：学习 Embedding，把'关键词匹配'升级为'语义检索'")
    print("=" * 60)
