"""
Utility script to format a Google Service Account JSON key file for use in a .env file.

This script takes a JSON file path as input, reads the file, and outputs a properly
formatted string that can be directly copied into a .env file.

Usage:
    python -m app.utils.format_service_account path/to/service-account.json

Example:
    python -m app.utils.format_service_account ./credentials/service-account.json
"""

import json
import sys
import argparse
from pathlib import Path


def format_service_account_json(json_file_path: str) -> str:
    """
    Format a Google Service Account JSON key file for use in a .env file.
    
    Args:
        json_file_path: Path to the JSON key file
        
    Returns:
        Formatted string for .env file
    """
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            service_account_info = json.load(f)
        
        # Convert to a properly formatted string for .env file
        env_value = json.dumps(service_account_info, separators=(',', ':'))
        
        # Return the formatted string
        return f"GOOGLE_SERVICE_ACCOUNT_INFO={env_value}"
    except json.JSONDecodeError:
        print(f"Error: The file {json_file_path} is not valid JSON.")
        return ""
    except FileNotFoundError:
        print(f"Error: The file {json_file_path} was not found.")
        return ""
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
        return ""


def format_from_string(json_string: str) -> str:
    """
    Format a Google Service Account JSON string for use in a .env file.
    
    Args:
        json_string: JSON string to format
        
    Returns:
        Formatted string for .env file
    """
    try:
        # Parse the JSON string
        service_account_info = json.loads(json_string)
        
        # Convert to a properly formatted string for .env file
        env_value = json.dumps(service_account_info, separators=(',', ':'))
        
        # Return the formatted string
        return f"GOOGLE_SERVICE_ACCOUNT_INFO={env_value}"
    except json.JSONDecodeError:
        print("Error: The provided string is not valid JSON.")
        return ""
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
        return ""


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Format a Google Service Account JSON key file for use in a .env file.'
    )
    parser.add_argument(
        'json_file_path',
        type=str,
        help='Path to the JSON key file'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Path to output file (optional, defaults to stdout)'
    )
    
    args = parser.parse_args()
    
    # Format the JSON file
    formatted_string = format_service_account_json(args.json_file_path)
    
    if formatted_string:
        if args.output:
            # Write to output file
            with open(args.output, 'w') as f:
                f.write(formatted_string)
            print(f"Formatted string written to {args.output}")
        else:
            # Print to stdout
            print("\n=== Copy the following line to your .env file ===\n")
            print(formatted_string)
            print("\n===================================================\n")


if __name__ == "__main__":
    main()
