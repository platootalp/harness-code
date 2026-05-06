# 安装配置

## 安装方式

### 方式一：一键脚本（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/HKUDS/OpenHarness/main/scripts/install.sh | bash
```

常用参数：
- `--from-source`：从源码安装
- `--with-channels`：安装 IM channel 依赖

```bash
curl -fsSL https://raw.githubusercontent.com/HKUDS/OpenHarness/main/scripts/install.sh | bash -s -- --with-channels
```

### 方式二：源码安装

```bash
git clone https://github.com/HKUDS/OpenHarness.git
cd OpenHarness
uv sync --extra dev
```

### 方式三：pip 安装

```bash
pip install openharness
```

## 安装目录结构

OpenHarness 使用以下配置目录：

- **Linux/macOS**: `~/.config/openharness/`
- **Windows**: `%APPDATA%/openharness/`

主要配置文件：
- `settings.json` - 主配置
- `credentials.json` - API 密钥（加密存储）
- `memory/` - 记忆文件
- `skills/` - 用户技能
- `plugins/` - 用户插件

## Channels 依赖

OpenHarness 支持多种 IM 渠道，需要额外安装依赖：

```bash
# 安装 channels 依赖
uv sync --extra channels

# 或使用安装脚本
curl -fsSL https://raw.githubusercontent.com/HKUDS/OpenHarness/main/scripts/install.sh | bash -s -- --with-channels
```

支持的 channels：
- Telegram
- Slack
- Discord
- Feishu（飞书）
- DingTalk
- QQ
- Email
- WhatsApp
- Matrix
- Mochat

## 验证安装

```bash
oh --version
```

## 开发依赖

```bash
# 安装所有开发依赖
uv sync --extra dev

# 运行测试
uv run pytest -q

# 代码检查
uv run ruff check src tests scripts

# 类型检查
uv run mypy src/openharness
```

## 卸载

```bash
pip uninstall openharness
rm -rf ~/.config/openharness/
```

## 常见问题

### Q: 提示 "command not found: oh"

确保 `~/.local/bin` 或 pip 安装路径在 PATH 中：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

或在 `~/.bashrc` / `~/.zshrc` 中添加：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Q: uv 命令不存在

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
