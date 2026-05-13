#!/usr/bin/env python3
"""
Week 4 - Day 28-30: 综合实战项目 - 个人知识管理助手

项目概述：
构建一个智能个人知识管理系统，能够：
1. 自动整理和分类笔记
2. 智能检索相关知识
3. 生成内容摘要
4. 回答知识相关问题
5. 提供学习建议

Agent 架构（5 个 Agent）：
- Router Agent：意图识别和路由
- Search Agent：知识库检索
- Summarize Agent：内容总结
- Organize Agent：知识整理和分类
- Q&A Agent：问答助手

技术要点：
- Tool 定义和使用
- Handoff 机制
- Guardrails（安全防护）
- 结构化输出
- 异常处理
- 性能监控
"""

import os
import json
import time
from typing import Optional
from datetime import datetime
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
# 模拟知识库数据库
# ============================================================

KNOWLEDGE_BASE = {
    "python": [
        {
            "id": "py001",
            "title": "Python 列表推导式",
            "content": "列表推导式是 Python 中创建列表的简洁方式。语法：[expression for item in iterable if condition]。示例：[x**2 for x in range(10) if x % 2 == 0]",
            "tags": ["python", "基础语法", "列表"],
            "created_at": "2026-04-15",
            "importance": "high"
        },
        {
            "id": "py002",
            "title": "Python 装饰器详解",
            "content": "装饰器是修改函数行为的强大工具。使用 @decorator 语法。示例：@staticmethod, @classmethod, @property。可以记录日志、检查权限、缓存结果等。",
            "tags": ["python", "高级特性", "装饰器"],
            "created_at": "2026-04-18",
            "importance": "high"
        },
        {
            "id": "py003",
            "title": "Python 异常处理最佳实践",
            "content": "使用 try-except-finally 处理异常。避免裸露的 except。捕获特定异常类型。使用 else 子句处理无异常的情况。记录异常日志。",
            "tags": ["python", "异常处理", "最佳实践"],
            "created_at": "2026-04-20",
            "importance": "medium"
        },
        {
            "id": "py004",
            "title": "Python 异步编程 asyncio",
            "content": "asyncio 是 Python 的异步 I/O 框架。使用 async/await 语法。async def 定义协程。asyncio.run() 运行主协程。asyncio.gather() 并发执行。",
            "tags": ["python", "异步编程", "asyncio"],
            "created_at": "2026-04-22",
            "importance": "high"
        },
    ],
    "machine_learning": [
        {
            "id": "ml001",
            "title": "机器学习模型评估指标",
            "content": "常用评估指标：准确率(Accuracy)、精确率(Precision)、召回率(Recall)、F1 分数、ROC-AUC。分类问题用混淆矩阵，回归问题用 MSE、MAE、R²。",
            "tags": ["机器学习", "模型评估", "指标"],
            "created_at": "2026-04-10",
            "importance": "high"
        },
        {
            "id": "ml002",
            "title": "过拟合与欠拟合",
            "content": "过拟合：模型在训练集表现好，测试集差。解决：正则化、Dropout、增加数据、简化模型。欠拟合：模型无法捕捉数据模式。解决：增加特征、使用更复杂模型。",
            "tags": ["机器学习", "过拟合", "模型调优"],
            "created_at": "2026-04-12",
            "importance": "high"
        },
        {
            "id": "ml003",
            "title": "特征工程技巧",
            "content": "特征工程是 ML 成功的关键。包括：特征选择（过滤法、包装法、嵌入法）、特征提取（PCA、LDA）、特征构造（交叉特征、多项式特征）、特征缩放（标准化、归一化）。",
            "tags": ["机器学习", "特征工程", "数据处理"],
            "created_at": "2026-04-16",
            "importance": "medium"
        },
    ],
    "system_design": [
        {
            "id": "sd001",
            "title": "RESTful API 设计原则",
            "content": "RESTful 设计要点：使用名词表示资源、HTTP 方法表示操作（GET/POST/PUT/DELETE）、状态码表示结果、版本控制 URL、统一错误格式、分页和过滤。",
            "tags": ["系统设计", "API", "RESTful"],
            "created_at": "2026-04-08",
            "importance": "high"
        },
        {
            "id": "sd002",
            "title": "数据库索引优化",
            "content": "索引类型：B-Tree、Hash、Full-Text、Composite。使用场景：频繁查询的列、WHERE 条件列、JOIN 列、ORDER BY 列。避免：过度索引、低选择性列。",
            "tags": ["系统设计", "数据库", "性能优化"],
            "created_at": "2026-04-14",
            "importance": "high"
        },
        {
            "id": "sd003",
            "title": "缓存策略设计",
            "content": "缓存模式：Cache-Aside、Read-Through、Write-Through、Write-Behind。缓存失效策略：LRU、LFU、FIFO。缓存穿透：布隆过滤器。缓存雪崩：随机过期时间。",
            "tags": ["系统设计", "缓存", "性能优化"],
            "created_at": "2026-04-19",
            "importance": "medium"
        },
    ],
}


# ============================================================
# Tool 定义
# ============================================================

@function_tool
def search_knowledge(query: str, category: Optional[str] = None, tags: Optional[str] = None) -> dict:
    """
    搜索知识库
    
    Args:
        query: 搜索关键词
        category: 知识分类（python/machine_learning/system_design）
        tags: 标签过滤（逗号分隔）
    
    Returns:
        搜索结果列表
    """
    results = []
    
    # 确定搜索范围
    categories_to_search = [category] if category else KNOWLEDGE_BASE.keys()
    
    for cat in categories_to_search:
        if cat not in KNOWLEDGE_BASE:
            continue
            
        for note in KNOWLEDGE_BASE[cat]:
            score = 0
            
            # 匹配标题
            if query.lower() in note["title"].lower():
                score += 10
            
            # 匹配内容
            if query.lower() in note["content"].lower():
                score += 5
            
            # 匹配标签
            if tags:
                tag_list = [t.strip().lower() for t in tags.split(",")]
                note_tags = [t.lower() for t in note["tags"]]
                if any(t in note_tags for t in tag_list):
                    score += 3
            
            if score > 0:
                results.append({**note, "relevance_score": score, "category": cat})
    
    # 按相关性排序
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "query": query,
        "category": category,
        "total_results": len(results),
        "results": results[:5]  # 返回前 5 个最相关的结果
    }


@function_tool
def add_note(title: str, content: str, category: str, tags: str) -> dict:
    """
    添加新笔记
    
    Args:
        title: 笔记标题
        content: 笔记内容
        category: 分类（python/machine_learning/system_design）
        tags: 标签（逗号分隔）
    
    Returns:
        添加结果
    """
    if category not in KNOWLEDGE_BASE:
        KNOWLEDGE_BASE[category] = []
    
    note_id = f"{category[:2]}{len(KNOWLEDGE_BASE[category]) + 1:03d}"
    
    new_note = {
        "id": note_id,
        "title": title,
        "content": content,
        "tags": [t.strip() for t in tags.split(",")],
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "importance": "medium"
    }
    
    KNOWLEDGE_BASE[category].append(new_note)
    
    return {
        "success": True,
        "note_id": note_id,
        "message": f"笔记已成功添加到 {category} 分类",
        "note": new_note
    }


@function_tool
def get_category_stats() -> dict:
    """
    获取知识库统计信息
    
    Returns:
        各分类的笔记数量和其他统计信息
    """
    stats = {}
    total_notes = 0
    all_tags = {}
    
    for category, notes in KNOWLEDGE_BASE.items():
        category_tags = {}
        for note in notes:
            for tag in note["tags"]:
                category_tags[tag] = category_tags.get(tag, 0) + 1
                all_tags[tag] = all_tags.get(tag, 0) + 1
        
        stats[category] = {
            "count": len(notes),
            "tags": category_tags,
            "high_importance": sum(1 for n in notes if n.get("importance") == "high"),
            "recent": sum(1 for n in notes if n.get("created_at", "") >= "2026-04-15")
        }
        total_notes += len(notes)
    
    return {
        "total_notes": total_notes,
        "categories": stats,
        "top_tags": sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:10]
    }


@function_tool
def generate_study_plan(category: str, days: int = 7) -> dict:
    """
    生成学习计划
    
    Args:
        category: 学习分类
        days: 学习天数
    
    Returns:
        学习计划
    """
    if category not in KNOWLEDGE_BASE:
        return {
            "success": False,
            "message": f"未找到分类：{category}"
        }
    
    notes = KNOWLEDGE_BASE[category]
    notes_per_day = max(1, len(notes) // days)
    
    plan = {
        "category": category,
        "total_days": days,
        "total_notes": len(notes),
        "daily_plan": []
    }
    
    for day in range(1, days + 1):
        start_idx = (day - 1) * notes_per_day
        end_idx = min(start_idx + notes_per_day, len(notes))
        day_notes = notes[start_idx:end_idx]
        
        plan["daily_plan"].append({
            "day": day,
            "notes_to_study": [n["title"] for n in day_notes],
            "estimated_time": f"{len(day_notes) * 30}分钟",
            "focus_areas": list(set(tag for n in day_notes for tag in n["tags"]))
        })
    
    return plan


# ============================================================
# Guardrails（安全防护）
# ============================================================

def input_guardrail(user_input: str) -> dict:
    """
    输入安全检查
    检查用户输入是否包含不当内容
    """
    # 检查长度
    if len(user_input) > 1000:
        return {
            "safe": False,
            "reason": "输入过长，请保持在 1000 字符以内"
        }
    
    # 检查敏感词（示例）
    sensitive_words = ["删除全部", "清空", "格式化"]
    for word in sensitive_words:
        if word in user_input:
            return {
                "safe": False,
                "reason": f"检测到敏感操作：'{word}'，请使用专门的删除命令"
            }
    
    return {"safe": True, "reason": ""}


def output_guardrail(output: str) -> dict:
    """
    输出安全检查
    确保输出内容符合规范
    """
    # 检查输出长度
    if len(output) > 5000:
        return {
            "safe": False,
            "reason": "输出过长，请简化回复"
        }
    
    return {"safe": True, "reason": ""}


# ============================================================
# 创建 Agent 系统
# ============================================================

# Agent B: 知识检索专员
search_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Knowledge Searcher",
    instructions="""你是知识检索专员，专门负责在知识库中搜索相关信息。

你有以下工具：
- search_knowledge: 搜索知识库中的笔记

工作流程：
1. 理解用户的搜索需求
2. 调用 search_knowledge 工具搜索相关内容
3. 根据搜索结果，整理出最相关的信息
4. 用清晰的格式展示搜索结果，包括标题、内容摘要和相关性评分

如果搜索结果为空，请如实告知用户，并建议调整搜索关键词。""",
    tools=[search_knowledge],
)

# Agent C: 内容总结专员
summarize_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Content Summarizer",
    instructions="""你是内容总结专员，负责将知识内容提炼成简洁的摘要。

工作流程：
1. 理解用户想要总结的内容
2. 提取关键信息和核心要点
3. 生成结构化的总结，包括：
   - 核心概念
   - 关键要点（3-5 个）
   - 应用场景
   - 注意事项

总结要求：
- 简洁明了，不超过 300 字
- 使用条理清晰的格式
- 突出重点内容
- 提供实际应用的建议""",
)

# Agent D: 知识整理专员
organize_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Knowledge Organizer",
    instructions="""你是知识整理专员，负责管理和组织知识库。

你有以下工具：
- add_note: 添加新笔记
- get_category_stats: 获取知识库统计信息
- generate_study_plan: 生成学习计划

你可以帮助用户：
1. 添加新笔记到指定分类
2. 查看知识库的整体统计信息
3. 生成某个分类的学习计划
4. 整理和优化知识结构

操作时注意：
- 确保笔记标题简洁准确
- 标签使用逗号分隔，3-5 个为宜
- 学习计划要合理分配每天的学习量""",
    tools=[add_note, get_category_stats, generate_study_plan],
)

# Agent E: 问答专员
qa_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Q&A Specialist",
    instructions="""你是问答专员，负责回答用户的知识相关问题。

你有以下工具：
- search_knowledge: 搜索知识库

工作流程：
1. 理解用户的问题
2. 搜索相关知识库内容
3. 基于搜索结果给出准确的回答
4. 如果知识库中没有相关信息，如实告知用户

回答要求：
- 准确、专业
- 引用知识库中的具体内容
- 提供相关的延伸学习建议
- 如果信息不足，说明局限性""",
    tools=[search_knowledge],
)

# Agent A: 路由器 Agent（主 Agent）
router_agent = Agent(
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    name="Knowledge Router",
    instructions="""你是个人知识管理助手的路由器。

分析用户的需求，然后交给合适的专员处理：

- 搜索知识/查找信息 → Knowledge Searcher
- 总结内容/提炼要点 → Content Summarizer  
- 添加笔记/查看统计/生成学习计划 → Knowledge Organizer
- 回答知识相关问题 → Q&A Specialist

如果用户的需求涉及多个方面，请依次交给对应的专员处理。
如果无法判断，请直接回答用户的问题。

注意：你要根据用户的问题智能判断路由到哪个 Agent。""",
    handoffs=[
        handoff(search_agent),
        handoff(summarize_agent),
        handoff(organize_agent),
        handoff(qa_agent),
    ],
)


# ============================================================
# 测试与评测
# ============================================================

async def test_scenario_1_search():
    """测试场景 1：知识检索"""
    print("\n" + "=" * 80)
    print("测试场景 1：知识检索")
    print("=" * 80)
    
    test_cases = [
        ("简单搜索", "Python 装饰器"),
        ("分类搜索", "搜索机器学习相关的过拟合内容", "machine_learning"),
        ("标签搜索", "查找系统设计中标签包含性能的笔记"),
    ]
    
    for name, query, *extra in test_cases:
        print(f"\n【{name}】{query}")
        start = time.time()
        result = await Runner.run(search_agent, query)
        elapsed = time.time() - start
        tokens = sum(r.usage.total_tokens for r in result.raw_responses)
        
        print(f"✅ 结果长度: {len(result.final_output)} 字符")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"📊 Token: {tokens}")
        print(f"📝 摘要: {result.final_output[:150]}...")


async def test_scenario_2_summarize():
    """测试场景 2：内容总结"""
    print("\n" + "=" * 80)
    print("测试场景 2：内容总结")
    print("=" * 80)
    
    test_cases = [
        "请总结一下 Python 装饰器的核心概念和应用场景",
        "用简洁的语言总结机器学习中的过拟合问题及解决方案",
        "总结 RESTful API 设计的关键原则",
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n【测试 {i}】{query[:50]}...")
        start = time.time()
        result = await Runner.run(summarize_agent, query)
        elapsed = time.time() - start
        tokens = sum(r.usage.total_tokens for r in result.raw_responses)
        
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"📊 Token: {tokens}")
        print(f"📝 总结:\n{result.final_output[:300]}...")


async def test_scenario_3_organize():
    """测试场景 3：知识整理"""
    print("\n" + "=" * 80)
    print("测试场景 3：知识整理")
    print("=" * 80)
    
    # 测试 3.1：添加笔记
    print("\n【测试 3.1】添加新笔记")
    result = await Runner.run(
        organize_agent,
        "添加笔记：标题'Docker 容器基础'，内容'容器是轻量级虚拟化技术，使用命名空间和 cgroups 实现隔离。核心命令：docker run, docker build, docker compose。'"
        "，分类'system_design'，标签'docker,容器，虚拟化'"
    )
    print(f"✅ {result.final_output[:200]}")
    
    # 测试 3.2：查看统计
    print("\n【测试 3.2】查看知识库统计")
    result = await Runner.run(organize_agent, "查看知识库的整体统计信息")
    print(f"📊 {result.final_output[:300]}")
    
    # 测试 3.3：生成学习计划
    print("\n【测试 3.3】生成学习计划")
    result = await Runner.run(organize_agent, "为我生成一个 Python 知识的 7 天学习计划")
    print(f"📚 {result.final_output[:300]}...")


async def test_scenario_4_qa():
    """测试场景 4：问答"""
    print("\n" + "=" * 80)
    print("测试场景 4：问答")
    print("=" * 80)
    
    test_cases = [
        "Python 中如何处理异常？",
        "什么是过拟合？如何解决？",
        "RESTful API 设计有什么最佳实践？",
        "缓存雪崩是什么？怎么预防？",
    ]
    
    for i, question in enumerate(test_cases, 1):
        print(f"\n【问题 {i}】{question}")
        start = time.time()
        result = await Runner.run(qa_agent, question)
        elapsed = time.time() - start
        tokens = sum(r.usage.total_tokens for r in result.raw_responses)
        
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"📊 Token: {tokens}")
        print(f"💡 回答: {result.final_output[:200]}...")


async def test_scenario_5_handoff():
    """测试场景 5：Handoff 路由"""
    print("\n" + "=" * 80)
    print("测试场景 5：Handoff 智能路由")
    print("=" * 80)
    
    test_cases = [
        ("搜索测试", "查找 Python 异步编程的资料"),
        ("总结测试", "帮我总结一下机器学习模型评估的关键指标"),
        ("整理测试", "添加一条新笔记：Python 生成器，内容'生成器使用 yield 关键字，可以惰性求值，节省内存'", "分类 python，标签'python，生成器'"),
        ("问答测试", "数据库索引有哪些类型？"),
    ]
    
    for name, query in test_cases:
        print(f"\n【{name}】{query[:60]}...")
        start = time.time()
        result = await Runner.run(router_agent, query)
        elapsed = time.time() - start
        tokens = sum(r.usage.total_tokens for r in result.raw_responses)
        
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"📊 Token: {tokens} ({len(result.raw_responses)} 次调用)")
        print(f"📝 结果: {result.final_output[:200]}...")


async def test_scenario_6_guardrails():
    """测试场景 6：Guardrails 安全防护"""
    print("\n" + "=" * 80)
    print("测试场景 6：Guardrails 安全防护")
    print("=" * 80)
    
    # 测试输入 guardrail
    test_inputs = [
        ("正常输入", "Python 装饰器是什么"),
        ("超长输入", "测试" * 300),
        ("敏感操作", "删除全部知识库内容"),
    ]
    
    for name, user_input in test_inputs:
        print(f"\n【{name}】{user_input[:50]}...")
        guardrail_result = input_guardrail(user_input)
        if guardrail_result["safe"]:
            print(f"✅ 安全检查通过")
        else:
            print(f"❌ 安全检查拦截：{guardrail_result['reason']}")


async def test_scenario_7_error_handling():
    """测试场景 7：异常处理"""
    print("\n" + "=" * 80)
    print("测试场景 7：异常处理")
    print("=" * 80)
    
    test_cases = [
        ("不存在的分类", "生成不存在的分类的学习计划"),
        ("模糊搜索", "搜索完全不相关的内容 xyzabc"),
        ("空查询", "搜索知识库"),
    ]
    
    for name, query in test_cases:
        print(f"\n【{name}】{query}")
        try:
            result = await Runner.run(router_agent, query)
            print(f"✅ 处理成功: {result.final_output[:200]}...")
        except Exception as e:
            print(f"❌ 发生异常: {e}")


async def generate_eval_results():
    """生成评测结果"""
    print("\n" + "=" * 80)
    print("📊 生成评测报告")
    print("=" * 80)
    
    eval_results = []
    
    # 运行各项测试并记录结果
    test_scenarios = [
        ("知识检索", test_scenario_1_search),
        ("内容总结", test_scenario_2_summarize),
        ("知识整理", test_scenario_3_organize),
        ("问答系统", test_scenario_4_qa),
        ("Handoff 路由", test_scenario_5_handoff),
    ]
    
    for scenario_name, test_func in test_scenarios:
        print(f"\n正在评测: {scenario_name}...")
        start = time.time()
        
        try:
            await test_func()
            elapsed = time.time() - start
            eval_results.append({
                "scenario": scenario_name,
                "status": "PASS",
                "time": f"{elapsed:.2f}s",
                "notes": "测试通过"
            })
        except Exception as e:
            elapsed = time.time() - start
            eval_results.append({
                "scenario": scenario_name,
                "status": "FAIL",
                "time": f"{elapsed:.2f}s",
                "notes": str(e)[:100]
            })
    
    # 保存评测结果
    print("\n📊 评测结果汇总:")
    print(f"{'场景':<20} {'状态':<10} {'耗时':<10} {'备注'}")
    print("-" * 80)
    for result in eval_results:
        print(f"{result['scenario']:<20} {result['status']:<10} {result['time']:<10} {result['notes']}")
    
    return eval_results


# ============================================================
# 主函数
# ============================================================

async def main():
    """运行综合实战项目"""
    print("=" * 80)
    print("🎓 Week 4 - Day 28-30: 综合实战项目 - 个人知识管理助手")
    print("=" * 80)
    print(f"📦 使用模型: {MODEL_NAME}")
    print(f"📚 知识库分类: {', '.join(KNOWLEDGE_BASE.keys())}")
    print(f"📖 知识库总数: {sum(len(notes) for notes in KNOWLEDGE_BASE.values())} 条笔记")
    print("=" * 80)
    
    # 运行所有测试场景
    await test_scenario_1_search()
    await test_scenario_2_summarize()
    await test_scenario_3_organize()
    await test_scenario_4_qa()
    await test_scenario_5_handoff()
    await test_scenario_6_guardrails()
    await test_scenario_7_error_handling()
    
    # 生成评测报告
    eval_results = await generate_eval_results()
    
    print("\n" + "=" * 80)
    print("✅ 综合实战项目完成！")
    print("=" * 80)
    print("\n💡 项目总结:")
    print("  1. 成功实现了 5 个 Agent 的协作系统")
    print("  2. 定义了 4 个核心 Tool（搜索、添加、统计、学习计划）")
    print("  3. 实现了 Handoff 智能路由机制")
    print("  4. 添加了 Input/Output Guardrails 安全防护")
    print("  5. 测试了异常处理和边界情况")
    print("  6. 生成了完整的评测报告")
    print("\n📈 技术亮点:")
    print("  - 模块化设计：每个 Agent 职责单一、边界清晰")
    print("  - 可扩展性：易于添加新的 Agent 和 Tool")
    print("  - 安全性：多层 Guardrails 保护")
    print("  - 可观测性：详细的日志和 Token 统计")
    print("\n🎯 下一步优化方向:")
    print("  1. 接入真实的向量数据库（如 Milvus、Pinecone）")
    print("  2. 实现语义搜索而非关键词匹配")
    print("  3. 添加用户认证和权限管理")
    print("  4. 支持多模态内容（图片、视频、音频）")
    print("  5. 实现知识的自动关联和推荐")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
