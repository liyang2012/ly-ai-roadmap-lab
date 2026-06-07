"""
Day 1-2: RAG 基础概念演示

目标：理解 RAG 的完整流程，用硬编码的方式体验"检索增强生成"
不需要向量数据库，纯粹理解概念

=== 学习路线 ===
Part 1: 为什么需要 RAG？—— 知识库 + 关键词检索
Part 2: RAG 的"增强"阶段 —— 把检索结果拼到 prompt 里
Part 3: 有 RAG vs 无 RAG 的对比
Part 4: RAG 的关键参数（top_k 的作用）

=== 核心概念 ===
RAG = Retrieval-Augmented Generation（检索增强生成）
拆解：
  Retrieval   = 检索：从知识库中找到和问题相关的文档
  Augmented   = 增强：把检索到的文档拼到 prompt 里，给 LLM 当参考资料
  Generation  = 生成：LLM 基于参考资料生成回答

类比：
  没有 RAG = 开卷考试但不准带资料（只能凭记忆）
  有了 RAG = 开卷考试且带了参考书（先翻书找答案，再组织语言）
"""

# ============================================================
# Part 1: 为什么需要 RAG？
# ============================================================
#
# LLM 的三大痛点：
# 1. 知识截止：训练数据有截止日期，不知道最新信息
# 2. 幻觉：对于不知道的问题，可能会"一本正经地胡说"
# 3. 私有数据：企业内部文档、个人笔记，LLM 训练数据里根本没有
#
# RAG 的解决思路：
# → 不让 LLM 凭记忆回答，而是给它参考资料，让它"阅读理解"

# 假设我们有一个"知识库"——关于 Python 基础的小文档集
# 在真实场景中，这些可能是：
# - 企业内部文档（产品手册、FAQ、政策）
# - 技术文档（API 文档、架构设计）
# - 个人笔记（Obsidian、Notion）
KNOWLEDGE_BASE = {
    "doc1": "Python 的列表（list）是一种有序的可变序列。可以用方括号 [] 创建，如 [1, 2, 3]。",
    "doc2": "Python 的字典（dict）是键值对的集合。用花括号 {} 创建，如 {'name': 'Alice', 'age': 30}。",
    "doc3": "Python 的元组（tuple）是不可变序列。用圆括号 () 创建，如 (1, 2, 3)。一旦创建不能修改。",
    "doc4": "Python 的集合（set）是无序且不重复的元素集合。用 set() 或 {} 创建，自动去重。",
    "doc5": "Python 的字符串可以用单引号或双引号。三引号 ''' 或 \"\"\" 可以跨行。字符串是不可变的。",
}


def naive_retrieve(query: str, docs: dict, top_k: int = 2) -> list:
    """
    最简单的"检索"——关键词匹配（也叫 Bag of Words）
    
    这是 Naive RAG 的检索阶段。
    真正的 RAG 会用向量检索（后面 Day 3-4 会学）。
    
    原理：
    1. 把 query 和每篇文档都拆成词的集合
    2. 计算两个集合的交集大小（有多少个相同的词）
    3. 交集越大 → 越相关
    4. 按相关度排序，返回 top_k 个
    
    局限性：
    - "什么是不可变的序列？" 里没有"元组"这个词 → 匹配失败
    - "怎么去除重复？" 里没有"集合"这个词 → 匹配失败
    - 只能匹配字面相同的词，不理解同义词和语义
    
    参数：
        query: 用户问题
        docs: 知识库 {doc_id: 文档内容}
        top_k: 返回最相关的 K 个结果
    """
    results = []
    query_words = set(query.lower().split())
    
    for doc_id, content in docs.items():
        content_words = set(content.lower().split())
        # 简单的关键词重叠度 = 两个词集的交集大小
        overlap = len(query_words & content_words)
        results.append((doc_id, content, overlap))
    
    # 按重叠度降序排序，取 top_k
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]


def augment_prompt(query: str, retrieved_docs: list) -> str:
    """
    RAG 的"增强"（Augmented）阶段——把检索到的文档拼到 prompt 里
    
    这是 RAG 最核心的一步：
    不是让 LLM 凭记忆回答，而是给它参考资料
    
    Prompt 结构：
    ┌─────────────────────────────────┐
    │ 系统指令（角色 + 要求）          │
    │                                 │
    │ 参考资料：                      │
    │   [doc1]: 文档内容...           │
    │   [doc2]: 文档内容...           │
    │                                 │
    │ 用户问题：xxx                   │
    │ 请回答：                        │
    └─────────────────────────────────┘
    
    这个技巧叫 "In-Context Learning"：
    不修改模型参数，只是通过 prompt 注入上下文
    
    参数：
        query: 用户问题
        retrieved_docs: 检索到的文档列表 [(doc_id, content, score), ...]
    """
    # 拼接检索到的文档作为 context
    context = "\n\n".join([f"[{doc_id}]: {content}" for doc_id, content, _ in retrieved_docs])
    
    # 构建 augmented prompt
    prompt = f"""请根据以下参考资料回答用户问题。如果参考资料中没有答案，请说"我不确定"。

参考资料：
{context}

用户问题：{query}

请回答："""
    return prompt


# ============================================================
# Part 2: 对比演示——有 RAG vs 无 RAG
# ============================================================
#
# 无 RAG：
#   用户问题 → LLM → 回答（凭训练数据记忆）
#   
# 有 RAG：
#   用户问题 → 检索相关文档 → 拼 prompt → LLM → 回答（基于参考资料）
#
# 核心区别：LLM 从"凭记忆答题"变成"开卷答题"

def demo():
    """演示 RAG 的完整流程"""
    print("=" * 60)
    print("📚 RAG 基础概念演示")
    print("=" * 60)
    
    # 场景：用户问一个 LLM 训练数据里可能没有的问题
    query = "Python 怎么创建字典？"
    
    print(f"\n❓ 用户问题: {query}")
    
    # Step 1: 检索（Retrieval）
    # 从知识库中找到和问题相关的文档
    print("\n🔍 Step 1: 检索相关文档...")
    retrieved = naive_retrieve(query, KNOWLEDGE_BASE, top_k=2)
    for doc_id, content, score in retrieved:
        print(f"   [{doc_id}] (相关度: {score}) → {content[:50]}...")
    
    # Step 2: 增强（Augmented）
    # 把检索到的文档拼到 prompt 里
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
#
# top_k 决定了检索返回多少篇文档
# - top_k 太小（如 1）：可能漏掉相关文档
# - top_k 太大（如 10）：会引入不相关文档，浪费 context window
# - 经验值：2-5 篇
#
# Context Window 限制：
# - LLM 一次能"看到"的最大 token 数
# - GPT-4: 128K tokens, glm-4-flash: 128K tokens
# - 所以不能把所有文档都塞进去，必须先检索筛选

def demo_parameters():
    """演示 top_k 参数和关键词匹配的局限性"""
    print("\n" + "=" * 60)
    print("⚙️ RAG 的关键参数 + 关键词匹配的局限性")
    print("=" * 60)
    
    queries = [
        "Python 怎么创建字典？",        # 关键词匹配效果好
        "什么是不可变的序列？",          # ⚠️ 关键词匹配失效！
        "Python 有哪些数据类型？",      # 关键词匹配一般
    ]
    
    for query in queries:
        print(f"\n❓ {query}")
        retrieved = naive_retrieve(query, KNOWLEDGE_BASE, top_k=3)
        
        print(f"   Top-3 检索结果:")
        for i, (doc_id, content, score) in enumerate(retrieved, 1):
            print(f"   {i}. [{doc_id}] 相关度={score} → {content[:40]}...")
    
    # 重点分析第二个查询
    print("\n" + "-" * 60)
    print("⚠️ 关键词匹配的致命缺陷：")
    print("   '什么是不可变的序列？' → 所有文档相关度相同（都是 0）")
    print("   因为 query 里没有'元组'、'tuple'、'字符串'这些文档中的关键词")
    print("   虽然答案应该是 doc3（元组）和 doc5（字符串）")
    print()
    print("   这就是为什么需要 Embedding 语义检索（Day 3-4 会学）！")


if __name__ == "__main__":
    demo()
    demo_parameters()
    
    print("\n" + "=" * 60)
    print("✅ Day 1 完成！")
    print()
    print("你学到了：")
    print("  1. RAG = Retrieval + Augmented + Generation")
    print("  2. 关键词匹配有局限性（不理解同义词和语义）")
    print("  3. top_k 控制检索数量，影响 Context Window 使用")
    print()
    print("下一步：Day 3-4 学习 Embedding，把'关键词匹配'升级为'语义检索'")
    print("=" * 60)
