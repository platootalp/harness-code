# Condition-Based Waiting

**Key Insight:** Replace arbitrary timeouts with polling-based condition checking.

**Best Practices:**
- Poll every 10ms (not faster) to avoid CPU waste
- Always include a timeout with descriptive error
- Call getters inside the loop for fresh data

**Real Results:** One debugging session fixed 15 flaky tests, raising pass rate from 60% to 100%.
