# Getting Started

## Quick Start Guide

This guide will help you set up and run your first agent system in under 5 minutes.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- A code editor (VS Code, PyCharm, etc.)

## Installation

### Step 1: Clone or Navigate to Project Directory

```bash
cd /Users/lijunyi/road/learn-claude-code/agents
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you don't have a requirements.txt file yet, create one with essential dependencies:

```txt
python-dotenv>=1.0.0
pyyaml>=6.0
aiofiles>=23.0.0
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Agent Configuration
AGENT_NAME="MyFirstAgent"
MAX_ITERATIONS=50
CONTEXT_SIZE_LIMIT=500
LOG_LEVEL=INFO

# API Keys (if needed)
OPENAI_API_KEY="your-api-key-here"
```

## Your First Agent

### Basic Example

Create a new file `my_first_agent.py`:

```python
from agents import Agent, Tool

# Define a simple greeting tool
def greet_tool(name: str = "User") -> str:
    """Greet someone by name"""
    return f"Hello, {name}! Welcome to the agent world."

greet = Tool(
    name="greet",
    description="Greet someone by their name",
    parameters={"name": {"type": "string", "required": False}},
    execute_fn=greet_tool
)

# Create your first agent
agent = Agent(
    name="HelloBot",
    tools={"greet": greet}
)

# Run the agent
response = agent.run("Please say hello to Alice using your greeting tool")
print(response)
```

Run it:

```bash
python my_first_agent.py
```

Expected output:
```
Hello, Alice! Welcome to the agent world.
```

## Building More Capable Agents

### Adding Multiple Tools

```python
# Import necessary components
from agents import Agent, Tool

# Calculator tool
def calculate(expression: str) -> str:
    """Evaluate mathematical expression safely"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Calculation error: {str(e)}"

calc = Tool(
    name="calculate",
    description="Evaluate mathematical expressions",
    parameters={"expression": {"type": "string", "required": True}},
    execute_fn=calculate
)

# Date time tool
from datetime import datetime

def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current time in specified format"""
    return datetime.now().strftime(format)

datetime_tool = Tool(
    name="get_current_time",
    description="Get current date and time",
    parameters={"format": {"type": "string", "required": False}},
    execute_fn=get_current_time
)

# File reading tool
def read_file(file_path: str) -> str:
    """Read contents of a text file"""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

read_file_tool = Tool(
    name="read_file",
    description="Read contents of a text file",
    parameters={"file_path": {"type": "string", "required": True}},
    execute_fn=read_file
)

# Create agent with multiple tools
powerful_agent = Agent(
    name="MultiToolAgent",
    tools={
        "calculate": calc,
        "datetime": datetime_tool,
        "read_file": read_file_tool
    }
)

# Test the agent
result = powerful_agent.run("""
I need you to:
1. Calculate 25 * 4 + 10
2. Get today's date
3. Read the file /path/to/sample.txt

Please complete all three tasks and report results.
""")

print(result)
```

### Working with Skills

```python
from agents import Agent, SkillManager

# Initialize basic agent
agent = Agent(name="BaseAgent")

# Load skills dynamically
skill_manager = SkillManager()

# Load data analysis skill
skill_manager.load_skill("/skills/data_analysis.yaml")
agent.add_skill("data_analysis")

# Use the agent for analytical tasks
analysis_result = agent.run("""
Analyze this dataset summary:
- 1000 customer records
- Average age: 34 years
- Purchase frequency: 2.3 times/month
Identify key insights and patterns.
""")

print(analysis_result)
```

## Advanced Usage Patterns

### Multi-Agent Teams

```python
from agents import Team, Agent

# Create specialized agents
researcher = Agent(name="Researcher", skills=["information_retrieval"])
analyst = Agent(name="Analyst", skills=["data_analysis"])
writer = Agent(name="Writer", skills=["document_generation"])

# Form a team
report_team = Team(
    name="ReportGenerationTeam",
    protocol="consensus",
    members=[researcher, analyst, writer]
)

# Assign team task
team_result = report_team.broadcast(
    message="Create a market analysis report on renewable energy trends",
    sender="system"
)

print(team_result)
```

### Autonomous Background Tasks

```python
from agents import Agent, BackgroundTask
import time

# Create monitoring agent
monitor = Agent(
    name="SystemMonitor",
    skills=["health_check", "alerting"]
)

# Set up periodic monitoring
def check_system_health():
    health_status = monitor.run("Check overall system health")
    if "critical" in health_status.lower():
        monitor.run("Send critical alert to admin team")
    else:
        print(f"System status: {health_status}")

# Schedule background task
health_monitor = BackgroundTask(
    name="system_health",
    interval_seconds=300,  # Every 5 minutes
    function=check_system_health
)

# Start monitoring
health_monitor.start()
print("Monitoring started... Press Ctrl+C to stop")

try:
    while True:
        time.sleep(60)  # Main loop keeps running
except KeyboardInterrupt:
    health_monitor.stop()
    print("Monitoring stopped.")
```

## Debugging Tips

### Enable Detailed Logging

```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run agent with verbose output
agent.run("Your command here")
```

### Check Agent State

```python
# Inspect current agent state
state = agent.get_state()
print(f"Iteration count: {state['iteration_count']}")
print(f"Context size: {state['context_size']}")
print(f"Current task: {state['current_task']}")
```

### Test Individual Components

```python
# Test tool independently
tool_result = calculate.execute("15 * 8 + 20")
print(f"Direct tool execution: {tool_result}")

# Test skill in isolation
if agent.has_skill("data_analysis"):
    isolated_result = agent.skills["data_analysis"].analyze_sample_data()
    print(f"Skill result: {isolated_result}")
```

## Common Issues and Solutions

### Issue 1: Module Not Found Error

**Problem:** `ModuleNotFoundError: No module named 'agents'`

**Solution:** Ensure you're running from the correct directory and that the `__init__.py` file exists.

```bash
# Verify directory structure
ls -la

# Add current directory to PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue 2: Tool Execution Timeout

**Problem:** Tool execution takes too long or hangs

**Solution:** Implement timeouts and resource limits

```python
tool = Tool(
    name="slow_operation",
    execute_fn=timeout_safe_function,
    security_constraints={"max_execution_time": 30}
)
```

### Issue 3: Context Size Exceeded

**Problem:** Context becomes too large and performance degrades

**Solution:** Enable automatic context compaction

```python
from agents import Context

agent = Agent(
    name="OptimizedAgent",
    context=Context(max_size=500, compact_threshold=400)
)
```

## Next Steps

After completing this guide, explore these advanced topics:

1. **Component Details**: Learn about each system component in detail
2. **API Reference**: Understand all available APIs and methods
3. **Use Cases**: See real-world examples and applications
4. **Best Practices**: Follow industry standards for robust implementations
5. **Architecture**: Deep dive into system architecture decisions

## Additional Resources

- Source code examples in the main directory (`s01_*.py`, `s02_*.py`, etc.)
- OpenAI-specific implementations in `*_openai.py` files
- Documentation files in the `docs/` directory
- Community forums and support channels

## Getting Help

If you encounter issues:

1. Check the error messages carefully
2. Review relevant documentation sections
3. Test components individually to isolate problems
4. Consult community resources and issue trackers
5. Contact support if needed

---

*Happy building! Start small, iterate frequently, and scale gradually.*
