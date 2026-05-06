# API Reference

## Agent Core API

### Agent Class

```python
class Agent:
    """Main agent class that manages the agent loop and state"""
    
    def __init__(self, 
                 name: str = "Agent",
                 skills: List[str] = None,
                 tools: Dict[str, Tool] = None,
                 initial_context: List[Message] = None):
        """Initialize agent with configuration"""
        
    def run(self, input_message: str) -> str:
        """Execute single iteration with given input"""
        
    def run_loop(self, input_message: str, max_iterations: int = 100) -> str:
        """Run complete agent loop until completion or max iterations"""
        
    def add_skill(self, skill_name: str, skill_config: dict) -> bool:
        """Register a new skill"""
        
    def add_tool(self, tool: Tool) -> bool:
        """Register a new tool"""
        
    def get_state(self) -> dict:
        """Get current agent state"""
        
    def reset(self) -> None:
        """Reset agent to initial state"""
```

## Tool System API

### Tool Class

```python
class Tool:
    """Base class for all tools"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 parameters: Dict[str, Any],
                 execute_fn: Callable):
        """Initialize tool with configuration"""
        
    @property
    def name(self) -> str:
        """Tool name"""
        
    @property
    def description(self) -> str:
        """Tool description for agent understanding"""
        
    @property
    def parameters(self) -> Dict[str, Any]:
        """Parameter schema for the tool"""
        
    def execute(self, **kwargs) -> Any:
        """Execute tool with given parameters"""
```

### Tool Registry

```python
class ToolRegistry:
    """Central registry for all available tools"""
    
    def register(self, tool: Tool) -> bool:
        """Register a tool in the system"""
        
    def unregister(self, tool_name: str) -> bool:
        """Remove a tool from the registry"""
        
    def get(self, tool_name: str) -> Optional[Tool]:
        """Retrieve a tool by name"""
        
    def list_all(self) -> List[str]:
        """List all registered tool names"""
        
    def search(self, query: str) -> List[Tool]:
        """Search tools by keyword or capability"""
```

## Task System API

### Task Class

```python
class Task:
    """Represents a work item in the task system"""
    
    def __init__(self, 
                 id: str,
                 title: str,
                 description: str,
                 priority: int = 5,
                 assignee: str = None):
        """Initialize task with metadata"""
        
    @property
    def status(self) -> str:
        """Current task status (pending/in_progress/completed/failed)"""
        
    def mark_in_progress(self) -> None:
        """Mark task as being worked on"""
        
    def mark_completed(self, result: Any = None) -> None:
        """Mark task as completed with optional result"""
        
    def mark_failed(self, error: Exception) -> None:
        """Mark task as failed with error information"""
```

### TaskQueue Class

```python
class TaskQueue:
    """Priority-based task queue management"""
    
    def enqueue(self, task: Task) -> None:
        """Add task to queue"""
        
    def dequeue(self) -> Optional[Task]:
        """Get next high-priority task"""
        
    def peek(self) -> Optional[Task]:
        """View next task without removing it"""
        
    def size(self) -> int:
        """Return number of pending tasks"""
        
    def clear(self) -> None:
        """Remove all tasks from queue"""
```

## Team API

### Team Class

```python
class Team:
    """Group of collaborating agents"""
    
    def __init__(self, 
                 name: str,
                 protocol: str = "flat",
                 members: List[Agent] = None):
        """Initialize team with configuration"""
        
    def add_member(self, agent: Agent) -> bool:
        """Add agent to team"""
        
    def remove_member(self, agent_id: str) -> bool:
        """Remove agent from team"""
        
    def broadcast(self, message: str, sender: str) -> Dict[str, str]:
        """Send message to all team members"""
        
    def assign_task(self, task: Task, member_id: str) -> None:
        """Assign specific task to team member"""
        
    def get_status(self) -> dict:
        """Get current team status overview"""
```

## Sub-Agent API

### SubAgent Class

```python
class SubAgent:
    """Specialized agent created for specific subtasks"""
    
    def __init__(self,
                 parent_agent: Agent,
                 name: str,
                 scope: str,
                 context: ContextView):
        """Initialize sub-agent with parent reference and scope"""
        
    def execute(self, task_description: str) -> Any:
        """Execute specific subtask"""
        
    def get_result(self) -> Any:
        """Retrieve execution result"""
        
    def terminate(self) -> None:
        """Clean up sub-agent resources"""
```

## Skill System API

### Skill Class

```python
class Skill:
    """Encapsulated capability for agents"""
    
    def __init__(self,
                 name: str,
                 description: str,
                 capabilities: List[str],
                 dependencies: List[str] = None,
                 config: dict = None):
        """Initialize skill with properties"""
        
    def activate(self, agent: Agent) -> bool:
        """Activate skill for use by agent"""
        
    def deactivate(self, agent: Agent) -> bool:
        """Deactivate skill from agent"""
        
    def is_available(self, agent: Agent) -> bool:
        """Check if skill is available to agent"""
```

### SkillManager Class

```python
class SkillManager:
    """Manages loading and unloading of skills"""
    
    def load_skill(self, skill_path: str) -> bool:
        """Load skill from file or URL"""
        
    def unload_skill(self, skill_name: str) -> bool:
        """Unload skill from system"""
        
    def list_loaded_skills(self) -> List[str]:
        """List all currently loaded skills"""
        
    def reload_skill(self, skill_name: str) -> bool:
        """Reload skill with fresh configuration"""
```

## Context Management API

### Context Class

```python
class Context:
    """Manages conversation history and agent state"""
    
    def __init__(self, 
                 max_size: int = 100,
                 compact_threshold: int = 80):
        """Initialize context with limits"""
        
    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history"""
        
    def get_recent_messages(self, count: int = 10) -> List[Dict]:
        """Get recent messages from history"""
        
    def compact(self) -> bool:
        """Apply compaction strategy to reduce size"""
        
    def create_isolated_view(self) -> ContextView:
        """Create isolated view for sub-agent"""
        
    def clear(self) -> None:
        """Clear all conversation history"""
```

### ContextView Class

```python
class ContextView:
    """Read-only view of context for specific operations"""
    
    def read_only_messages(self) -> List[Dict]:
        """Read-only access to messages"""
        
    def restricted_write(self, role: str, content: str) -> bool:
        """Write with restrictions applied"""
```

## Configuration API

### ConfigClass

```python
class Config:
    """Central configuration manager"""
    
    def load_from_file(self, path: str) -> bool:
        """Load configuration from file"""
        
    def set_value(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default fallback"""
        
    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        
    def export_to_dict(self) -> dict:
        """Export configuration as dictionary"""
```

## Error Handling API

### AgentError Base Class

```python
class AgentError(Exception):
    """Base exception for agent-related errors"""
    
    pass

class ToolError(AgentError):
    """Error during tool execution"""
    
    def __init__(self, tool_name: str, message: str, original_error: Exception = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(message)

class TaskError(AgentError):
    """Error during task processing"""
    
    pass

class TeamError(AgentError):
    """Error in team coordination"""
    
    pass
```

## Logging API

### Logger Class

```python
class AgentLogger:
    """Comprehensive logging for agent operations"""
    
    def info(self, message: str, extra_data: dict = None) -> None:
        """Log informational message"""
        
    def warning(self, message: str, extra_data: dict = None) -> None:
        """Log warning message"""
        
    def error(self, message: str, error: Exception = None) -> None:
        """Log error message"""
        
    def debug(self, message: str, extra_data: dict = None) -> None:
        """Log debug message"""
        
    def trace_execution(self, step: str, details: dict) -> None:
        """Trace agent execution steps"""
```

---

*For complete implementation examples, see source files in main directory*
*All APIs support async/await patterns where applicable*
