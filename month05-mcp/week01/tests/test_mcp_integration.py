"""
month05-mcp/tests/test_mcp_integration.py
=========================================
MCP 协议实战 — 完整测试套件

测试覆盖:
  - Filesystem MCP Server (4 个工具 + 安全拦截)
  - Weather MCP Server (2 个工具 + 1 个资源)
  - MCP 协议: Tools 发现、调用、Resources 读取
  - 跨 Server 联合调用
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from mcp_agent_integration import test_mcp_direct


async def test_all():
    print("=" * 60)
    print("📋 第 5 月 Week 1 — MCP 协议实战测试套件")
    print("=" * 60)

    # 运行全部直连测试
    ok = await test_mcp_direct()

    if not ok:
        print("\n❌ 测试失败！")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 所有 MCP 协议测试通过！")
    print("=" * 60)
    print("""
📊 已验证的 MCP 核心能力:

  1. ✅ Server 开发 — 标准 MCP Server 创建和注册
  2. ✅ Transport   — stdio transport 通信
  3. ✅ Tools       — 工具声明(list_tools) + 调用(call_tool)
  4. ✅ Resources   — 资源声明(list_resources) + 读取(read_resource)
  5. ✅ 协议发现   — Client 自动发现 Server 的能力
  6. ✅ 安全约束   — 路径越界检测和拦截
  7. ✅ 跨 Server  — 同时连接 2 个 MCP Server
  8. ✅ 错误处理   — 无效工具名/城市名的优雅降级
""")


if __name__ == "__main__":
    asyncio.run(test_all())
