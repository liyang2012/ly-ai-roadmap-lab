#!/usr/bin/env python3
"""
Week 2: Tracing 调试（Day 14，1.5 小时）

Week 2 学习目标：
1. 多 Tool 协作与优先级
2. Instructions 对 Tool 选择的影响
3. 结构化输出
4. Tracing 调试 ⬅️ 本节内容

本节目标：
1. 理解 Tracing 的作用和原理
2. 启用和配置 Tracing
3. 使用 Tracing 调试 Agent 工作流
4. 分析 Trace 数据优化性能

核心概念：
- Trace：完整的工作流（如"订单查询"）
- Span：工作流中的单个操作（如"调用 LLM"、"执行 Tool"）
- Trace Tree：Span 的层级关系（父子结构）
"""

import asyncio
import json
import os
import time
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field
from agents import Agent, Runner, function_tool, trace
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
# Tracing 核心概念
# ============================================================

"""
📊 Tracing 是什么？

Tracing = 追踪 + 记录 Agent 执行过程中的每一步操作

类比：
- 飞机黑匣子 → 记录飞行过程中的所有操作
- 代码调试器 → 记录每一行代码的执行
- 监控摄像头 → 记录整个工作流程

┌─────────────────────────────────────────────────────────┐
│  Trace: "订单查询工作流"                                 │
│  └── Span 1: 用户输入 "查询订单 ORD123"                 │
│  └── Span 2: Agent 思考（LLM 调用）                     │
│      └── 输入：用户问题 + instructions                  │
│      └── 输出：决定调用 get_order tool                  │
│  └── Span 3: 执行 Tool (get_order)                      │
│      └── 输入：order_id="ORD123"                        │
│      └── 输出：订单数据                                 │
│  └── Span 4: Agent 生成回复（LLM 调用）                 │
│      └── 输入：Tool 结果 + 上下文                       │
│      └── 输出：最终回复                                 │
│  └── Span 5: 输出给用户                                 │
└─────────────────────────────────────────────────────────┘

为什么需要 Tracing？
1. 🔍 调试：查看 Agent 为什么做出某个决策
2. 🐛 排错：定位 Tool 调用失败的原因
3. ⚡ 优化：找出性能瓶颈（哪个步骤最慢）
4. 📈 监控：生产环境中的 Agent 行为分析
5. 💰 成本：统计每次调用的 Token 消耗
"""


# ============================================================
# 场景 1：基础 Tracing - 订单查询
# ============================================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(BaseModel):
    order_id: str
    product_name: str
    amount: float
    status: OrderStatus
    order_date: str
    logistics_no: Optional[str] = None
    estimated_delivery: Optional[str] = None


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
}


@function_tool
def get_order(order_id: str) -> Optional[Order]:
    """查询订单（带延迟模拟）"""
    # 模拟数据库查询延迟
    time.sleep(0.5)
    
    data = ORDERS_DB.get(order_id)
    if not data:
        return None
    
    return Order(order_id=order_id, **data)


def create_order_agent_with_tracing():
    """创建带 Tracing 的订单查询 Agent"""
    
    instructions = """
你是一个订单查询助手。当用户查询订单时：
1. 调用 get_order 工具获取订单信息
2. 如果订单存在，返回 JSON 格式的订单详情
3. 如果订单不存在，返回 {"error": "订单不存在"}

【重要】始终返回纯 JSON 格式。
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="订单查询助手",
        instructions=instructions,
        tools=[get_order]
    )
    
    return agent


async def test_basic_tracing():
    """测试基础 Tracing"""
    
    print("=" * 70)
    print("📊 测试 1：基础 Tracing - 订单查询")
    print("=" * 70)
    
    agent = create_order_agent_with_tracing()
    
    # 使用 trace 上下文管理器包裹整个工作流
    with trace("订单查询工作流", group_id="test_001") as t:
        print(f"\n✅ Trace 已启动: {t.trace_id}")
        print(f"   Group ID: test_001")
        
        # 运行 Agent
        result = await Runner.run(agent, "查询订单 ORD20260417001")
        
        print(f"\n🤖 Agent 回复:\n{result.final_output}")
        
        # 尝试解析 JSON
        try:
            order_data = json.loads(result.final_output)
            print(f"\n✅ 结构化数据:")
            print(f"   订单号：{order_data.get('order_id')}")
            print(f"   商品：{order_data.get('product_name')}")
            print(f"   金额：¥{order_data.get('amount'):,.2f}")
        except:
            pass
    
    print(f"\n✅ Trace 完成")


# ============================================================
# 场景 2：多步骤工作流 - 订单 + 物流查询
# ============================================================

@function_tool
def query_logistics(logistics_no: str) -> str:
    """查询物流轨迹（带延迟模拟）"""
    # 模拟 API 调用延迟
    time.sleep(0.8)
    
    logistics_info = {
        "SF1234567890": [
            ("2026-04-18 14:30", "【北京市】已签收"),
            ("2026-04-18 09:15", "【北京市】派送中"),
            ("2026-04-17 20:30", "【廊坊市】已发出"),
        ],
    }
    
    tracks = logistics_info.get(logistics_no)
    if not tracks:
        return f"❌ 未找到物流单号 {logistics_no}"
    
    result = f"🚚 物流轨迹 - {logistics_no}\n"
    for time_str, desc in tracks:
        result += f"  {time_str} {desc}\n"
    
    return result


def create_full_workflow_agent():
    """创建完整工作流 Agent（订单 + 物流）"""
    
    instructions = """
你是一个全能客服助手，可以查询订单和物流信息。

【工作流程】
1. 用户查询订单 → 调用 get_order
2. 如果订单已发货且有物流单号 → 自动调用 query_logistics
3. 整合订单和物流信息，返回 JSON 格式

【返回格式】
{
  "order": { ...订单信息... },
  "logistics": { ...物流信息... }  # 如果有的话
}
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="全能客服助手",
        instructions=instructions,
        tools=[get_order, query_logistics]
    )
    
    return agent


async def test_multi_step_tracing():
    """测试多步骤工作流 Tracing"""
    
    print("=" * 70)
    print("📊 测试 2：多步骤工作流 Tracing - 订单 + 物流")
    print("=" * 70)
    
    agent = create_full_workflow_agent()
    
    # 使用 trace 包裹完整工作流
    with trace("订单 + 物流查询工作流", group_id="test_002") as t:
        print(f"\n✅ Trace 已启动：{t.trace_id}")
        
        start_time = time.time()
        
        # 运行 Agent（会自动调用多个 Tool）
        result = await Runner.run(agent, "查询订单 ORD20260417001 的物流信息")
        
        elapsed = time.time() - start_time
        
        print(f"\n🤖 Agent 回复:\n{result.final_output[:500]}...")
        print(f"\n⏱️ 总耗时：{elapsed:.2f}秒")
        
        # 分析性能
        if elapsed > 2.0:
            print(f"\n⚠️  性能提示：总耗时超过 2 秒")
            print(f"   可能原因：多次 LLM 调用或 Tool 延迟")
            print(f"   优化建议：查看 Trace 中哪个 Span 最慢")
    
    print(f"\n✅ Trace 完成")


# ============================================================
# 场景 3：错误调试 - 模拟失败场景
# ============================================================

@function_tool
def get_order_with_error(order_id: str) -> Optional[Order]:
    """查询订单（模拟随机错误）"""
    time.sleep(0.3)
    
    # 模拟数据库错误
    if order_id == "ORD_ERROR":
        raise Exception("数据库连接失败")
    
    data = ORDERS_DB.get(order_id)
    if not data:
        return None
    
    return Order(order_id=order_id, **data)


def create_debug_agent():
    """创建用于调试的 Agent"""
    
    instructions = """
你是一个订单查询助手。当用户查询订单时：
1. 调用 get_order_with_error 工具
2. 如果工具抛出异常，捕获并返回友好的错误消息
3. 如果订单不存在，返回 {"error": "订单不存在", "order_id": "xxx"}
4. 如果成功，返回订单 JSON

【重要】始终返回纯 JSON 格式。
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="订单查询助手",
        instructions=instructions,
        tools=[get_order_with_error]
    )
    
    return agent


async def test_error_debug_tracing():
    """测试错误调试 Tracing"""
    
    print("=" * 70)
    print("📊 测试 3：错误调试 Tracing - 模拟失败场景")
    print("=" * 70)
    
    agent = create_debug_agent()
    
    # 测试正常情况
    print("\n【测试 3a】正常订单查询")
    with trace("错误调试 - 正常场景", group_id="test_003a") as t:
        result = await Runner.run(agent, "查询订单 ORD20260417001")
        print(f"🤖 回复：{result.final_output[:200]}")
    
    # 测试错误情况
    print("\n【测试 3b】模拟数据库错误")
    with trace("错误调试 - 错误场景", group_id="test_003b") as t:
        try:
            result = await Runner.run(agent, "查询订单 ORD_ERROR")
            print(f"🤖 回复：{result.final_output[:200]}")
        except Exception as e:
            print(f"❌ 捕获异常：{e}")
            print(f"   Trace 会记录异常发生的位置和上下文")
    
    # 测试订单不存在
    print("\n【测试 3c】订单不存在")
    with trace("错误调试 - 订单不存在", group_id="test_003c") as t:
        result = await Runner.run(agent, "查询订单 ORD_NOT_EXIST")
        print(f"🤖 回复：{result.final_output[:200]}")
    
    print(f"\n✅ 所有错误场景 Trace 完成")


# ============================================================
# 场景 4：性能分析 - 查看哪个步骤最慢
# ============================================================

@function_tool
def slow_tool_1(query: str) -> str:
    """慢速 Tool 1（模拟 1 秒延迟）"""
    time.sleep(1.0)
    return f"Slow tool 1 result for: {query}"


@function_tool
def fast_tool_1(query: str) -> str:
    """快速 Tool 1（模拟 0.1 秒延迟）"""
    time.sleep(0.1)
    return f"Fast tool 1 result for: {query}"


def create_performance_agent():
    """创建性能测试 Agent"""
    
    instructions = """
你是一个测试助手。根据用户请求调用不同的工具：
- "慢速" → 调用 slow_tool_1
- "快速" → 调用 fast_tool_1

返回工具的结果即可。
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="性能测试助手",
        instructions=instructions,
        tools=[slow_tool_1, fast_tool_1]
    )
    
    return agent


async def test_performance_tracing():
    """测试性能分析 Tracing"""
    
    print("=" * 70)
    print("📊 测试 4：性能分析 Tracing - 识别瓶颈")
    print("=" * 70)
    
    agent = create_performance_agent()
    
    # 测试慢速场景
    print("\n【测试 4a】慢速 Tool 场景")
    with trace("性能测试 - 慢速", group_id="test_004a") as t:
        start = time.time()
        result = await Runner.run(agent, "使用慢速工具查询")
        elapsed = time.time() - start
        print(f"⏱️  总耗时：{elapsed:.2f}秒")
        print(f"🤖 回复：{result.final_output[:100]}")
        
        if elapsed > 1.0:
            print(f"\n💡 性能分析:")
            print(f"   - Tool 执行时间：~1.0 秒（主要瓶颈）")
            print(f"   - LLM 调用时间：~0.5 秒")
            print(f"   - 优化建议：缓存 Tool 结果或异步执行")
    
    # 测试快速场景
    print("\n【测试 4b】快速 Tool 场景")
    with trace("性能测试 - 快速", group_id="test_004b") as t:
        start = time.time()
        result = await Runner.run(agent, "使用快速工具查询")
        elapsed = time.time() - start
        print(f"⏱️  总耗时：{elapsed:.2f}秒")
        print(f"🤖 回复：{result.final_output[:100]}")
    
    print(f"\n✅ 性能对比完成")


# ============================================================
# Tracing 最佳实践
# ============================================================

async def run_all_tests():
    """运行所有 Tracing 测试"""
    
    print("\n" + "=" * 70)
    print("🎯 Day 14: Tracing 调试 - 完整测试套件")
    print("=" * 70)
    
    await test_basic_tracing()
    print("\n" + "-" * 70 + "\n")
    
    await test_multi_step_tracing()
    print("\n" + "-" * 70 + "\n")
    
    await test_error_debug_tracing()
    print("\n" + "-" * 70 + "\n")
    
    await test_performance_tracing()
    
    print("\n" + "=" * 70)
    print("✅ 所有 Tracing 测试完成！")
    print("=" * 70)


# ============================================================
# Tracing 配置指南
# ============================================================

"""
🔧 如何启用 Tracing？

方法 1：默认启用（推荐）
- Tracing 默认已启用
- 无需额外配置

方法 2：通过环境变量控制
```bash
# 启用详细日志（包括模型输入输出）
export OPENAI_AGENTS_DONT_LOG_MODEL_DATA=false
export OPENAI_AGENTS_DONT_LOG_TOOL_DATA=false

# 禁用 Tracing（不推荐，除非性能关键）
export OPENAI_AGENTS_DISABLE_TRACING=true
```

方法 3：代码中控制
```python
from agents import set_trace_processors

# 添加自定义 Trace 处理器
set_trace_processors([MyCustomProcessor()])
```

📊 查看 Trace 数据

1. OpenAI Dashboard（如果使用 OpenAI API）
   - 访问：https://platform.openai.com/trace
   - 查看完整的 Trace Tree
   - 分析每个 Span 的详细信息

2. 本地日志（开发环境）
   - 启用详细日志模式
   - 查看控制台输出

3. 第三方工具
   - Langfuse：开源追踪平台
   - LangSmith：LangChain 的追踪服务
   - Phoenix：Arize AI 的追踪工具

💡 Tracing 调试技巧

1. 🔍 定位问题
   - 查看哪个 Span 抛出异常
   - 检查异常发生时的输入数据
   - 分析上下文信息

2. ⚡ 性能优化
   - 找出最慢的 Span
   - 分析是否可以并行执行
   - 考虑缓存重复调用

3. 🐛 调试 Tool 调用
   - 查看 Tool 的输入参数
   - 检查 Tool 的返回结果
   - 确认 Agent 是否正确理解结果

4. 💰 成本控制
   - 统计每次 Trace 的 Token 消耗
   - 识别高成本的 LLM 调用
   - 优化 prompts 减少 Token

⚠️ 注意事项

1. 隐私保护
   - 生产环境避免记录敏感数据
   - 使用 DONT_LOG_MODEL_DATA 标志
   - 对 Trace 数据进行脱敏处理

2. 性能影响
   - Tracing 会增加少量开销（~5-10%）
   - 高并发场景考虑采样（只记录部分请求）
   - 禁用不必要的详细日志

3. 数据存储
   - Trace 数据可能很大，定期清理
   - 使用合适的存储后端（数据库、对象存储）
   - 设置合理的保留期限
"""


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(run_all_tests())
    else:
        # 默认运行基础测试
        print("=" * 70)
        print("📊 Day 14: Tracing 调试演示")
        print("💡 输入 'test' 运行完整测试集，输入 'quit' 退出")
        print("=" * 70)
        
        async def interactive():
            while True:
                try:
                    user_input = input("\n👤 您：").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 再见！")
                        break
                    
                    if user_input.lower() == 'test':
                        await run_all_tests()
                        continue
                    
                    if not user_input:
                        continue
                    
                    # 运行基础 Tracing
                    with trace("交互式查询", group_id="interactive"):
                        agent = create_order_agent_with_tracing()
                        result = await Runner.run(agent, user_input)
                        print(f"\n🤖 Agent:\n{result.final_output}")
                
                except KeyboardInterrupt:
                    print("\n👋 再见！")
                    break
                except Exception as e:
                    print(f"❌ 错误：{e}")
        
        asyncio.run(interactive())


# ============================================================
# 学习总结
# ============================================================

"""
📚 Day 14 关键知识点

1. Tracing 核心概念
   - Trace：完整工作流
   - Span：单个操作
   - Trace Tree：层级关系

2. 启用 Tracing
   - 默认已启用
   - 可用环境变量控制
   - 支持自定义处理器

3. 使用场景
   - 🔍 调试：查看决策过程
   - 🐛 排错：定位异常位置
   - ⚡ 优化：识别性能瓶颈
   - 📈 监控：生产环境分析
   - 💰 成本：统计 Token 消耗

4. 最佳实践
   - 使用 descriptive 的 Trace 名称
   - 用 group_id 关联相关 Trace
   - 添加有意义的 metadata
   - 注意隐私和数据安全

5. 下一步学习
   - Week 3: Guardrails（输入/输出验证）
   - Week 4: Handoffs（多 Agent 协作）
   - 第 4 月：Multi-Agent 协作模式

🎯 实践建议
1. 开发阶段：始终启用 Tracing
2. 测试阶段：分析 Trace 优化性能
3. 生产环境：采样记录（如 10% 请求）
4. 问题排查：临时提高采样率
"""
