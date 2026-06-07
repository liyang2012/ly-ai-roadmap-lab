"""
Day 5-6: 第一个完整的 RAG Pipeline

目标：构建一个完整的 RAG 系统
1. Indexing: 文档 → Embedding → 存入向量数据库
2. Retrieval: 用户查询 → 语义检索相关文档
3. Generation: 检索结果 + 用户问题 → LLM 生成回答

使用:
- ChromaDB (向量数据库)
- Ollama qwen3-embedding:4b (中文 Embedding)
- 阿里云百炼 qwen3.5-plus (LLM 生成)
"""

import os
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# ============================================================
# 配置
# ============================================================

# Ollama Embedding 配置
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"

# 智谱 AI API
from openai import OpenAI


def get_llm_client() -> OpenAI:
    """获取智谱 AI LLM 客户端"""
    api_key = os.environ.get("ZHIPUAI_API_KEY", "")
    if not api_key:
        # 尝试从 .env 文件加载
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
# Step 2: Indexing —— 文档入库
# ============================================================

class SimpleRAG:
    """简单的 RAG Pipeline"""
    
    def __init__(self, persist_dir: str = None):
        # Embedding 函数
        self.embedding_fn = OllamaEmbeddingFunction(
            url=OLLAMA_BASE_URL,
            model_name=EMBEDDING_MODEL,
        )
        
        # ChromaDB Client
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()
        
        self.collection = None
        self.llm = get_llm_client()
    
    def index(self, documents: list[dict]):
        """Indexing: 文档 → Embedding → 存入 ChromaDB"""
        print("📥 Indexing: 文档入库中...")
        
        # 删除旧 collection（如果存在）
        try:
            self.client.delete_collection("knowledge_base")
        except Exception:
            pass
        
        # 创建 collection
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        
        # 添加文档
        self.collection.add(
            documents=[doc["text"] for doc in documents],
            ids=[doc["id"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents],
        )
        
        print(f"   ✅ 已索引 {len(documents)} 篇文档")
        return self
    
    def retrieve(self, query: str, top_k: int = 2) -> list[dict]:
        """Retrieval: 用户查询 → 语义检索"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        
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
        """Generation: 检索结果 + 问题 → LLM 回答"""
        # 拼接 context
        context = "\n\n---\n\n".join([
            f"[来源: {doc['metadata']['source']}]\n{doc['text']}"
            for doc in context_docs
        ])
        
        # 构建 prompt
        prompt = f"""你是一个专业的电商客服。请根据以下参考资料回答用户问题。

要求：
1. 只根据参考资料回答，不要编造信息
2. 如果参考资料中没有答案，明确告诉用户
3. 引用信息来源

参考资料：
{context}

用户问题：{query}

请回答："""
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        
        return response.choices[0].message.content
    
    def query(self, question: str, top_k: int = 2) -> dict:
        """完整的 RAG Pipeline: Query → Retrieve → Generate"""
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
    print("=" * 60)
    print("📚 完整 RAG Pipeline 演示")
    print("=" * 60)
    
    # 初始化
    rag = SimpleRAG()
    
    # Indexing
    rag.index(KNOWLEDGE_DOCS)
    
    # 测试查询
    test_questions = [
        "买了手机用了一个月坏了怎么办？",
        "怎么才能免运费？",
        "退款多久能到账？",
        "钻石会员有什么好处？",
        "我昨天下的单怎么还没收到？",
        "能同时用两张优惠券吗？",
    ]
    
    results = []
    for q in test_questions:
        result = rag.query(q)
        results.append(result)
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    for r in results:
        print(f"\n❓ {r['question']}")
        print(f"   检索到: {', '.join([d['id'] for d in r['retrieved_docs']])}")
        answer_preview = r['answer'][:80].replace('\n', ' ')
        print(f"   回答: {answer_preview}...")


def interactive_mode():
    """交互模式：可以自由提问"""
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
