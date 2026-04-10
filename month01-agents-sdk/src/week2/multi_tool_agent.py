#!/usr/bin/env python3
"""
Week 2: 多 Tool 协作示例
包含：query_refund_policy, check_order_status, calculate_shipping
"""

import asyncio
import os
import logging
from agents import Agent, Runner, function_tool
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)

# 禁用 OpenAI Responses API，使用标准的 Chat Completions API
set_use_responses_by_default(False)


# ============ 定义 Tools ============

@function_tool
def query_refund_policy(product_type: str) -> str:
    """
    查询某类商品的退货政策。
    
    Args:
        product_type: 商品类型，如 "electronics", "clothing", "books"
    
    Returns:
        退货政策说明
    """
    policies = {
        "electronics": "电子产品：7 天无理由退货，需保持包装完整，配件齐全。开封后不支持退货（质量问题除外）。",
        "clothing": "服装：30 天无理由退货，需未洗涤、未穿着，吊牌完整。",
        "books": "图书：7 天无理由退货，需无涂写、无破损。",
        "food": "食品：不支持无理由退货（质量问题可退换）。",
        "default": "通用政策：15 天无理由退货，商品需保持完好。"
    }
    return policies.get(product_type.lower(), policies["default"])


@function_tool
def check_order_status(order_id: str) -> str:
    """
    查询订单状态。
    
    Args:
        order_id: 订单号
    
    Returns:
        订单当前状态
    """
    # 模拟订单状态
    statuses = {
        "ORD001": "已发货，预计明天送达",
        "ORD002": "处理中，预计今天发货",
        "ORD003": "已签收",
        "ORD004": "已取消"
    }
    return statuses.get(order_id.upper(), f"订单 {order_id} 未找到")


@function_tool
def calculate_shipping(weight_kg: float, destination: str) -> float:
    """
    计算运费。
    
    Args:
        weight_kg: 包裹重量（公斤）
        destination: 目的地城市
    
    Returns:
        运费（元）
    """
    base_rate = 10.0  # 首重 1kg
    extra_rate = 5.0  # 续重每 kg
    
    # 偏远地区加价
    remote_areas = ["拉萨", "乌鲁木齐", "西宁"]
    multiplier = 1.5 if destination in remote_areas else 1.0
    
    if weight_kg <= 1:
        return base_rate * multiplier
    else:
        return (base_rate + (weight_kg - 1) * extra_rate) * multiplier


# ============ 创建 Agent ============
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 初始化兼容 OpenAI 的百炼客户端
client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://coding.dashscope.aliyuncs.com/v1",
)

customer_service_agent = Agent(
    # 使用 OpenAIChatCompletionsModel 并且传入自定义 client
    model=OpenAIChatCompletionsModel(model="qwen3.5-plus", openai_client=client),
    name="客服助手",
    instructions="""你是一个电商客服助手。你可以帮助用户：
1. 查询退货政策
2. 查询订单状态
3. 计算运费

根据用户问题，自动调用合适的工具。回答要简洁友好。""",
    tools=[
        query_refund_policy,
        check_order_status,
        calculate_shipping
    ]
)


# ============ 测试 ============

async def main():
    print("=" * 60)
    print("Week 2: 多 Tool 协作示例")
    print("=" * 60)
    
    test_cases = [
        "电子产品怎么退货？",
        "帮我查一下订单 ORD001 的状态",
        "从北京寄一个 2.5kg 的包裹到上海，运费多少？",
        "衣服穿了一次不喜欢，能退吗？",
        "订单 ORD999 查不到吗？"
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n【测试 {i}】用户问：{query}")
        print("-" * 40)
        
        # 使用 Runner 执行 Agent
        result = await Runner.run(customer_service_agent, query)
        print(f"客服回答：{result.final_output}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
