"""快速验证：MCP Filesystem Server 协议通信"""
import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test():
    server_path = Path(__file__).parent / "filesystem_mcp_server.py"

    params = StdioServerParameters(command="python3", args=[str(server_path)])
    print("📡 连接 Filesystem MCP Server...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ 握手成功！")

            # 发现工具
            tools = await session.list_tools()
            print(f"\n🔧 可用工具 ({len(tools.tools)} 个):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            # 调用工具
            print("\n📂 list_dir('') 测试:")
            result = await session.call_tool("list_dir", {"path": ""})
            for c in result.content:
                print(c.text)

            print("\n📄 read_file('sample.txt') 测试:")
            result = await session.call_tool("read_file", {"path": "sample.txt"})
            for c in result.content:
                print(c.text)

            print("\n🔍 search_files('**/*.json') 测试:")
            result = await session.call_tool("search_files", {"pattern": "**/*.json"})
            for c in result.content:
                print(c.text)

            print("\n✍️ write_file 测试:")
            result = await session.call_tool("write_file", {
                "path": "mcp_test.txt",
                "content": "MCP 协议测试成功！✓"
            })
            for c in result.content:
                print(c.text)

    print("\n✅ 所有测试完成！")

if __name__ == "__main__":
    asyncio.run(test())
