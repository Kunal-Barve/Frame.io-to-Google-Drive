"""
Command-line script to format a Google Service Account JSON key file for use in a .env file.

This script provides a simple command-line interface to the format_service_account utility.

Usage:
    python scripts/format_service_account_cli.py path/to/service-account.json

Example:
    python scripts/format_service_account_cli.py ./credentials/service-account.json
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the utility function
from app.utils.format_service_account import format_service_account_json, format_from_string


def print_usage():
    """Print usage instructions."""
    print("Usage:")
    print("  python scripts/format_service_account_cli.py path/to/service-account.json")
    print("  python scripts/format_service_account_cli.py --string '{\"type\":\"service_account\",...}'")
    print("\nOptions:")
    print("  --string, -s    Format a JSON string instead of a file")
    print("  --output, -o    Write output to a file instead of stdout")
    print("  --help, -h      Show this help message")


def main():
    """Main function to run the script."""
    # Parse command-line arguments
    args = sys.argv[1:]
    
    if not args or "--help" in args or "-h" in args:
        print_usage()
        return
    
    # Check for output file option
    output_file = None
    if "--output" in args or "-o" in args:
        try:
            output_index = args.index("--output") if "--output" in args else args.index("-o")
            output_file = args[output_index + 1]
            # Remove output option and value from args
            args.pop(output_index)
            args.pop(output_index)
        except (IndexError, ValueError):
            print("Error: --output option requires a file path")
            return
    
    # Check for string option
    if "--string" in args or "-s" in args:
        try:
            string_index = args.index("--string") if "--string" in args else args.index("-s")
            json_string = args[string_index + 1]
            # Format from string
            formatted_string = format_from_string(json_string)
        except (IndexError, ValueError):
            print("Error: --string option requires a JSON string")
            return
    else:
        # Format from file
        if not args:
            print("Error: No JSON file path provided")
            print_usage()
            return
        
        json_file_path = args[0]
        formatted_string = format_service_account_json(json_file_path)
    
    if formatted_string:
        if output_file:
            # Write to output file
            with open(output_file, 'w') as f:
                f.write(formatted_string)
            print(f"Formatted string written to {output_file}")
        else:
            # Print to stdout
            print("\n=== Copy the following line to your .env file ===\n")
            print(formatted_string)
            print("\n===================================================\n")


if __name__ == "__main__":
    main()
