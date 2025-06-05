"""
Script to test the Frame.io asset download functionality in headless mode.

This script uses the BrowserService to download an asset from Frame.io
using a headless browser.
"""

import os
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the BrowserService
from app.services.browser_service import BrowserService
from app.config import settings

# Sample Frame.io asset URL
SAMPLE_ASSET_URL = "https://next.frame.io/share/ec2520d4-c076-41e6-9ff3-a7d9ed6f2aa7/view/6588ba86-a8c2-4ce9-9962-e0bda4252e0c"


async def test_headless_download():
    """
    Test the Frame.io asset download functionality in headless mode.
    """
    print("Testing Frame.io asset download in headless mode...")
    
    # Create a BrowserService instance
    browser_service = BrowserService()
    
    try:
        # Launch the browser in headless mode
        await browser_service.launch_browser(headless=True)
        print("Browser launched in headless mode")
        
        # Download the asset
        download_path = await browser_service.download_frame_io_asset(SAMPLE_ASSET_URL)
        
        if download_path:
            print(f"Asset download test successful. File saved to: {download_path}")
            
            # Get file info
            file_size = os.path.getsize(download_path)
            file_name = os.path.basename(download_path)
            
            print(f"File name: {file_name}")
            print(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
            
            return True
        else:
            print("Asset download test failed.")
            return False
            
    except Exception as e:
        print(f"Error during asset download test: {e}")
        return False
        
    finally:
        # Close the browser
        await browser_service.close_browser()
        
        # Give asyncio a chance to clean up resources
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    # Run the test function
    success = asyncio.run(test_headless_download())
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
