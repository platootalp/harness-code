# 认证系统

本文档介绍 OpenHarness 的认证架构，包括 Auth Manager、认证 Flow 和凭证存储。

## 架构概览

```
src/openharness/auth/
├── manager.py      # AuthManager — 中心认证权威
├── flows.py        # 交互式认证 Flow
├── storage.py      # 凭证存储（文件/keyring）
└── external.py     # 外部 CLI 绑定（Claude CLI 等）
```

## AuthManager

`manager.py` 中的 `AuthManager` 是整个认证系统的中心入口：

```python
class AuthManager:
    """Central authority for provider authentication state."""
```

### 核心职责

1. **Provider 状态追踪** — `get_auth_status()` 返回所有已知 Provider 的认证状态
2. **Profile 管理** — `use_profile()` / `upsert_profile()` / `update_profile()` 等
3. **凭证 CRUD** — `store_credential()` / `clear_credential()`
4. **Auth Source 切换** — `switch_auth_source()`

### 已知 Providers

```python
_KNOWN_PROVIDERS = [
    "anthropic",        # API Key
    "anthropic_claude", # Claude Subscription (OAuth)
    "openai",           # API Key
    "openai_codex",     # Codex Subscription (OAuth)
    "copilot",          # GitHub OAuth
    "dashscope",        # API Key
    "bedrock",          # AWS 凭证
    "vertex",           # GCP 凭证
    "moonshot",         # API Key
]
```

### Auth Sources

```python
_AUTH_SOURCES = [
    "anthropic_api_key",
    "openai_api_key",
    "codex_subscription",
    "claude_subscription",
    "copilot_oauth",
    "dashscope_api_key",
    "bedrock_api_key",
    "vertex_api_key",
    "moonshot_api_key",
]
```

### Profile 与 Provider 映射

```python
_PROFILE_BY_PROVIDER = {
    "anthropic": "claude-api",
    "anthropic_claude": "claude-subscription",
    "openai": "openai-compatible",
    "openai_codex": "codex",
    "copilot": "copilot",
    "moonshot": "moonshot",
}
```

## 认证 Flow

`flows.py` 定义了三种交互式认证 Flow，继承自 `AuthFlow` 抽象基类：

```python
class AuthFlow(ABC):
    @abstractmethod
    def run(self) -> str:
        """Execute the flow and return the obtained credential value."""
```

### ApiKeyFlow

直接提示用户输入 API Key 并通过 storage 持久化：

```python
class ApiKeyFlow(AuthFlow):
    def __init__(self, provider: str, prompt_text: str | None = None) -> None:
        self.provider = provider
        self.prompt_text = prompt_text or f"Enter your {provider} API key"

    def run(self) -> str:
        key = getpass.getpass(f"{self.prompt_text}: ").strip()
        if not key:
            raise ValueError("API key cannot be empty.")
        return key
```

### DeviceCodeFlow

GitHub OAuth Device Code Flow，适用于 Copilot：

```python
class DeviceCodeFlow(AuthFlow):
    def __init__(
        self,
        client_id: str | None = None,
        github_domain: str = "github.com",
        enterprise_url: str | None = None,
        *,
        progress_callback: Any | None = None,
    ) -> None:
```

流程：
1. 请求 Device Code
2. 打印验证 URL 和用户码
3. 自动尝试打开浏览器
4. 轮询访问令牌（支持自定义进度回调）

### BrowserFlow

打开浏览器让用户完成认证，然后粘贴返回的 Token：

```python
class BrowserFlow(AuthFlow):
    def __init__(self, auth_url: str, prompt_text: str = "Paste the token from your browser") -> None:
        self.auth_url = auth_url
        self.prompt_text = prompt_text
```

## 凭证存储

`storage.py` 提供两种存储后端：

### 文件存储（默认）

路径：`~/.openharness/credentials.json`（权限 600）

```python
def store_credential(provider: str, key: str, value: str, *, use_keyring: bool | None = None) -> None:
def load_credential(provider: str, key: str, *, use_keyring: bool | None = None) -> str | None:
def clear_provider_credentials(provider: str, *, use_keyring: bool | None = None) -> None:
```

### Keyring 存储（可选）

如果 `keyring` 包已安装，自动优先使用系统 keyring。可用时自动降级到文件。

### 外部认证绑定

支持绑定到外部 CLI（如 Claude CLI）管理的凭证：

```python
@dataclass(frozen=True)
class ExternalAuthBinding:
    provider: str
    source_path: str       # 外部 CLI 路径
    source_kind: str       # 绑定类型
    managed_by: str        # 管理方标识
    profile_label: str = ""
```

### 轻量级混淆

凭证文件使用 XOR 混淆（不是真正的加密）：
- `encrypt()` — base64(XOR)
- `decrypt()` — 逆向

## Auth 状态检测

```python
def auth_status(settings: Settings) -> str:
    """Return a compact auth status string."""
```

- 检查环境变量 `ANTHROPIC_API_KEY`、`OPENAI_API_KEY`
- 检查文件/keyring 中的存储凭证
- 检查外部绑定（Claude OAuth、Codex Subscription）
- 检查 Copilot OAuth 文件

## Provider 能力检测

`provider.py` 中的 `detect_provider()` 推断活跃 Provider 的能力：

```python
@dataclass(frozen=True)
class ProviderInfo:
    name: str           # "anthropic", "openai-compatible", "github_copilot" 等
    auth_kind: str      # "api_key", "oauth_device", "external_oauth"
    voice_supported: bool
    voice_reason: str   # 不支持时的原因
```

## 扩展指南

### 添加新的 Provider

1. 在 `_KNOWN_PROVIDERS` 列表中添加 Provider 名称
2. 在 `get_auth_status()` 中添加凭证检测逻辑
3. 在 `_PROFILE_BY_PROVIDER` 中添加到 Profile 的映射
4. 如需特殊 Flow，在 `flows.py` 中实现新的 `AuthFlow`

### 添加新的 Auth Source

1. 在 `_AUTH_SOURCES` 列表中添加 Source 名称
2. 在 `get_auth_source_statuses()` 中添加检测逻辑
3. 更新 `switch_auth_source()` 的验证列表

## 关键文件

| 文件 | 职责 |
|------|------|
| `manager.py` | 认证中心、Profile/Provider 管理 |
| `flows.py` | 交互式认证流程（API Key、OAuth Device Code、Browser） |
| `storage.py` | 文件/keyring 凭证存储 |
| `external.py` | 外部 CLI 绑定（Claude OAuth） |
| `provider.py` | Provider 能力检测 |
