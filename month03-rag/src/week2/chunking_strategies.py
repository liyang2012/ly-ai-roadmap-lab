"""
Day 3-5: 分块策略对比 — 固定长度 / 递归分块 / 语义分块

目标：掌握不同的分块策略及其适用场景

=== 分块为什么重要 ===

分块 (Chunking) 是 RAG Pipeline 中最关键的步骤之一。

如果分块太短：
- 丢失上下文（每个块信息不完整）
- 语义碎片化

如果分块太长：
- 一个块包含多个主题 → 检索不精确
- LLM 上下文窗口压力大
- 超出 Embedding 模型的最大输入长度

=== 三种核心策略 ===

1. 固定长度分块 (FixedSizeChunking)
   - 最简单：按字符或 token 数切分
   - 问题：可能切在句子中间
   - 适用：代码、结构化数据、不需要语义完整性的场景

2. 递归分块 (RecursiveCharacterTextSplitter) ← LangChain 推荐
   - 按分隔符优先级递归切分（\n\n → \n → 空格 → 字符）
   - 尽可能保持段落和句子的完整性
   - 适用：通用文本，大多数 RAG 场景

3. 语义分块 (Semantic Chunking) — 进阶
   - 用 Embedding 检测"语义边界"（主题转换点）
   - 效果最好，但计算开销最大
   - 适用：长文档（书籍、研究报告），对精度要求高的场景

=== 分块参数 ===

- chunk_size: 每个块的目标大小（字符数或 token 数）
- chunk_overlap: 块之间的重叠部分
  - 为什么要重叠？避免一个话题被切在边界上
  - 经验值：chunk_size 的 10-20%
  - 例子：chunk_size=500, overlap=50

=== 运行方式 ===
    python chunking_strategies.py          # 自动演示
    python chunking_strategies.py --demo   # 详细演示
"""

import os
import sys
import textwrap

# LangChain Text Splitters
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,     # 递归分块（推荐）
    CharacterTextSplitter,              # 固定长度分块
    MarkdownHeaderTextSplitter,         # Markdown 标题分块
)
from langchain_core.documents import Document


# ============================================================
# Part 1: 测试文本
# ============================================================

# 模拟一个较长的文档（产品手册）
LONG_DOCUMENT = """智能家居系统使用手册

第一章：系统概述

欢迎使用智能家居系统。本系统可以帮助您远程控制家中的灯光、
空调、窗帘等设备，让您的生活更加便捷。

1.1 系统组成
本系统由以下部件组成：智能网关、智能开关、温湿度传感器、
窗帘电机、红外遥控器。所有设备通过 Zigbee 协议连接。

1.2 系统要求
使用本系统需要以下条件：
- 稳定的 Wi-Fi 网络（2.4GHz）
- 智能手机（iOS 14+ 或 Android 10+）
- 系统 App（可从应用商店下载）

第二章：安装指南

2.1 智能网关安装
1. 将网关连接到路由器
2. 等待指示灯变为常亮（约 30 秒）
3. 打开 App 扫描二维码添加网关
4. 等待固件更新完成

2.2 传感器配对
1. 进入网关管理页面
2. 点击"添加设备"
3. 长按传感器按钮 3 秒
4. 等待听到"嘀"的一声
5. App 中确认添加

2.3 设备安装位置注意事项
- 温湿度传感器：避免阳光直射，离地 1.2-1.5 米
- 红外遥控器：安装在视野开阔处，与空调直线距离 < 8 米
- 窗帘电机：需要预留电源插座和窗帘导轨

第三章：日常使用

3.1 场景模式
系统支持以下场景模式：
- 回家模式：自动开灯、开空调、拉窗帘
- 离家模式：关闭所有设备、启动安防模式
- 睡眠模式：关灯、关窗帘、设置空调温度
- 自定义场景：用户自行组合

3.2 定时任务
您可以设置以下定时任务：
- 每天早上 7:00 自动拉开窗帘
- 每天晚上 22:00 自动关灯
- 离家后自动关闭空调

第四章：故障排除

4.1 设备离线
- 检查电源是否正常
- 检查距离是否在有效范围（室内 30 米）
- 重启网关后重新配对

4.2 App 连接失败
- 检查手机是否在同一 Wi-Fi 网络
- 重启 App
- 卸载重装 App 后重新登录

4.3 传感器数据不准
- 检查传感器是否在正确位置
- 清洁传感器表面灰尘
- 恢复出厂设置后重新配对

第五章：注意事项

- 请勿在潮湿环境安装网关（避免短路）
- 定期检查电池电量（传感器电池寿命约 1 年）
- 系统固件会自动更新，请保持网关在线
- 建议定期重启网关（每月 1 次）
"""

# 一篇 Markdown 格式的产品文档
MD_DOCUMENT = """# X100 智能手表快速上手指南

## 首次使用
### 开箱检查
打开包装盒，确认包含以下物品：
- X100 智能手表 × 1
- 磁吸充电线 × 1
- 快速上手指南 × 1

### 开机配对
1. 长按右侧按钮 5 秒开机
2. 手机下载 X100 App
3. 打开 App 扫描手表二维码
4. 确认配对请求

### 首次充电
建议首次充电充满 100%，充电约 2 小时。

## 日常使用

### 基础操作
**触控操作**
- 主屏幕：显示时间和日期
- 右滑：返回
- 下滑：控制中心
- 上滑：通知列表

**按键操作**
- 短按电源键：亮屏/息屏
- 长按电源键：开机/关机
- 双击电源键：快速打开支付

### 健康监测
心率监测：默认 10 分钟自动测量一次
血氧监测：睡眠时自动监测
睡眠分析：记录深睡、浅睡、REM 时长

### 运动模式
支持 100+ 种运动模式，包括：
- 户外跑步（自动记录 GPS 轨迹）
- 室内跑步
- 游泳（自动计算泳姿）
- 骑行
- 登山

## 充电与续航

### 充电方式
- 使用磁吸充电线
- 充电触点对准手表背面
- 充满约 2 小时

### 续航时间
- 典型使用：14 天（心率常开、通知开启）
- 重度使用：7 天（GPS 运动每天 1 小时）
- 省电模式：30 天（关闭心率、通知）

## 常见问题

**问：防水吗？**
答：支持 IP68 防水，可在 50 米水深下工作。

**问：电池能换吗？**
答：内置锂电池，无法更换。电池寿命约 2-3 年。

**问：支持微信支付吗？**
答：支持支付宝支付，暂不支持微信支付。
"""


# ============================================================
# Part 2: 分块策略实现
# ============================================================

def demo_fixed_size_chunking():
    """
    固定长度分块 (CharacterTextSplitter)
    
    原理：
    1. 按 chunk_size 的固定长度切分
    2. optional: overlap 让相邻块有重叠
    
    优缺点：
    + 简单快速，O(n) 时间复杂度
    + 确定性结果，可复现
    - 可能切在句子中间，破坏语义
    - 不考虑文档结构
    
    适用场景：
    - 源代码文件
    - 日志文件
    - 不需要语义完整性的数据
    - 数据量极大、需要高性能的场景
    """
    print("\n" + "=" * 60)
    print("🔪 固定长度分块 (CharacterTextSplitter)")
    print("=" * 60)

    # chunk_size = 字符数
    # chunk_overlap = 重叠字符数
    splitter = CharacterTextSplitter(
        separator="\n",          # 优先按换行符切分
        chunk_size=200,          # 每个块目标 200 字符
        chunk_overlap=30,        # 重叠 30 字符
        length_function=len,     # 用 len() 测量长度
    )

    chunks = splitter.split_text(LONG_DOCUMENT)
    print(f"\n   原文档长度: {len(LONG_DOCUMENT)} 字符")
    print(f"   生成块数: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n   📦 块 #{i+1} (长度: {len(chunk)})")
        # 高亮可能的断句问题
        preview = chunk[:100]
        if not chunk.endswith(("。", "？", "！", "\n", ".", "?")):
            preview += "... ⚠️ (断句)"
        print(f"      {preview}")

    return chunks


def demo_recursive_chunking():
    """
    递归分块 (RecursiveCharacterTextSplitter) — LangChain 推荐
    
    原理：
    1. 按分隔符优先级列表切分
    2. 默认优先级：["\n\n", "\n", " ", ""]（中英文通用）
    3. 如果当前分隔符切出的块太大 → 用下一个分隔符递归切分
    
    分隔符优先级的实际效果：
    - 先按段落(\n\n)切 → 常见结构要么太长，要么适合作块
    - 段落太长 → 按句子(\n)切
    - 句子太长 → 按空格或字符硬切（作为最后手段）
    
    优缺点：
    + 保持段落和句子完整性（大部分情况）
    + 更好的语义完整性
    + LangChain 官方推荐
    - 比固定长度略慢（但可以忽略不计）
    
    适用场景：
    - 通用文本（推荐首选）
    - 大多数 RAG 场景
    - 不需要知道文档结构时
    """
    print("\n" + "=" * 60)
    print("🔪 递归分块 (RecursiveCharacterTextSplitter)")
    print("=" * 60)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,          # 每个块目标 200 字符
        chunk_overlap=30,        # 重叠 30 字符
        length_function=len,     # 用 len() 测量长度
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],  # 中文适配
    )

    chunks = splitter.split_text(LONG_DOCUMENT)
    print(f"\n   原文档长度: {len(LONG_DOCUMENT)} 字符")
    print(f"   生成块数: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n   📦 块 #{i+1} (长度: {len(chunk)})")
        preview = chunk[:120]
        print(f"      {preview}")

    return chunks


def demo_markdown_chunking():
    """
    Markdown 标题分块 (MarkdownHeaderTextSplitter)
    
    原理：
    1. 按 Markdown 标题（H1, H2, H3…）切分文档
    2. 自动把标题信息加入 metadata
    3. 每个"标题→下一个标题"之间的内容成为一个块
    
    关键参数：
    - headers_to_split_on: [(级别, 名称), ...]
      - 例如 [(("h1", "章"), ("h2", "节")]
      - 先按 h1 切，再按 h2 切
    
    返回：
    - 每个块都包含 metadata，记录它属于哪章哪节
    
    优缺点：
    + 利用文档的结构信息，保留章节上下文
    + metadata 可以用于溯源
    + 最好的语义完整性
    - 只适用于 Markdown 格式（或能转成 MD 的文档）
    - 需要文档有良好的标题结构
    
    适用场景：
    - Markdown 文档（GitHub Wiki、技术文档、README）
    - 有章节结构的长文档
    - 需要按章节溯源的时候
    """
    print("\n" + "=" * 60)
    print("🔪 Markdown 标题分块 (MarkdownHeaderTextSplitter)")
    print("=" * 60)

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "章节"),       # H1 → metadata["章节"]
            ("##", "小节"),      # H2 → metadata["小节"]
            ("###", "子节"),     # H3 → metadata["子节"]
        ],
        return_each_line=False,  # 不要把每行作为一个单独文档
    )

    chunks = splitter.split_text(MD_DOCUMENT)
    print(f"\n   生成块数: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n   📦 块 #{i+1}")
        print(f"      长度: {len(chunk.page_content)}")
        print(f"      元数据: {chunk.metadata}")
        print(f"      内容: {chunk.page_content[:150]}")
        print(f"      ...")

    return chunks


def demo_combine_strategies():
    """
    组合策略：Markdown 分块 + 递归分块

    实践中，MarkdownHeaderTextSplitter 经常配合 RecursiveCharacterTextSplitter 使用：
    1. 先用 Markdown 标题把文档按章节切成大块
    2. 如果某个章节正文太长，再用递归分块细化

    这样兼顾了结构完整性和块大小控制。
    """
    print("\n" + "=" * 60)
    print("🔪 组合策略：Markdown + 递归分块")
    print("=" * 60)

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "章节"),
            ("##", "小节"),
        ],
    )

    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    # 第一步：按 Markdown 标题切分
    md_chunks = markdown_splitter.split_text(MD_DOCUMENT)
    print(f"\n   第一步（Markdown 分块）: {len(md_chunks)} 个块")

    # 第二步：对每个大块，如果太长就用递归分块细化
    final_chunks = []
    for chunk in md_chunks:
        if len(chunk.page_content) > 300:
            # 这个大块太长了，需要进一步细化
            sub_chunks = recursive_splitter.split_documents([chunk])
            # 保留章节信息在 metadata 中
            for sc in sub_chunks:
                sc.metadata.update(chunk.metadata)
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk)

    print(f"   第二步（递归细化）: {len(final_chunks)} 个块")
    print(f"   最终块数: {len(final_chunks)}")

    for i, chunk in enumerate(final_chunks):
        print(f"\n   📦 块 #{i+1} (长度: {len(chunk.page_content)})")
        print(f"      元数据: {chunk.metadata}")
        print(f"      内容: {chunk.page_content[:150]}")

    return final_chunks


# ============================================================
# Part 3: 分块策略对比实验
# ============================================================

def demo_comparison():
    """
    核心对比实验：同一种文档，不同分块策略的差异

    我们用三段测试文本，模拟不同场景：
    - 长段落（产品介绍）：检查断句情况
    - 结构化文本（使用步骤）：检查结构保留
    - Markdown 文档（FAQ）：检查章节完整性

    关键观察点：
    1. 块是否包含完整句子？
    2. 是否保持了段落/章节结构？
    3. 是否有信息丢失或重复？
    """
    print("\n" + "=" * 60)
    print("🔬 分块策略对比实验")
    print("=" * 60)

    test_texts = {
        "长段落": ("第三章：日常使用\n\n3.1 场景模式\n系统支持以下场景模式：回家模式、离家模式、睡眠模式、自定义场景。"
                   "回家模式会自动开灯、开空调、拉窗帘。离家模式会关闭所有设备并启动安防模式。"
                   "睡眠模式会关灯、关窗帘、设置空调温度到舒适的 26℃。"),
        "结构化文本": ("2.2 传感器配对\n1. 进入网关管理页面\n2. 点击「添加设备」\n"
                      "3. 长按传感器按钮 3 秒\n4. 等待听到「嘀」的一声\n5. App 中确认添加"),
        "Markdown": ("# 常见问题\n\n**问：防水吗？**\n答：支持 IP68 防水，可在 50 米水深下工作。\n\n"
                     "**问：电池能换吗？**\n答：内置锂电池，无法更换。\n\n"
                     "**问：支持微信支付吗？**\n答：支持支付宝支付。"),
    }

    strategies = {
        "固定长度": CharacterTextSplitter(separator="\n", chunk_size=100, chunk_overlap=20),
        "递归分块": RecursiveCharacterTextSplitter(
            chunk_size=100, chunk_overlap=20,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        ),
    }

    for text_name, text in test_texts.items():
        print(f"\n{'─' * 60}")
        print(f"📄 测试文本: {text_name}")
        print(f"   原文: {text[:80]}...")

        for strategy_name, splitter in strategies.items():
            chunks = splitter.split_text(text)
            print(f"\n   🔪 {strategy_name}: {len(chunks)} 个块")
            for i, chunk in enumerate(chunks):
                completeness = "完整" if chunk.endswith(("。", "？", "！", "\n")) else "断句 ⚠️"
                print(f"      块#{i+1}({len(chunk)}字, {completeness}): {chunk}")


# ============================================================
# 演示入口
# ============================================================

def demo():
    """运行所有分块演示"""
    print("=" * 60)
    print("📏 Week 2 - 分块策略对比")
    print("=" * 60)

    # Part 2: 逐个策略演示
    fixed_chunks = demo_fixed_size_chunking()
    recursive_chunks = demo_recursive_chunking()
    md_chunks = demo_markdown_chunking()
    combined_chunks = demo_combine_strategies()

    # Part 3: 对比实验
    demo_comparison()

    # ─── 总结 ───
    print("\n" + "=" * 60)
    print("📊 分块策略选择指南")
    print("=" * 60)
    print("""
    固定长度分块 (CharacterTextSplitter):
        适用: 代码、日志、纯数据文本
        优点: 简单快速
        缺点: 可能破坏语义

    递归分块 (RecursiveCharacterTextSplitter) ✅ 推荐:
        适用: 通用文本（大多数场景）
        优点: 保持段落/句子完整性
        缺点: 不利用文档结构信息

    Markdown 标题分块 (MarkdownHeaderTextSplitter):
        适用: Markdown 格式文档
        优点: 保留章节结构，便于溯源
        缺点: 正文太长时块可能过大

    组合策略 (Markdown + 递归) ⭐ 强力推荐:
        适用: 结构化长文档
        优点: 兼顾结构和长度控制
        缺点: 实现稍复杂

    经验参数:
        chunk_size: 200-1000 (字符)
        chunk_overlap: 10-20% of chunk_size
        LLM 上下文越大，chunk_size 可以越大

    ⏭  下一步: 多格式文档 RAG 实战 (multi_format_rag.py)
    """)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        # 快速测试模式
        print(f"📏 Chunking strategies loaded.")
        print(f"   Functions: demo_fixed_size_chunking, demo_recursive_chunking,")
        print(f"             demo_markdown_chunking, demo_combine_strategies")
        print(f"   Run with --demo for full demonstration")
        demo()
