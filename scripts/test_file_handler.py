"""
Script to test the file handling functionality.

This script tests the file_handler.py module's functionality for managing downloaded files.
"""

import os
import sys
import time
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the file_handler module
from app.utils.file_handler import (
    ensure_temp_dirs,
    get_file_info,
    format_file_size,
    calculate_md5,
    validate_video_file,
    move_to_processing,
    cleanup_temp_files,
    get_temp_file_stats
)
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


def test_file_info():
    """Test the get_file_info function."""
    print("\n=== Testing get_file_info ===")
    
    # Create a test file
    test_file = os.path.join(settings.temp_download_dir, "test_file_info.mp4")
    create_test_file(test_file, 500)  # 500 KB
    
    try:
        # Get file info
        file_info = get_file_info(test_file)
        
        # Print file info
        print(f"File name: {file_info['name']}")
        print(f"File size: {file_info['size']} bytes ({file_info['size_human']})")
        print(f"File extension: {file_info['extension']}")
        print(f"MIME type: {file_info['mime_type']}")
        print(f"MD5 hash: {file_info['md5']}")
        print(f"Created: {file_info['created']}")
        print(f"Modified: {file_info['modified']}")
        
        # Validate the results
        assert file_info['name'] == "test_file_info.mp4"
        assert file_info['size'] == 500 * 1024
        assert file_info['extension'] == ".mp4"
        assert file_info['mime_type'] == "video/mp4"
        assert file_info['md5'] is not None
        
        print("✅ get_file_info test passed")
    except Exception as e:
        print(f"❌ get_file_info test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)


def test_validate_video_file():
    """Test the validate_video_file function."""
    print("\n=== Testing validate_video_file ===")
    
    # Create test files
    valid_file = os.path.join(settings.temp_download_dir, "valid_video.mp4")
    invalid_ext = os.path.join(settings.temp_download_dir, "invalid_ext.xyz")
    empty_file = os.path.join(settings.temp_download_dir, "empty_video.mp4")
    
    create_test_file(valid_file, 500)  # 500 KB
    create_test_file(invalid_ext, 500)  # 500 KB
    create_test_file(empty_file, 0)     # 0 KB
    
    try:
        # Test valid video file
        is_valid, error = validate_video_file(valid_file)
        print(f"Valid video file: {is_valid} {error or ''}")
        assert is_valid, "Valid video file should be validated"
        
        # Test invalid extension
        is_valid, error = validate_video_file(invalid_ext)
        print(f"Invalid extension: {is_valid} {error or ''}")
        assert not is_valid, "Invalid extension should not be validated"
        
        # Test empty file
        is_valid, error = validate_video_file(empty_file)
        print(f"Empty file: {is_valid} {error or ''}")
        assert not is_valid, "Empty file should not be validated"
        
        # Test non-existent file
        is_valid, error = validate_video_file("non_existent_file.mp4")
        print(f"Non-existent file: {is_valid} {error or ''}")
        assert not is_valid, "Non-existent file should not be validated"
        
        print("✅ validate_video_file test passed")
    except Exception as e:
        print(f"❌ validate_video_file test failed: {e}")
    finally:
        # Clean up
        for file_path in [valid_file, invalid_ext, empty_file]:
            if os.path.exists(file_path):
                os.remove(file_path)


def test_move_to_processing():
    """Test the move_to_processing function."""
    print("\n=== Testing move_to_processing ===")
    
    # Create a test file
    test_file = os.path.join(settings.temp_download_dir, "test_move.mp4")
    create_test_file(test_file, 200)  # 200 KB
    
    try:
        # Move the file to processing
        processing_path = move_to_processing(test_file)
        
        # Verify the file was moved
        print(f"File moved to: {processing_path}")
        assert os.path.exists(processing_path), "File should exist in processing directory"
        assert not os.path.exists(test_file), "File should not exist in download directory"
        
        # Verify file content was preserved (by checking file size)
        assert os.path.getsize(processing_path) == 200 * 1024, "File size should be preserved"
        
        print("✅ move_to_processing test passed")
    except Exception as e:
        print(f"❌ move_to_processing test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        
        processing_file = os.path.join(settings.temp_processing_dir, "test_move.mp4")
        if os.path.exists(processing_file):
            os.remove(processing_file)


def test_cleanup_temp_files():
    """Test the cleanup_temp_files function."""
    print("\n=== Testing cleanup_temp_files ===")
    
    # Create test files with different ages
    old_file = os.path.join(settings.temp_download_dir, "old_file.mp4")
    new_file = os.path.join(settings.temp_download_dir, "new_file.mp4")
    
    create_test_file(old_file, 100)
    create_test_file(new_file, 100)
    
    # Set the modification time of the old file to 2 days ago
    old_time = time.time() - (2 * 24 * 3600)  # 2 days ago
    os.utime(old_file, (old_time, old_time))
    
    try:
        # Get stats before cleanup
        before_stats = get_temp_file_stats()
        print(f"Before cleanup: {before_stats['total_files']} files, {before_stats['total_size_human']}")
        
        # Cleanup files older than 1 day
        deleted_files = cleanup_temp_files(max_age_hours=24)
        print(f"Deleted files: {deleted_files}")
        
        # Get stats after cleanup
        after_stats = get_temp_file_stats()
        print(f"After cleanup: {after_stats['total_files']} files, {after_stats['total_size_human']}")
        
        # Verify old file was deleted
        assert not os.path.exists(old_file), "Old file should be deleted"
        
        # Verify new file was not deleted
        assert os.path.exists(new_file), "New file should not be deleted"
        
        # Verify number of files decreased by 1
        assert after_stats['total_files'] == before_stats['total_files'] - 1, "Total files should decrease by 1"
        
        print("✅ cleanup_temp_files test passed")
    except Exception as e:
        print(f"❌ cleanup_temp_files test failed: {e}")
    finally:
        # Clean up
        for file_path in [old_file, new_file]:
            if os.path.exists(file_path):
                os.remove(file_path)


def run_all_tests():
    """Run all tests."""
    print("Starting file handler tests...")
    
    # Ensure the temporary directories exist
    ensure_temp_dirs()
    
    # Run tests
    test_file_info()
    test_validate_video_file()
    test_move_to_processing()
    test_cleanup_temp_files()
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    # Fix paths for Windows
    if os.name == 'nt':
        # Override the default /tmp paths for Windows
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "downloads")
        processing_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "processing")
        
        settings.temp_download_dir = downloads_dir
        settings.temp_processing_dir = processing_dir
    
    # Run tests
    run_all_tests()
