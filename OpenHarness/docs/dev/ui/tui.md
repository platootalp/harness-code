# React TUI

OpenHarness 的终端用户界面（Terminal UI）由 React + Ink 构建，运行在 Node.js 环境中，通过 JSON 行协议与 Python 后端通信。

## 架构概览

```
frontend/terminal/
├── src/
│   ├── App.tsx              # 根组件，状态管理中枢
│   ├── index.tsx            # 入口点
│   ├── types.ts             # TypeScript 类型定义
│   ├── hooks/
│   │   └── useBackendSession.ts  # 后端通信 hook
│   ├── components/
│   │   ├── ConversationView.tsx   # 对话展示
│   │   ├── PromptInput.tsx        # 输入框
│   │   ├── StatusBar.tsx          # 状态栏
│   │   ├── CommandPicker.tsx      # 命令补全
│   │   ├── SelectModal.tsx        # 选择弹窗
│   │   ├── ModalHost.tsx          # 弹窗容器
│   │   ├── TodoPanel.tsx          # Todo 面板
│   │   ├── SwarmPanel.tsx         # Swarm 面板
│   │   ├── ToolCallDisplay.tsx    # 工具调用展示
│   │   └── ...
│   └── theme/
│       ├── ThemeContext.tsx       # 主题上下文
│       └── builtinThemes.ts       # 内置主题
└── package.json
```

## 技术栈

- **React 18** — UI 组件库
- **Ink 5** — React 的终端渲染引擎（替代 DOM）
- **TypeScript** — 类型安全
- **tsx** — 开发环境快速执行

## App 组件

`App.tsx` 是整个 TUI 的核心，包含：

### 状态管理

```typescript
function AppInner({config}: {config: FrontendConfig}): React.JSX.Element {
    const session = useBackendSession(config, () => exit());

    const [input, setInput] = useState('');           // 用户输入
    const [history, setHistory] = useState<string[]>([]);  // 命令历史
    const [selectModal, setSelectModal] = useState<...>(null);  // 选择弹窗
    const [busy, setBusy] = useState(false);          // 是否忙碌
    const [ready, setReady] = useState(false);       // 后端就绪
}
```

### 布局结构

```
┌─────────────────────────────────────────┐
│ ConversationView (flexGrow: 1)          │  ← 对话区域
│   - TranscriptPane                      │
│   - ToolCallDisplay                     │
│   - WelcomeBanner                       │
├─────────────────────────────────────────┤
│ ModalHost / SelectModal / CommandPicker │  ← 弹窗层
├─────────────────────────────────────────┤
│ TodoPanel / SwarmPanel                  │  ← 侧边面板
├─────────────────────────────────────────┤
│ StatusBar                               │  ← 状态栏
├─────────────────────────────────────────┤
│ PromptInput                             │  ← 输入框
├─────────────────────────────────────────┤
│ 键盘提示                                │  ← 底部提示
└─────────────────────────────────────────┘
```

## 后端通信协议

源码：`frontend/terminal/src/hooks/useBackendSession.ts`

### 协议格式

使用 JSON 行协议，每行以 `OHJSON:` 前缀开头：

```typescript
const PROTOCOL_PREFIX = 'OHJSON:';
// 后端发送: OHJSON:<JSON>\n
// 前端发送: <JSON>\n
```

### BackendEvent 类型

| 事件类型 | 触发时机 |
|----------|----------|
| `ready` | 后端初始化完成，发送初始状态 |
| `state_snapshot` | 状态快照更新 |
| `transcript_item` | 单条对话记录 |
| `assistant_delta` | Assistant 文本增量（流式） |
| `assistant_complete` | Assistant 回复完成 |
| `tool_started` | 工具开始执行 |
| `tool_completed` | 工具执行完成 |
| `select_request` | 需要用户选择（如 /resume） |
| `modal_request` | 需要用户确认（如权限弹窗） |
| `error` | 错误消息 |
| `shutdown` | 后端请求关闭 |

### FrontendRequest 类型

| 请求类型 | 说明 |
|----------|------|
| `submit_line` | 提交用户输入行 |
| `select_command` | 执行选择命令 |
| `apply_select_command` | 应用选择项 |
| `permission_response` | 权限响应（y/n） |
| `question_response` | 问题回答 |
| `shutdown` | 请求后端关闭 |

### 流式文本处理

```typescript
// 增量缓冲，避免每 token 触发重渲染
const ASSISTANT_DELTA_FLUSH_MS = 33;   // ~30fps
const ASSISTANT_DELTA_FLUSH_CHARS = 256;  // 或 256 字符
```

当 `assistant_delta` 事件到达时：
1. 累积到 `pendingAssistantDeltaRef`
2. 达到 256 字符或 33ms 后刷新到 UI
3. `assistant_complete` 时最终提交

## 组件详解

### ConversationView

展示对话历史，包括：
- `TranscriptItem`：角色（user/assistant/tool/system/log）
- `assistantBuffer`：流式文本（未完成）
- `ToolCallDisplay`：工具调用展示

### PromptInput

基于 `ink-text-input` 的输入框组件：
- 处理 Enter 提交（`onSubmit`）
- 支持 Tab 补全（命令补全）
- 工具执行期间显示工具名称

### CommandPicker

以 `/` 开头的命令自动触发补全：
```typescript
const SELECTABLE_COMMANDS = new Set([
    '/provider', '/model', '/theme', '/output-style',
    '/permissions', '/resume', '/effort', '/passes',
    '/turns', '/fast', '/vim', '/voice',
]);
```

### SelectModal

后端 `select_request` 事件触发的选择弹窗，支持：
- 上下箭头导航
- 数字键快速选择（1-9）
- Enter 确认，Escape 取消

### ModalHost

处理两类弹窗：
- **permission**：权限确认（y/n）
- **question**：自由文本回答

## 主题系统

```typescript
// builtinThemes.ts
export const builtinThemes: Record<string, Theme> = {
    default: { ... },
    // ...
};
```

通过 `ThemeContext` 提供主题，支持动态切换：
```typescript
const {theme, setThemeName} = useTheme();
```

## 入口点

`src/index.tsx` 使用 `render()` 渲染 `App`：
```typescript
import {render} from 'ink';
import {App} from './App.js';
render(<App config={config} />);
```

启动命令：
```bash
cd frontend/terminal && npm start
```

## 扩展指南

### 添加新组件

1. 在 `components/` 创建 `{ComponentName}.tsx`
2. 引入 React + Ink + TypeScript
3. 在 `App.tsx` 中导入并使用

### 添加新命令

1. 在 `SELECTABLE_COMMANDS` 中添加命令名
2. 在 `handleCommand()` 中添加处理逻辑：
```typescript
if (trimmed === '/mycommand') {
    session.sendRequest({type: 'select_command', command: 'mycommand'});
    return true;
}
```

### 添加新事件类型

1. 在 `types.ts` 中添加事件类型定义
2. 在 `useBackendSession.ts` 的 `handleEvent()` 中处理

## 关键文件

| 文件 | 职责 |
|------|------|
| `App.tsx` | 根组件，状态中枢，键盘处理 |
| `useBackendSession.ts` | 后端进程管理，协议编解码 |
| `types.ts` | TypeScript 类型定义 |
| `ConversationView.tsx` | 对话展示 |
| `PromptInput.tsx` | 文本输入 |
| `StatusBar.tsx` | 状态栏 |
| `CommandPicker.tsx` | 命令补全 |
| `SelectModal.tsx` | 选择弹窗 |
| `ModalHost.tsx` | 弹窗容器 |
| `ThemeContext.tsx` | 主题管理 |
