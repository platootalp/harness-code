# 代码风格命令

## Python

- 使用 Python 3.11+
- 行长度限制 100 字符
- 使用双引号
- 缩进 4 空格
- 导入排序: stdlib → third-party → local
- 禁止通配导入 `from module import *`
- 函数参数和返回值必须类型注解
- 类属性必须类型注解
- 模块级常量必须类型注解
- 公共函数必须文档字符串
- 使用 `async`/`await`，禁止回调风格
- 自定义异常继承 `MoziError`
- 使用 `from` 保留异常链
- 禁止捕获裸 `Exception`
- 模块命名: snake_case
- 类命名: PascalCase
- 函数命名: snake_case
- 常量命名: UPPER_SNAKE
- 私有成员前缀下划线

## TypeScript

- 使用 ES2022+
- 行长度限制 100 字符
- 使用双引号
- 缩进 2 空格
- 必须使用分号
- 函数参数和返回值必须类型注解
- 禁止 `any`，使用 `unknown`
- 接口使用 `interface`
- 联合类型使用 `type`
- 使用 `async`/`await`，禁止回调风格
- 使用自定义错误类继承 `Error`

---
*版本: 1.0 | 生效: 立即*
