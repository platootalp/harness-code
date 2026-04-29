# Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix silent exception handling in observability components. Currently exceptions are silently ignored, making debugging difficult. Per design spec Section 14.

**Architecture:** Add logging to OTLPExporter, _HTTPOTLPExporter, and evaluator.py so failures are visible.

---

## File Structure

```
src_py/observability/
├── span_processors.py     # MODIFY: Add logging to OTLPExporter and _HTTPOTLPExporter
├── evaluator.py            # MODIFY: Add logging to _try_phoenix_eval
├── tracer.py               # MODIFY: Add logging to _notify_observers
└── test_observability.py   # CREATE: Unit tests for error logging
```

---

### Task 1: Add Logging to OTLPExporter

**Files:**
- Modify: `src_py/observability/span_processors.py:284-297`

- [ ] **Step 1: Add logger import at top of file**

Add after existing imports:

```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Replace silent exception in OTLPExporter.export**

Replace lines 296-297:
```python
        except Exception:
            pass
```

With:
```python
        except Exception as e:
            logger.warning(f"OTLPExporter.export failed: {e}")
```

- [ ] **Step 3: Replace silent exception in _HTTPOTLPExporter.export**

Replace lines 366-367:
```python
        except Exception:
            pass
```

With:
```python
        except Exception as e:
            logger.warning(f"HTTPOTLPExporter.export failed to {self._endpoint}: {e}")
```

- [ ] **Step 4: Replace silent exception in _HTTPOTLPExporter.shutdown**

Replace lines 369-370:
```python
    async def shutdown(self) -> None:
        pass
```

With:
```python
    async def shutdown(self) -> None:
        # No-op for HTTP exporter
        pass
```

---

### Task 2: Add Logging to Evaluator

**Files:**
- Modify: `src_py/observability/evaluator.py`

- [ ] **Step 1: Add logger import at top**

Add after existing imports:
```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Replace silent exception in _try_phoenix_eval**

Replace the exception handling around line 212-213:
```python
        except Exception:
            pass
```

With:
```python
        except Exception as e:
            logger.warning(f"Phoenix evaluation failed: {e}")
```

- [ ] **Step 3: Check for similar patterns in evaluator.py**

Search for other bare `except Exception: pass` patterns and add logging.

---

### Task 3: Add Logging to Tracer

**Files:**
- Modify: `src_py/observability/tracer.py`

- [ ] **Step 1: Find _notify_observers method**

Locate the `_notify_observers` method and check for silent exception handling.

- [ ] **Step 2: Add logging for observer notification failures**

Replace any silent exception handling with:
```python
        except Exception as e:
            logger.warning(f"Observer notification failed: {e}")
```

---

### Task 4: Write Tests for Error Logging

**Files:**
- Create: `src_py/observability/test_observability.py`

```python
"""Tests for observability error handling and logging."""
import pytest
import logging
from unittest.mock import MagicMock, patch
from src_py.observability.span_processors import (
    OTLPExporter,
    ConsoleSpanExporter,
    Span,
)
from src_py.observability.evaluator import Evaluator


@pytest.fixture
def otlp_exporter():
    return OTLPExporter(endpoint="http://localhost:4317")


@pytest.fixture
def evaluator():
    return Evaluator(eval_model="test-model")


@pytest.fixture
def sample_span():
    from datetime import datetime
    return Span(
        name="test-span",
        type="tool",
        trace_id="abc123",
        span_id="span1",
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration_ms=10.5,
        attributes={"tool": "Bash"},
        status="ok",
    )


class TestOTLPExporterErrorLogging:
    """Test that OTLPExporter logs errors instead of silently ignoring."""

    @pytest.mark.asyncio
    async def test_export_logs_on_failure(self, otlp_exporter, sample_span, caplog):
        """OTLPExporter.export should log warnings on failure."""
        # Mock _get_client to return something that will fail
        with caplog.at_level(logging.WARNING):
            with patch.object(otlp_exporter, '_get_client', side_effect=Exception("Connection refused")):
                await otlp_exporter.export([sample_span])

        # Should have logged a warning
        assert any("OTLPExporter.export failed" in record.message for record in caplog.records)


class TestEvaluatorErrorLogging:
    """Test that evaluator logs Phoenix evaluation failures."""

    @pytest.mark.asyncio
    async def test_try_phoenix_eval_logs_on_failure(self, evaluator, caplog):
        """_try_phoenix_eval should log warnings on failure."""
        with caplog.at_level(logging.WARNING):
            # Mock httpx to raise an exception
            with patch('httpx.AsyncClient', side_effect=Exception("Connection refused")):
                score, details = await evaluator._try_phoenix_eval(
                    prompt="test prompt",
                    input_text="test input",
                    output_text="test output",
                )

        # Should have returned None and logged a warning
        assert score is None
        assert any("Phoenix evaluation failed" in record.message for record in caplog.records)
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/observability/test_observability.py -v
```

Expected: Tests pass with proper logging.

---

## Verification

```bash
cd /Users/lijunyi/road/claude-code
python3 -m pytest src_py/observability/test_observability.py -v
```

Expected: **All tests pass**

---

## Implementation Notes

1. Use Python's standard `logging` module
2. Log at WARNING level (not ERROR) since these are expected failure cases
3. Include endpoint/connection details in log messages for debugging
4. Never silently swallow exceptions - always log the error
