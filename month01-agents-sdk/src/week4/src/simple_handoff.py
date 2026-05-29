"""
Week 4 - Day 24-25: 简单 Handoff 示例

学习目标：
1. 理解 Agent 之间的手动交接模式
2. 掌握 handoff() 函数的基本用法
3. 验证上下文传递的正确性
4. 使用智谱 AI glm-5.1 模型
"""

import os
from agents import Agent, handoff, Runner
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 加载环境变量
load_dotenv()

# 禁用 Responses API，使用 Chat Completions
set_use_responses_by_default(False)

# 初始化智谱 AI 客户端
client = AsyncOpenAI(
    # 智谱 AI API Key，从环境变量读取
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    # 智谱 AI API 地址
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)

# 定义模型名称
MODEL_NAME = "glm-5.1"

# ============================================================
# 模式 1：简单 Handoff - 客服路由
# ============================================================

# 子 Agent：专门处理退款问题
refund_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Refund Specialist",
    instructions="""你是退款专员，专门处理退款相关的问题。
如果用户询问退款政策、退款进度、退款金额等问题，请详细解答。
回复要专业、准确。""",
)

# 子 Agent：专门处理物流问题
logistics_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Logistics Specialist",
    instructions="""你是物流专员，专门处理物流相关的问题。
如果用户查询包裹状态、预计到达时间、物流异常等，请详细解答。""",
)

# 主 Agent：负责意图识别和路由
router_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Router Agent",
    instructions="""你是一个智能客服路由器。
分析用户的问题意图，然后交给合适的专员处理：
- 退款相关 → Refund Specialist
- 物流相关 → Logistics Specialist
如果无法判断，请直接回答用户的问题。""",
    handoffs=[
        handoff(refund_agent),
        handoff(logistics_agent),
    ],
)


async def main():
    """运行 Handoff 测试"""
    print("=" * 70)
    print("🔄 Week 4 - Day 24-25: 简单 Handoff 示例")
    print("=" * 70)
    print(f"📦 使用模型: {MODEL_NAME}")
    print("=" * 70)
    
    # 测试 1：退款问题（应该路由到 Refund Specialist）
    print("\n" + "=" * 70)
    print("测试 1：退款问题 → 预期路由到 Refund Specialist")
    print("=" * 70)
    result = await Runner.run(router_agent, "我想申请退款，怎么办？")
    print(f"🤖 最终回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次模型调用")
    for i, response in enumerate(result.raw_responses, 1):
        print(f"   调用 {i}: {response.usage.total_tokens} tokens")
    print()

    # 测试 2：物流问题（应该路由到 Logistics Specialist）
    print("=" * 70)
    print("测试 2：物流问题 → 预期路由到 Logistics Specialist")
    print("=" * 70)
    result = await Runner.run(router_agent, "我的包裹到哪里了？物流单号 SF1234567890")
    print(f"🤖 最终回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次模型调用")
    for i, response in enumerate(result.raw_responses, 1):
        print(f"   调用 {i}: {response.usage.total_tokens} tokens")
    print()

    # 测试 3：通用问题（应该由 Router Agent 直接回答）
    print("=" * 70)
    print("测试 3：通用问题 → 预期由 Router Agent 直接回答")
    print("=" * 70)
    result = await Runner.run(router_agent, "你们的产品有哪些特点？")
    print(f"🤖 最终回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次模型调用")
    for i, response in enumerate(result.raw_responses, 1):
        print(f"   调用 {i}: {response.usage.total_tokens} tokens")
    print()
    
    # 测试 4：复杂的退款问题（测试上下文传递）
    print("=" * 70)
    print("测试 4：复杂退款问题 → 测试 Handoff 后上下文是否正确传递")
    print("=" * 70)
    result = await Runner.run(
        router_agent, 
        "我昨天买了一个 iPhone 15 Pro，订单号 ORD20260417001，"
        "但是现在不想要了，能退款吗？退款流程是什么？"
    )
    print(f"🤖 最终回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次模型调用")
    total_tokens = sum(r.usage.total_tokens for r in result.raw_responses)
    print(f"   总计: {total_tokens} tokens")
    
    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
