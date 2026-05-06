# 调试模式

本文档介绍如何调试 OpenHarness 的 Python 后端。

## 核心问题

TUI 前端通过 `spawn()` 将后端作为**子进程**启动。PyCharm 无法直接捕获 TUI spawn 的进程。

**解决方案**：后端监听 debugpy 端口，PyCharm Attach 连接。

---

## 详细步骤

### 步骤 1：安装 debugpy

```bash
pip install debugpy
```

### 步骤 2：配置 PyCharm Remote Debug

1. **Run → Edit Configurations → + → Python Remote Debug**
2. 配置：

| 设置项 | 值 |
|--------|-----|
| **Name** | `Attach Backend` |
| **Host** | `localhost` |
| **Port** | `5678` |

3. 保存（**不要点击运行**）

### 步骤 3：启动 TUI + 后端（带调试端口）

在**系统终端**（iTerm、Terminal.app）中运行：

```bash
cd /Users/lijunyi/road/reference/OpenHarness/frontend/terminal && \
OPENHARNESS_FRONTEND_CONFIG=$(python -c "
import json, sys
from pathlib import Path
backend_command = [sys.executable, '-m', 'openharness', '--backend-only', '--debug-port', '5678', '--cwd', '/Users/lijunyi/road/reference/OpenHarness']
print(json.dumps({'backend_command': backend_command, 'initial_prompt': '', 'theme': 'default'}))
") \
script -q /dev/null ./node_modules/.bin/tsx src/index.tsx
```

### 步骤 4：等待后端日志

后端启动时会打印以下日志：

```
Starting debugpy server on port 5678 ...
debugpy server started on port 5678 — PyCharm: Run → Attach to Process → port 5678
```

看到 `debugpy server started on port 5678` 后即可 Attach。

### 步骤 5：PyCharm Attach

看到上面的消息后，在 PyCharm 中：
1. 点击 **Run → Attach to Process**
2. 或者使用之前配置的 **"Attach Backend"** Remote Debug
3. PyCharm 连接到 `localhost:5678`

### 步骤 6：设置断点调试

连接成功后，在任何 Python 代码处设置断点，断点应该生效。

**注意**：断点只有在 PyCharm Attach **之后**执行的代码才会触发。之前已经执行过的代码不会命中断点。

---

## 快速验证

在继续之前，可以用这个命令验证 debug port 功能是否正常：

```bash
# 启动后端
cd /Users/lijunyi/road/reference/OpenHarness
python -m openharness --backend-only --debug-port 5678 --cwd /Users/lijunyi/road/reference/OpenHarness

# 看到 "debugpy server started" 日志后，在另一个终端验证端口：
python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 5678)); s.close(); print('Port is listening!')"
```

如果看到 `Port is listening!`，说明 debug port 工作正常。

**注意**：在 subprocess 或后台进程中，`lsof -i :5678` 可能无法显示端口（macOS 限制）。使用 Python socket connect 测试更可靠。

---

## 参数说明

| 参数 | 说明 |
|------|------|
| `--backend-only` | 仅运行后端服务（不启动 TUI） |
| `--debug-port 5678` | 在端口 5678 监听调试连接 |
| `--cwd PATH` | 工作目录 |

---

## 常见问题

### Q: 端口被占用

使用其他端口，如 `--debug-port 5679`（PyCharm 配置中也要同步修改）

### Q: "Raw mode is not supported"

使用 `script -q /dev/null` 包装命令：
```bash
script -q /dev/null ./node_modules/.bin/tsx src/index.tsx
```

### Q: PyCharm Attach 后断点没生效

1. 确保看到 "debugpy server started on port 5678" 日志后再 Attach
2. 使用正确的端口号
3. 检查 PyCharm 连接的是 `localhost:5678`
4. 断点只能命中 Attach 之后执行的代码

### Q: TUI 无法连接后端

检查 `--cwd` 指向项目根目录（不是 `frontend/terminal/`）

### Q: `lsof -i :5678` 显示端口不监听

这是 macOS subprocess 环境的限制。`lsof` 在子进程中可能不显示 debugpy 的监听端口。使用 Python socket 测试：

```bash
python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 5678)); s.close(); print('OK')"
```

如果返回 `OK`，说明端口实际是正常监听的。
