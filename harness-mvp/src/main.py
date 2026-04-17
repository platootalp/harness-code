"""CLI entry point."""
from __future__ import annotations

import argparse
import os

from .lib.config import load_config, apply_config


def main() -> None:
    parser = argparse.ArgumentParser(description='MVP AI CLI')
    parser.add_argument('--config', help='Config file path (.json)')
    parser.add_argument('--model', help='Model to use')
    parser.add_argument('--api-key', help='Anthropic API key (or set ANTHROPIC_AUTH_TOKEN)')
    parser.add_argument('--base-url', help='API base URL')
    parser.add_argument('--cwd', default=os.getcwd(), help='Working directory')
    args = parser.parse_args()

    # Load config from file and environment
    config = load_config(args.config)
    apply_config(config)

    # CLI args override config
    if args.api_key:
        os.environ['ANTHROPIC_AUTH_TOKEN'] = args.api_key
    if args.base_url:
        os.environ['ANTHROPIC_BASE_URL'] = args.base_url
    if args.model:
        os.environ['ANTHROPIC_MODEL'] = args.model

    # Show current config
    print("=== MVP AI CLI Configuration ===")
    print(f"ANTHROPIC_BASE_URL: {os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')}")
    print(f"ANTHROPIC_MODEL: {os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')}")
    print(f"API_TIMEOUT_MS: {os.environ.get('API_TIMEOUT_MS', '300000')}")
    print("================================")

    # Import and launch REPL
    from .repl_launcher import launch_repl
    launch_repl()


if __name__ == '__main__':
    main()
