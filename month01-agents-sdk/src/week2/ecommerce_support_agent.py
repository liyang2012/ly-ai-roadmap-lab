#!/usr/bin/env python3
"""
Week 2: 电商客服 Agent 实战版
功能：订单查询、退款处理、物流跟踪、产品咨询、优惠券查询

学习重点：
1. 多个 Tool 的协作与优先级
2. Instructions 对 Tool 选择的影响
3. 结构化输出与错误处理
4. Tracing 调试
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

from agents import Agent, Runner, function_tool
from agents.models._openai_shared import set_use_responses_by_default
from dotenv import load_dotenv
# 引入官方的 AsyncOpenAI 客户端以及底层的 OpenAI 兼容模型类
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 加载环境变量
load_dotenv()

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用 Responses API，使用 Chat Completions
set_use_responses_by_default(False)

# 初始化兼容 OpenAI 格式的百炼客户端。
# AsyncOpenAI 是用来发送网络请求的客户端组件。
client = AsyncOpenAI(
    # 智谱 AI API Key，从环境变量读取
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    # 智谱 AI API 地址
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
)



# ============================================================
# 模拟数据库
# ============================================================

ORDERS_DB = {
    "ORD20260417001": {
        "status": "已发货",
        "product": "iPhone 15 Pro",
        "amount": 7999.00,
        "order_date": "2026-04-15",
        "logistics": "顺丰 SF1234567890",
        "estimated_delivery": "2026-04-19"
    },
    "ORD20260417002": {
        "status": "处理中",
        "product": "AirPods Pro 2",
        "amount": 1899.00,
        "order_date": "2026-04-17",
        "logistics": "待发货",
        "estimated_delivery": "2026-04-20"
    },
    "ORD20260417003": {
        "status": "已签收",
        "product": "MacBook Air M2",
        "amount": 9499.00,
        "order_date": "2026-04-10",
        "logistics": "京东 JD9876543210",
        "estimated_delivery": "已送达"
    },
}

REFUND_RULES = {
    "未发货": {"allowed": True, "days": "1-3 工作日到账", "fee": "无手续费"},
    "已发货": {"allowed": True, "days": "拒收或退货后", "fee": "运费自理"},
    "已签收": {"allowed": True, "days": "7 天内", "fee": "无质量问题需自理运费"},
    "超过 7 天": {"allowed": False, "days": "仅质量问题", "fee": "免费"},
}

COUPONS_DB = {
    "USER001": [
        {"code": "NEW100", "discount": 100, "min_amount": 1000, "expire": "2026-05-01", "status": "可用"},
        {"code": "VIP50", "discount": 50, "min_amount": 500, "expire": "2026-04-30", "status": "可用"},
    ],
    "USER002": [
        {"code": "NEW100", "discount": 100, "min_amount": 1000, "expire": "2026-05-01", "status": "已使用"},
    ],
}

PRODUCT_KB = {
    "iPhone": {
        "warranty": "1 年全国联保",
        "return": "7 天无理由",
        "features": "A17 芯片、钛金属边框、4800 万像素"
    },
    "MacBook": {
        "warranty": "1 年全国联保",
        "return": "14 天无理由（未激活）",
        "features": "M 系列芯片、Liquid 视网膜屏、18 小时续航"
    },
    "AirPods": {
        "warranty": "1 年全国联保",
        "return": "7 天无理由",
        "features": "主动降噪、空间音频、MagSafe 充电"
    },
}


# ============================================================
# Tool 定义
# ============================================================

@function_tool
def query_order_status(order_id: str) -> str:
    """
    查询订单状态和物流信息
    
    Args:
        order_id: 订单号，格式如 "ORD20260417001"
    
    Returns:
        订单详细信息，包括状态、商品、金额、物流等
    """
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"❌ 未找到订单 {order_id}，请确认订单号是否正确"
    
    return f"""
📦 订单详情
━━━━━━━━━━━━━━━━
订单号：{order_id}
商品：{order['product']}
金额：¥{order['amount']:,.2f}
下单日期：{order['order_date']}
状态：{order['status']}
物流：{order['logistics']}
预计送达：{order['estimated_delivery']}
━━━━━━━━━━━━━━━━
"""


@function_tool
def query_refund_policy(order_status: str) -> str:
    """
    查询退款政策
    
    Args:
        order_status: 订单状态，如 "未发货"、"已发货"、"已签收"
    
    Returns:
        退款政策说明
    """
    # 模糊匹配
    matched_key = None
    for key in REFUND_RULES:
        if key in order_status:
            matched_key = key
            break
    
    if not matched_key:
        return "❌ 无法识别订单状态，请提供：未发货/已发货/已签收/超过 7 天"
    
    rule = REFUND_RULES[matched_key]
    allowed = "✅ 支持退款" if rule["allowed"] else "❌ 不支持退款"
    
    return f"""
💰 退款政策
━━━━━━━━━━━━━━━━
订单状态：{order_status}
{allowed}
时效：{rule['days']}
费用：{rule['fee']}
━━━━━━━━━━━━━━━━
"""


@function_tool
def process_refund_apply(order_id: str, reason: str) -> str:
    """
    提交退款申请
    
    Args:
        order_id: 订单号
        reason: 退款原因，如 "七天无理由"、"质量问题"、"拍错/多拍"
    
    Returns:
        退款申请结果
    """
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"❌ 订单 {order_id} 不存在，无法提交退款申请"
    
    # 检查是否可退款
    status = order["status"]
    rule = REFUND_RULES.get(status, REFUND_RULES["超过 7 天"])
    
    if not rule["allowed"]:
        return f"""
❌ 退款申请被拒绝

订单 {order_id} 当前状态为【{status}】
根据政策，此状态不支持退款申请。

建议您：
1. 联系人工客服进一步咨询
2. 如为质量问题，可申请售后维修
"""
    
    # 生成退款单号
    refund_id = f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return f"""
✅ 退款申请已提交
━━━━━━━━━━━━━━━━
退款单号：{refund_id}
原订单：{order_id}
退款原因：{reason}
商品：{order['product']}
退款金额：¥{order['amount']:,.2f}
预计到账：{rule['days']}
━━━━━━━━━━━━━━━━

请保持手机畅通，物流人员可能会联系您取件。
"""


@function_tool
def query_logistics(logistics_no: str) -> str:
    """
    查询物流轨迹
    
    Args:
        logistics_no: 物流单号，如 "SF1234567890"
    
    Returns:
        物流轨迹信息
    """
    # 模拟物流信息
    logistics_info = {
        "SF1234567890": [
            ("2026-04-18 14:30", "【北京市】已签收，签收人：本人"),
            ("2026-04-18 09:15", "【北京市】快递员正在派送"),
            ("2026-04-18 06:00", "【北京市】到达朝阳区集散中心"),
            ("2026-04-17 20:30", "【廊坊市】已发出"),
            ("2026-04-17 15:00", "【廊坊市】顺丰速运已收件"),
        ],
        "JD9876543210": [
            ("2026-04-12 16:00", "【北京市】已签收，签收人：前台"),
            ("2026-04-12 08:30", "【北京市】京东快递员正在派送"),
            ("2026-04-11 22:00", "【北京市】到达北京大兴分拣中心"),
            ("2026-04-11 14:00", "【苏州市】已发出"),
        ],
    }
    
    tracks = logistics_info.get(logistics_no)
    if not tracks:
        return f"❌ 未找到物流单号 {logistics_no} 的信息"
    
    result = f"""
🚚 物流轨迹 - {logistics_no}
━━━━━━━━━━━━━━━━
"""
    for time, desc in tracks:
        result += f"{time}\n{desc}\n"
    result += "━━━━━━━━━━━━━━━━"
    
    return result


@function_tool
def query_coupons(user_id: str) -> str:
    """
    查询用户可用优惠券
    
    Args:
        user_id: 用户 ID，如 "USER001"
    
    Returns:
        优惠券列表
    """
    coupons = COUPONS_DB.get(user_id)
    if not coupons:
        return f"❌ 未找到用户 {user_id} 的优惠券信息"
    
    available = [c for c in coupons if c["status"] == "可用"]
    used = [c for c in coupons if c["status"] == "已使用"]
    
    result = f"""
🎫 优惠券 - {user_id}
━━━━━━━━━━━━━━━━
【可用优惠券】{len(available)} 张
"""
    
    if available:
        for c in available:
            result += f"• {c['code']}: 减¥{c['discount']} (满¥{c['min_amount']}可用)  expire:{c['expire']}\n"
    else:
        result += "暂无可用优惠券\n"
    
    result += f"\n【已使用】{len(used)} 张\n"
    result += "━━━━━━━━━━━━━━━━"
    
    return result


@function_tool
def query_product_info(product_name: str) -> str:
    """
    查询产品信息和售后政策
    
    Args:
        product_name: 产品名称，如 "iPhone"、"MacBook"、"AirPods"
    
    Returns:
        产品信息
    """
    # 模糊匹配
    matched_key = None
    for key in PRODUCT_KB:
        if key.lower() in product_name.lower():
            matched_key = key
            break
    
    if not matched_key:
        return f"❌ 未找到产品【{product_name}】的信息，请尝试：iPhone、MacBook、AirPods"
    
    info = PRODUCT_KB[matched_key]
    
    return f"""
📱 产品信息 - {matched_key}
━━━━━━━━━━━━━━━━
保修政策：{info['warranty']}
退货政策：{info['return']}
核心特性：{info['features']}
━━━━━━━━━━━━━━━━
"""


@function_tool
def escalate_to_human(issue_type: Literal["投诉", "复杂问题", "特殊申请", "其他"], summary: str) -> str:
    """
    转接人工客服
    
    Args:
        issue_type: 问题类型（投诉/复杂问题/特殊申请/其他）
        summary: 问题摘要
    
    Returns:
        工单信息
    """
    import random
    ticket_id = f"TKT{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
    wait_time = "24 小时" if issue_type == "投诉" else "48 小时"
    
    return f"""
👤 已转接人工客服
━━━━━━━━━━━━━━━━
工单号：{ticket_id}
问题类型：{issue_type}
问题摘要：{summary[:50]}...
预计响应：{wait_time}内
━━━━━━━━━━━━━━━━

人工客服会通过电话或短信联系您，请保持手机畅通。
"""


# ============================================================
# 创建客服 Agent
# ============================================================

def create_ecommerce_support_agent():
    """创建电商客服 Agent"""
    
    tools = [
        query_order_status,
        query_refund_policy,
        process_refund_apply,
        query_logistics,
        query_coupons,
        query_product_info,
        escalate_to_human,
    ]
    
    instructions = """
你是一名专业的电商客服助手，服务于一家电子产品商城。

【你的职责】
1. 解答订单、物流、退款、产品咨询等问题
2. 根据用户问题自动调用合适的工具
3. 无法处理时转接人工客服

【工具选择指南】
- 查询订单状态 → query_order_status
- 询问退款政策 → query_refund_policy
- 提交退款申请 → process_refund_apply
- 查询物流轨迹 → query_logistics（需要物流单号）
- 查询优惠券 → query_coupons（需要用户 ID）
- 产品咨询 → query_product_info
- 投诉/复杂问题 → escalate_to_human

【回复规范】
1. 先理解用户意图，再选择工具
2. 如果缺少必要参数（如订单号），先礼貌询问
3. 回复要专业、友好、简洁
4. 使用 emoji 让回复更亲切（📦💰🚚🎫📱👤）
5. 重要信息用【】或 加粗 标记

【边界处理】
- 订单号不存在 → 提示用户确认
- 状态无法识别 → 列出可选状态
- 超出权限 → 转人工客服
"""
    
    agent = Agent(
        model=OpenAIChatCompletionsModel(model="glm-5.1", openai_client=client),
        name="电商客服助手",
        instructions=instructions,
        tools=tools
    )
    
    return agent


# ============================================================
# 测试用例
# ============================================================

TEST_CASES = [
    # 订单查询
    ("帮我查一下订单 ORD20260417001 的状态", "query_order_status"),
    ("ORD20260417002 发货了吗？", "query_order_status"),
    ("订单 ORD99999 存在吗？", "query_order_status"),
    
    # 退款相关
    ("已发货的订单能退款吗？", "query_refund_policy"),
    ("我要申请退款，订单 ORD20260417001，七天无理由", "process_refund_apply"),
    ("退款需要什么条件？", "query_refund_policy"),
    
    # 物流查询
    ("帮我查一下物流 SF1234567890", "query_logistics"),
    ("我的包裹到哪了？物流单号 JD9876543210", "query_logistics"),
    
    # 优惠券
    ("我有哪些优惠券？用户 ID 是 USER001", "query_coupons"),
    ("USER002 的优惠券情况", "query_coupons"),
    
    # 产品咨询
    ("iPhone 的保修政策是什么？", "query_product_info"),
    ("MacBook 有什么特点？", "query_product_info"),
    
    # 转人工
    ("我要投诉！服务态度太差了！", "escalate_to_human"),
    ("这个情况太复杂了，叫人工客服", "escalate_to_human"),
    
    # 边界测试
    ("你好", "闲聊"),
    ("谢谢", "闲聊"),
]


async def run_tests():
    """运行测试集"""
    agent = create_ecommerce_support_agent()
    
    print("=" * 70)
    print("🛍️  电商客服 Agent 测试集")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, (query, expected_tool) in enumerate(TEST_CASES, 1):
        print(f"\n【测试 {i:2d}/{len(TEST_CASES)}】")
        print(f"👤 用户：{query}")
        print(f"🎯 预期：{expected_tool}")
        print("-" * 70)
        
        try:
            result = await Runner.run(agent, query)
            print(f"🤖 客服：{result.final_output[:300]}...")
            
            # 简单判断：有输出就算过
            if result.final_output:
                print("✅ 通过")
                passed += 1
            else:
                print("❌ 无输出")
                failed += 1
                
        except Exception as e:
            print(f"❌ 错误：{e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 测试结果：通过 {passed}/{len(TEST_CASES)}  失败 {failed}/{len(TEST_CASES)}")
    print("=" * 70)


async def interactive_mode():
    """交互模式"""
    agent = create_ecommerce_support_agent()
    
    print("=" * 70)
    print("🛍️  电商客服助手已启动")
    print("💡 输入 'quit' 退出，输入 'test' 运行测试集")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\n👤 您：").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 感谢您的使用，再见！")
                break
            
            if user_input.lower() == 'test':
                await run_tests()
                continue
            
            if not user_input:
                continue
            
            result = await Runner.run(agent, user_input)
            print(f"\n🤖 客服：{result.final_output}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误：{e}")
            logger.exception("详细错误：")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(run_tests())
    else:
        asyncio.run(interactive_mode())
