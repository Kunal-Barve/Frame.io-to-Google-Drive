"""
Script to test the download management functionality.

This script tests the download_manager.py module's functionality for managing downloads,
including progress tracking, timeout handling, completion verification, and file integrity checks.
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
from app.services.download_manager import (
    DownloadManager,
    DownloadProgress,
    format_speed,
    print_progress_callback
)
from app.utils.file_handler import ensure_temp_dirs
from app.config import settings


def create_test_file(file_path: str, size_kb: int = 100) -> str:
    """
    Create a test file of specified size.
    
    Args:
        file_path: Path where the file will be created
        size_kb: Size of the file in KB
        
    Returns:
        Path to the created file
    """
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create a file with random data
    with open(file_path, 'wb') as f:
        # Write size_kb kilobytes of random-like data
        for i in range(size_kb):
            f.write(bytes([i % 256 for _ in range(1024)]))
    
    print(f"Created test file: {file_path} ({size_kb} KB)")
    return file_path


class ProgressTracker:
    """Simple class to track progress updates."""
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.last_percentage = 0
        self.updates = []
        
    def callback(self, progress_info: Dict[str, Any]) -> None:
        """
        Callback function to receive progress updates.
        
        Args:
            progress_info: Dictionary with progress information
        """
        percentage = progress_info.get("percentage", 0)
        
        # Only log when percentage changes by at least 5%
        if int(percentage / 5) > int(self.last_percentage / 5):
            print(f"Progress: {percentage:.1f}% ({progress_info.get('downloaded_size', 0) / 1024:.1f} KB)")
            self.updates.append(progress_info)
            self.last_percentage = percentage


async def test_progress_tracking():
    """Test the progress tracking functionality."""
    print("\n=== Testing progress tracking ===")
    
    # Create a download manager
    manager = DownloadManager()
    
    # Create a test file
    file_path = os.path.join(settings.temp_download_dir, "test_progress.mp4")
    create_test_file(file_path, 1000)  # 1000 KB
    
    try:
        # Register a download
        download_id = manager.register_download(
            file_path=file_path,
            url="https://example.com/test_progress.mp4",
            total_size=1000 * 1024  # 1000 KB
        )
        
        # Add a progress tracker
        tracker = ProgressTracker()
        manager.active_downloads[download_id].add_callback(tracker.callback)
        
        # Also add the standard print callback
        manager.active_downloads[download_id].add_callback(print_progress_callback)
        
        # Simulate download progress
        for i in range(0, 101, 10):
            manager.update_progress(
                download_id=download_id,
                downloaded_size=int(i * 10 * 1024),  # i * 10 KB
                status="downloading"
            )
            await asyncio.sleep(0.1)
        
        # Mark as completed
        success = manager.mark_completed(download_id, file_path)
        
        # Verify results
        assert success, "Download should be marked as completed successfully"
        assert len(tracker.updates) > 0, "Progress tracker should have received updates"
        assert tracker.updates[-1]["status"] == "completed", "Final status should be 'completed'"
        
        # Get download info
        info = manager.get_download_info(download_id)
        print(f"Final download info: {info}")
        
        print("✅ Progress tracking test passed")
    except Exception as e:
        print(f"❌ Progress tracking test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)


async def test_file_monitoring():
    """Test the file growth monitoring functionality."""
    print("\n=== Testing file monitoring ===")
    
    # Create a download manager
    manager = DownloadManager()
    
    # Create a test file path (don't create the file yet)
    file_path = os.path.join(settings.temp_download_dir, "test_monitor.mp4")
    
    try:
        # Register a download
        download_id = manager.register_download(
            file_path=file_path,
            url="https://example.com/test_monitor.mp4",
            total_size=500 * 1024  # 500 KB
        )
        
        # Add the standard print callback
        manager.active_downloads[download_id].add_callback(print_progress_callback)
        
        # Start monitoring in a separate task
        monitor_task = asyncio.create_task(
            manager.monitor_file_growth(
                download_id=download_id,
                file_path=file_path,
                timeout_seconds=10,  # Short timeout for testing
                progress_interval=0.5  # Quick updates
            )
        )
        
        # Simulate a file being created and growing over time
        # Wait a bit before creating the file
        await asyncio.sleep(1)
        
        # Create the file with initial content
        create_test_file(file_path, 100)  # 100 KB
        
        # Simulate the file growing over time
        for i in range(2, 6):
            await asyncio.sleep(1)
            create_test_file(file_path, i * 100)  # Increase by 100 KB each time
        
        # Wait for monitoring to detect completion
        success = await monitor_task
        
        # Verify results
        assert success, "File monitoring should succeed"
        assert download_id not in manager.active_downloads, "Download should be moved from active downloads"
        assert any(d.get("id") == download_id for d in manager.completed_downloads), "Download should be in completed downloads"
        
        print("✅ File monitoring test passed")
    except Exception as e:
        print(f"❌ File monitoring test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)


async def test_timeout_handling():
    """Test the timeout handling functionality."""
    print("\n=== Testing timeout handling ===")
    
    # Create a download manager
    manager = DownloadManager()
    
    # Create a test file
    file_path = os.path.join(settings.temp_download_dir, "test_timeout.mp4")
    create_test_file(file_path, 100)  # 100 KB
    
    try:
        # Register a download with incorrect size
        download_id = manager.register_download(
            file_path=file_path,
            url="https://example.com/test_timeout.mp4",
            total_size=1000 * 1024  # 1000 KB (much larger than actual)
        )
        
        # Start monitoring in a separate task with very short timeout
        monitor_task = asyncio.create_task(
            manager.monitor_file_growth(
                download_id=download_id,
                file_path=file_path,
                timeout_seconds=3,  # Very short timeout
                progress_interval=0.5
            )
        )
        
        # Wait for monitoring to time out
        success = await monitor_task
        
        # Verify results
        assert not success, "Monitoring should fail due to timeout"
        assert download_id not in manager.active_downloads, "Download should be moved from active downloads"
        assert any(d.get("id") == download_id for d in manager.failed_downloads), "Download should be in failed downloads"
        
        # Get download info
        info = manager.get_download_info(download_id)
        print(f"Failed download info: {info}")
        assert info.get("status") == "timed_out", "Status should be 'timed_out'"
        
        print("✅ Timeout handling test passed")
    except Exception as e:
        print(f"❌ Timeout handling test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)


async def test_download_verification():
    """Test the download verification functionality."""
    print("\n=== Testing download verification ===")
    
    # Create a download manager
    manager = DownloadManager()
    
    # Create test files
    valid_file = os.path.join(settings.temp_download_dir, "valid_download.mp4")
    invalid_file = os.path.join(settings.temp_download_dir, "invalid_download.txt")
    missing_file = os.path.join(settings.temp_download_dir, "missing_download.mp4")
    
    create_test_file(valid_file, 200)    # 200 KB valid video file
    create_test_file(invalid_file, 200)  # 200 KB non-video file
    
    try:
        # Test valid file
        valid_id = manager.register_download(
            file_path=valid_file,
            url="https://example.com/valid.mp4",
            total_size=200 * 1024  # 200 KB
        )
        
        valid_result = manager.mark_completed(valid_id, valid_file)
        print(f"Valid file verification: {valid_result}")
        assert valid_result, "Valid file should be verified successfully"
        
        # Test invalid file (wrong extension)
        invalid_id = manager.register_download(
            file_path=invalid_file,
            url="https://example.com/invalid.txt",
            total_size=200 * 1024  # 200 KB
        )
        
        invalid_result = manager.mark_completed(invalid_id, invalid_file)
        print(f"Invalid file verification: {invalid_result}")
        assert not invalid_result, "Invalid file should fail verification"
        
        # Test missing file
        missing_id = manager.register_download(
            file_path=missing_file,
            url="https://example.com/missing.mp4",
            total_size=200 * 1024  # 200 KB
        )
        
        missing_result = manager.mark_completed(missing_id, missing_file)
        print(f"Missing file verification: {missing_result}")
        assert not missing_result, "Missing file should fail verification"
        
        print("✅ Download verification test passed")
    except Exception as e:
        print(f"❌ Download verification test failed: {e}")
    finally:
        # Clean up
        for file_path in [valid_file, invalid_file]:
            if os.path.exists(file_path):
                os.remove(file_path)


async def test_process_completed_download():
    """Test the process_completed_download functionality."""
    print("\n=== Testing process_completed_download ===")
    
    # Create a download manager
    manager = DownloadManager()
    
    # Create a test file
    file_path = os.path.join(settings.temp_download_dir, "test_process.mp4")
    create_test_file(file_path, 300)  # 300 KB
    
    try:
        # Register and complete a download
        download_id = manager.register_download(
            file_path=file_path,
            url="https://example.com/test_process.mp4",
            total_size=300 * 1024  # 300 KB
        )
        
        manager.mark_completed(download_id, file_path)
        
        # Process the completed download
        processing_path = await manager.process_completed_download(download_id)
        
        # Verify results
        assert processing_path is not None, "Processing path should not be None"
        assert os.path.exists(processing_path), "File should exist in processing directory"
        assert not os.path.exists(file_path), "File should not exist in download directory"
        
        # Get download info and check status
        info = manager.get_download_info(download_id)
        print(f"Processed download info: {info}")
        assert info.get("status") == "processing", "Status should be 'processing'"
        assert info.get("file_path") == processing_path, "File path should be updated"
        
        print("✅ Process completed download test passed")
    except Exception as e:
        print(f"❌ Process completed download test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        processing_file = os.path.join(settings.temp_processing_dir, "test_process.mp4")
        if os.path.exists(processing_file):
            os.remove(processing_file)


async def run_all_tests():
    """Run all tests."""
    print("Starting download manager tests...")
    
    # Ensure the temporary directories exist
    ensure_temp_dirs()
    
    # Run tests
    await test_progress_tracking()
    await test_file_monitoring()
    await test_timeout_handling()
    await test_download_verification()
    await test_process_completed_download()
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    # Fix paths for Windows
    if os.name == 'nt':
        # Override the default /tmp paths for Windows
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "downloads")
        processing_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "processing")
        
        settings.temp_download_dir = downloads_dir
        settings.temp_processing_dir = processing_dir
    
    # Run all tests
    asyncio.run(run_all_tests())
