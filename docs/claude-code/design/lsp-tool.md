# LSP 工具文档

## 概述

LSP（Language Server Protocol）工具通过与不同编程语言配置的 LSP 服务器通信，提供代码智能功能。它支持跳转到定义、查找引用、探索符号层级等操作，无需手动搜索代码。

## 文件结构

```
src/tools/LSPTool/
├── LSPTool.ts          # 主工具实现
├── prompt.ts           # 工具描述和元数据
├── schemas.ts          # Zod 输入验证 schema
├── formatters.ts       # 结果格式化工具
├── UI.tsx              # React UI 组件渲染
└── symbolContext.ts    # 光标位置符号提取
```

## 支持的操作

### 1. goToDefinition（跳转到定义）
查找符号（函数、类、变量等）的定义位置。

**使用场景：** 跳转到正在使用的函数或类型的源码定义。

### 2. findReferences（查找引用）
查找符号在代码库中的所有使用位置。

**使用场景：** 找出某个函数被调用的所有地方或某个变量的所有使用。

### 3. hover（悬停信息）
获取符号的悬停信息，包括文档和类型详情。

**使用场景：** 无需跳转即可快速查看类型信息或文档注释。

### 4. documentSymbol（文档符号）
列出文档中的所有符号（函数、类、接口等）。

**使用场景：** 获取文件的结构大纲。

### 5. workspaceSymbol（工作区符号）
在整个工作区中搜索符号。

**使用场景：** 不知道符号在哪个文件时，按名称查找特定的函数或类。

### 6. goToImplementation（跳转到实现）
查找接口或抽象方法的实现。

**使用场景：** 查看协议或抽象类的所有具体实现。

### 7. prepareCallHierarchy（准备调用层级）
获取指定位置的调用层级项（分析调用的前置步骤）。

**使用场景：** 分析函数调用者或被调用者的入口点。

### 8. incomingCalls（入站调用）
查找调用指定位置函数的所有函数/方法。

**使用场景：** 理解哪些代码依赖于某个特定函数。

### 9. outgoingCalls（出站调用）
查找指定位置函数调用的所有函数/方法。

**使用场景：** 理解函数内部依赖于什么。

## 输入参数

所有操作都需要以下参数：

| 参数 | 类型 | 描述 |
|------|------|------|
| `operation` | string | 9 种支持操作之一 |
| `filePath` | string | 文件的绝对或相对路径 |
| `line` | number | 行号（1-based，与编辑器显示一致） |
| `character` | number | 字符偏移量（1-based，与编辑器显示一致） |

## 输出格式

```typescript
{
  operation: string,           // 执行的操作
  result: string,              // 格式化的结果消息
  filePath: string,            // 执行操作的文件
  resultCount?: number,         // 找到的结果数量
  fileCount?: number,          // 包含结果的文件数量
}
```

## 使用示例

### 跳转到函数定义
```
operation: goToDefinition
filePath: src/utils/helper.ts
line: 42
character: 10
```
**结果:** `Defined in src/core/parser.ts:128:5`

### 查找所有引用
```
operation: findReferences
filePath: src/api/client.ts
line: 15
character: 8
```
**结果:**
```
Found 5 references across 3 files:

src/api/client.ts:
  Line 15:5

src/services/validator.ts:
  Line 23:8, Line 45:12

src/tests/client.test.ts:
  Line 89:3, Line 112:7
```

### 获取悬停信息
```
operation: hover
filePath: src/tools/lsp.ts
line: 100
character: 20
```
**结果:**
```
Hover info at 100:20:

function processFile(path: string): Promise<Result>
Processes a file and returns the processing result.
```

### 文档符号（大纲）
```
operation: documentSymbol
filePath: src/tools/lsp.ts
line: 1
character: 1
```
**结果:**
```
Document symbols:
  LSPTool (Class) - Line 1
    call (Method) - Line 45
    validateInput (Method) - Line 120
    formatResult (Method) - Line 280
  getMethodAndParams (Function) - Line 400
```

## 架构

### 工具注册
通过 `buildTool()` 注册，配置包括：
- `isLsp: true` - 标记为基于 LSP 的工具
- `shouldDefer: true` - 允许延迟执行
- `isReadOnly: true` - 只读操作
- `isConcurrencySafe: true` - 可安全并发执行

### LSP 服务器管理器集成
- 在发送请求前等待 LSP 服务器初始化
- 分析前自动将文件打开到 LSP 服务器
- 处理文件大小限制（最大 10MB）
- 从结果中过滤 gitignore 的文件

### 符号提取（`symbolContext.ts`）
- 提取光标位置的符号用于显示上下文
- 为性能只读取文件前 64KB
- 支持多种符号模式，包括：
  - 标准标识符（字母数字 + 下划线）
  - Rust 生命周期（`'a`、`'static`）
  - Rust 宏（`macro_name!`）
  - 运算符和特殊符号

### 结果格式化（`formatters.ts`）
处理全部 9 种操作的格式化：
- `formatGoToDefinitionResult()` - 定义位置
- `formatFindReferencesResult()` - 按文件分组的引用位置
- `formatHoverResult()` - 悬停文档
- `formatDocumentSymbolResult()` - 层级文档大纲
- `formatWorkspaceSymbolResult()` - 按文件分组的扁平符号列表
- `formatPrepareCallHierarchyResult()` - 调用层级项
- `formatIncomingCallsResult()` - 按文件分组的调用者
- `formatOutgoingCallsResult()` - 按文件分组的被调用者

### 错误处理
- 在 LSP 请求前验证文件存在和权限
- 优雅处理 LSP 服务器返回的 undefined/null URI
- 符号提取失败时回退到位置显示
- 记录格式错误的 LSP 响应用于调试

## UI 渲染（`UI.tsx`）

### 工具使用消息
- 显示操作类型和文件路径
- 对于基于位置的操作，显示提取的符号
- 符号提取失败时回退到显示位置（行:字符）

### 工具结果消息
- 对多结果操作使用可折叠/展开视图
- 显示摘要：「在 M 个文件中找到 N 个符号」
- 在展开视图中显示详细结果

### 错误消息
- 非 verbose 模式下显示「LSP 操作失败」
- verbose 模式下显示详细错误消息

## 安全

- 在 LSP 操作前验证文件存在
- 阻止 UNC 路径（Windows 网络路径）以防止 NTLM 凭证泄露
- 强制文件大小限制（10MB）
- 从结果中过滤 gitignore 的文件
- 通过 `checkReadPermissionForTool()` 检查读取权限

## 限制

1. **需要 LSP 服务器：** 如果文件类型没有配置 LSP 服务器，操作将失败
2. **文件大小限制：** 超过 10MB 的文件会被拒绝
3. **基于位置：** 部分操作需要特定光标位置（不仅仅是文件）
4. **服务器支持：** 不是所有 LSP 服务器都实现了全部操作（如调用层级）
