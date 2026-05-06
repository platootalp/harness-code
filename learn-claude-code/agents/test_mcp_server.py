#!/usr/bin/env python3
"""
测试 MCP 服务器的工具脚本
用于验证 MCP 服务器是否正常工作
"""

import asyncio
import json
import sys
from mcp.server import Server
from mcp.client.stdio import stdio_client


async def test_server():
    """测试服务器连接和功能."""
    
    # 启动服务器进程
    server_process = await asyncio.create_subprocess_exec(
        sys.executable, 
        "my_mcp_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        async with stdio_client(
            server_process.stdin,
            server_process.stdout
        ) as (read, write):
            
            print("✓ Connected to MCP Server\n")
            
            # 1. Test tools/list - 获取可用工具列表
            print("📋 Testing: tools/list")
            await write.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }).encode() + b'\n'
            )
            
            response = await read.readline()
            print(f"Response: {response.decode().strip()}")
            print()
            
            # 2. Test tools/call - 调用 calculate 工具
            print("🔧 Testing: calculate('2 + 3 * 4')")
            await write.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "calculate",
                        "arguments": {
                            "expression": "2 + 3 * 4"
                        }
                    }
                }).encode() + b'\n'
            )
            
            response = await read.readline()
            print(f"Response: {response.decode().strip()}")
            print()
            
            # 3. Test tools/call - 调用 system_info 工具
            print("🖥️  Testing: system_info()")
            await write.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "system_info",
                        "arguments": {}
                    }
                }).encode() + b'\n'
            )
            
            response = await read.readline()
            print(f"Response: {response.decode().strip()}")
            print()
            
            # 4. Test resources/list - 获取可用资源列表
            print("📁 Testing: resources/list")
            await write.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "resources/list",
                    "params": {}
                }).encode() + b'\n'
            )
            
            response = await read.readline()
            print(f"Response: {response.decode().strip()}")
            print()
            
            # 5. Test resources/read - 读取 config://settings 资源
            print("📄 Testing: resources/read 'config://settings'")
            await write.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "resources/read",
                    "params": {
                        "uri": "config://settings"
                    }
                }).encode() + b'\n'
            )
            
            response = await read.readline()
            print(f"Response: {response.decode().strip()}")
            print()
            
            print("=" * 50)
            print("✅ All tests completed!")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
    
    finally:
        # 关闭服务器进程
        server_process.terminate()
        await server_process.wait()


if __name__ == "__main__":
    print("MCP Server Test Runner")
    print("=" * 50)
    print()
    asyncio.run(test_server())
