"""Tests for security/permissions.py."""

from __future__ import annotations

from claude_code.security.permissions import (
    EXTERNAL_PERMISSION_MODES,
    INTERNAL_PERMISSION_MODES,
    PERMISSION_MODE_CONFIG,
    PERMISSION_MODES,
    AdditionalWorkingDirectory,
    ClassifierResult,
    ClassifierUsage,
    DecisionReasonClassifier,
    DecisionReasonHook,
    DecisionReasonMode,
    DecisionReasonOther,
    DecisionReasonRule,
    DecisionReasonSafetyCheck,
    PendingClassifierCheck,
    PermissionAllowDecision,
    PermissionAskDecision,
    PermissionDenyDecision,
    PermissionExplanation,
    PermissionMode,
    PermissionModeConfig,
    PermissionPassthroughDecision,
    PermissionRule,
    PermissionRuleValue,
    ToolPermissionContext,
    YoloClassifierResult,
    check_tool_permission,
    get_empty_tool_permission_context,
    get_mode_color,
    get_rule_behavior_description,
    is_default_mode,
    is_external_permission_mode,
    permission_mode_from_string,
    permission_mode_short_title,
    permission_mode_symbol,
    permission_mode_title,
    to_external_permission_mode,
)


class TestPermissionModes:
    def test_external_permission_modes(self) -> None:
        """EXTERNAL_PERMISSION_MODES should contain expected modes."""
        assert "acceptEdits" in EXTERNAL_PERMISSION_MODES
        assert "bypassPermissions" in EXTERNAL_PERMISSION_MODES
        assert "default" in EXTERNAL_PERMISSION_MODES
        assert "dontAsk" in EXTERNAL_PERMISSION_MODES
        assert "plan" in EXTERNAL_PERMISSION_MODES

    def test_internal_permission_modes_extends_external(self) -> None:
        """INTERNAL_PERMISSION_MODES should extend external with internal modes."""
        assert "auto" in INTERNAL_PERMISSION_MODES
        assert "bubble" in INTERNAL_PERMISSION_MODES

    def test_permission_modes_matches_internal(self) -> None:
        """PERMISSION_MODES should match INTERNAL_PERMISSION_MODES."""
        assert PERMISSION_MODES == INTERNAL_PERMISSION_MODES

    def test_permission_mode_from_string_valid(self) -> None:
        """permission_mode_from_string should return valid modes."""
        assert permission_mode_from_string("default") == "default"
        assert permission_mode_from_string("plan") == "plan"
        assert permission_mode_from_string("acceptEdits") == "acceptEdits"

    def test_permission_mode_from_string_invalid(self) -> None:
        """permission_mode_from_string should return default for invalid."""
        assert permission_mode_from_string("invalid") == "default"
        assert permission_mode_from_string("") == "default"

    def test_is_external_permission_mode(self) -> None:
        """is_external_permission_mode should exclude auto and bubble."""
        assert is_external_permission_mode("default")
        assert is_external_permission_mode("plan")
        assert is_external_permission_mode("acceptEdits")
        assert not is_external_permission_mode("auto")
        assert not is_external_permission_mode("bubble")

    def test_to_external_permission_mode(self) -> None:
        """to_external_permission_mode should convert correctly."""
        assert to_external_permission_mode("default") == "default"
        assert to_external_permission_mode("plan") == "plan"
        assert to_external_permission_mode("acceptEdits") == "acceptEdits"
        assert to_external_permission_mode("auto") == "default"
        assert to_external_permission_mode("bubble") == "default"


class TestModeDisplayFunctions:
    def test_permission_mode_title(self) -> None:
        """permission_mode_title should return correct titles."""
        assert permission_mode_title("default") == "Default"
        assert permission_mode_title("plan") == "Plan Mode"
        assert permission_mode_title("acceptEdits") == "Accept edits"
        assert permission_mode_title("bypassPermissions") == "Bypass Permissions"

    def test_permission_mode_short_title(self) -> None:
        """permission_mode_short_title should return correct short titles."""
        assert permission_mode_short_title("default") == "Default"
        assert permission_mode_short_title("plan") == "Plan"
        assert permission_mode_short_title("acceptEdits") == "Accept"

    def test_permission_mode_symbol(self) -> None:
        """permission_mode_symbol should return correct symbols."""
        assert permission_mode_symbol("default") == ""
        assert permission_mode_symbol("plan") == "⏵⏵"
        assert permission_mode_symbol("auto") == "⏵⏵"

    def test_get_mode_color(self) -> None:
        """get_mode_color should return correct colors."""
        assert get_mode_color("default") == "text"
        assert get_mode_color("plan") == "planMode"
        assert get_mode_color("acceptEdits") == "autoAccept"
        assert get_mode_color("bypassPermissions") == "error"
        assert get_mode_color("auto") == "warning"

    def test_is_default_mode(self) -> None:
        """is_default_mode should correctly identify default modes."""
        assert is_default_mode("default")
        assert is_default_mode(None)
        assert not is_default_mode("plan")
        assert not is_default_mode("acceptEdits")


class TestPermissionRuleValue:
    def test_creation(self) -> None:
        """PermissionRuleValue should accept tool_name and optional rule_content."""
        rv = PermissionRuleValue(tool_name="Bash")
        assert rv.tool_name == "Bash"
        assert rv.rule_content is None

        rv2 = PermissionRuleValue(tool_name="Bash", rule_content="rm -rf")
        assert rv2.tool_name == "Bash"
        assert rv2.rule_content == "rm -rf"


class TestPermissionRule:
    def test_creation(self) -> None:
        """PermissionRule should accept source, behavior, and value."""
        rule = PermissionRule(
            source="userSettings",
            rule_behavior="allow",
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert rule.source == "userSettings"
        assert rule.rule_behavior == "allow"
        assert rule.rule_value.tool_name == "Bash"


class TestToolPermissionContext:
    def test_default_context(self) -> None:
        """ToolPermissionContext should have sensible defaults."""
        ctx = ToolPermissionContext()
        assert ctx.mode == "default"
        assert ctx.additional_working_directories == {}
        assert ctx.always_allow_rules == {}
        assert ctx.always_deny_rules == {}
        assert ctx.always_ask_rules == {}
        assert ctx.is_bypass_permissions_mode_available is False

    def test_context_with_mode(self) -> None:
        """ToolPermissionContext should accept custom mode."""
        ctx = ToolPermissionContext(mode="plan")
        assert ctx.mode == "plan"

    def test_get_empty_tool_permission_context(self) -> None:
        """Factory function should return default context."""
        ctx = get_empty_tool_permission_context()
        assert isinstance(ctx, ToolPermissionContext)
        assert ctx.mode == "default"


class TestPermissionDecisions:
    def test_permission_allow_decision(self) -> None:
        """PermissionAllowDecision should have allow behavior."""
        decision = PermissionAllowDecision()
        assert decision.behavior == "allow"

    def test_permission_allow_decision_with_details(self) -> None:
        """PermissionAllowDecision should accept all fields."""
        decision = PermissionAllowDecision(
            updated_input={"command": "ls"},
            user_modified=True,
            tool_use_id="abc123",
        )
        assert decision.behavior == "allow"
        assert decision.updated_input == {"command": "ls"}
        assert decision.user_modified is True
        assert decision.tool_use_id == "abc123"

    def test_permission_ask_decision(self) -> None:
        """PermissionAskDecision should have ask behavior."""
        decision = PermissionAskDecision(message="Run rm?")
        assert decision.behavior == "ask"
        assert decision.message == "Run rm?"

    def test_permission_ask_decision_with_classifier(self) -> None:
        """PermissionAskDecision should accept pending classifier check."""
        check = PendingClassifierCheck(
            command="rm -rf",
            cwd="/tmp",
            descriptions=("dangerous command",),
        )
        decision = PermissionAskDecision(
            message="Run rm?",
            pending_classifier_check=check,
        )
        assert decision.behavior == "ask"
        assert decision.pending_classifier_check is not None
        assert decision.pending_classifier_check.command == "rm -rf"

    def test_permission_deny_decision(self) -> None:
        """PermissionDenyDecision should have deny behavior."""
        decision = PermissionDenyDecision(
            message="Denied",
            decision_reason=DecisionReasonMode(type="mode", mode="bypassPermissions"),
        )
        assert decision.behavior == "deny"
        assert decision.message == "Denied"

    def test_permission_passthrough_decision(self) -> None:
        """PermissionPassthroughDecision should have passthrough behavior."""
        decision = PermissionPassthroughDecision(message="Passed to hook")
        assert decision.behavior == "passthrough"


class TestDecisionReasons:
    def test_decision_reason_rule(self) -> None:
        """DecisionReasonRule should capture rule-based decisions."""
        rule = PermissionRule(
            source="userSettings",
            rule_behavior="allow",
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        reason = DecisionReasonRule(rule=rule)
        assert reason.type == "rule"
        assert reason.rule == rule

    def test_decision_reason_mode(self) -> None:
        """DecisionReasonMode should capture mode-based decisions."""
        reason = DecisionReasonMode(type="mode", mode="plan")
        assert reason.type == "mode"
        assert reason.mode == "plan"

    def test_decision_reason_hook(self) -> None:
        """DecisionReasonHook should capture hook-based decisions."""
        reason = DecisionReasonHook(
            type="hook",
            hook_name="pre_tool_check",
            hook_source="hooks.ts",
            reason="Tool not allowed",
        )
        assert reason.type == "hook"
        assert reason.hook_name == "pre_tool_check"

    def test_decision_reason_classifier(self) -> None:
        """DecisionReasonClassifier should capture classifier decisions."""
        reason = DecisionReasonClassifier(
            type="classifier",
            classifier="yolo",
            reason="dangerous pattern detected",
        )
        assert reason.type == "classifier"
        assert reason.classifier == "yolo"

    def test_decision_reason_safety_check(self) -> None:
        """DecisionReasonSafetyCheck should capture safety check decisions."""
        reason = DecisionReasonSafetyCheck(
            type="safetyCheck",
            reason="dangerous pattern",
            classifier_approvable=True,
        )
        assert reason.type == "safetyCheck"
        assert reason.classifier_approvable is True

    def test_decision_reason_other(self) -> None:
        """DecisionReasonOther should capture miscellaneous decisions."""
        reason = DecisionReasonOther(type="other", reason="Custom reason")
        assert reason.type == "other"
        assert reason.reason == "Custom reason"


class TestRuleBehaviorDescription:
    def test_allow_description(self) -> None:
        """get_rule_behavior_description should return 'allowed' for allow."""
        assert get_rule_behavior_description("allow") == "allowed"

    def test_deny_description(self) -> None:
        """get_rule_behavior_description should return 'denied' for deny."""
        assert get_rule_behavior_description("deny") == "denied"

    def test_ask_description(self) -> None:
        """get_rule_behavior_description should return confirmation text for ask."""
        assert get_rule_behavior_description("ask") == "asked for confirmation for"


class TestClassifierTypes:
    def test_classifier_result(self) -> None:
        """ClassifierResult should capture classifier evaluation results."""
        result = ClassifierResult(
            matches=True,
            confidence="high",
            reason="safe command",
            matched_description="ls is safe",
        )
        assert result.matches is True
        assert result.confidence == "high"

    def test_classifier_usage(self) -> None:
        """ClassifierUsage should capture token usage."""
        usage = ClassifierUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=20,
            cache_creation_input_tokens=10,
        )
        assert usage.input_tokens == 100
        assert usage.cache_read_input_tokens == 20

    def test_yolo_classifier_result(self) -> None:
        """YoloClassifierResult should capture YOLO classifier results."""
        result = YoloClassifierResult(
            should_block=False,
            reason="command appears safe",
            model="claude-3-5",
            thinking="Analyzing...",
            usage=ClassifierUsage(input_tokens=100),
            duration_ms=500,
        )
        assert result.should_block is False
        assert result.model == "claude-3-5"
        assert result.usage is not None


class TestPermissionExplanation:
    def test_permission_explanation(self) -> None:
        """PermissionExplanation should capture explanation details."""
        explanation = PermissionExplanation(
            risk_level="HIGH",
            explanation="This command removes files",
            reasoning="rm -rf is destructive",
            risk="File deletion",
        )
        assert explanation.risk_level == "HIGH"
        assert "removes files" in explanation.explanation


class TestPermissionModeConfig:
    def test_config_fields(self) -> None:
        """PermissionModeConfig should have correct field values."""
        config = PERMISSION_MODE_CONFIG["plan"]
        assert config.title == "Plan Mode"
        assert config.short_title == "Plan"
        assert config.symbol == "⏵⏵"
        assert config.color == "planMode"
        assert config.external == "plan"

    def test_all_modes_have_config(self) -> None:
        """All permission modes should have a config entry."""
        for mode in PERMISSION_MODES:
            assert mode in PERMISSION_MODE_CONFIG, f"Missing config for {mode}"


class TestAdditionalWorkingDirectory:
    def test_creation(self) -> None:
        """AdditionalWorkingDirectory should store path and source."""
        dir = AdditionalWorkingDirectory(path="/tmp/build", source="projectSettings")
        assert dir.path == "/tmp/build"
        assert dir.source == "projectSettings"


class TestCheckToolPermission:
    def test_deny_rule_blocks_tool(self) -> None:
        """Tool in deny_rules should return deny decision."""
        ctx = ToolPermissionContext(
            always_deny_rules={"userSettings": ("Bash",)},
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "deny"
        assert isinstance(result, PermissionDenyDecision)
        assert "has been denied" in result.message

    def test_ask_rule_returns_ask(self) -> None:
        """Tool in ask_rules should return ask decision."""
        ctx = ToolPermissionContext(
            always_ask_rules={"userSettings": ("Bash",)},
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "ask"
        assert isinstance(result, PermissionAskDecision)
        assert "required" in result.message

    def test_bypass_permissions_mode_always_allows(self) -> None:
        """bypassPermissions mode should always allow."""
        ctx = ToolPermissionContext(mode="bypassPermissions")
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "allow"
        assert isinstance(result, PermissionAllowDecision)
        assert isinstance(result.decision_reason, DecisionReasonMode)
        assert result.decision_reason.mode == "bypassPermissions"

    def test_plan_mode_with_bypass_available_allows(self) -> None:
        """plan mode with isBypassPermissionsModeAvailable should allow."""
        ctx = ToolPermissionContext(
            mode="plan",
            is_bypass_permissions_mode_available=True,
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "allow"
        assert isinstance(result, PermissionAllowDecision)

    def test_plan_mode_without_bypass_prompts(self) -> None:
        """plan mode without bypass available should return passthrough."""
        ctx = ToolPermissionContext(
            mode="plan",
            is_bypass_permissions_mode_available=False,
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "passthrough"
        assert isinstance(result, PermissionPassthroughDecision)

    def test_allow_rule_returns_allow(self) -> None:
        """Tool in always_allow_rules should return allow decision."""
        ctx = ToolPermissionContext(
            always_allow_rules={"userSettings": ("Bash",)},
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "allow"
        assert isinstance(result, PermissionAllowDecision)
        assert isinstance(result.decision_reason, DecisionReasonRule)

    def test_default_mode_returns_passthrough(self) -> None:
        """Default mode with no rules should return passthrough."""
        ctx = ToolPermissionContext(mode="default")
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "passthrough"
        assert isinstance(result, PermissionPassthroughDecision)

    def test_wildcard_rule_matches_all_tools(self) -> None:
        """Wildcard rule (*) should match all tools."""
        ctx = ToolPermissionContext(
            always_allow_rules={"userSettings": ("*",)},
        )
        result = check_tool_permission("AnyTool", ctx)
        assert result.behavior == "allow"

    def test_deny_rule_takes_precedence_over_allow(self) -> None:
        """Deny rules should take precedence over allow rules."""
        ctx = ToolPermissionContext(
            always_deny_rules={"userSettings": ("Bash",)},
            always_allow_rules={"userSettings": ("Bash",)},
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "deny"

    def test_deny_rule_takes_precedence_over_ask(self) -> None:
        """Deny rules should take precedence over ask rules."""
        ctx = ToolPermissionContext(
            always_deny_rules={"userSettings": ("Bash",)},
            always_ask_rules={"userSettings": ("Bash",)},
        )
        result = check_tool_permission("Bash", ctx)
        assert result.behavior == "deny"

    def test_unknown_tool_with_no_rules(self) -> None:
        """Unknown tool with no rules should return passthrough."""
        ctx = ToolPermissionContext(mode="default")
        result = check_tool_permission("UnknownTool", ctx)
        assert result.behavior == "passthrough"

