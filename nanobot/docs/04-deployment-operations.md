# nanobot 部署与运维指南

> **文档版本**: v1.0  
> **最后更新**: 2026-03-10  
> **适用范围**: nanobot v0.1.4.post4+

---

## 1. 部署架构

### 1.1 部署模式总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      部署模式对比                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  模式1: CLI 模式 (个人使用)                                      │
│  ─────────────────────────                                       │
│  适用: 个人开发、快速测试、脚本集成                               │
│                                                                 │
│  ┌─────────────┐                                                │
│  │   Terminal  │──► nanobot agent -m "Hello"                   │
│  └─────────────┘                                                │
│         │                                                       │
│         └──► 直接调用 LLM，无需常驻进程                          │
│                                                                 │
│  启动命令: nanobot agent                                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  模式2: Gateway 模式 (渠道接入)                                  │
│  ─────────────────────────────                                   │
│  适用: Telegram/Discord/WhatsApp等渠道接入                        │
│                                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │ Telegram │────►│ nanobot  │────►│   LLM    │                │
│  │  Bot     │     │ Gateway  │     │ Provider │                │
│  └──────────┘     └────┬─────┘     └──────────┘                │
│  ┌──────────┐          │                                        │
│  │ Discord  │──────────┤  常驻进程，监听所有渠道                │
│  │  Bot     │          │                                        │
│  └──────────┘     ┌────┴─────┐                                  │
│  ┌──────────┐     │  Bus/    │                                  │
│  │ WhatsApp │────►│  Session │                                  │
│  └──────────┘     └──────────┘                                  │
│                                                                 │
│  启动命令: nanobot gateway                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  模式3: 多实例部署 (生产环境)                                    │
│  ───────────────────────────                                     │
│  适用: 多平台独立运营、团队多租户                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    服务器                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ nanobot-tg  │  │ nanobot-dc  │  │ nanobot-api │     │   │
│  │  │  :18790     │  │  :18791     │  │  :18792     │     │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │   │
│  │         │                │                │            │   │
│  │         └────────────────┴────────────────┘            │   │
│  │                          │                             │   │
│  │                    Nginx/Traefik                        │   │
│  │                    (反向代理)                            │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│                      ┌──────┴──────┐                           │
│                      │   Users     │                           │
│                      └─────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 架构组件

| 组件 | 职责 | 资源需求 | 高可用 |
|------|------|----------|--------|
| **nanobot-gateway** | 消息路由、Agent调度 | 100MB内存 | 多实例 |
| **config.json** | 配置中心 | - | 版本控制 |
| **workspace/** | 数据存储 | 取决于用户量 | 定期备份 |
| **LLM Provider** | 外部API | - | 多Provider降级 |

---

## 2. 安装部署

### 2.1 系统要求

| 环境 | 最低配置 | 推荐配置 |
|------|----------|----------|
| **CPU** | 1核 | 2核+ |
| **内存** | 512MB | 1GB+ |
| **磁盘** | 100MB | 1GB+ |
| **Python** | 3.11 | 3.12 |
| **网络** | 出站443 | 稳定连接 |

### 2.2 安装方式

#### 方式1: pip 安装 (推荐)

```bash
# 安装
pip install nanobot-ai

# 验证
nanobot --version

# 初始化配置
nanobot onboard
```

#### 方式2: uv 安装 (更快)

```bash
# 使用 uv (Python包管理器)
uv tool install nanobot-ai

# 升级
uv tool upgrade nanobot-ai
```

#### 方式3: 源码安装 (开发)

```bash
# 克隆仓库
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 验证
nanobot --version
```

### 2.3 初始化配置

```bash
# 1. 初始化 (创建默认配置)
nanobot onboard

# 2. 编辑配置文件
vim ~/.nanobot/config.json
```

**最小可用配置**:
```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4",
      "provider": "openrouter"
    }
  }
}
```

---

## 3. 生产部署

### 3.1 Docker 部署

#### Docker Compose (推荐)

```yaml
# docker-compose.yml
version: '3.8'

services:
  nanobot-gateway:
    build: .
    container_name: nanobot-gateway
    restart: unless-stopped
    ports:
      - "18790:18790"
    volumes:
      - ~/.nanobot:/root/.nanobot:rw
    environment:
      - NANOBOT_LOG_LEVEL=INFO
    command: gateway
    healthcheck:
      test: ["CMD", "nanobot", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 可选: 搭配反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - nanobot-gateway
```

#### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir nanobot-ai

# 运行网关
EXPOSE 18790
CMD ["nanobot", "gateway"]
```

#### 部署步骤

```bash
# 1. 构建镜像
docker build -t nanobot:latest .

# 2. 初始化配置 (一次性)
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard

# 3. 编辑配置
vim ~/.nanobot/config.json

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

### 3.2 Linux Systemd 服务

```ini
# ~/.config/systemd/user/nanobot-gateway.service
[Unit]
Description=Nanobot Gateway
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/nanobot gateway
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=%h

# 资源限制
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=default.target
```

```bash
# 启用并启动
systemctl --user daemon-reload
systemctl --user enable --now nanobot-gateway

# 查看状态
systemctl --user status nanobot-gateway

# 查看日志
journalctl --user -u nanobot-gateway -f

# 重启
systemctl --user restart nanobot-gateway
```

### 3.3 多实例部署

```bash
# 实例1: Telegram Bot
mkdir -p ~/.nanobot-telegram
nanobot onboard --config ~/.nanobot-telegram/config.json
vim ~/.nanobot-telegram/config.json
nanobot gateway --config ~/.nanobot-telegram/config.json --port 18790

# 实例2: Discord Bot
mkdir -p ~/.nanobot-discord
nanobot onboard --config ~/.nanobot-discord/config.json
vim ~/.nanobot-discord/config.json
nanobot gateway --config ~/.nanobot-discord/config.json --port 18791

# 实例3: API服务
mkdir -p ~/.nanobot-api
nanobot onboard --config ~/.nanobot-api/config.json
vim ~/.nanobot-api/config.json
nanobot gateway --config ~/.nanobot-api/config.json --port 18792
```

**Nginx 反向代理配置**:
```nginx
# /etc/nginx/conf.d/nanobot.conf

upstream nanobot_backend {
    least_conn;
    server 127.0.0.1:18790;
    server 127.0.0.1:18791;
    server 127.0.0.1:18792;
}

server {
    listen 80;
    server_name nanobot.yourdomain.com;

    location / {
        proxy_pass http://nanobot_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## 4. 配置管理

### 4.1 配置文件结构

```
~/.nanobot/
├── config.json          # 主配置
├── workspace/           # 工作区
│   ├── skills/         # 技能文件
│   ├── memory/         # 记忆存储
│   ├── HEARTBEAT.md    # 心跳任务
│   ├── AGENTS.md       # Agent定义
│   └── SOUL.md         # 个性化定义
├── sessions/           # 会话数据
├── cron/              # 定时任务
└── media/             # 媒体文件
```

### 4.2 完整配置示例

```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4",
      "provider": "openrouter",
      "workspace": "~/.nanobot/workspace",
      "temperature": 0.7,
      "maxTokens": 4096,
      "thinkingMode": false
    },
    "coder": {
      "model": "openai-codex/gpt-5.1-codex",
      "temperature": 0.2,
      "workspace": "~/projects"
    }
  },
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx",
      "timeout": 60
    },
    "anthropic": {
      "apiKey": "sk-ant-xxx"
    },
    "deepseek": {
      "apiKey": "sk-xxx",
      "apiBase": "https://api.deepseek.com"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"],
      "groupPolicy": "mention"
    },
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"],
      "groupPolicy": "mention"
    }
  },
  "tools": {
    "restrictToWorkspace": true,
    "execPathAppend": "/usr/local/bin:/opt/bin",
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/.nanobot/workspace"],
        "toolTimeout": 60
      },
      "brave-search": {
        "url": "https://api.brave.com/mcp",
        "headers": {
          "Authorization": "Bearer xxx"
        }
      }
    }
  },
  "gateway": {
    "port": 18790,
    "host": "0.0.0.0",
    "logLevel": "INFO"
  }
}
```

### 4.3 环境变量配置

```bash
# ~/.bashrc 或 ~/.zshrc

# LLM API Keys (比config.json更安全，不进入版本控制)
export OPENROUTER_API_KEY="sk-or-v1-xxx"
export ANTHROPIC_API_KEY="sk-ant-xxx"
export DEEPSEEK_API_KEY="sk-xxx"

# nanobot 配置
export NANOBOT_LOG_LEVEL="INFO"
export NANOBOT_CONFIG_PATH="/etc/nanobot/config.json"
export NANOBOT_WORKSPACE="/var/lib/nanobot/workspace"

# 代理设置 (如果需要)
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
```

### 4.4 配置验证

```bash
# 验证配置语法
nanobot status

# 详细配置信息
nanobot status --verbose

# 测试Provider连接
nanobot provider test openrouter

# 测试Channel连接
nanobot channels status
```

---

## 5. 监控与日志

### 5.1 日志配置

```json
// config.json
{
  "gateway": {
    "logLevel": "INFO",  // DEBUG, INFO, WARNING, ERROR
    "logFormat": "json"  // text 或 json
  }
}
```

### 5.2 日志查看

```bash
# 实时日志
nanobot gateway --logs

# 日志文件位置 (Linux/Mac)
tail -f ~/.nanobot/logs/nanobot.log

# 按级别过滤
nanobot gateway --logs | grep ERROR

# JSON格式日志处理
nanobot gateway --logs --format json | jq '.level == "ERROR"'
```

### 5.3 健康检查

```bash
# HTTP健康检查端点
curl http://localhost:18790/health

# 预期响应
{
  "status": "healthy",
  "version": "0.1.4.post4",
  "uptime": 3600,
  "channels": {
    "telegram": "connected",
    "discord": "connected"
  },
  "providers": {
    "openrouter": "available"
  }
}
```

### 5.4 指标监控 (Prometheus)

```python
# nanobot 内置 Prometheus 指标

# 消息计数
nanobot_messages_total{channel="telegram"} 1523
nanobot_messages_total{channel="discord"} 892

# LLM调用
nanobot_llm_calls_total{provider="openrouter",model="claude-sonnet-4"} 2341
nanobot_llm_latency_seconds{quantile="0.99"} 2.5

# 工具执行
nanobot_tool_executions_total{tool="shell"} 423
nanobot_tool_executions_total{tool="filesystem"} 891

# 错误率
nanobot_errors_total{type="llm_timeout"} 12
```

**Prometheus 配置**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'nanobot'
    static_configs:
      - targets: ['localhost:18790']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 5.5 Grafana 仪表盘

```json
{
  "dashboard": {
    "title": "nanobot Monitoring",
    "panels": [
      {
        "title": "Messages per Minute",
        "targets": [
          {
            "expr": "rate(nanobot_messages_total[1m])"
          }
        ]
      },
      {
        "title": "LLM Latency",
        "targets": [
          {
            "expr": "nanobot_llm_latency_seconds{quantile=\"0.99\"}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(nanobot_errors_total[5m])"
          }
        ]
      }
    ]
  }
}
```

---

## 6. 安全最佳实践

### 6.1 访问控制

```json
// config.json - 安全配置
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "${TELEGRAM_BOT_TOKEN}",  // 使用环境变量
      "allowFrom": ["12345678"],  // 明确白名单
      "groupPolicy": "mention"     // 群组中仅响应@提及
    }
  },
  "tools": {
    "restrictToWorkspace": true,   // 限制文件操作范围
    "execPathAppend": ""           // 限制命令执行路径
  }
}
```

### 6.2 API Key 管理

```bash
# 不推荐: 直接写在config.json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"  // ❌ 不安全
    }
  }
}

# 推荐: 使用环境变量
{
  "providers": {
    "openrouter": {
      "apiKey": "${OPENROUTER_API_KEY}"  // ✅ 安全
    }
  }
}

# 或完全省略，自动读取环境变量
{
  "providers": {
    "openrouter": {}  // 自动读取 OPENROUTER_API_KEY
  }
}
```

### 6.3 网络安全

```bash
# 防火墙规则 (iptables)
# 仅允许必要端口
iptables -A INPUT -p tcp --dport 18790 -s 127.0.0.1 -j ACCEPT  # 仅本地
iptables -A INPUT -p tcp --dport 18790 -j DROP                   # 拒绝其他

# SSL/TLS 配置 (使用反向代理)
# Nginx 配置
server {
    listen 443 ssl http2;
    server_name nanobot.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://127.0.0.1:18790;
    }
}
```

### 6.4 审计日志

```json
// config.json - 审计配置
{
  "gateway": {
    "auditLog": true,
    "auditLogPath": "/var/log/nanobot/audit.log",
    "auditEvents": [
      "message.received",
      "tool.executed",
      "file.accessed",
      "config.changed"
    ]
  }
}
```

---

## 7. 备份与恢复

### 7.1 备份策略

```bash
#!/bin/bash
# backup-nanobot.sh

BACKUP_DIR="/backups/nanobot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/nanobot_backup_$DATE.tar.gz"

# 创建备份
tar -czf $BACKUP_FILE \
    ~/.nanobot/config.json \
    ~/.nanobot/workspace/ \
    ~/.nanobot/sessions/ \
    ~/.nanobot/cron/

# 保留最近30个备份
ls -t $BACKUP_DIR/nanobot_backup_*.tar.gz | tail -n +31 | xargs rm -f

echo "Backup created: $BACKUP_FILE"
```

```bash
# 添加到 crontab (每日备份)
0 2 * * * /path/to/backup-nanobot.sh
```

### 7.2 恢复流程

```bash
# 1. 停止服务
systemctl --user stop nanobot-gateway

# 2. 恢复配置
tar -xzf nanobot_backup_20260310_020000.tar.gz -C ~/

# 3. 重启服务
systemctl --user start nanobot-gateway

# 4. 验证
nanobot status
```

### 7.3 迁移到新服务器

```bash
# 1. 旧服务器: 创建备份
tar -czf nanobot-migration.tar.gz ~/.nanobot/

# 2. 传输到新服务器
scp nanobot-migration.tar.gz new-server:~/

# 3. 新服务器: 安装nanobot
pip install nanobot-ai

# 4. 新服务器: 恢复配置
tar -xzf nanobot-migration.tar.gz -C ~/

# 5. 新服务器: 启动
nanobot gateway
```

---

## 8. 故障排查

### 8.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **无法启动** | 配置错误 | `nanobot status` 检查配置 |
| **Channel连接失败** | Token无效 | 检查token和权限 |
| **LLM调用超时** | 网络问题 | 增加timeout配置 |
| **内存溢出** | 历史过长 | 清理sessions目录 |
| **工具执行失败** | 权限不足 | 检查workspace权限 |
| **无响应** | allowFrom为空 | 配置用户白名单 |

### 8.2 调试模式

```bash
# 启用DEBUG日志
nanobot gateway --log-level DEBUG

# 测试单个Provider
nanobot agent -m "Hello" --provider openrouter --model gpt-4

# 测试Channel连接
nanobot channels test telegram

# 验证工具
nanobot tools test shell --command "echo test"
```

### 8.3 性能调优

```json
// 高性能配置
{
  "agents": {
    "defaults": {
      "maxTokens": 2048,        // 限制输出长度
      "temperature": 0.5        // 降低随机性
    }
  },
  "gateway": {
    "workers": 4,               // 增加工作进程
    "maxConnections": 100      // 限制连接数
  },
  "tools": {
    "timeout": 30              // 限制工具执行时间
  }
}
```

---

## 9. 升级维护

### 9.1 升级流程

```bash
# 1. 备份
./backup-nanobot.sh

# 2. 停止服务
systemctl --user stop nanobot-gateway

# 3. 升级
pip install -U nanobot-ai

# 4. 验证版本
nanobot --version

# 5. 检查配置兼容性
nanobot config validate

# 6. 启动服务
systemctl --user start nanobot-gateway

# 7. 验证功能
nanobot status
```

### 9.2 版本兼容性

| nanobot版本 | Python版本 | 配置变化 |
|-------------|------------|----------|
| 0.1.4.post4 | 3.11+ | 当前版本 |
| 0.1.4 | 3.11+ | 新增MCP支持 |
| 0.1.3 | 3.11+ | 新增多Provider |
| 0.1.0 | 3.11+ | 初始版本 |

---

## 参考文档

- [Architecture Overview](./01-architecture-overview.md) - 架构总览
- [Core Modules](./02-core-modules.md) - 核心模块详解
- [OpenClaw Comparison](./03-openclaw-comparison.md) - 与OpenClaw对比
