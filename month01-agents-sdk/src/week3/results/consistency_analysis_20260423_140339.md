# 一致性测试分析报告

**测试时间**: 2026-04-23 14:11:07

**测试问题数**: 10
**运行次数**: 5 次

## 📊 总体统计

- **一致的问题数**: 7/10
- **不一致的问题数**: 3
- **一致率**: 70.0%

## ❌ 不一致的问题详情

### 问题：帮我查一下订单 ORD20260417001 的状态

**5 次运行的 tool 调用**:
- Run 1: `unknown`
- Run 2: `direct_response`
- Run 3: `direct_response`
- Run 4: `direct_response`
- Run 5: `direct_response`

**可能原因**:
- 模型随机性导致意图理解不同
- instructions 不够清晰
- tool 描述存在歧义

### 问题：退款需要什么条件？

**5 次运行的 tool 调用**:
- Run 1: `direct_response`
- Run 2: `unknown`
- Run 3: `direct_response`
- Run 4: `query_refund_policy`
- Run 5: `unknown`

**可能原因**:
- 模型随机性导致意图理解不同
- instructions 不够清晰
- tool 描述存在歧义

### 问题：我要投诉！服务态度太差了！

**5 次运行的 tool 调用**:
- Run 1: `direct_response`
- Run 2: `unknown`
- Run 3: `unknown`
- Run 4: `unknown`
- Run 5: `unknown`

**可能原因**:
- 模型随机性导致意图理解不同
- instructions 不够清晰
- tool 描述存在歧义

## 💡 下一步建议

1. 如果不一致率 > 20%，需要优化 instructions
2. 检查不一致的问题，分析是 prompt 问题还是 schema 问题
3. 继续 Day 17-18：Token Usage 日志分析
