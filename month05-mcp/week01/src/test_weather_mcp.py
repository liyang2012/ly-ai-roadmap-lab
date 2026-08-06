"""快速验证：MCP Weather Server 协议通信"""
import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test():
    server_path = Path(__file__).parent / "weather_mcp_server.py"
    params = StdioServerParameters(command="python3", args=[str(server_path)])

    print("📡 连接 Weather MCP Server...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ 握手成功！")

            tools = await session.list_tools()
            print(f"\n🔧 可用工具 ({len(tools.tools)} 个):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            resources = await session.list_resources()
            print(f"\n📦 可用资源 ({len(resources.resources)} 个):")
            for r in resources.resources:
                print(f"  - {r.uri}: {r.name}")

            print("\n🌤️ get_current_weather('beijing'):")
            result = await session.call_tool("get_current_weather", {"city": "beijing"})
            for c in result.content:
                print(c.text)

            print("\n📅 get_forecast('shanghai'):")
            result = await session.call_tool("get_forecast", {"city": "shanghai"})
            for c in result.content:
                print(c.text)

            print("\n🏙️ 读取 weather://cities 资源:")
            content = await session.read_resource("weather://cities")
            print(f"  支持城市: {content}")

            print("\n❌ 测试无效城市:")
            result = await session.call_tool("get_current_weather", {"city": "mars"})
            for c in result.content:
                print(f"  {c.text}")

    print("\n✅ Weather 测试完成！")

if __name__ == "__main__":
    asyncio.run(test())
