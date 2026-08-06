"""
month05-mcp/src/weather_mcp_server.py
=====================================
Weather MCP Server — 封装外部天气 API 为标准 MCP 工具

提供 Tools:
  - get_current_weather: 获取当前天气
  - get_forecast: 获取未来天气预报

提供 Resources:
  - weather://cities : 支持的城市列表
"""

import asyncio
from typing import Any

from pydantic import AnyUrl
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource


# ── 模拟天气数据 ───────────────────────────────────

CITIES_WEATHER = {
    "beijing": {
        "current": {"temp": 32, "humidity": 75, "wind": "东南风 3级", "condition": "多云", "aqi": 85},
        "forecast": [
            {"date": "周一", "high": 34, "low": 26, "condition": "多云转晴"},
            {"date": "周二", "high": 36, "low": 27, "condition": "晴"},
            {"date": "周三", "high": 33, "low": 25, "condition": "雷阵雨"},
        ],
    },
    "shanghai": {
        "current": {"temp": 35, "humidity": 80, "wind": "西南风 4级", "condition": "晴", "aqi": 62},
        "forecast": [
            {"date": "周一", "high": 36, "low": 28, "condition": "晴"},
            {"date": "周二", "high": 37, "low": 29, "condition": "多云"},
            {"date": "周三", "high": 34, "low": 27, "condition": "雷阵雨"},
        ],
    },
    "shenzhen": {
        "current": {"temp": 30, "humidity": 85, "wind": "南风 2级", "condition": "阵雨", "aqi": 35},
        "forecast": [
            {"date": "周一", "high": 31, "low": 26, "condition": "阵雨"},
            {"date": "周二", "high": 32, "low": 27, "condition": "多云"},
            {"date": "周三", "high": 33, "low": 28, "condition": "晴"},
        ],
    },
    "chengdu": {
        "current": {"temp": 28, "humidity": 70, "wind": "北风 2级", "condition": "阴", "aqi": 55},
        "forecast": [
            {"date": "周一", "high": 30, "low": 24, "condition": "阴转小雨"},
            {"date": "周二", "high": 29, "low": 23, "condition": "小雨"},
            {"date": "周三", "high": 31, "low": 25, "condition": "多云"},
        ],
    },
    "tokyo": {
        "current": {"temp": 33, "humidity": 65, "wind": "南风 3级", "condition": "晴", "aqi": 45},
        "forecast": [
            {"date": "周一", "high": 34, "low": 26, "condition": "晴"},
            {"date": "周二", "high": 35, "low": 27, "condition": "晴"},
            {"date": "周三", "high": 32, "low": 25, "condition": "多云"},
        ],
    },
}

SUPPORTED_CITIES = list(CITIES_WEATHER.keys())


# ── Server ──────────────────────────────────────────

server = Server("weather-mcp", version="1.0.0")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_weather",
            description=f"获取指定城市的当前天气。支持: {', '.join(SUPPORTED_CITIES)}",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": f"城市名（英文小写），如 'beijing'",
                    }
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_forecast",
            description=f"获取指定城市未来 3 天天气预报",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": f"城市名（英文小写），如 'beijing'",
                    }
                },
                "required": ["city"],
            },
        ),
    ]


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="weather://cities",
            name="Supported Cities",
            description=f"天气服务支持的城市列表",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if str(uri) == "weather://cities":
        return "\n".join(SUPPORTED_CITIES)
    return f"未知资源: {uri}"


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    city = arguments.get("city", "").lower()

    if city not in CITIES_WEATHER:
        return [TextContent(
            type="text",
            text=f"❌ 不支持的城市 '{city}'。支持: {', '.join(SUPPORTED_CITIES)}"
        )]

    data = CITIES_WEATHER[city]

    if name == "get_current_weather":
        c = data["current"]
        result = (
            f"🌤️ {city.title()} 当前天气:\n"
            f"  温度: {c['temp']}°C\n"
            f"  湿度: {c['humidity']}%\n"
            f"  风力: {c['wind']}\n"
            f"  天气: {c['condition']}\n"
            f"  空气质量指数(AQI): {c['aqi']}"
        )
        if c["aqi"] > 100:
            result += " ⚠️ 轻度污染"
        elif c["aqi"] > 50:
            result += " 🟡 良"
        else:
            result += " 🟢 优"
        return [TextContent(type="text", text=result)]

    elif name == "get_forecast":
        lines = [f"📅 {city.title()} 未来 3 天天气预报:"]
        ICONS = {"晴": "☀️", "多云": "⛅", "阴": "☁️", "阵雨": "🌧️", "雷阵雨": "⛈️", "小雨": "🌦️", "多云转晴": "⛅→☀️", "阴转小雨": "☁️→🌦️"}
        for f in data["forecast"]:
            icon = ICONS.get(f["condition"], "🌤️")
            lines.append(
                f"  {f['date']} {icon} {f['condition']}  {f['low']}°C ~ {f['high']}°C"
            )
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"❌ 未知工具: {name}")]


# ── 启动 ────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
