"""
Script to install Playwright browsers.

This script installs the Chromium, Firefox, and WebKit browsers
required by Playwright. It's intended to be run once during setup
or in a Docker build process.
"""

import os
import sys
import subprocess
import asyncio
from playwright.async_api import async_playwright


def install_browsers_cli():
    """
    Install Playwright browsers using the CLI.
    
    This method uses the playwright CLI to install browsers.
    It's the recommended way to install browsers.
    """
    print("Installing Playwright browsers using CLI...")
    try:
        # Run the playwright install command
        result = subprocess.run(
            ["playwright", "install", "--with-deps", "chromium"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Installation output: {result.stdout}")
        print("Playwright browsers installed successfully using CLI.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing browsers using CLI: {e}")
        print(f"Error output: {e.stderr}")
        return False


async def install_browsers_api():
    """
    Install Playwright browsers using the API.
    
    This method uses the Playwright API to install browsers.
    It's an alternative if the CLI method fails.
    """
    print("Installing Playwright browsers using API...")
    try:
        async with async_playwright() as p:
            # Install Chromium browser
            print("Installing Chromium...")
            await p.chromium.install()
            print("Chromium installed successfully.")
            
            # Optionally install Firefox and WebKit
            # print("Installing Firefox...")
            # await p.firefox.install()
            # print("Firefox installed successfully.")
            
            # print("Installing WebKit...")
            # await p.webkit.install()
            # print("WebKit installed successfully.")
            
        print("All Playwright browsers installed successfully using API.")
        return True
    except Exception as e:
        print(f"Error installing browsers using API: {e}")
        return False


async def main():
    """
    Main function to install Playwright browsers.
    
    First tries to install using the CLI, then falls back to the API if needed.
    """
    # Try CLI method first
    if install_browsers_cli():
        return
    
    # Fall back to API method if CLI fails
    print("CLI installation failed, trying API method...")
    if await install_browsers_api():
        return
    
    # If both methods fail, exit with error
    print("Failed to install Playwright browsers using both methods.")
    sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
