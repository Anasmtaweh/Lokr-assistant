"""
Lokr Assistant CLI Entrypoint.

This script provides a command-line interface to interact with the Lokr Assistant
using the main run_assistant() orchestrator entry point.
"""

import argparse
import sys
import json
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from modes.orchestrator import run_assistant

def main():
    """
    Parse command-line arguments and route to the orchestrator assistant.
    """
    parser = argparse.ArgumentParser(
        description="Lokr Assistant CLI. Run in repair, review, or prevent mode."
    )
    
    parser.add_argument(
        "mode",
        choices=["repair", "review", "prevent"],
        help="The mode of operation: 'repair', 'review', or 'prevent'."
    )
    
    parser.add_argument(
        "-c", "--code",
        type=str,
        help="The code string to analyze (used for 'repair' and 'prevent' modes)."
    )
    
    parser.add_argument(
        "-d", "--diff",
        type=str,
        help="The code diff string to review (used for 'review' mode)."
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5-coder:7b",
        help="The name of the LLM model to use (default: 'qwen2.5-coder:7b')."
    )
    
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:11434",
        help="The base URL of the LLM API (default: 'http://localhost:11434')."
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for OpenAI-compatible endpoints."
    )

    parser.add_argument(
        "--api-type",
        type=str,
        default="ollama",
        choices=["ollama", "openai"],
        help="The API provider type: 'ollama' or 'openai' (default: 'ollama')."
    )

    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Path to the project directory to analyze."
    )

    args = parser.parse_args()

    # Validate inputs based on mode and construct user_input
    if args.mode == "repair":
        if not args.code:
            print("Error: The '--code' or '-c' argument is required for 'repair' mode.")
            sys.exit(1)
        user_input = f"Repair this code:\n{args.code}"
    elif args.mode == "review":
        if not args.diff:
            print("Error: The '--diff' or '-d' argument is required for 'review' mode.")
            sys.exit(1)
        user_input = f"Review this diff:\n{args.diff}"
    elif args.mode == "prevent":
        input_data = args.code or args.diff
        if not input_data:
            print("Error: Either '--code'/' -c' or '--diff'/' -d' is required for 'prevent' mode.")
            sys.exit(1)
        user_input = f"Check if this change is safe to deploy:\n{input_data}"

    # Auto-detect openai provider if api_key is provided and api-type wasn't explicitly passed
    api_key = args.api_key or os.environ.get("API_KEY")
    api_type = args.api_type
    if api_key and api_type == "ollama" and ("--api-type" not in sys.argv):
        api_type = "openai"

    # Call run_assistant from modes.orchestrator
    try:
        result = run_assistant(
            user_input=user_input,
            project_path=args.project,
            model=args.model,
            use_lokr=bool(args.project),
            progress_callback=print,
            api_type=api_type,
            base_url=args.api_url,
            api_key=api_key
        )
        print("\nFinal Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error executing assistant: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
