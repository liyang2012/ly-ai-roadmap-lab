#!/usr/bin/env python3
"""
Week 2: 多 Tool 协作示例
包含：query_refund_policy, check_order_status, calculate_shipping
"""

# import 是 Python 引入外部库的关键字。
# asyncio 库用于处理异步操作，例如网络请求等耗时任务。
import asyncio

# os 库提供了与操作系统交互的功能，在这里用来读取环境变量。
import os

# logging 库用来输出程序运行时的日志信息，方便我们调试。
import logging

# 从 agents 库中导入我们需要使用的核心类和函数：
# - Agent: AI 智能体类
# - Runner: 运行器，负责驱动 Agent 执行
# - function_tool: 装饰器，用来把普通的 Python 函数变成 AI 可以调用的工具
from agents import Agent, Runner, function_tool

# 导入一个特定的配置函数，用来兼容一些不同的模型 API 格式。
from agents.models._openai_shared import set_use_responses_by_default

# dotenv 库用来从项目的 .env 文件读取环境变量，避免把密码、密钥等写死在代码里。
from dotenv import load_dotenv

# load_dotenv() 会自动寻找当前目录下的 .env 文件并加载它。
load_dotenv()

# 设置日志的基础级别为 INFO。这意味着 INFO 以及以上级别（WARNING, ERROR）的日志都会被打印出来。
logging.basicConfig(level=logging.INFO)

# 禁用 OpenAI Responses API，使用标准的 Chat Completions API。
# 这是因为阿里云百炼平台（兼容 OpenAI）当前更支持基础的 Chat API。
set_use_responses_by_default(False)


# ============ 定义 Tools (工具) ============
# 在这里，我们将编写一些普通的 Python 函数，并通过 @function_tool 将其声明给大模型。

# @function_tool 是一个 "装饰器"。它的作用是告诉大模型："这是一个你可以调用的工具"。
# 当大模型认为需要查询退货政策时，它会自动调用这个函数。
@function_tool
def query_refund_policy(product_type: str) -> str:
    # 这里的 """ ... """ 是函数的文档字符串（Docstring）。
    # 这部分内容非常重要！它不仅是给程序员看的，更是给 AI 模型看的。
    # AI 主要是通过阅读这里的内容，来知道这个工具是用来干嘛的，以及需要传入什么参数。
    """
    查询某类商品的退货政策。
    
    Args:
        product_type: 商品类型，如 "electronics", "clothing", "books"
    
    Returns:
        退货政策说明
    """
    # 字典（dict）类型，用一对大括号 {} 包裹。它由 键(key): 值(value) 组成。
    policies = {
        "electronics": "电子产品：7 天无理由退货，需保持包装完整，配件齐全。开封后不支持退货（质量问题除外）。",
        "clothing": "服装：30 天无理由退货，需未洗涤、未穿着，吊牌完整。",
        "books": "图书：7 天无理由退货，需无涂写、无破损。",
        "food": "食品：不支持无理由退货（质量问题可退换）。",
        "default": "通用政策：15 天无理由退货，商品需保持完好。"
    }
    # return 是函数的返回语句。
    # product_type.lower() 是把传入的商品类型转为小写字母。
    # policies.get(...) 是尝试从字典中取出对应的值，如果没找到，就会返回第二个参数 policies["default"]。
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
    # 模拟的一个小型订单数据库（字典）
    statuses = {
        "ORD001": "已发货，预计明天送达",
        "ORD002": "处理中，预计今天发货",
        "ORD003": "已签收",
        "ORD004": "已取消"
    }
    # order_id.upper() 把订单号强制转为大写，确保不管用户输入大写小写都能查到。
    # f"..." 是 Python 的 f-string 语法，可以在字符串内部用 {} 直接插入变量的值。
    return statuses.get(order_id.upper(), f"订单 {order_id} 未找到")


@function_tool
def calculate_shipping(weight_kg: float, destination: str) -> float:
    # Python 函数参数后面的冒号和类型（如 : float）是类型注解（Type Hinting）。
    # 它不会影响程序的运行，但能帮助代码编辑器和 AI 更好地明白你的参数应该是数字还是字符串。
    """
    计算运费。
    
    Args:
        weight_kg: 包裹重量（公斤）
        destination: 目的地城市
    
    Returns:
        运费（元）
    """
    base_rate = 10.0  # 定义首重价格 (1公斤以内)
    extra_rate = 5.0  # 定义续重价格 (超出1公斤的部分每公斤价格)
    
    # 定义偏远地区的列表 (List)。列表用一对方括号 [] 包裹，可以存放多个数据。
    remote_areas = ["拉萨", "乌鲁木齐", "西宁"]
    
    # 这是一个三元条件表达式。
    # 如果目的地 (destination) 在 remote_areas 列表里，则 multiplier = 1.5，否则 multiplier = 1.0
    multiplier = 1.5 if destination in remote_areas else 1.0
    
    # if / else 分支选择语句
    if weight_kg <= 1:
        return base_rate * multiplier
    else:
        # 当重量超过 1 公斤时，计算 (首重 + 续重) * 倍数
        return (base_rate + (weight_kg - 1) * extra_rate) * multiplier


# ============ 创建 Agent (AI 智能体) ============

# 引入官方的 AsyncOpenAI 客户端以及底层的 OpenAI 兼容模型类
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 初始化兼容 OpenAI 格式的百炼客户端。
# AsyncOpenAI 是用来发送网络请求的客户端组件。
client = AsyncOpenAI(
    # os.getenv(...) 是从操作系统的环境变量中获取值。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # base_url 是网关地址，把大模型的请求指向阿里云百炼。
    base_url="https://coding.dashscope.aliyuncs.com/v1",
)

# 真正实例化并创建一个 Agent (客服助手) 对象。
customer_service_agent = Agent(
    # 1. model: 指定我们要使用的模型。百炼环境需要使用 OpenAIChatCompletionsModel 并传入我们的 client。
    model=OpenAIChatCompletionsModel(model="qwen3.5-plus", openai_client=client),
    
    # 2. name: 给智能体起一个名字，方便阅读和后台识别。
    name="客服助手",
    
    # 3. instructions: 指令提示词（即系统设定/System Prompt）。
    # 这是 Agent 最核心的“人设”，用 """...""" 包裹允许换行的多行字符串。
    instructions="""你是一个电商客服助手。你可以帮助用户：
1. 查询退货政策
2. 查询订单状态
3. 计算运费

根据用户问题，自动调用合适的工具。回答要简洁友好。""",

    # 4. tools: 工具列表。我们将自己编写的 3 个函数名放进中括号 [] 里传给 Agent。
    # 这样当用户提问时，AI 就会自动判断该选用那个工具。
    tools=[
        query_refund_policy,
        check_order_status,
        calculate_shipping
    ]
)


# ============ 测试部分 ============

# async def 表示定义一个异步函数。
# 异步编程可以让程序在等待大模型响应网络返回时，不至于一直卡死，可以去做别的事情。
async def main():
    # 打印一些好看的分割线。 "*" * 60 表示把星号重复 60 次。
    print("=" * 60)
    print("Week 2: 多 Tool 协作示例")
    print("=" * 60)
    
    # 构建一个测试用例列表。
    test_cases = [
        "电子产品怎么退货？",
        "帮我查一下订单 ORD001 的状态",
        "从北京寄一个 2.5kg 的包裹到上海，运费多少？",
        "衣服穿了一次不喜欢，能退吗？",
        "订单 ORD999 查不到吗？"
    ]
    
    # for 循环遍历每一个测试用例。
    # enumerate(test_cases, 1) 的作用是给遍历出来的元素按顺序加个序号，1 代表序号从 1 开始。
    # 所以在第一次循环时: i = 1, query = "电子产品怎么退货？"
    for i, query in enumerate(test_cases, 1):
        # 打印用户提问内容。
        print(f"\n【测试 {i}】用户问：{query}")
        print("-" * 40)
        
        # await 关键字只能在 async 函数里使用。
        # 它的意思是：“现在向大模型发送请求，并且在这里暂停等待，直到有结果返回才继续往下走”。
        # Runner.run 会调用刚才配置好的 customer_service_agent，并将用户输入(query)送给它处理。
        result = await Runner.run(customer_service_agent, query)
        
        # result.final_output 就是 AI 最终向用户输出的文本结果。
        print(f"客服回答：{result.final_output}")
        print()


# 这是 Python 程序的标准“入口点”判断规范。
# "__name__" 是 Python 的内置变量。如果通过 `python multi_tool_agent.py` 直接运行该脚本，
# 那么 __name__ 的值就会变成 "__main__"，进而执行下面的代码块。
# 要是这个脚本里的函数是被别的文件导入(import)使用的，下面这段就不会被执行。
if __name__ == "__main__":
    # 我们没法像调用普通函数一样直接 main() 来调用异步函数，
    # 必须要借助 asyncio.run(...) 来正式启动异步主程序的执行。
    asyncio.run(main())
