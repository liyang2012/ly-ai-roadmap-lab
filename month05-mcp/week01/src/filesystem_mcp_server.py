"""
month05-mcp/src/filesystem_mcp_server.py
========================================
Filesystem MCP Server — 符合 MCP 协议标准的文件操作服务

MCP SDK 1.28+ API:
  - Server.run(read_stream, write_stream, initialization_options)
  - initialization_options 通过 server.create_initialization_options() 创建

提供 Tools:
  - list_dir: 列出目录内容
  - read_file: 读取文件内容
  - write_file: 写入文件（仅限安全目录内）
  - search_files: 搜索文件（glob 匹配）

提供 Resources:
  - file:///* : 只读方式暴露文件内容

安全约束:
  - 所有操作限制在 allowed_root 目录内
  - write_file 检查路径不越界
"""

import os
import glob as glob_module
from pathlib import Path
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)


# ── 配置 ────────────────────────────────────────────
ALLOWED_ROOT = Path(os.environ.get("MCP_FS_ROOT", os.path.expanduser("~/mcp-filesystem-sandbox"))).expanduser().resolve()
ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)


def is_safe_path(path: str) -> Path:
    """解析路径并确保不越出 allowed_root"""
    resolved = (ALLOWED_ROOT / path).resolve()
    if not str(resolved).startswith(str(ALLOWED_ROOT)):
        raise PermissionError(f"路径越界: {path}")
    return resolved


# ── Server 实例 ──────────────────────────────────────
server = Server("filesystem-mcp", version="1.0.0")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """MCP 协议: 声明可用工具"""
    return [
        Tool(
            name="list_dir",
            description="列出指定目录下的文件和子目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对路径，空字符串表示根目录",
                        "default": "",
                    }
                },
            },
        ),
        Tool(
            name="read_file",
            description="读取文件内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件相对路径",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="写入文件内容（仅限安全目录内）",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="search_files",
            description="用 glob 模式搜索文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "glob 匹配模式，如 '*.py' 或 '**/*.md'",
                        "default": "**/*",
                    }
                },
            },
        ),
    ]


# ── Tool Handlers ──────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """MCP 协议: 处理工具调用"""
    if name == "list_dir":
        path = arguments.get("path", "")
        target = is_safe_path(path)

        if not target.exists():
            return [TextContent(type="text", text=f"❌ 目录不存在: {path}")]
        if not target.is_dir():
            return [TextContent(type="text", text=f"❌ 不是目录: {path}")]

        entries = []
        for entry in sorted(target.iterdir()):
            prefix = "📁" if entry.is_dir() else "📄"
            size = ""
            if entry.is_file():
                size = f" ({entry.stat().st_size:,} bytes)"
            entries.append(f"  {prefix} {entry.name}{size}")

        result = f"📂 {path or '/'} ({len(entries)} 项):\n" + "\n".join(entries)
        return [TextContent(type="text", text=result)]

    elif name == "read_file":
        path = arguments["path"]
        target = is_safe_path(path)

        if not target.exists():
            return [TextContent(type="text", text=f"❌ 文件不存在: {path}")]
        if target.is_dir():
            return [TextContent(type="text", text=f"❌ 是目录不是文件: {path}")]

        try:
            content = target.read_text(encoding="utf-8")
            return [TextContent(type="text", text=content)]
        except UnicodeDecodeError:
            return [TextContent(type="text", text=f"❌ 无法以 UTF-8 读取（可能是二进制文件）")]

    elif name == "write_file":
        path = arguments["path"]
        content = arguments["content"]
        target = is_safe_path(path)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        size = target.stat().st_size

        return [TextContent(
            type="text",
            text=f"✅ 写入成功: {path} ({size:,} bytes)"
        )]

    elif name == "search_files":
        pattern = arguments.get("pattern", "**/*")

        matches = glob_module.glob(
            pattern,
            root_dir=str(ALLOWED_ROOT),
            recursive=True,
        )

        if not matches:
            return [TextContent(type="text", text=f"🔍 未找到匹配 '{pattern}' 的文件")]

        lines = [f"🔍 搜索 '{pattern}' — {len(matches)} 个结果:"]
        for m in sorted(matches)[:50]:
            full = ALLOWED_ROOT / m
            prefix = "📁" if full.is_dir() else "📄"
            lines.append(f"  {prefix} {m}")
        if len(matches) > 50:
            lines.append(f"  ... 还有 {len(matches) - 50} 个结果")

        return [TextContent(type="text", text="\n".join(lines))]

    else:
        return [TextContent(type="text", text=f"❌ 未知工具: {name}")]


# ── 启动 ────────────────────────────────────────────

async def main():
    """用 stdio transport 启动 MCP Server"""
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
