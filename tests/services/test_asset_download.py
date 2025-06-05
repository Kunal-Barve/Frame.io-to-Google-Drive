"""
Script to test the Frame.io asset download functionality.

This script uses the BrowserService to download an asset from Frame.io.
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
SAMPLE_ASSET_URL = "https://f.io/TafALVxa"  # Replace with a valid Frame.io asset URL


async def test_asset_download():
    """
    Test the Frame.io asset download functionality.
    """
    print("Testing Frame.io asset download...")
    
    # Create a BrowserService instance
    browser_service = BrowserService()
    
    try:
        # Launch the browser (non-headless for debugging)
        await browser_service.launch_browser(headless=False)
        
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


if __name__ == "__main__":
    # Run the test function
    success = asyncio.run(test_asset_download())
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
