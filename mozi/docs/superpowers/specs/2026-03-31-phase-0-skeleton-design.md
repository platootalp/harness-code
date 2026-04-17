# Phase 0 基础设施搭建 - 设计方案

## 概述

创建 `scripts/bootstrap_project.py` 脚本，读取 `docs/init/tasks/phase_0.json` 自动生成完整的项目骨架。

## 脚本逻辑

1. 读取 `docs/init/tasks/phase_0.json` 获取任务列表
2. 遍历 `iterations[].tasks[].children` 创建目录和文件
3. 配置文件用预定义模板生成
4. 支持幂等运行（`--force` 强制覆盖）

## 生成的目录结构

```
mozi/
├── __init__.py
├── __version__.py           # __version__ = "0.1.0"
├── exceptions.py            # MoziError 基类 + 通用异常类
├── ingress/__init__.py
├── session/__init__.py
├── orchestrator/
│   ├── __init__.py
│   ├── core/__init__.py
│   └── workers/__init__.py
├── core/
│   ├── __init__.py
│   ├── model/__init__.py
│   └── tools/
│       ├── __init__.py
│       ├── builtin/__init__.py
│       ├── analysis/__init__.py
│       └── external/__init__.py
├── context/__init__.py
├── memory/
│   ├── __init__.py
│   └── stores/__init__.py
├── infrastructure/__init__.py

tests/
├── unit/__init__.py
├── integration/__init__.py
└── e2e/__init__.py

docs/foundation/architecture/

.claude/rules/
├── coding-style.md
├── ci-cd.md
├── testing.md
├── workflow.md
├── security.md
└── documentation.md

pyproject.toml
ruff.toml
mypy.ini
pytest.ini
bandit.toml
.pre-commit-config.yaml
.gitignore
```

## 配置文件模板

### pyproject.toml
- 项目名: mozi
- Python: >=3.11
- 依赖: httpx, pydantic
- 开发依赖: ruff, mypy, pytest, pytest-cov, bandit

### ruff.toml
- 行长度: 100
- 双引号
- isort 排序

### mypy.ini
- strict = true
- python_version = 3.11

### pytest.ini
- testpaths = tests
- markers = unit, integration, e2e, slow

### bandit.toml
- 扫描 mozi/ 目录
- 详情级别: low

### .pre-commit-config.yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
- hooks: trailing-whitespace, end-of-file-fixer, check-yaml
- repo: local (ruff)

### .gitignore
- Python 标准忽略项
- .venv/, __pycache__/, *.pyc
- .coverage, htmlcov/
- dist/, build/, *.egg-info/

## 异常类模板

```python
class MoziError(Exception):
    """Base exception for src."""
    pass

class ConfigurationError(MoziError):
    """Configuration related errors."""
    pass

class ExecutionError(MoziError):
    """Execution related errors."""
    pass
```

## 使用方式

```bash
# 生成完整骨架
python scripts/bootstrap_project.py

# 强制覆盖已存在的文件
python scripts/bootstrap_project.py --force
```

## 验证

生成后运行：
- `uv sync` 安装依赖
- `ruff check mozi/` 应无错误
- `mypy mozi/` 应无错误
- `pytest tests/` 应通过
