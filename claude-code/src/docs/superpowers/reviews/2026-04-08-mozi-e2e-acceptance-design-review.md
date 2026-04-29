# Mozi E2E Acceptance Design Review

**Review Date:** 2026-04-08 (Initial), 2026-04-09 (Update)
**Reviewer:** Code Reviewer (AI)
**Document:** `docs/superpowers/specs/2026-04-08-mozi-e2e-acceptance-design.md`
**Git Range:** `93077c1..89b5e59` (Initial), `89b5e59..788ee05` (Update)

---

## Assessment Summary

**Ready to implement?** No

**Reasoning:** The design has a solid structure with good coverage and realistic phases, but contains critical implementation blockers that must be addressed before Phase 1 can proceed.

---

## Strengths

- **Comprehensive matrix**: The 8 scenarios × 9 layers coverage matrix is well-structured and ensures no critical paths are missed
- **Realistic scope**: Using real Claude API calls validates the complete chain, not just mocks
- **Phase-based plan**: Breaking into 3 phases with increasing complexity is a sound approach
- **CI integration**: Standard GitHub Actions workflow with artifact upload is production-ready
- **Sensible constraints**: The `< 60s per test` and `independent tests` requirements are practical
- **CLI flags verified**: `--print` and `--permission-mode` exist in the codebase

---

## Issues

### Critical (Must Fix)

#### 1. Invalid pytest `--report` flag
- **Location:** e2e.sh:107, 136
- **Code:**
  ```bash
  pytest tests/e2e/ -v --report="$REPORT_FORMAT"
  ```
- **Problem:** Standard pytest does not have a `--report` flag. This requires a third-party plugin like `pytest-report` or custom implementation.
- **Impact:** JSON/HTML report generation cannot work as specified
- **Fix:** Either add `pytest-report` to dependencies, or implement a custom `pytest_terminal_summary` hook, or use `pytest --json-report` with `pytest-json-report` plugin

#### 2. `cli_process` fixture has no cleanup
- **Location:** conftest.py:88-92
- **Problem:** The fixture stub shows `async def cli_process(): ...` with no cleanup mechanism
- **Impact:** CLI processes started as subprocesses must be explicitly terminated to avoid zombie processes and port conflicts
- **Fix:** Add teardown logic using `async_generator` or `yield` pattern:
  ```python
  @pytest.fixture
  async def cli_process():
      proc = await subprocess.start(...)
      yield proc
      proc.terminate()
      await proc.wait()
  ```

#### 3. Layer scope selection broken in e2e.sh
- **Location:** e2e.sh:120-126
- **Problem:**
  ```bash
  *)
      pytest "tests/e2e/test_scenarios/test_${SCOPE}.py" \
          -v --report="$REPORT_FORMAT"
      ;;
  ```
  The default case only handles scenarios. When a user runs `./e2e.sh l7_security`, it will fail trying to find `test_scenarios/test_l7_security.py` instead of `test_layers/test_l7_security.py`.
- **Fix:** Add pattern matching to distinguish layers from scenarios:
  ```bash
  if [[ "$SCOPE" =~ ^l[0-9]+ ]]; then
      pytest "tests/e2e/test_layers/test_${SCOPE}.py" -v
  else
      pytest "tests/e2e/test_scenarios/test_${SCOPE}.py" -v
  fi
  ```

#### 4. `session_store` fixture declared but not defined
- **Location:** conftest.py:98
- **Problem:** Referenced in the conftest.py section but only shows `...`. The fixture is used by tests but has no implementation specified.
- **Fix:** Add full implementation:
  ```python
  @pytest.fixture
  def session_store(tmp_path):
      """Create temporary session store"""
      store_path = tmp_path / "sessions"
      store_path.mkdir()
      # Initialize with expected structure
      yield SessionStore(store_path)
      # Cleanup happens via tmp_path自动清理
  ```

---

### Important (Should Fix)

#### 5. Missing async patterns and event loop specification
- **Location:** Line 156-168 (example code)
- **Problem:** The example shows:
  ```python
  async for event in engine.submit_message(...)
  ```
  But does not specify:
  - How the event loop is managed
  - Whether `pytest-asyncio` mode is `auto` or `strict`
  - How to properly handle streaming responses in tests
- **Fix:** Add `pytest-asyncio` configuration section and document expected async patterns

#### 6. L8 Bridge layer underspecified
- **Location:** Matrix row L8
- **Problem:** "IDE 协议通信" is vague. No indication of:
  - Which IDEs are targeted (VS Code, JetBrains, etc.)
  - How to mock IDE connections in tests
  - What the Bridge protocol actually tests
- **Fix:** Add a section explaining which IDE protocol is used and how to test it, or mark as deferred to future phase

#### 7. S7 MCP and S8 Plugins lack test scenario details
- **Location:** Matrix rows S7, S8
- **Problem:** Only mentions "MCP 服务器连接和资源访问" and "插件加载和执行" without describing:
  - How to set up a mock MCP server
  - What plugin interface is being tested
  - How to verify plugin execution
- **Fix:** Add concrete test scenario descriptions for both S7 and S8

#### 8. Security testing incomplete
- **Location:** S5-L7 example, Line 148-155
- **Problem:** The example only tests `--permission-mode deny` with `rm -rf /`. Missing:
  - `--permission-mode read-only` behavior
  - Budget enforcement testing
  - Custom rules evaluation with actual rule files
  - Error message verification
- **Fix:** Add specific test cases for permissions, budgets, and rules separately in the security scenario

#### 9. No API retry/rate-limit handling
- **Location:** General
- **Problem:** Real API calls can hit rate limits. The design does not specify:
  - Whether tests should retry on 429 responses
  - Timeout values for API calls
  - How to handle quota exhaustion
- **Fix:** Add API client configuration section with retry policies and timeouts

#### 10. Test isolation not addressed
- **Location:** General
- **Problem:** No specification for:
  - Port allocation for parallel test execution (pytest-xdist)
  - Session store cleanup between tests
  - Preventing API state pollution between tests
- **Fix:** Add test isolation section documenting parallel execution strategy

---

### Minor (Nice to Have)

#### 11. Typo in title
- **Location:** Line 3
- **Problem:** "moz Mozio E2E" - "moz" appears to be a stray prefix
- **Fix:** Change to "Mozio E2E 验收测试套件"

#### 12. Report format specification missing
- **Location:** Line 131-144
- **Problem:** Describes text/json/html output but does not define:
  - JSON schema for the report
  - HTML template structure
  - What constitutes "passed" vs "failed" in edge cases
- **Fix:** Add report schema appendix

#### 13. `temp_project` cleanup not specified
- **Location:** conftest.py:86-88
- **Problem:** If a test crashes, does the temp directory persist? Any retry mechanism?
- **Fix:** Document that `tmp_path` fixture automatically handles cleanup

#### 14. `e2e-setup` and `verify` modes are stubs
- **Location:** Line 173-178
- **Problem:** `./start.sh e2e-setup` and `./start.sh verify` are mentioned but not implemented
- **Fix:** Either implement these modes or remove from design until needed

---

## Recommendations

1. **Add conftest.py skeleton**: Include full fixture implementations with proper async cleanup
2. **Specify pytest-report plugin**: Either add `pytest-report` to dependencies or implement a custom `pytest_terminal_summary` hook
3. **Add layer scope handling**: Extend the `case "*"` in e2e.sh to check for both scenario and layer patterns
4. **Document L8 Bridge protocol**: Add a section explaining which IDE protocol is used and how to test it
5. **Add security test matrix**: Break S5 into specific test cases for permissions, budgets, and rules separately
6. **Add async test utilities**: Document expected patterns for `async for` streaming tests and event loop handling
7. **Consider test parallelization**: If tests will run in parallel, add resource locking or dynamic port allocation

---

## Round 2 Review (2026-04-09)

### Previous Critical Issues Status

| Issue | Status |
|-------|--------|
| 1. Invalid pytest `--report` flag | ✅ FIXED - Uses `--json-report --json-report-file` with pytest-json-report |
| 2. `cli_process` fixture no cleanup | ✅ FIXED - Teardown with terminate/kill/wait |
| 3. Layer scope selection broken | ✅ FIXED - Regex `^l[0-9]+$` to distinguish layers |
| 4. `session_store` fixture undefined | ✅ FIXED - SessionStorage implemented |

---

### Round 2 Issues Status

| Issue | Status |
|-------|--------|
| P0: `SessionStore` → `SessionStorage` | ✅ FIXED - Changed to `SessionStorage` |
| P0: `ToolResult` in Bridge example | ✅ FIXED - Corrected to use `BridgeMessage` with payload |
| P1: `http_mock_server` stub | ✅ FIXED - Added pytest.skip with TODO |
| P1: Empty test implementations | ✅ FIXED - Replaced pass with pytest.skip + TODO |
| P2: `event_loop_policy` fixture | ✅ FIXED - Removed (conflicts with asyncio auto mode) |

---

### Round 2 Assessment

**Ready to implement?** ✅ YES

**Reasoning:** All 5 issues from Round 2 review have been addressed. The design is now ready for Phase 1 implementation.

Git commit: `26b1d9c`
