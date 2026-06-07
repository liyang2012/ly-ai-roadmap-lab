"""
Day 5-6: 第一个完整的 RAG Pipeline

目标：构建一个完整的 RAG 系统
1. Indexing: 文档 → Embedding → 存入向量数据库
2. Retrieval: 用户查询 → 语义检索相关文档
3. Generation: 检索结果 + 用户问题 → LLM 生成回答

使用技术栈：
- ChromaDB (向量数据库，存储文档和向量)
- Ollama qwen3-embedding:4b (中文 Embedding 模型，2560 维)
- 智谱 AI glm-4-flash (LLM 生成回答)

=== 架构图 ===

    ┌──────────────┐
    │  知识库文档   │  ← 企业FAQ、产品手册、技术文档等
    └──────┬───────┘
           │ Indexing（只做一次，或文档更新时做）
           ▼
    ┌──────────────┐
    │  ChromaDB    │  ← 文档被转成 Embedding 向量存入
    │  向量数据库   │
    └──────┬───────┘
           │ Retrieval（每次查询时做）
           ▼
    ┌──────────────┐
    │  检索 Top-K  │  ← 找到和用户问题最相关的 K 篇文档
    │  相关文档     │
    └──────┬───────┘
           │ Augmented（拼接到 prompt）
           ▼
    ┌──────────────┐
    │  LLM 生成    │  ← 基于检索到的文档内容回答问题
    │  最终回答     │
    └──────────────┘

=== 运行方式 ===
    python simple_rag.py              # 自动运行 6 个测试问题
    python simple_rag.py --interactive # 交互模式，自由提问
"""

import os
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# ============================================================
# 配置
# ============================================================

# Ollama Embedding 配置
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"  # 中文 Embedding，输出 2560 维向量

# 智谱 AI API 配置
from openai import OpenAI


def get_llm_client() -> OpenAI:
    """
    获取智谱 AI LLM 客户端
    
    智谱 AI（BigModel）是国内的大模型平台
    使用 OpenAI 兼容 API，所以可以用 openai 库
    
    为什么用 glm-4-flash？
    - 免费
    - 速度快（~500ms）
    - 质量足够用于 RAG 回答生成
    """
    api_key = os.environ.get("ZHIPUAI_API_KEY", "")
    if not api_key:
        # 尝试从 .env 文件加载
        # .env 文件格式：ZHIPUAI_API_KEY="your-key-here"
        env_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".env"
        )
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.strip().startswith("ZHIPUAI_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip().strip('"')
                        os.environ["ZHIPUAI_API_KEY"] = key
                        api_key = key
                        break
    
    return OpenAI(
        api_key=api_key,
        base_url="https://open.bigmodel.cn/api/paas/v4",
    )


LLM_MODEL = "glm-4-flash"  # 智谱免费模型，足够 RAG 演示用


# ============================================================
# Step 1: 知识库（模拟企业内部文档）
# ============================================================
#
# 在真实场景中，这些文档可能来自：
# - 企业内部 Wiki / Confluence
# - 产品手册 / FAQ 文档
# - 技术文档 / API 文档
# - 客服对话记录
#
# 每篇文档有三个属性：
# - id: 唯一标识
# - text: 文档内容（这是检索和回答的基础）
# - metadata: 附加信息（来源、分类等，可用于过滤）

KNOWLEDGE_DOCS = [
    {
        "id": "refund_policy",
        "text": """退款政策：
1. 未发货订单：支持全额退款，1-3个工作日到账
2. 已发货未签收：支持退款，需扣除运费（10-30元）
3. 已签收7天内：支持退货退款，需保持商品完好
4. 已签收超过7天：不支持退货退款
5. 特殊商品（内衣、食品、定制商品）：一经售出不支持退货
6. 退款申请提交后，客服会在24小时内审核""",
        "metadata": {"source": "refund_policy", "category": "policy"},
    },
    {
        "id": "shipping_info",
        "text": """物流配送说明：
1. 默认快递：顺丰速运
2. 发货时效：下单后24小时内发货（节假日顺延）
3. 配送时效：一线城市1-2天，二三线城市2-4天，偏远地区5-7天
4. 运费标准：订单满99元免运费，不满99元收取8元运费
5. 支持指定快递：圆通、中通、韵达（需备注说明）
6. 海外配送：暂不支持""",
        "metadata": {"source": "shipping_info", "category": "logistics"},
    },
    {
        "id": "coupon_rules",
        "text": """优惠券使用规则：
1. 满减券：订单金额需达到满减门槛才能使用
2. 折扣券：直接按比例折扣，最多折扣50%
3. 新人券：首次注册用户专享，有效期30天
4. 生日券：生日当月自动发放，有效期7天
5. 叠加规则：每笔订单只能使用一张优惠券
6. 退款处理：使用优惠券的订单退款后，优惠券不退回""",
        "metadata": {"source": "coupon_rules", "category": "promotion"},
    },
    {
        "id": "product_warranty",
        "text": """商品保修政策：
1. 电子产品：7天无理由退换，15天质量问题换货，1年保修
2. 服装鞋帽：7天无理由退换，30天质量问题换货
3. 家居用品：15天无理由退换，90天质量问题换货
4. 保修凭证：订单号 + 商品照片
5. 非保修范围：人为损坏、超出保修期、无购买凭证
6. 保修流程：联系客服 → 提交凭证 → 审核 → 寄回维修/换新""",
        "metadata": {"source": "product_warranty", "category": "policy"},
    },
    {
        "id": "vip_benefits",
        "text": """会员等级与权益：
1. 普通会员：注册即得，享受基础服务
2. 银卡会员：累计消费满1000元，享95折
3. 金卡会员：累计消费满5000元，享9折 + 优先发货
4. 钻石会员：累计消费满20000元，享85折 + 免运费 + 专属客服
5. 会员等级每半年评估一次，根据消费金额调整
6. 所有会员生日当月享受额外折扣""",
        "metadata": {"source": "vip_benefits", "category": "membership"},
    },
]


# ============================================================
# Step 2: SimpleRAG —— RAG Pipeline 封装
# ============================================================
#
# 整个 Pipeline 分为三步：
# 1. index() —— Indexing 阶段：文档入库（只做一次）
# 2. retrieve() —— Retrieval 阶段：语义检索
# 3. generate() —— Generation 阶段：LLM 回答
#
# query() = retrieve() + generate()，对外暴露的统一接口

class SimpleRAG:
    """
    简单的 RAG Pipeline
    
    使用方法：
        rag = SimpleRAG()
        rag.index(documents)          # Indexing（只做一次）
        result = rag.query("问题")     # 查询
    
    参数：
        persist_dir: ChromaDB 持久化目录
            - None: 内存模式（程序结束数据消失，适合测试）
            - 路径: 持久化到磁盘（适合生产，下次启动不需要重新索引）
    """
    
    def __init__(self, persist_dir: str = None):
        # ─── Embedding 函数 ───
        # 使用 Ollama 本地中文 Embedding 模型
        # 每次调用 query() 或 add() 时，ChromaDB 会自动调用这个函数生成向量
        self.embedding_fn = OllamaEmbeddingFunction(
            url=OLLAMA_BASE_URL,
            model_name=EMBEDDING_MODEL,
        )
        
        # ─── ChromaDB Client ───
        if persist_dir:
            # 持久化模式：数据保存到指定目录
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            # 内存模式：程序结束数据消失
            self.client = chromadb.Client()
        
        self.collection = None
        self.llm = get_llm_client()
    
    def index(self, documents: list[dict]):
        """
        Indexing 阶段：文档 → Embedding → 存入 ChromaDB
        
        这个方法做了什么：
        1. 清除旧的 collection（重新索引）
        2. 创建新的 collection（使用余弦相似度）
        3. 把所有文档添加到 collection
           - ChromaDB 自动调用 embedding_fn 生成向量
           - 存储文档内容 + 向量 + metadata
        
        参数：
            documents: 文档列表，每个元素是 {"id": ..., "text": ..., "metadata": ...}
        """
        print("📥 Indexing: 文档入库中...")
        
        # 删除旧 collection（如果存在）
        # 在生产环境中，应该用 upsert 而不是删除重建
        try:
            self.client.delete_collection("knowledge_base")
        except Exception:
            pass
        
        # 创建 collection
        # metadata={"hnsw:space": "cosine"} 指定使用余弦相似度
        # HNSW = Hierarchical Navigable Small World，一种近似最近邻算法
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        
        # 添加文档
        # ChromaDB 会自动：
        # 1. 调用 embedding_fn 把每篇文档转成 2560 维向量
        # 2. 构建 HNSW 索引（用于快速检索）
        # 3. 存储文档内容、向量、metadata
        self.collection.add(
            documents=[doc["text"] for doc in documents],
            ids=[doc["id"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents],
        )
        
        print(f"   ✅ 已索引 {len(documents)} 篇文档")
        return self
    
    def retrieve(self, query: str, top_k: int = 2) -> list[dict]:
        """
        Retrieval 阶段：用户查询 → 语义检索
        
        这个方法做了什么：
        1. 把用户查询转成 Embedding 向量
        2. 在 ChromaDB 中查找最接近的 top_k 个文档
        3. 返回文档内容 + 距离 + metadata
        
        距离（distance）含义（cosine 空间）：
        - 0.0 ~ 0.3: 非常相关（几乎就是同一内容）
        - 0.3 ~ 0.6: 高度相关（包含想要的信息）
        - 0.6 ~ 1.0: 有一定相关性
        - > 1.0: 不太相关
        
        参数：
            query: 用户问题
            top_k: 返回最相关的 K 个文档（默认 2）
        
        返回：
            [{"id": ..., "text": ..., "distance": ..., "metadata": ...}, ...]
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        
        # 解包结果（ChromaDB 返回的是嵌套列表）
        retrieved = []
        for i in range(len(results["ids"][0])):
            retrieved.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "distance": results["distances"][0][i],
                "metadata": results["metadatas"][0][i],
            })
        
        return retrieved
    
    def generate(self, query: str, context_docs: list[dict]) -> str:
        """
        Generation 阶段：检索结果 + 问题 → LLM 回答
        
        这个方法做了什么：
        1. 把检索到的文档拼接成 context
        2. 构建 prompt（角色 + 要求 + context + 问题）
        3. 调用 LLM 生成回答
        
        Prompt 设计要点：
        - 明确告诉 LLM "只根据参考资料回答"
        - 要求"不要编造信息"（减少幻觉）
        - 要求"引用信息来源"（可追溯）
        - 如果资料中没有答案，要求说"不确定"（避免瞎编）
        
        参数：
            query: 用户问题
            context_docs: 检索到的文档列表
        """
        # ─── 拼接 context ───
        # 每篇文档标注来源，方便 LLM 引用
        context = "\n\n---\n\n".join([
            f"[来源: {doc['metadata']['source']}]\n{doc['text']}"
            for doc in context_docs
        ])
        
        # ─── 构建 prompt ───
        # 结构：角色设定 + 要求 + 参考资料 + 用户问题
        prompt = f"""你是一个专业的电商客服。请根据以下参考资料回答用户问题。

要求：
1. 只根据参考资料回答，不要编造信息
2. 如果参考资料中没有答案，明确告诉用户
3. 引用信息来源

参考资料：
{context}

用户问题：{query}

请回答："""
        
        # ─── 调用 LLM ───
        # temperature=0.3: 较低温度，让回答更确定、更忠于参考资料
        #   0.0 = 完全确定（总是选概率最高的）
        #   1.0 = 很有创造力（随机性大）
        #   RAG 场景建议 0.1~0.3，因为我们要"忠于文档"而不是"发挥创意"
        # max_tokens=500: 限制回答长度，避免太长浪费 token
        response = self.llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        
        return response.choices[0].message.content
    
    def query(self, question: str, top_k: int = 2) -> dict:
        """
        完整的 RAG Pipeline: Query → Retrieve → Generate
        
        这是外部调用的统一接口
        内部按顺序执行：retrieve() → generate()
        
        参数：
            question: 用户问题
            top_k: 检索返回的文档数量
        
        返回：
            {
                "question": 原始问题,
                "retrieved_docs": 检索到的文档列表,
                "answer": LLM 生成的回答,
            }
        """
        print(f"\n{'='*60}")
        print(f"❓ 用户问题: {question}")
        
        # Step 1: 检索
        print(f"🔍 Step 1: 检索 Top-{top_k} 相关文档...")
        docs = self.retrieve(question, top_k)
        for i, doc in enumerate(docs, 1):
            print(f"   {i}. [{doc['id']}] 距离: {doc['distance']:.4f}")
        
        # Step 2: 生成
        print(f"🤖 Step 2: LLM 生成回答...")
        answer = self.generate(question, docs)
        
        # Step 3: 输出
        print(f"💬 回答:\n{answer}")
        
        return {
            "question": question,
            "retrieved_docs": docs,
            "answer": answer,
        }


# ============================================================
# 演示
# ============================================================

def demo():
    """
    自动运行 6 个测试问题，验证 RAG Pipeline 的效果
    
    测试设计覆盖了不同的场景：
    1. 口语化表达："买了手机用了一个月坏了" → 保修政策
    2. 直接提问："怎么才能免运费" → 物流配送
    3. 具体细节："退款多久能到账" → 退款政策
    4. 概念查询："钻石会员有什么好处" → 会员权益
    5. 时间相关："昨天下的单还没收到" → 物流配送
    6. 否定问题："能同时用两张优惠券吗" → 优惠券规则
    """
    print("=" * 60)
    print("📚 完整 RAG Pipeline 演示")
    print("=" * 60)
    
    # 初始化
    rag = SimpleRAG()
    
    # Indexing（只做一次）
    rag.index(KNOWLEDGE_DOCS)
    
    # 测试查询——覆盖不同类型的用户问题
    test_questions = [
        "买了手机用了一个月坏了怎么办？",  # 口语化 → 保修政策
        "怎么才能免运费？",                # 直接提问 → 物流配送
        "退款多久能到账？",                # 具体细节 → 退款政策
        "钻石会员有什么好处？",            # 概念查询 → 会员权益
        "我昨天下的单怎么还没收到？",      # 时间相关 → 物流配送
        "能同时用两张优惠券吗？",          # 否定问题 → 优惠券规则
    ]
    
    results = []
    for q in test_questions:
        result = rag.query(q)
        results.append(result)
    
    # ─── 汇总报告 ───
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    for r in results:
        print(f"\n❓ {r['question']}")
        print(f"   检索到: {', '.join([d['id'] for d in r['retrieved_docs']])}")
        answer_preview = r['answer'][:80].replace('\n', ' ')
        print(f"   回答: {answer_preview}...")


def interactive_mode():
    """
    交互模式：可以自由提问
    
    运行方式：python simple_rag.py --interactive
    
    在这个模式下，你可以：
    - 自由输入问题测试 RAG 的检索和回答效果
    - 观察不同措辞对检索结果的影响
    - 测试 RAG 的边界（问知识库中没有的内容）
    """
    print("=" * 60)
    print("📚 RAG 问答系统 — 交互模式")
    print("输入问题进行提问，输入 'quit' 退出")
    print("=" * 60)
    
    rag = SimpleRAG()
    rag.index(KNOWLEDGE_DOCS)
    
    while True:
        question = input("\n❓ 请输入问题: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not question:
            continue
        
        rag.query(question)


if __name__ == "__main__":
    import sys
    
    if "--interactive" in sys.argv:
        interactive_mode()
    else:
        demo()
