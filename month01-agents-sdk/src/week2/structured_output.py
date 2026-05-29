#!/usr/bin/env python3
"""
Week 2: 结构化输出（Structured Output）

学习目标：
1. 理解为什么需要结构化输出（vs 自由文本）
2. 使用 Pydantic 模型定义输出格式
3. 让 Agent 返回可解析的 JSON 数据
4. 应用场景：API 数据交换、数据库存储、多 Agent 协作

核心概念：
- 自由文本：适合人类阅读，但难以程序化处理
- 结构化输出：固定格式（JSON/对象），适合机器解析和下游使用
"""

import asyncio
import json
import os
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field
from agents import Agent, Runner, function_tool
from agents.model_settings import ModelSettings
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化百炼客户端
client = AsyncOpenAI(
    # 智谱 AI API Key，从环境变量读取
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    # 智谱 AI API 地址
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)


# ============================================================
# 场景 1：订单查询 - 返回结构化订单对象
# ============================================================

class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    SHIPPED = "shipped"  # 已发货
    DELIVERED = "delivered"  # 已签收
    CANCELLED = "cancelled"  # 已取消


class Order(BaseModel):
    """订单数据结构"""
    order_id: str = Field(description="订单号，例如：ORD20260417001")
    product_name: str = Field(description="商品名称，例如：iPhone 15 Pro")
    amount: float = Field(description="订单金额（元），例如：7999.00")
    status: OrderStatus = Field(description="订单状态，必须是以下之一：pending, processing, shipped, delivered, cancelled")
    order_date: str = Field(description="下单日期（YYYY-MM-DD），例如：2026-04-15")
    logistics_no: Optional[str] = Field(default=None, description="物流单号，例如：SF1234567890")
    estimated_delivery: Optional[str] = Field(default=None, description="预计送达日期（YYYY-MM-DD），例如：2026-04-19")


# 模拟订单数据库
ORDERS_DB = {
    "ORD20260417001": {
        "product_name": "iPhone 15 Pro",
        "amount": 7999.00,
        "status": "shipped",
        "order_date": "2026-04-15",
        "logistics_no": "SF1234567890",
        "estimated_delivery": "2026-04-19"
    },
    "ORD20260417002": {
        "product_name": "AirPods Pro 2",
        "amount": 1899.00,
        "status": "processing",
        "order_date": "2026-04-17",
        "logistics_no": None,
        "estimated_delivery": "2026-04-20"
    },
    "ORD20260417003": {
        "product_name": "MacBook Air M2",
        "amount": 9499.00,
        "status": "delivered",
        "order_date": "2026-04-10",
        "logistics_no": "JD9876543210",
        "estimated_delivery": "2026-04-12"
    },
}


@function_tool
def get_order(order_id: str) -> Optional[Order]:
    """
    查询订单（返回结构化 Order 对象）
    
    Args:
        order_id: 订单号
    
    Returns:
        Order 对象或 None（如果订单不存在）
    """
    data = ORDERS_DB.get(order_id)
    if not data:
        return None
    
    return Order(
        order_id=order_id,
        **data
    )


def create_order_query_agent():
    """创建订单查询 Agent（返回结构化数据）"""
    
    instructions = """
你是一个订单查询助手。当用户查询订单时：
1. 调用 get_order 工具获取订单信息
2. 根据工具返回的结果，将其转换为 JSON 格式输出
3. 如果订单不存在，返回 {"error": "订单不存在", "order_id": "xxx"}

【重要】你的最终输出必须是纯 JSON 格式，不要包含任何其他文本、解释或 markdown 代码块标记。

输出的 JSON 必须符合以下结构：
{
  "order_id": "订单号",
  "product_name": "商品名称",
  "amount": 订单金额（数字）,
  "status": "订单状态（pending/processing/shipped/delivered/cancelled）",
  "order_date": "下单日期（YYYY-MM-DD）",
  "logistics_no": "物流单号（可选）",
  "estimated_delivery": "预计送达日期（可选）"
}
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="订单查询助手",
        instructions=instructions,
        tools=[get_order]
    )
    
    return agent


# ============================================================
# 场景 2：多订单查询 - 返回订单列表
# ============================================================

class OrderSummary(BaseModel):
    """订单摘要（简化版）"""
    order_id: str
    product_name: str
    amount: float
    status: OrderStatus


class OrderListResponse(BaseModel):
    """订单列表响应"""
    orders: List[OrderSummary] = Field(description="订单列表")
    total_count: int = Field(description="订单总数")
    total_amount: float = Field(description="订单总金额")


@function_tool
def get_all_orders() -> OrderListResponse:
    """
    获取所有订单（返回列表结构）
    
    Returns:
        OrderListResponse 对象
    """
    orders = []
    total_amount = 0.0
    
    for order_id, data in ORDERS_DB.items():
        orders.append(OrderSummary(
            order_id=order_id,
            product_name=data["product_name"],
            amount=data["amount"],
            status=OrderStatus(data["status"])
        ))
        total_amount += data["amount"]
    
    return OrderListResponse(
        orders=orders,
        total_count=len(orders),
        total_amount=total_amount
    )


def create_order_list_agent():
    """创建订单列表 Agent"""
    
    instructions = """
你是一个订单列表助手。当用户请求查看所有订单时：
1. 调用 get_all_orders 工具
2. 根据工具返回的结果，将其转换为 JSON 格式输出

【重要】你的最终输出必须是纯 JSON 格式，不要包含任何其他文本、解释或 markdown 代码块标记。

输出的 JSON 必须符合以下结构：
{
  "orders": [
    {
      "order_id": "订单号",
      "product_name": "商品名称",
      "amount": 订单金额（数字）,
      "status": "订单状态"
    }
  ],
  "total_count": 订单总数（数字）,
  "total_amount": 订单总金额（数字）
}
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="订单列表助手",
        instructions=instructions,
        tools=[get_all_orders]
    )
    
    return agent


# ============================================================
# 场景 3：数据分析 - 返回统计报告
# ============================================================

class SalesStatistics(BaseModel):
    """销售统计报告"""
    total_orders: int = Field(description="总订单数")
    total_revenue: float = Field(description="总销售额（元）")
    average_order_value: float = Field(description="平均订单金额（元）")
    status_breakdown: dict = Field(description="各状态订单数量统计")
    top_product: str = Field(description="最畅销商品")


@function_tool
def generate_sales_report() -> SalesStatistics:
    """
    生成销售统计报告
    
    Returns:
        SalesStatistics 对象
    """
    total_orders = len(ORDERS_DB)
    total_revenue = sum(data["amount"] for data in ORDERS_DB.values())
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
    
    # 状态统计
    status_breakdown = {}
    for data in ORDERS_DB.values():
        status = data["status"]
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    # 找出最畅销商品（简单按金额）
    top_product = max(ORDERS_DB.items(), key=lambda x: x[1]["amount"])[1]["product_name"]
    
    return SalesStatistics(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=round(average_order_value, 2),
        status_breakdown=status_breakdown,
        top_product=top_product
    )


def create_analytics_agent():
    """创建数据分析 Agent"""
    
    instructions = """
你是一个数据分析助手。当用户请求销售统计或分析报告时：
1. 调用 generate_sales_report 工具
2. 根据工具返回的结果，将其转换为 JSON 格式输出

【重要】你的最终输出必须是纯 JSON 格式，不要包含任何其他文本、解释或 markdown 代码块标记。

输出的 JSON 必须符合以下结构：
{
  "total_orders": 总订单数（数字）,
  "total_revenue": 总销售额（数字）,
  "average_order_value": 平均订单金额（数字）,
  "status_breakdown": {"状态": 数量},
  "top_product": "最畅销商品名称"
}
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="数据分析助手",
        instructions=instructions,
        tools=[generate_sales_report]
    )
    
    return agent


# ============================================================
# 测试与演示
# ============================================================

async def test_structured_output():
    """测试结构化输出"""
    
    print("=" * 70)
    print("📊 结构化输出测试")
    print("=" * 70)
    
    # 测试 1：单个订单查询
    print("\n【测试 1】单个订单查询")
    print("-" * 70)
    agent1 = create_order_query_agent()
    result1 = await Runner.run(agent1, "查询订单 ORD20260417001")
    print(f"👤 用户：查询订单 ORD20260417001")
    
    # 提取并解析 JSON
    output_text = result1.final_output
    print(f"🤖 Agent 输出:\n{output_text}")
    
    try:
        # 尝试从输出中提取 JSON（可能包含 markdown 代码块）
        json_str = output_text
        if "```json" in output_text:
            json_str = output_text.split("```json")[1].split("```")[0].strip()
        elif "```" in output_text:
            json_str = output_text.split("```")[1].split("```")[0].strip()
        
        order_json = json.loads(json_str)
        print(f"\n✅ 成功解析为 JSON:")
        print(f"   订单号：{order_json.get('order_id')}")
        print(f"   商品：{order_json.get('product_name')}")
        print(f"   金额：¥{order_json.get('amount'):,.2f}")
        print(f"   状态：{order_json.get('status')}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
    except Exception as e:
        print(f"\n❌ 解析错误: {e}")
    
    # 测试 2：订单列表
    print("\n【测试 2】订单列表查询")
    print("-" * 70)
    agent2 = create_order_list_agent()
    result2 = await Runner.run(agent2, "显示所有订单")
    print(f"👤 用户：显示所有订单")
    
    output_text = result2.final_output
    print(f"🤖 Agent 输出:\n{output_text}")
    
    try:
        json_str = output_text
        if "```json" in output_text:
            json_str = output_text.split("```json")[1].split("```")[0].strip()
        elif "```" in output_text:
            json_str = output_text.split("```")[1].split("```")[0].strip()
        
        order_list = json.loads(json_str)
        print(f"\n✅ 成功解析为 JSON:")
        print(f"   订单总数：{order_list.get('total_count')}")
        print(f"   总金额：¥{order_list.get('total_amount'):,.2f}")
        print(f"   订单列表：{len(order_list.get('orders', []))} 个")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
    except Exception as e:
        print(f"\n❌ 解析错误: {e}")
    
    # 测试 3：销售统计
    print("\n【测试 3】销售统计报告")
    print("-" * 70)
    agent3 = create_analytics_agent()
    result3 = await Runner.run(agent3, "生成销售统计报告")
    print(f"👤 用户：生成销售统计报告")
    
    output_text = result3.final_output
    print(f"🤖 Agent 输出:\n{output_text}")
    
    try:
        json_str = output_text
        if "```json" in output_text:
            json_str = output_text.split("```json")[1].split("```")[0].strip()
        elif "```" in output_text:
            json_str = output_text.split("```")[1].split("```")[0].strip()
        
        stats = json.loads(json_str)
        print(f"\n✅ 成功解析为 JSON:")
        print(f"   总订单数：{stats.get('total_orders')}")
        print(f"   总销售额：¥{stats.get('total_revenue'):,.2f}")
        print(f"   平均订单：¥{stats.get('average_order_value'):,.2f}")
        print(f"   最畅销商品：{stats.get('top_product')}")
        print(f"   状态分布：{stats.get('status_breakdown')}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
    except Exception as e:
        print(f"\n❌ 解析错误: {e}")
    
    print("\n" + "=" * 70)


async def interactive_mode():
    """交互模式"""
    print("=" * 70)
    print("📊 结构化输出演示系统")
    print("💡 输入 'test' 运行测试集，输入 'quit' 退出")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\n👤 您：").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if user_input.lower() == 'test':
                await test_structured_output()
                continue
            
            if not user_input:
                continue
            
            # 根据关键词选择 Agent
            if "订单" in user_input and ("所有" in user_input or "列表" in user_input):
                agent = create_order_list_agent()
            elif "统计" in user_input or "报告" in user_input:
                agent = create_analytics_agent()
            else:
                agent = create_order_query_agent()
            
            result = await Runner.run(agent, user_input)
            
            # 提取并解析 JSON
            output_text = result.final_output
            print(f"\n🤖 Agent:\n{output_text}")
            
            try:
                json_str = output_text
                if "```json" in output_text:
                    json_str = output_text.split("```json")[1].split("```")[0].strip()
                elif "```" in output_text:
                    json_str = output_text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_str)
                print(f"\n✅ 结构化数据解析成功:")
                print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                pass
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误：{e}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_structured_output())
    else:
        asyncio.run(interactive_mode())


# ============================================================
# 学习总结
# ============================================================

"""
📚 关键知识点

1. 为什么需要结构化输出？
   - ✅ 可解析：下游程序可以直接使用
   - ✅ 类型安全：Pydantic 提供类型检查
   - ✅ 文档化：模型定义即文档
   - ✅ 验证：自动验证数据格式

2. 自由文本 vs 结构化输出
   自由文本：
   "订单 ORD20260417001 已发货，商品是 iPhone 15 Pro，金额 7999 元"
   
   结构化输出：
   {
     "order_id": "ORD20260417001",
     "product_name": "iPhone 15 Pro",
     "amount": 7999.00,
     "status": "shipped"
   }

3. Pydantic 模型的优势
   - 类型注解：IDE 自动补全
   - 默认值：Field(default=...)
   - 验证：自动检查数据类型和格式
   - 序列化：.model_dump() 或 .json()

4. 实际应用场景
   - API 响应格式标准化
   - 数据库存储前的数据验证
   - 多 Agent 协作（下游 Agent 需要结构化输入）
   - 前端数据渲染

5. 下一步学习
   - Week 3: Guardrails（输入/输出验证）
   - Week 4: Handoffs（多 Agent 协作）
   - 第 4 月：Multi-Agent 协作模式
"""
