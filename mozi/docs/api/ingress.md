# Ingress API

## Overview

The Ingress module handles command-line interface and REPL interactions.

## CLI Interface

### Methods

#### `run(command: str) -> None`

Runs a single command.

**Parameters:**
- `command` (str): Command to execute

#### `start_repl() -> None`

Starts an interactive REPL session.

## Command Parser

### Methods

#### `parse(input_str: str) -> ParsedCommand`

Parses user input into a command.

**Parameters:**
- `input_str` (str): User input

**Returns:**
- `ParsedCommand`: Parsed command object

## Output Handler

### Methods

#### `format_response(response: Response) -> str`

Formats a response for display.

**Parameters:**
- `response` (Response): Response to format

**Returns:**
- `str`: Formatted string

#### `format_error(error: Exception) -> str`

Formats an error for display.

**Parameters:**
- `error` (Exception): Error to format

**Returns:**
- `str`: Formatted error string

## Command Types

| Command | Description |
|---------|-------------|
| `ask` | Ask the agent a question |
| `execute` | Execute a task |
| `session` | Manage sessions |
| `context` | View/manipulate context |
| `exit` | Exit REPL |

## Usage Example

```python
from mozi.ingress import CLI

cli = CLI()
await cli.run("ask How do I implement a login feature?")
```

## REPL Commands

```
mozi> ask Implement a login feature
mozi> context show
mozi> session list
mozi> exit
```
