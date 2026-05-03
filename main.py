"""
Lokr Assistant CLI Entrypoint.

This script provides a command-line interface to interact with the Lokr Assistant's
different modes: repair, review, and prevent.
"""

import argparse
import sys
import json

from modes.repair.runner import run_repair
from modes.review.runner import run_review
from modes.prevent.runner import run_prevent

def main():
    """
    Parse command-line arguments and route to the appropriate pipeline mode.
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
        help="The code string to analyze (required for 'repair' and 'prevent' modes)."
    )
    
    parser.add_argument(
        "-d", "--diff",
        type=str,
        help="The code diff string to review (required for 'review' mode)."
    )

    args = parser.parse_args()

    # Validate inputs based on mode
    if args.mode == "review":
        if not args.diff:
            print("Error: The '--diff' or '-d' argument is required for 'review' mode.")
            sys.exit(1)
        input_data = args.diff
    else:
        # For repair and prevent
        if not args.code:
            print(f"Error: The '--code' or '-c' argument is required for '{args.mode}' mode.")
            sys.exit(1)
        input_data = args.code

    config = {}

    # Execute the appropriate pipeline
    if args.mode == "repair":
        result = run_repair(input_data, config)
    elif args.mode == "review":
        result = run_review(input_data, config)
    elif args.mode == "prevent":
        result = run_prevent(input_data, config)
        
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
