#!/usr/bin/env python3
"""
Week 3 - Day 15-16：连续测试与对比

目标：
1. 用同样的 10 个问题连续跑 5 次
2. 对比每次的输出是否一致
3. 记录不一致的情况并分析原因

输出：
- results/consistency_run_{timestamp}.csv
- results/consistency_analysis.md
"""

import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加父目录到路径，以便导入 week2 的 agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from week2.ecommerce_support_agent import create_ecommerce_support_agent
from agents import Runner


# 精选 10 个测试问题（覆盖所有 tool）
TEST_QUESTIONS = [
    # 订单查询 (2 个)
    "帮我查一下订单 ORD20260417001 的状态",
    "ORD20260417002 发货了吗？",
    
    # 退款政策 (2 个)
    "已发货的订单能退款吗？",
    "退款需要什么条件？",
    
    # 退款申请 (1 个)
    "我要申请退款，订单 ORD20260417001，七天无理由",
    
    # 物流查询 (2 个)
    "帮我查一下物流 SF1234567890",
    "我的包裹到哪了？物流单号 JD9876543210",
    
    # 优惠券 (1 个)
    "我有哪些优惠券？用户 ID 是 USER001",
    
    # 产品咨询 (1 个)
    "iPhone 的保修政策是什么？",
    
    # 转人工 (1 个)
    "我要投诉！服务态度太差了！",
]


def extract_tool_call(output: str) -> str:
    """从输出中提取调用的 tool 名称（简化版）"""
    # 这里只是简单判断，实际应该分析 trace
    if "📦 订单详情" in output:
        return "query_order_status"
    elif "💰 退款政策" in output:
        return "query_refund_policy"
    elif "✅ 退款申请已提交" in output:
        return "process_refund_apply"
    elif "🚚 物流轨迹" in output:
        return "query_logistics"
    elif "🎫 优惠券" in output:
        return "query_coupons"
    elif "📱 产品信息" in output:
        return "query_product_info"
    elif "👤 已转接人工客服" in output:
        return "escalate_to_human"
    elif "❌" in output or "✅" in output:
        return "direct_response"
    else:
        return "unknown"


async def run_consistency_test():
    """运行一致性测试"""
    agent = create_ecommerce_support_agent()
    
    # 创建结果目录
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = results_dir / f"consistency_run_{timestamp}.csv"
    
    print("=" * 80)
    print("🧪 Week 3 - Day 15-16：连续测试与对比")
    print("=" * 80)
    print(f"\n📝 测试问题数：{len(TEST_QUESTIONS)}")
    print(f"🔄 运行次数：5 次")
    print(f"📊 结果文件：{csv_path}")
    print("=" * 80)
    
    # 存储所有运行结果
    # 结构：{question: [output1, output2, output3, output4, output5]}
    all_results = {q: [] for q in TEST_QUESTIONS}
    
    # 运行 5 次
    for run_idx in range(1, 6):
        print(f"\n{'='*80}")
        print(f"🚀 第 {run_idx} 次运行")
        print(f"{'='*80}")
        
        for q_idx, question in enumerate(TEST_QUESTIONS, 1):
            print(f"\n[{q_idx}/{len(TEST_QUESTIONS)}] {question[:50]}...")
            
            try:
                result = await Runner.run(agent, question)
                output = result.final_output
                tool_called = extract_tool_call(output)
                
                all_results[question].append({
                    "output": output,
                    "tool": tool_called,
                    "tokens": result.usage.total_tokens if hasattr(result, 'usage') else 0
                })
                
                print(f"  ✅ Tool: {tool_called}, Tokens: {result.usage.total_tokens if hasattr(result, 'usage') else 'N/A'}")
                
            except Exception as e:
                print(f"  ❌ 错误：{e}")
                all_results[question].append({
                    "output": f"ERROR: {e}",
                    "tool": "error",
                    "tokens": 0
                })
    
    # 写入 CSV
    print(f"\n{'='*80}")
    print("📝 写入 CSV 文件...")
    print(f"{'='*80}")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "question", "run_index", "tool_called", "total_tokens", 
            "output_preview", "is_consistent"
        ])
        
        for question in TEST_QUESTIONS:
            results = all_results[question]
            # 判断是否一致（所有 tool 调用相同）
            tools = [r["tool"] for r in results]
            is_consistent = len(set(tools)) == 1
            
            for i, r in enumerate(results, 1):
                output_preview = r["output"][:200].replace('\n', ' ')
                writer.writerow([
                    question,
                    i,
                    r["tool"],
                    r["tokens"],
                    output_preview,
                    "✅" if is_consistent else "❌"
                ])
    
    # 生成分析报告
    analysis_path = results_dir / f"consistency_analysis_{timestamp}.md"
    
    print(f"\n{'='*80}")
    print("📊 生成分析报告...")
    print(f"{'='*80}")
    
    # 统计一致性
    consistent_count = 0
    inconsistent_questions = []
    
    for question in TEST_QUESTIONS:
        results = all_results[question]
        tools = [r["tool"] for r in results]
        if len(set(tools)) == 1:
            consistent_count += 1
        else:
            inconsistent_questions.append({
                "question": question,
                "tools": tools,
                "results": results
            })
    
    consistency_rate = (consistent_count / len(TEST_QUESTIONS)) * 100
    
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write(f"# 一致性测试分析报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**测试问题数**: {len(TEST_QUESTIONS)}\n")
        f.write(f"**运行次数**: 5 次\n\n")
        
        f.write(f"## 📊 总体统计\n\n")
        f.write(f"- **一致的问题数**: {consistent_count}/{len(TEST_QUESTIONS)}\n")
        f.write(f"- **不一致的问题数**: {len(inconsistent_questions)}\n")
        f.write(f"- **一致率**: {consistency_rate:.1f}%\n\n")
        
        if inconsistent_questions:
            f.write(f"## ❌ 不一致的问题详情\n\n")
            
            for item in inconsistent_questions:
                f.write(f"### 问题：{item['question']}\n\n")
                f.write(f"**5 次运行的 tool 调用**:\n")
                for i, tool in enumerate(item['tools'], 1):
                    f.write(f"- Run {i}: `{tool}`\n")
                f.write(f"\n**可能原因**:\n")
                f.write(f"- 模型随机性导致意图理解不同\n")
                f.write(f"- instructions 不够清晰\n")
                f.write(f"- tool 描述存在歧义\n\n")
        else:
            f.write(f"## ✅ 所有问题表现一致！\n\n")
            f.write(f"这是一个好迹象，说明 agent 的行为稳定。\n\n")
        
        f.write(f"## 💡 下一步建议\n\n")
        f.write(f"1. 如果不一致率 > 20%，需要优化 instructions\n")
        f.write(f"2. 检查不一致的问题，分析是 prompt 问题还是 schema 问题\n")
        f.write(f"3. 继续 Day 17-18：Token Usage 日志分析\n")
    
    print(f"\n{'='*80}")
    print("✅ 测试完成！")
    print(f"{'='*80}")
    print(f"\n📁 CSV 结果：{csv_path}")
    print(f"📄 分析报告：{analysis_path}")
    print(f"\n📊 一致率：{consistency_rate:.1f}% ({consistent_count}/{len(TEST_QUESTIONS)})")
    
    if inconsistent_questions:
        print(f"\n⚠️  发现 {len(inconsistent_questions)} 个不一致的问题，请查看分析报告")
    else:
        print(f"\n🎉 所有问题表现一致！")


async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 快速测试：只跑 2 次
        print("⚡ 快速测试模式（只跑 2 次）")
        global TEST_QUESTIONS
        # 这里可以缩减问题数量，但为了简单先不处理
        await run_consistency_test()
    else:
        await run_consistency_test()


if __name__ == "__main__":
    asyncio.run(main())
