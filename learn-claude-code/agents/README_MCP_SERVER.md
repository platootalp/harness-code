# MCP 实用服务器 (My Utility MCP Server)

一个功能丰富的通用 MCP 服务器，提供多种实用工具和资源。

## 📋 功能概览

### Tools（可调用的工具）

1. **calculate(expression: str)** - 数学表达式计算
   - 支持：+、-、*、/、()、数字
   - 示例：`"2 + 3 * 4"` → `"Result: 2 + 3 * 4 = 14"`

2. **get_current_time(timezone: str = "UTC")** - 获取当前时间
   - 默认时区 UTC
   - 返回格式化的时间字符串

3. **echo(message: str)** - 回显消息
   - 简单测试工具，原样返回输入

4. **format_json(data_str: str)** - JSON 格式化
   - 将 JSON 字符串格式化为美观的显示格式
   - 自动错误处理

5. **system_info()** - 系统信息
   - 返回 hostname、platform、Python 版本、工作目录等
   - 返回字典类型结果

### Resources（可读取的资源）

1. **config://settings** - 应用程序设置
   - 服务器版本、特性列表、创建时间等配置信息

2. **file://{path}** - 文件读取
   - 安全限制：只能读取当前工作目录下的文件
   - 防止路径遍历攻击

3. **info://status** - 服务器状态
   - 运行状态、可用工具和资源的列表

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装必要的 Python 包
pip install mcp
```

### 2. 直接运行测试

```bash
cd /Users/lijunyi/road/learn-claude-code/agents
python3 test_mcp_server.py
```

这会启动服务器并执行一组自动化测试，验证所有功能是否正常工作。

### 3. 与 Claude 集成

#### 方法一：使用 MCP Inspector（推荐用于开发调试）

```bash
# 全局安装 MCP Inspector（需要 npm）
npm install -g @modelcontextprotocol/inspector

# 启动调试器
npx @modelcontextprotocol/inspector python3 my_mcp_server.py
```

#### 方法二：添加到 Claude 配置文件

创建或编辑 `~/.claude/mcp.json`：

```json
{
  "my-utility-server": {
    "command": "python3",
    "args": ["/Users/lijunyi/road/learn-claude-code/agents/my_mcp_server.py"]
  }
}
```

然后重启 Claude，即可在对话中使用这些工具。

## 🔧 自定义扩展

### 添加新工具

在 `my_mcp_server.py` 中添加：

```python
@server.tool()
async def your_new_tool(param1: str, param2: int) -> str:
    """工具描述.
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回内容说明
    """
    # 你的实现代码
    return result
```

### 添加新资源

```python
@server.resource("your-scheme://endpoint")
async def your_resource_handler() -> str:
    """资源描述."""
    return "资源内容"
```

## 📝 使用示例

### 在 Claude 对话中可以使用：

```
帮我计算一下：(10 + 5) * 3
```

```
给我看看当前的系统信息
```

```
格式化这段 JSON: {"name":"test","value":123}
```

```
读取这个文件的内容：./README_MCP_SERVER.md
```

## 🛡️ 安全特性

- **文件系统访问控制**：只允许读取工作目录内的文件
- **表达式计算安全**：只允许使用基本的数学运算符
- **异步执行**：I/O 操作使用 async/await，避免阻塞

## 🔄 测试

手动测试：

```bash
# 发送简单的 RPC 请求
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 my_mcp_server.py
```

自动测试：

```bash
python3 test_mcp_server.py
```

## 📚 参考文档

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)

## 🤝 贡献

欢迎添加更多实用的工具和资源！只需遵循现有的模式即可。
