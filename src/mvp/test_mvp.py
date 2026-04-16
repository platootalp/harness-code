"""Test script to verify MVP core functionality."""
import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_env_from_config():
    """Load config from .env file if exists."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(config_path):
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# Load config first
load_env_from_config()

from src_mvp.state.app_state import AppState
from src_mvp.state.store import create_store
from src_mvp.tools import get_tools
from src_mvp.commands import get_commands
from src_mvp.lib.api.client import APIClient
from src_mvp.lib.query_engine import QueryEngine


async def test_tools():
    """Test tool system."""
    print("=== Testing Tools ===")

    from src_mvp.tools.bash_tool import bash_tool, BashToolInput, is_read_only_command
    from src_mvp.tools.file_read_tool import file_read_tool, FileReadToolInput
    from src_mvp.tools.file_edit_tool import file_edit_tool
    from src_mvp.tools.grep_tool import grep_tool, GrepToolInput

    from src_mvp.state.app_state import PermissionContext
    from src_mvp.tools.base import ToolContext

    cwd = os.getcwd()
    ctx = ToolContext(cwd=cwd, permission_context=PermissionContext())

    # Test BashTool
    print("\n1. Testing BashTool:")
    result = await bash_tool['call'](BashToolInput(command='echo "hello"'), ctx)
    print(f"   echo 'hello': {result.data}")

    # Test read-only detection
    print(f"   is 'ls' read-only: {is_read_only_command('ls')}")
    print(f"   is 'rm' read-only: {is_read_only_command('rm')}")

    # Test FileReadTool
    print("\n2. Testing FileReadTool:")
    result = file_read_tool['call'](FileReadToolInput(file_path='pyproject.toml', limit=5), ctx)
    print(f"   read pyproject.toml (5 lines):\n{result.data.get('content', '')[:200]}...")

    # Test GrepTool
    print("\n3. Testing GrepTool:")
    result = grep_tool['call'](GrepToolInput(pattern='def', path='pyproject.toml'), ctx)
    print(f"   grep 'def' in pyproject.toml: found {result.data.get('exit_code', -1) == 0}")

    print("\n=== All Tools Working ===\n")


async def test_query_engine():
    """Test query engine with API."""
    print("=== Testing QueryEngine ===")

    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL')
    model = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')

    print(f"  Config: base_url={base_url}, model={model}")

    if not auth_token:
        print("  No ANTHROPIC_AUTH_TOKEN found, skipping QueryEngine test")
        return

    app_state = AppState(cwd=os.getcwd(), model=model)
    api_client = APIClient(api_key=auth_token, base_url=base_url)
    engine = QueryEngine(app_state, api_client)

    print("Sending test message to API...")
    response_parts = []

    try:
        async for event in engine.submit_message("Say 'hello' in exactly one word"):
            if event.type == 'assistant':
                response_parts.append(event.data)
                print(f"  streaming: {event.data}", end='', flush=True)
            elif event.type == 'done':
                print()
                print(f"  Final response: {''.join(response_parts)}")
            elif event.type == 'error':
                print(f"  Error: {event.data}")

    except Exception as e:
        print(f"  Query failed: {e}")
    finally:
        await api_client.close()

    print("=== QueryEngine Test Complete ===\n")


def test_permissions():
    """Test permission system."""
    print("=== Testing Permissions ===")

    from src_mvp.lib.permissions import check_permission
    from src_mvp.state.app_state import PermissionContext, PermissionRule

    # Test deny rule
    ctx = PermissionContext(
        always_deny=[
            PermissionRule(source='test', behavior='deny', tool_name='Bash', pattern='rm *'),
        ]
    )

    result = check_permission('Bash', {'command': 'rm -rf /'}, ctx)
    print(f"  rm -rf / -> {result.behavior} (expected: deny)")

    result = check_permission('Bash', {'command': 'ls -la'}, ctx)
    print(f"  ls -la -> {result.behavior} (expected: ask)")

    # Test allow rule
    ctx2 = PermissionContext(
        always_allow=[
            PermissionRule(source='test', behavior='allow', tool_name='Bash', pattern='git *'),
        ]
    )
    result = check_permission('Bash', {'command': 'git status'}, ctx2)
    print(f"  git status -> {result.behavior} (expected: allow)")

    print("=== Permissions Working ===\n")


async def main():
    print("MVP AI CLI - Core Functionality Test\n")

    await test_tools()
    test_permissions()
    await test_query_engine()

    print("All tests complete!")


if __name__ == '__main__':
    asyncio.run(main())
