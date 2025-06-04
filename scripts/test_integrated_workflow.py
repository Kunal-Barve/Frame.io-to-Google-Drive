"""
Integrated workflow test for Frame.io to Google Drive automation.

This script tests the complete workflow from downloading a Frame.io asset to processing it,
integrating the browser service, file handling, and download management functionality.
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the modules
from app.services.browser_service import BrowserService
from app.services.download_manager import DownloadManager, print_progress_callback
from app.utils.file_handler import ensure_temp_dirs, get_file_info, validate_video_file
from app.config import settings


async def integrated_test(frame_io_url: str):
    """
    Run an integrated test of the entire workflow.
    
    This test:
    1. Downloads an asset from Frame.io using the browser service
    2. Tracks the download progress using the download manager
    3. Validates the downloaded file using the file handler
    4. Moves the file to the processing directory
    
    Args:
        frame_io_url: URL of the Frame.io asset to download
    """
    print(f"\n===== Starting Integrated Workflow Test with URL: {frame_io_url} =====\n")
    
    # Ensure temp directories exist
    ensure_temp_dirs()
    
    # Initialize services
    browser_service = BrowserService()
    download_manager = DownloadManager()
    
    # Extract expected filename from URL for easier tracking
    url_parts = frame_io_url.split("/")
    asset_id = url_parts[-1] if len(url_parts) > 1 else "asset"
    
    try:
        # Step 1: Launch browser and download the asset
        print("\n[Step 1] Launching browser and downloading asset...")
        
        await browser_service.launch_browser(headless=True)
        print(f"Browser launched in headless mode")
        
        # Pre-register the download (we don't know the filename or size yet)
        temp_download_id = f"temp_{asset_id}_{int(time.time())}"
        
        # Register download with download manager
        download_id = download_manager.register_download(
            file_path=os.path.join(settings.temp_download_dir, f"temp_{asset_id}.mp4"),
            url=frame_io_url,
            total_size=0  # We don't know the size yet
        )
        
        # Add progress callback
        download_manager.active_downloads[download_id].add_callback(print_progress_callback)
        
        # Start the download
        print(f"Starting download from {frame_io_url}")
        download_path = await browser_service.download_frame_io_asset(frame_io_url)
        
        if not download_path:
            raise Exception("Download failed")
        
        print(f"Download completed: {download_path}")
        
        # Step 2: Track and verify the download
        print("\n[Step 2] Tracking and verifying download...")
        
        # Get file info
        file_info = get_file_info(download_path)
        print(f"Downloaded file: {file_info['name']}")
        print(f"File size: {file_info['size_human']}")
        print(f"MIME type: {file_info['mime_type']}")
        
        # Update download manager with actual file path and size
        # First, mark the temporary download as failed
        download_manager.mark_failed(download_id, "Replaced with actual download")
        
        # Register the actual download
        real_download_id = download_manager.register_download(
            file_path=download_path,
            url=frame_io_url,
            total_size=file_info['size']
        )
        
        # Mark as completed immediately since we already have the file
        success = download_manager.mark_completed(real_download_id, download_path)
        if not success:
            raise Exception("Failed to verify download")
        
        print("Download verified successfully")
        
        # Step 3: Process the download
        print("\n[Step 3] Processing the download...")
        
        # Validate that it's a video file
        is_valid, error = validate_video_file(download_path)
        if not is_valid:
            raise Exception(f"Invalid video file: {error}")
        
        print("File validated as a valid video file")
        
        # Process the completed download (move to processing directory)
        processing_path = await download_manager.process_completed_download(real_download_id)
        if not processing_path:
            raise Exception("Failed to process download")
        
        print(f"File moved to processing directory: {processing_path}")
        
        # Get download info
        download_info = download_manager.get_download_info(real_download_id)
        print(f"Final download status: {download_info['status']}")
        
        print("\n===== Integrated Workflow Test Completed Successfully =====")
        return processing_path
        
    except Exception as e:
        print(f"Error during integrated test: {e}")
        raise
    finally:
        # Close the browser
        if browser_service and browser_service.browser:
            await browser_service.close_browser()
            print("Browser closed")


async def main():
    """Main function to run the integrated test."""
    # Frame.io asset URL
    frame_io_url = "https://f.io/Uty0aKCs"
    
    # Fix paths for Windows
    if os.name == 'nt':
        # Override the default /tmp paths for Windows
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "downloads")
        processing_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "processing")
        
        settings.temp_download_dir = downloads_dir
        settings.temp_processing_dir = processing_dir
    
    try:
        # Run the integrated test
        result_path = await integrated_test(frame_io_url)
        
        # Print final result
        if result_path and os.path.exists(result_path):
            print("\nFinal Result:")
            print(f"Successfully downloaded and processed file: {os.path.basename(result_path)}")
            print(f"File location: {result_path}")
            print(f"File size: {os.path.getsize(result_path) / (1024 * 1024):.2f} MB")
            return 0  # Success
        else:
            print("\nTest failed: Final file not found")
            return 1  # Failure
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return 1  # Failure


if __name__ == "__main__":
    # Run the integrated test
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
