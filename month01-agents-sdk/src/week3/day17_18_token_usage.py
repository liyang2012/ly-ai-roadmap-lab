#!/usr/bin/env python3
"""
Week 3 - Day 17-18: Token Usage 日志分析

目标：
1. 记录 10 次调用的 token 消耗
2. 分析哪个问题最费 token
3. 理解 prompt_tokens vs completion_tokens 的关系

输出：
- results/usage_log.csv
- results/usage_analysis.md
"""

import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from week2.ecommerce_support_agent import create_ecommerce_support_agent
from agents import Runner


# 10 个测试问题（覆盖所有 tool）
TEST_QUESTIONS = [
    "帮我查一下订单 ORD20260417001 的状态",
    "ORD20260417002 发货了吗？",
    "已发货的订单能退款吗？",
    "退款需要什么条件？",
    "我要申请退款，订单 ORD20260417001，七天无理由",
    "帮我查一下物流 SF1234567890",
    "我的包裹到哪了？物流单号 JD9876543210",
    "我有哪些优惠券？用户 ID 是 USER001",
    "iPhone 的保修政策是什么？",
    "我要投诉！服务态度太差了！",
]


async def run_token_usage_analysis():
    """运行 Token Usage 分析"""
    agent = create_ecommerce_support_agent()
    
    # 创建结果目录
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = results_dir / f"usage_log_{timestamp}.csv"
    
    print("=" * 80)
    print("📊 Week 3 - Day 17-18: Token Usage 日志分析")
    print("=" * 80)
    print(f"\n📝 测试问题数：{len(TEST_QUESTIONS)}")
    print(f"📁 结果文件：{csv_path}")
    print("=" * 80)
    
    # 存储所有结果
    all_results = []
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(TEST_QUESTIONS)}] {question[:50]}...")
        
        try:
            result = await Runner.run(agent, question)
            
            # 提取 token usage（从 raw_responses 中汇总）
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_all_tokens = 0
            
            for response in result.raw_responses:
                usage = response.usage
                total_prompt_tokens += usage.input_tokens if hasattr(usage, 'input_tokens') else 0
                total_completion_tokens += usage.output_tokens if hasattr(usage, 'output_tokens') else 0
                total_all_tokens += usage.total_tokens if hasattr(usage, 'total_tokens') else 0
            
            all_results.append({
                "id": i,
                "question": question,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_all_tokens,
                "ratio": f"{total_completion_tokens/total_prompt_tokens:.2f}" if total_prompt_tokens > 0 else "N/A"
            })
            
            print(f"  Prompt: {total_prompt_tokens:4d} | Completion: {total_completion_tokens:4d} | Total: {total_all_tokens:4d} | Ratio: {total_completion_tokens/total_prompt_tokens:.2f}" if total_prompt_tokens > 0 else "  N/A")
            
        except Exception as e:
            print(f"  ❌ 错误：{e}")
            all_results.append({
                "id": i,
                "question": question,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "ratio": "ERROR"
            })
    
    # 写入 CSV
    print(f"\n{'='*80}")
    print("📝 写入 CSV 文件...")
    print(f"{'='*80}")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "question", "prompt_tokens", "completion_tokens", "total_tokens", "ratio"])
        writer.writeheader()
        writer.writerows(all_results)
    
    # 生成分析报告
    analysis_path = results_dir / f"usage_analysis_{timestamp}.md"
    
    # 统计分析
    total_prompt = sum(r["prompt_tokens"] for r in all_results)
    total_completion = sum(r["completion_tokens"] for r in all_results)
    total_all = sum(r["total_tokens"] for r in all_results)
    avg_total = total_all / len(all_results) if all_results else 0
    
    # 找出最费 token 的问题
    max_token_question = max(all_results, key=lambda x: x["total_tokens"])
    min_token_question = min(all_results, key=lambda x: x["total_tokens"])
    
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write(f"# Token Usage 分析报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"## 📊 总体统计\n\n")
        f.write(f"- **测试问题数**: {len(TEST_QUESTIONS)}\n")
        f.write(f"- **总 Prompt Tokens**: {total_prompt}\n")
        f.write(f"- **总 Completion Tokens**: {total_completion}\n")
        f.write(f"- **总消耗 Tokens**: {total_all}\n")
        f.write(f"- **平均每题消耗**: {avg_total:.1f} tokens\n\n")
        
        f.write(f"## 🔍 极值分析\n\n")
        f.write(f"### 最费 Token 的问题\n\n")
        f.write(f"**问题**: {max_token_question['question']}\n")
        f.write(f"- Prompt: {max_token_question['prompt_tokens']} tokens\n")
        f.write(f"- Completion: {max_token_question['completion_tokens']} tokens\n")
        f.write(f"- Total: {max_token_question['total_tokens']} tokens\n\n")
        
        f.write(f"### 最省 Token 的问题\n\n")
        f.write(f"**问题**: {min_token_question['question']}\n")
        f.write(f"- Prompt: {min_token_question['prompt_tokens']} tokens\n")
        f.write(f"- Completion: {min_token_question['completion_tokens']} tokens\n")
        f.write(f"- Total: {min_token_question['total_tokens']} tokens\n\n")
        
        f.write(f"## 📋 详细数据\n\n")
        f.write(f"| ID | 问题 | Prompt | Completion | Total | Ratio |\n")
        f.write(f"|----|------|--------|------------|-------|-------|\n")
        for r in all_results:
            f.write(f"| {r['id']} | {r['question'][:20]}... | {r['prompt_tokens']} | {r['completion_tokens']} | {r['total_tokens']} | {r['ratio']} |\n")
        
        f.write(f"\n## 💡 优化建议\n\n")
        f.write(f"1. **减少 Prompt Tokens**:\n")
        f.write(f"   - 精简 instructions，去除冗余描述\n")
        f.write(f"   - 优化 tool 描述，使其更简洁清晰\n\n")
        
        f.write(f"2. **控制 Completion Tokens**:\n")
        f.write(f"   - 设置 max_tokens 限制\n")
        f.write(f"   - 在 instructions 中要求简洁回复\n\n")
        
        f.write(f"3. **性价比优化**:\n")
        f.write(f"   - Ratio > 1.0 说明回复较长，可能需要精简\n")
        f.write(f"   - Ratio < 0.5 说明回复简短，可能是好现象\n")
    
    print(f"\n{'='*80}")
    print("✅ 分析完成！")
    print(f"{'='*80}")
    print(f"\n📁 CSV 结果：{csv_path}")
    print(f"📄 分析报告：{analysis_path}")
    print(f"\n📊 统计摘要:")
    print(f"  总消耗：{total_all} tokens")
    print(f"  平均每题：{avg_total:.1f} tokens")
    print(f"  最费 Token: {max_token_question['question'][:30]}... ({max_token_question['total_tokens']} tokens)")


if __name__ == "__main__":
    asyncio.run(run_token_usage_analysis())
