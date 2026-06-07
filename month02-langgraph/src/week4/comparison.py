"""
Week 4: Workflow vs Agent 对比实验

学习目标：
1. 用相同测试集对比两种模式
2. 量化对比：延迟、token、一致性、准确率
3. 形成选型判断力

实验设计：
- 10 个测试用例（7 个标准 + 3 个模糊）
- 每个用例跑 5 次取平均
- 对比维度：延迟、Token 消耗、LLM 调用次数、响应一致率、意图准确率
"""

import time
import json
import random
from workflow_version import run_single as workflow_run
from agent_version import run_agent as agent_run


# ============================================================
# 测试用例
# ============================================================

TEST_CASES = [
    # 标准意图（关键词明确）
    {"id": 1, "input": "帮我查一下订单 ORD20260417001 的状态", "expected_intent": "order_query", "type": "标准"},
    {"id": 2, "input": "退款需要什么条件？", "expected_intent": "refund", "type": "标准"},
    {"id": 3, "input": "帮我查一下物流 SF1234567890", "expected_intent": "logistics", "type": "标准"},
    {"id": 4, "input": "USER001 有哪些优惠券？", "expected_intent": "coupon", "type": "标准"},
    {"id": 5, "input": "iPhone 15 Pro 多少钱？", "expected_intent": "product", "type": "标准"},
    {"id": 6, "input": "我要投诉！转人工！", "expected_intent": "escalate", "type": "标准"},
    {"id": 7, "input": "你好", "expected_intent": "greeting", "type": "标准"},

    # 模糊意图（Agent 理论上更好）
    {"id": 8, "input": "我的东西什么时候到", "expected_intent": "logistics", "type": "模糊"},
    {"id": 9, "input": "这个手机能退吗", "expected_intent": "refund", "type": "模糊"},
    {"id": 10, "input": "已发货的订单能退款吗？订单 ORD20260417001", "expected_intent": "refund", "type": "混合"},
]

NUM_RUNS = 5  # 每个用例跑 5 次


# ============================================================
# 意图识别准确率检查
# ============================================================

def check_intent_match(response: str, expected: str) -> bool:
    """检查回复是否匹配预期意图"""
    intent_keywords = {
        "order_query": ["订单", "ORD"],
        "refund": ["退款", "退货", "退款政策"],
        "logistics": ["物流", "快递", "包裹", "揽件"],
        "coupon": ["优惠券", "券", "SAVE", "VIP"],
        "product": ["价格", "多少钱", "¥", "保修"],
        "escalate": ["人工客服", "转接", "工单"],
        "greeting": ["您好", "我是智能客服"],
    }
    keywords = intent_keywords.get(expected, [])
    return any(k in response for k in keywords)


# ============================================================
# 运行实验
# ============================================================

def run_experiment():
    results = {
        "workflow": {"cases": [], "summary": {}},
        "agent": {"cases": [], "summary": {}},
    }

    print("=" * 70)
    print("🧪 Workflow vs Agent 对比实验")
    print(f"   测试用例: {len(TEST_CASES)} 个 | 每个跑 {NUM_RUNS} 次")
    print("=" * 70)
    print()

    for tc in TEST_CASES:
        q = tc["input"]
        expected = tc["expected_intent"]
        tc_type = tc["type"]

        print(f"📝 用例 {tc['id']} [{tc_type}]: {q}")

        # --- Workflow 版 ---
        wf_latencies = []
        wf_responses = []
        wf_tokens = []
        wf_nodes = []
        wf_correct = 0

        for _ in range(NUM_RUNS):
            result = workflow_run(q)
            wf_latencies.append(result["metrics"]["latency_ms"])
            wf_tokens.append(result["metrics"]["token_count"])
            wf_nodes.append(result["metrics"]["nodes_visited"])
            wf_responses.append(result["response"])
            if check_intent_match(result["response"], expected):
                wf_correct += 1

        # --- Agent 版 ---
        ag_latencies = []
        ag_responses = []
        ag_tokens = []
        ag_nodes = []
        ag_llm_calls = []
        ag_correct = 0

        for _ in range(NUM_RUNS):
            result = agent_run(q)
            ag_latencies.append(result["metrics"]["latency_ms"])
            ag_tokens.append(result["metrics"]["token_count"])
            ag_nodes.append(result["metrics"]["nodes_visited"])
            ag_llm_calls.append(result["metrics"]["llm_calls"])
            ag_responses.append(result["response"])
            if check_intent_match(result["response"], expected):
                ag_correct += 1

        # 一致性：5 次中有多少次回复相同
        wf_unique = len(set(wf_responses))
        ag_unique = len(set(ag_responses))
        wf_consistency = (NUM_RUNS - wf_unique + 1) / NUM_RUNS * 100
        ag_consistency = (NUM_RUNS - ag_unique + 1) / NUM_RUNS * 100

        # 准确率
        wf_accuracy = wf_correct / NUM_RUNS * 100
        ag_accuracy = ag_correct / NUM_RUNS * 100

        wf_case = {
            "id": tc["id"], "type": tc_type,
            "avg_latency": sum(wf_latencies) / NUM_RUNS,
            "total_tokens": sum(wf_tokens),
            "avg_nodes": sum(wf_nodes) / NUM_RUNS,
            "accuracy": wf_accuracy,
            "consistency": wf_consistency,
        }
        ag_case = {
            "id": tc["id"], "type": tc_type,
            "avg_latency": sum(ag_latencies) / NUM_RUNS,
            "total_tokens": sum(ag_tokens),
            "avg_nodes": sum(ag_nodes) / NUM_RUNS,
            "avg_llm_calls": sum(ag_llm_calls) / NUM_RUNS,
            "accuracy": ag_accuracy,
            "consistency": ag_consistency,
        }

        results["workflow"]["cases"].append(wf_case)
        results["agent"]["cases"].append(ag_case)

        # 打印对比
        print(f"  ┌ Workflow: 延迟={wf_case['avg_latency']:.1f}ms | Token={wf_case['total_tokens']} | "
              f"准确={wf_accuracy:.0f}% | 一致={wf_consistency:.0f}%")
        print(f"  └ Agent:   延迟={ag_case['avg_latency']:.0f}ms | Token={ag_case['total_tokens']} | "
              f"准确={ag_accuracy:.0f}% | 一致={ag_consistency:.0f}% | LLM={ag_case['avg_llm_calls']:.1f}次")
        print()

    # ============================================================
    # 汇总
    # ============================================================

    wf_cases = results["workflow"]["cases"]
    ag_cases = results["agent"]["cases"]

    # 分标准/模糊统计
    for case_type in ["标准", "模糊", "混合"]:
        wf_type = [c for c in wf_cases if c["type"] == case_type]
        ag_type = [c for c in ag_cases if c["type"] == case_type]
        if not wf_type:
            continue

        n = len(wf_type)
        wf_avg_lat = sum(c["avg_latency"] for c in wf_type) / n
        wf_avg_acc = sum(c["accuracy"] for c in wf_type) / n
        wf_avg_con = sum(c["consistency"] for c in wf_type) / n

        ag_avg_lat = sum(c["avg_latency"] for c in ag_type) / n
        ag_avg_acc = sum(c["accuracy"] for c in ag_type) / n
        ag_avg_con = sum(c["consistency"] for c in ag_type) / n
        ag_avg_tok = sum(c["total_tokens"] for c in ag_type) / n
        ag_avg_llm = sum(c["avg_llm_calls"] for c in ag_type) / n

        results["workflow"]["summary"][case_type] = {
            "avg_latency": wf_avg_lat,
            "avg_accuracy": wf_avg_acc,
            "avg_consistency": wf_avg_con,
        }
        results["agent"]["summary"][case_type] = {
            "avg_latency": ag_avg_lat,
            "avg_accuracy": ag_avg_acc,
            "avg_consistency": ag_avg_con,
            "avg_tokens": ag_avg_tok,
            "avg_llm_calls": ag_avg_llm,
        }

    # 打印汇总表
    print("=" * 70)
    print("📊 对比汇总（每类用例的平均值）")
    print("=" * 70)
    print()
    print(f"{'维度':<16} {'Workflow':>12} {'Agent':>12} {'胜出':>8}")
    print("-" * 52)

    for case_type in ["标准", "模糊", "混合"]:
        wf_s = results["workflow"]["summary"].get(case_type, {})
        ag_s = results["agent"]["summary"].get(case_type, {})
        if not wf_s:
            continue

        print(f"\n[{case_type}意图]")
        lat_winner = "✅ WF" if wf_s["avg_latency"] < ag_s["avg_latency"] else "✅ AG"
        acc_winner = "✅ WF" if wf_s["avg_accuracy"] >= ag_s["avg_accuracy"] else "✅ AG"
        con_winner = "✅ WF" if wf_s["avg_consistency"] >= ag_s["avg_consistency"] else "✅ AG"

        print(f"  {'延迟':<14} {wf_s['avg_latency']:>10.1f}ms {ag_s['avg_latency']:>10.0f}ms {lat_winner:>8}")
        print(f"  {'准确率':<14} {wf_s['avg_accuracy']:>9.0f}% {ag_s['avg_accuracy']:>9.0f}% {acc_winner:>8}")
        print(f"  {'一致率':<14} {wf_s['avg_consistency']:>9.0f}% {ag_s['avg_consistency']:>9.0f}% {con_winner:>8}")
        print(f"  {'Token':<14} {'0':>10} {ag_s.get('avg_tokens', 0):>10.0f} {'✅ WF':>8}")
        print(f"  {'LLM调用':<14} {'0':>10} {ag_s.get('avg_llm_calls', 0):>10.1f} {'✅ WF':>8}")

    # 保存结果
    output_file = "comparison_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 详细结果已保存到 {output_file}")

    return results


if __name__ == "__main__":
    run_experiment()
