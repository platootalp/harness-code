#!/usr/bin/env python3
"""
My MCP Server - 一个实用的通用 MCP 服务器
包含多个工具和资源，演示 MCP 的基本用法
"""

import asyncio
import json
import os
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource


# 创建服务器实例
server = Server("my-utility-server")


# ==================== TOOLS (Claude可调用的函数) ====================

@server.tool()
async def calculate(expression: str) -> str:
    """执行数学表达式计算.
    
    Args:
        expression: 要计算的数学表达式，例如 '2 + 3 * 4'
    
    Returns:
        计算结果或错误信息
    """
    try:
        # 安全计算表达式
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Expression contains invalid characters"
        
        result = eval(expression)
        return f"Result: {expression} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@server.tool()
async def get_current_time(timezone: str = "UTC") -> str:
    """获取当前时间.
    
    Args:
        timezone: 时区，默认 UTC
    
    Returns:
        当前时间字符串
    """
    # 简单实现，实际可以使用 pytz 处理多时区
    current_time = datetime.utcnow()
    return f"Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"


@server.tool()
async def echo(message: str) -> str:
    """回显消息.
    
    Args:
        message: 要回显的消息
    
    Returns:
        原始消息
    """
    return f"Echo: {message}"


@server.tool()
async def format_json(data_str: str) -> str:
    """格式化 JSON 字符串.
    
    Args:
        data_str: 要格式化的 JSON 字符串
    
    Returns:
        格式化后的 JSON
    """
    try:
        data = json.loads(data_str)
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        return formatted
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {str(e)}"


@server.tool()
async def system_info() -> dict:
    """获取系统基本信息.
    
    Returns:
        系统信息字典
    """
    return {
        "hostname": os.uname().nodename,
        "platform": os.uname().sysname,
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        "working_directory": os.getcwd(),
        "timestamp": datetime.now().isoformat()
    }


# ==================== RESOURCES (Claude可读取的数据) ====================

@server.resource("config://settings")
async def get_settings() -> str:
    """获取应用程序设置.
    
    Returns:
        设置内容
    """
    settings = {
        "version": "1.0.0",
        "description": "MCP 实用服务器",
        "features": ["calculate", "echo", "format_json", "system_info"],
        "created_at": datetime.now().isoformat()
    }
    return json.dumps(settings, indent=2, ensure_ascii=False)


@server.resource("file://{path}")
async def read_file(path: str) -> str:
    """读取指定路径的文件.
    
    Args:
        path: 文件路径
    
    Returns:
        文件内容
    
    Raises:
        FileNotFoundError: 如果文件不存在
        PermissionError: 如果没有权限访问
    """
    try:
        # 安全性检查：只允许访问当前目录下的文件
        abs_path = os.path.abspath(path)
        cwd = os.getcwd()
        
        if not abs_path.startswith(cwd):
            return "Error: Access to files outside working directory is not allowed"
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"File '{path}' content:\n\n{content}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied to access '{path}'"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@server.resource("info://status")
async def get_status() -> str:
    """获取服务器状态.
    
    Returns:
        服务器状态信息
    """
    status = {
        "status": "running",
        "server_name": "my-utility-server",
        "uptime_since": datetime.now().isoformat(),
        "available_tools": [
            "calculate", "get_current_time", "echo", "format_json", "system_info"
        ],
        "available_resources": [
            "config://settings",
            "file://{path}",
            "info://status"
        ]
    }
    return json.dumps(status, indent=2, ensure_ascii=False)


# ==================== MAIN ENTRY POINT ====================

async def main():
    """启动 MCP 服务器."""
    async with stdio_server() as (read, write):
        await server.run(read, write)


if __name__ == "__main__":
    print("Starting MCP Server...")
    asyncio.run(main())
