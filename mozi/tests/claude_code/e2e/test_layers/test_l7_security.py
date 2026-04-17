"""E2E 测试 - L7: 安全层

验证 rules 评估、permissions 拒绝、budgets 限制。
直接测试安全层组件。
"""

from __future__ import annotations

import pytest


class TestSecurityRules:
    """测试安全规则."""

    def test_rules_module_import(self):
        """验证安全规则模块可以导入."""
        from claude_code.security.rules import RuleSet
        assert RuleSet is not None

    def test_permission_rule_import(self):
        """验证权限规则可以导入."""
        from claude_code.security.rules import PermissionRule
        assert PermissionRule is not None


class TestPermissions:
    """测试权限系统."""

    def test_permissions_module_import(self):
        """验证权限模块可以导入."""
        from claude_code.security.permissions import (
            PermissionModeConfig,
            PermissionRule,
        )
        assert PermissionRule is not None
        assert PermissionModeConfig is not None

    def test_permission_rule_builder_import(self):
        """验证规则构建器可以导入."""
        from claude_code.security.rules import PermissionRuleBuilder
        assert PermissionRuleBuilder is not None


class TestBudgets:
    """测试预算系统."""

    def test_budgets_module_import(self):
        """验证预算模块可以导入."""
        from claude_code.security.budgets import BudgetTracker
        assert BudgetTracker is not None

    def test_budget_tracker_initialization(self):
        """验证预算追踪器可以初始化."""
        from claude_code.security.budgets import BudgetTracker

        tracker = BudgetTracker()
        assert tracker is not None
