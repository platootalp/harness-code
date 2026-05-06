# Use Cases and Examples

## Introduction

This document provides practical examples of how to use the agent system for various real-world scenarios. Each example demonstrates specific features and best practices.

## Use Case 1: Simple File Processing Agent

### Scenario
Create an agent that can read files, analyze content, and generate summaries.

### Implementation

```python
from agents import Agent, Tool, Context

# Define a file reading tool
def read_file_tool(path: str) -> str:
    """Read contents of a file"""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

read_file = Tool(
    name="read_file",
    description="Read contents of a specified file",
    parameters={"path": {"type": "string", "required": True}},
    execute_fn=read_file_tool
)

# Create agent with file processing capability
agent = Agent(
    name="FileAnalyzer",
    tools={"read_file": read_file},
    skills=["text_analysis", "summary_generation"]
)

# Execute single analysis
result = agent.run("Please read /path/to/document.txt and provide a summary")
print(result)
```

### Key Features Demonstrated
- Tool registration and usage
- Single-purpose agent creation
- File I/O operations
- Result extraction

## Use Case 2: Multi-Step Research Task

### Scenario
An agent that conducts comprehensive research on a topic by searching multiple sources and synthesizing information.

### Implementation

```python
from agents import Agent, SubAgent, Team

# Define search capabilities
def search_web(query: str) -> str:
    """Search web for information"""
    # Implementation would integrate with search API
    return "Search results..."

search_tool = Tool(
    name="search_web",
    description="Search the web for information",
    parameters={"query": {"type": "string", "required": True}},
    execute_fn=search_web
)

# Create main research agent
researcher = Agent(
    name="ResearchLead",
    tools={"search": search_tool},
    skills=["research", "synthesis"]
)

# Break down complex research into subtasks
subtasks = [
    "Search for recent developments in AI ethics",
    "Find academic papers on machine learning fairness",
    "Collect industry case studies on algorithmic bias"
]

results = []
for i, task in enumerate(subtasks):
    # Create specialized sub-agent for each research area
    sub_agent = SubAgent(
        parent_agent=researcher,
        name=f"Researcher_{i}",
        scope=task,
        context=researcher.context.create_isolated_view()
    )
    
    result = sub_agent.execute(task)
    results.append({
        "topic": task,
        "findings": result,
        "source_count": len(result.split('\n')) if isinstance(result, str) else 0
    })

# Synthesize findings
final_report = researcher.run(
    f"Synthesize these research findings: {str(results)}"
)
print(final_report)
```

### Key Features Demonstrated
- Sub-agent architecture
- Parallel task execution
- Information synthesis
- Complex workflow management

## Use Case 3: Collaborative Code Review Team

### Scenario
A team of agents working together to review code changes from different perspectives.

### Implementation

```python
from agents import Team, Agent

# Create specialized reviewers
security_reviewer = Agent(
    name="SecurityExpert",
    skills=["security_analysis", "vulnerability_detection"],
    role="security"
)

performance_reviewer = Agent(
    name="PerformanceEngineer",
    skills=["performance_optimization", "bottleneck_identification"],
    role="performance"
)

style_reviewer = Agent(
    name="CodeStyleGuru",
    skills=["code_quality", "documentation_review"],
    role="quality"
)

# Form collaborative team
code_review_team = Team(
    name="CodeReviewTeam",
    protocol="consensus",
    members=[security_reviewer, performance_reviewer, style_reviewer]
)

# Assign code review task
code_changes = open("changes.py").read()

team_response = code_review_team.broadcast(
    message=f"Please review these code changes:\n\n{code_changes}",
    sender="system"
)

# Collect individual reviews
for member_id, response in team_response.items():
    print(f"{member_id}: {response}")

# Generate consensus recommendation
recommendation = security_reviewer.run(
    f"Based on these reviews: {str(team_response)}, what is our final recommendation?"
)
print(recommendation)
```

### Key Features Demonstrated
- Multi-agent teams
- Role-based specialization
- Consensus protocols
- Collaborative decision-making

## Use Case 4: Autonomous Data Pipeline Management

### Scenario
An autonomous agent that monitors data pipelines, detects issues, and triggers corrective actions.

### Implementation

```python
from agents import Agent, Task, BackgroundTask

# Define pipeline monitoring capabilities
def check_pipeline_health(pipeline_id: str) -> dict:
    """Check health status of a data pipeline"""
    # Implementation would query pipeline metrics
    return {"status": "healthy", "latency_ms": 45}

health_check_tool = Tool(
    name="check_pipeline_health",
    description="Monitor pipeline health metrics",
    parameters={"pipeline_id": {"type": "string", "required": True}},
    execute_fn=check_pipeline_health
)

def trigger_remediation(pipeline_id: str, action: str) -> str:
    """Trigger remediation action for problematic pipeline"""
    # Implementation would restart services or scale resources
    return f"Remediation action '{action}' triggered for {pipeline_id}"

remediation_tool = Tool(
    name="trigger_remediation",
    description="Execute remediation actions",
    parameters={
        "pipeline_id": {"type": "string", "required": True},
        "action": {"type": "string", "required": True}
    },
    execute_fn=trigger_remediation
)

# Create autonomous monitoring agent
monitor_agent = Agent(
    name="PipelineMonitor",
    tools={
        "health_check": health_check_tool,
        "remediation": remediation_tool
    },
    skills=["anomaly_detection", "automated_response"],
    autonomy_level=3  # Level 3 autonomy
)

# Set up periodic monitoring task
def monitoring_loop():
    pipelines = ["etl_main", "streaming_data", "batch_processing"]
    
    for pipeline_id in pipelines:
        health_status = monitor_agent.run(f"Check health of {pipeline_id}")
        
        if "unhealthy" in health_status.lower():
            action = "restart_pipeline" if "restartable" in health_status else "scale_resources"
            monitor_agent.run(f"Apply {action} to {pipeline_id}")

# Run background monitoring
background_task = BackgroundTask(
    name="pipeline_health_monitor",
    interval_seconds=300,
    function=monitoring_loop
)
background_task.start()
```

### Key Features Demonstrated
- Autonomous operation
- Periodic background tasks
- Automated issue detection and resolution
- Self-healing systems

## Use Case 5: Dynamic Skill Loading System

### Scenario
Load and unload skills dynamically based on current requirements without restarting the agent.

### Implementation

```python
from agents import Agent, SkillManager

# Initialize agent with basic capabilities
base_agent = Agent(
    name="FlexibleWorker",
    skills=["basic_reasoning", "task_planning"]
)

# Load domain-specific skills on demand
skill_manager = SkillManager()

# Load medical analysis skill when needed
if has_medical_question():
    success = skill_manager.load_skill("/skills/medical_analysis.yaml")
    if success:
        base_agent.add_skill("medical_analysis")
        response = base_agent.run(process_medical_query())
        # Unload after use to free resources
        skill_manager.unload_skill("medical_analysis")
    
# Load financial analysis skill for different task
elif needs_financial_analysis():
    skill_manager.load_skill("/skills/financial_analysis.yaml")
    base_agent.add_skill("financial_analysis")
    financial_report = base_agent.run(process_financial_request())
    skill_manager.unload_skill("financial_analysis")
```

### Key Features Demonstrated
- Dynamic skill management
- Resource optimization
- On-demand capability loading
- Flexible agent configuration

## Use Case 6: Context-Aware Document Analysis

### Scenario
An agent that maintains long-term context while analyzing documents and providing consistent insights over time.

### Implementation

```python
from agents import Agent, Context

# Initialize agent with large context window
analysis_agent = Agent(
    name="DocumentAnalyst",
    context=Context(max_size=500, compact_threshold=400)
)

# Analyze first document
doc1_content = open("document1.pdf").read()
initial_analysis = analysis_agent.run(f"""
Analyze this document: {doc1_content}
Identify key themes, conclusions, and supporting evidence.
""")

# Analyze second related document
doc2_content = open("document2.pdf").read()
comparative_analysis = analysis_agent.run(f"""
Compare this new document with our previous analysis:
Current analysis: {initial_analysis}
New document: {doc2_content}
What new insights does this document add? How does it relate to previous findings?
""")

# Later session - retrieve previous context
fresh_context_analysis = analysis_agent.run("""
Based on our previous document analyses, summarize the overall trends we've identified.
""")
```

### Key Features Demonstrated
- Long-context maintenance
- Progressive knowledge building
- Context compaction strategies
- Session continuity

## Use Case 7: Multi-Tenant Task Isolation

### Scenario
Process requests from multiple users simultaneously without cross-contamination of data or context.

### Implementation

```python
from agents import Agent, TaskQueue

# Create isolated worktrees for different users
user_tasks = {}

def process_user_request(user_id: str, request: str):
    """Process user request in isolated environment"""
    
    # Create unique task with isolation
    task = Task(
        id=f"{user_id}_{generate_uuid()}",
        title=f"Request from {user_id}",
        description=request,
        priority=5
    )
    
    # Assign to dedicated worktree
    isolated_agent = Agent(
        name=f"User_{user_id}_Agent",
        worktree=f"/tmp/worktrees/{user_id}"
    )
    
    result = isolated_agent.run(request)
    
    # Store result
    user_tasks[user_id] = {
        "task_id": task.id,
        "result": result,
        "timestamp": datetime.now()
    }
    
    return result

# Process multiple user requests concurrently
users = ["user_001", "user_002", "user_003"]
requests = [
    "Analyze my sales data from last quarter",
    "Generate marketing campaign ideas for summer",
    "Review customer feedback and suggest improvements"
]

results = parallel_process_users(users, requests)
```

### Key Features Demonstrated
- Multi-tenant isolation
- Concurrent task processing
- Worktree-based separation
- Independent state management

## Best Practices

### 1. Error Handling Always
```python
try:
    result = agent.run(complex_task)
except ToolError as e:
    log_error(f"Tool failure: {e.tool_name}", e)
    retry_with_alternative_tool()
except TaskError as e:
    escalate_to_human_or_adjust_strategy()
```

### 2. Context Size Management
```python
if agent.context.size > agent.context.compact_threshold:
    agent.context.compact()
```

### 3. Secure Tool Usage
```python
tool = Tool(
    name="dangerous_operation",
    parameters={...},
    execute_fn=sandboxed_execute,
    security_constraints=MaxExecutionTime(30),
)
```

### 4. Logging Everything Important
```python
logger.trace_execution(
    step="data_analysis",
    details={"input_size": 15000, "processing_time": 2.3}
)
```

## Common Pitfalls

### ❌ Ignoring Context Limits
Leading to truncated responses and lost information.

**✅ Solution**: Implement proactive context compaction.

### ❌ Overusing Sub-Agents
Creating too many child agents degrades performance.

**✅ Solution**: Limit sub-agent depth and duration.

### ❌ Not Isolating Tasks
Causing cross-contamination in multi-tenant scenarios.

**✅ Solution**: Use worktree isolation consistently.

### ❌ Hardcoding Tool Parameters
Making agents inflexible and error-prone.

**✅ Solution**: Use parameterized tools with validation.

---

*For more detailed implementation examples, refer to source files in the main directory.*
*Each use case can be extended and customized based on specific requirements.*
