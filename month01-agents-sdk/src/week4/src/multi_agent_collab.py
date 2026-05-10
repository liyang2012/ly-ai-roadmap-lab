#!/usr/bin/env python3
"""
Week 4 - Day 26-27: 多 Agent 协作 - 旅行规划助手

学习目标：
1. 设计多个 Agent 协同工作的场景
2. 实现 Agent 之间的数据传递
3. 处理异常情况（某个 Agent 失败怎么办）
4. 对比单 Agent vs 多 Agent 的优劣

场景：旅行规划助手
- Agent A: 意图分析 & 路由（Router Agent）
- Agent B: 机票查询（Flight Agent）
- Agent C: 酒店推荐（Hotel Agent）
- Agent D: 景点推荐（Attraction Agent）
- Agent E: 行程汇总（Summary Agent）
"""

import os
from typing import Optional
from agents import Agent, handoff, Runner, function_tool
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 加载环境变量
load_dotenv()

# 禁用 Responses API，使用 Chat Completions
set_use_responses_by_default(False)

# 初始化阿里云百炼客户端
client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://coding.dashscope.aliyuncs.com/v1",
)

# 定义模型名称
MODEL_NAME = "qwen3.6-plus"


# ============================================================
# 模拟数据库和工具函数
# ============================================================

@function_tool
def search_flights(origin: str, destination: str, date: str) -> dict:
    """
    查询航班信息
    
    Args:
        origin: 出发城市
        destination: 目的城市
        date: 出发日期 (YYYY-MM-DD)
    
    Returns:
        航班列表
    """
    # 模拟航班数据
    flights_db = {
        "北京-上海": [
            {"flight_no": "CA1234", "departure": "08:00", "arrival": "10:15", "price": 1200, "airline": "国航"},
            {"flight_no": "MU5678", "departure": "14:30", "arrival": "16:45", "price": 980, "airline": "东航"},
            {"flight_no": "CZ9012", "departure": "19:00", "arrival": "21:10", "price": 850, "airline": "南航"},
        ],
        "北京-成都": [
            {"flight_no": "CA4567", "departure": "09:30", "arrival": "12:30", "price": 1500, "airline": "国航"},
            {"flight_no": "3U8901", "departure": "15:00", "arrival": "18:00", "price": 1350, "airline": "川航"},
        ],
        "上海-西安": [
            {"flight_no": "MU2345", "departure": "10:00", "arrival": "12:30", "price": 1100, "airline": "东航"},
            {"flight_no": "HO6789", "departure": "16:30", "arrival": "19:00", "price": 950, "airline": "吉祥"},
        ],
    }
    
    route = f"{origin}-{destination}"
    flights = flights_db.get(route, [])
    
    return {
        "origin": origin,
        "destination": destination,
        "date": date,
        "flights": flights,
        "count": len(flights),
        "message": f"找到 {len(flights)} 个航班" if flights else f"未找到 {route} 的航班"
    }


@function_tool
def search_hotels(city: str, check_in: str, check_out: str, budget: Optional[str] = None) -> dict:
    """
    查询酒店信息
    
    Args:
        city: 城市
        check_in: 入住日期 (YYYY-MM-DD)
        check_out: 离店日期 (YYYY-MM-DD)
        budget: 预算范围 (low/medium/high)
    
    Returns:
        酒店列表
    """
    # 模拟酒店数据
    hotels_db = {
        "上海": [
            {"name": "上海和平饭店", "stars": 5, "price": 1800, "area": "外滩", "rating": 4.8},
            {"name": "上海浦东香格里拉", "stars": 5, "price": 1500, "area": "陆家嘴", "rating": 4.7},
            {"name": "全季酒店（人民广场店）", "stars": 3, "price": 450, "area": "人民广场", "rating": 4.5},
            {"name": "汉庭酒店（南京路店）", "stars": 2, "price": 280, "area": "南京路", "rating": 4.2},
        ],
        "成都": [
            {"name": "成都香格里拉大酒店", "stars": 5, "price": 1200, "area": "锦江区", "rating": 4.7},
            {"name": "成都宽窄巷子亚朵酒店", "stars": 4, "price": 600, "area": "宽窄巷子", "rating": 4.6},
            {"name": "如家精选（春熙路店）", "stars": 3, "price": 350, "area": "春熙路", "rating": 4.3},
        ],
        "西安": [
            {"name": "西安索菲特传奇酒店", "stars": 5, "price": 1100, "area": "钟楼", "rating": 4.8},
            {"name": "西安城墙亚朵酒店", "stars": 4, "price": 550, "area": "城墙", "rating": 4.6},
            {"name": "城市便捷酒店（大雁塔店）", "stars": 3, "price": 320, "area": "大雁塔", "rating": 4.4},
        ],
    }
    
    hotels = hotels_db.get(city, [])
    
    # 根据预算过滤
    if budget == "low":
        hotels = [h for h in hotels if h["price"] < 400]
    elif budget == "medium":
        hotels = [h for h in hotels if 400 <= h["price"] <= 1000]
    elif budget == "high":
        hotels = [h for h in hotels if h["price"] > 1000]
    
    return {
        "city": city,
        "check_in": check_in,
        "check_out": check_out,
        "hotels": hotels,
        "count": len(hotels),
        "message": f"找到 {len(hotels)} 家酒店" if hotels else f"未找到 {city} 的酒店"
    }


@function_tool
def search_attractions(city: str, days: int = 1) -> dict:
    """
    查询景点信息
    
    Args:
        city: 城市
        days: 游玩天数
    
    Returns:
        景点列表
    """
    # 模拟景点数据
    attractions_db = {
        "上海": [
            {"name": "外滩", "type": "地标", "duration": "2小时", "ticket": 0, "rating": 4.9},
            {"name": "东方明珠", "type": "地标", "duration": "3小时", "ticket": 180, "rating": 4.6},
            {"name": "豫园", "type": "园林", "duration": "2小时", "ticket": 40, "rating": 4.5},
            {"name": "上海博物馆", "type": "博物馆", "duration": "3小时", "ticket": 0, "rating": 4.7},
            {"name": "田子坊", "type": "文创", "duration": "2小时", "ticket": 0, "rating": 4.4},
            {"name": "上海迪士尼乐园", "type": "主题乐园", "duration": "1天", "ticket": 475, "rating": 4.8},
        ],
        "成都": [
            {"name": "大熊猫繁育研究基地", "type": "动物园", "duration": "4小时", "ticket": 55, "rating": 4.9},
            {"name": "宽窄巷子", "type": "历史文化", "duration": "2小时", "ticket": 0, "rating": 4.6},
            {"name": "锦里古街", "type": "历史文化", "duration": "2小时", "ticket": 0, "rating": 4.5},
            {"name": "武侯祠", "type": "历史遗迹", "duration": "2小时", "ticket": 50, "rating": 4.7},
            {"name": "青城山", "type": "自然风光", "duration": "1天", "ticket": 80, "rating": 4.8},
            {"name": "都江堰", "type": "历史遗迹", "duration": "半天", "ticket": 80, "rating": 4.7},
        ],
        "西安": [
            {"name": "秦始皇兵马俑", "type": "历史遗迹", "duration": "4小时", "ticket": 120, "rating": 4.9},
            {"name": "大雁塔", "type": "历史遗迹", "duration": "2小时", "ticket": 50, "rating": 4.7},
            {"name": "西安城墙", "type": "历史遗迹", "duration": "3小时", "ticket": 54, "rating": 4.8},
            {"name": "回民街", "type": "美食街", "duration": "2小时", "ticket": 0, "rating": 4.5},
            {"name": "华清宫", "type": "历史遗迹", "duration": "3小时", "ticket": 120, "rating": 4.6},
            {"name": "陕西历史博物馆", "type": "博物馆", "duration": "3小时", "ticket": 0, "rating": 4.8},
        ],
    }
    
    attractions = attractions_db.get(city, [])
    
    # 根据天数推荐景点数量（每天2-3个景点）
    recommended = attractions[:min(days * 3, len(attractions))]
    
    return {
        "city": city,
        "days": days,
        "attractions": recommended,
        "count": len(recommended),
        "message": f"为您推荐 {len(recommended)} 个景点" if recommended else f"未找到 {city} 的景点"
    }


# ============================================================
# 创建多 Agent 系统
# ============================================================

# Agent B: 机票查询专员
flight_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Flight Specialist",
    instructions="""你是机票查询专员。
当用户需要查询航班信息时：
1. 调用 search_flights 工具查询航班
2. 根据查询结果，为用户推荐最合适的航班
3. 推荐时要考虑价格、时间和航空公司的综合因素
4. 用清晰的格式展示航班信息

如果工具返回空结果，请如实告知用户并建议调整日期或路线。""",
    tools=[search_flights],
)

# Agent C: 酒店推荐专员
hotel_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Hotel Specialist",
    instructions="""你是酒店推荐专员。
当用户需要查询酒店信息时：
1. 调用 search_hotels 工具查询酒店
2. 根据用户的预算和偏好推荐合适的酒店
3. 推荐时要考虑位置、价格、评分的综合因素
4. 用清晰的格式展示酒店信息

如果工具返回空结果，请如实告知用户并建议调整预算或日期。""",
    tools=[search_hotels],
)

# Agent D: 景点推荐专员
attraction_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Attraction Specialist",
    instructions="""你是景点推荐专员。
当用户需要查询景点信息时：
1. 调用 search_attractions 工具查询景点
2. 根据用户的游玩天数推荐合适的景点
3. 推荐时要考虑景点的评分、类型和地理位置
4. 用清晰的格式展示景点信息，包括门票价格和游玩时长

如果工具返回空结果，请如实告知用户并推荐其他城市。""",
    tools=[search_attractions],
)

# Agent E: 行程汇总专员
summary_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Summary Specialist",
    instructions="""你是行程汇总专员。
当用户提供航班、酒店、景点信息后：
1. 将所有信息整合成一份完整的旅行计划
2. 按照时间顺序排列行程
3. 提供每日详细行程安排
4. 给出实用的旅行建议（交通、餐饮、注意事项等）
5. 计算总预算估算

输出格式要清晰、专业、易于阅读。""",
)

# Agent A: 路由器 Agent（主 Agent）
router_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Travel Router",
    instructions="""你是旅行规划助手的路由器。
分析用户的需求，然后交给合适的专员处理：

- 查询航班 → Flight Specialist
- 查询酒店 → Hotel Specialist
- 查询景点 → Attraction Specialist
- 整合完整行程 → Summary Specialist

如果用户的需求涉及多个方面，请依次交给对应的专员处理。
如果无法判断，请直接回答用户的问题。

注意：你要根据用户的问题智能判断路由到哪个 Agent。""",
    handoffs=[
        handoff(flight_agent),
        handoff(hotel_agent),
        handoff(attraction_agent),
        handoff(summary_agent),
    ],
)


# ============================================================
# 测试函数
# ============================================================

async def test_single_agent():
    """测试单个 Agent 的独立工作"""
    print("\n" + "=" * 80)
    print("测试 1：单 Agent 工作 - 查询航班")
    print("=" * 80)
    
    result = await Runner.run(flight_agent, "帮我查询北京到上海 2026-05-20 的航班")
    print(f"🤖 回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次调用")
    total_tokens = sum(r.usage.total_tokens for r in result.raw_responses)
    print(f"   总计: {total_tokens} tokens")


async def test_handoff():
    """测试 Handoff 路由"""
    print("\n" + "=" * 80)
    print("测试 2：Handoff 路由 - 查询酒店")
    print("=" * 80)
    
    result = await Runner.run(router_agent, "我想查询上海 2026-05-20 到 2026-05-23 的酒店，预算中等")
    print(f"🤖 回复: {result.final_output}")
    print(f"📊 Token 使用: 共 {len(result.raw_responses)} 次调用")
    for i, response in enumerate(result.raw_responses, 1):
        print(f"   调用 {i}: {response.usage.total_tokens} tokens")


async def test_multi_step_manual():
    """测试多步骤协作（手动方式）"""
    print("\n" + "=" * 80)
    print("测试 3：多 Agent 协作 - 完整旅行规划（手动串联）")
    print("=" * 80)
    
    # 第 1 步：查询航班
    print("\n【第 1 步】查询航班...")
    flight_result = await Runner.run(
        flight_agent, 
        "帮我查询北京到上海 2026-05-20 的航班，推荐最便宜的"
    )
    print(f"✈️ 航班信息: {flight_result.final_output[:200]}...")
    
    # 第 2 步：查询酒店
    print("\n【第 2 步】查询酒店...")
    hotel_result = await Runner.run(
        hotel_agent,
        "我想查询上海 2026-05-20 到 2026-05-23 的酒店，预算中等，推荐性价比最高的"
    )
    print(f"🏨 酒店信息: {hotel_result.final_output[:200]}...")
    
    # 第 3 步：查询景点
    print("\n【第 3 步】查询景点...")
    attraction_result = await Runner.run(
        attraction_agent,
        "我在上海游玩 3 天，推荐必去的景点"
    )
    print(f"🎯 景点信息: {attraction_result.final_output[:200]}...")
    
    # 第 4 步：整合行程
    print("\n【第 4 步】整合完整行程...")
    summary_input = f"""请根据以下信息整合一份完整的上海旅行计划：

【航班信息】
{flight_result.final_output}

【酒店信息】
{hotel_result.final_output}

【景点推荐】
{attraction_result.final_output}

请整合成一份详细的旅行计划，包括每日行程安排、预算估算和实用建议。"""
    
    summary_result = await Runner.run(summary_agent, summary_input)
    print(f"📋 完整行程:\n{summary_result.final_output}")
    
    # 统计总 token 使用
    total_tokens = (
        sum(r.usage.total_tokens for r in flight_result.raw_responses) +
        sum(r.usage.total_tokens for r in hotel_result.raw_responses) +
        sum(r.usage.total_tokens for r in attraction_result.raw_responses) +
        sum(r.usage.total_tokens for r in summary_result.raw_responses)
    )
    print(f"\n📊 总 Token 使用: {total_tokens} tokens")


async def test_comparison():
    """对比单 Agent vs 多 Agent"""
    print("\n" + "=" * 80)
    print("测试 4：对比 - 单 Agent vs 多 Agent")
    print("=" * 80)
    
    # 方式 1：使用通用的旅行 Agent（模拟单 Agent）
    print("\n【方式 1】单 Agent 方式...")
    general_agent = Agent(
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
        name="General Travel Agent",
        instructions="""你是一个通用的旅行规划助手。
你可以查询航班、酒店、景点信息，并为用户制定旅行计划。
你有以下工具可以使用：
- search_flights: 查询航班
- search_hotels: 查询酒店
- search_attractions: 查询景点

请根据用户的需求，调用相应的工具，然后给出完整的旅行建议。""",
        tools=[search_flights, search_hotels, search_attractions],
    )
    
    import time
    start = time.time()
    result1 = await Runner.run(
        general_agent,
        "我想 2026-05-20 从北京到上海游玩 3 天，帮我规划一下行程，包括航班、酒店和景点"
    )
    elapsed1 = time.time() - start
    tokens1 = sum(r.usage.total_tokens for r in result1.raw_responses)
    
    print(f"⏱️  耗时: {elapsed1:.2f}秒")
    print(f"📊 Token: {tokens1}")
    print(f"📝 回复长度: {len(result1.final_output)} 字符")
    
    # 方式 2：使用多 Agent 协作
    print("\n【方式 2】多 Agent 协作方式...")
    start = time.time()
    
    # 复用测试 3 的逻辑
    flight_result = await Runner.run(flight_agent, "北京到上海 2026-05-20 的航班")
    hotel_result = await Runner.run(hotel_agent, "上海 2026-05-20 到 2026-05-23 的酒店，中等预算")
    attraction_result = await Runner.run(attraction_agent, "上海游玩 3 天的景点推荐")
    
    summary_input = f"""请根据以下信息整合旅行计划：
航班：{flight_result.final_output}
酒店：{hotel_result.final_output}
景点：{attraction_result.final_output}"""
    
    result2 = await Runner.run(summary_agent, summary_input)
    elapsed2 = time.time() - start
    tokens2 = (
        sum(r.usage.total_tokens for r in flight_result.raw_responses) +
        sum(r.usage.total_tokens for r in hotel_result.raw_responses) +
        sum(r.usage.total_tokens for r in attraction_result.raw_responses) +
        sum(r.usage.total_tokens for r in result2.raw_responses)
    )
    
    print(f"⏱️  耗时: {elapsed2:.2f}秒")
    print(f"📊 Token: {tokens2}")
    print(f"📝 回复长度: {len(result2.final_output)} 字符")
    
    # 对比分析
    print("\n📈 对比分析:")
    print(f"  时间对比: {'单Agent 更快' if elapsed1 < elapsed2 else '多Agent 更快'}")
    print(f"  Token 对比: {'单Agent 更省' if tokens1 < tokens2 else '多Agent 更省'}")
    print(f"  质量对比: 需要人工评估（多 Agent 通常质量更高、更专业）")


# ============================================================
# 主函数
# ============================================================

async def main():
    """运行所有测试"""
    print("=" * 80)
    print("🌍 Week 4 - Day 26-27: 多 Agent 协作 - 旅行规划助手")
    print("=" * 80)
    print(f"📦 使用模型: {MODEL_NAME}")
    print("=" * 80)
    
    # 测试 1：单 Agent 工作
    await test_single_agent()
    
    # 测试 2：Handoff 路由
    await test_handoff()
    
    # 测试 3：多 Agent 协作（手动串联）
    await test_multi_step_manual()
    
    # 测试 4：对比单 Agent vs 多 Agent
    await test_comparison()
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
    print("\n💡 关键发现:")
    print("  1. 多 Agent 协作可以实现职责分离，每个 Agent 更专业")
    print("  2. Handoff 模式适合意图明确的路由场景")
    print("  3. 手动串联模式适合需要多步骤数据收集的场景")
    print("  4. 多 Agent 通常会消耗更多 Token，但质量更高")
    print("  5. 设计时要权衡：成本 vs 质量 vs 可维护性")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
