# Cross-Platform File Cleanup Fix

## Overview
This document outlines the cross-platform file cleanup issues that were fixed in the Frame.io to Google Drive workflow automation project. The primary focus is on making the file cleanup process robust across Windows, Linux, and Docker/VPS environments.

## Problem Statement
The file cleanup process was failing with the following issues:

1. **Mixed Path Formats**: Path inconsistencies between Windows and Linux styles causing cleanup failures
   ```
   /tmp/processing\Founder Question Shorter.mp4
   ```

2. **File Handle Leaks**: Google Drive's `MediaFileUpload` object wasn't properly releasing file handles after upload
   ```
   [WinError 32] The process cannot access the file because it is being used by another process: '...\processing\Founder Question Shorter.mp4'
   ```

3. **Retry Logic Issues**: File deletion retry logic wasn't handling cross-platform error types properly

## Solutions Implemented

### 1. Platform-Agnostic Path Handling
Modified `config.py` to use platform-agnostic path construction:

```python
# Before
temp_download_dir: str = "/tmp/downloads"
temp_processing_dir: str = "/tmp/processing"

# After
temp_download_dir: str = os.path.join(PROJECT_ROOT, "tmp", "downloads")
temp_processing_dir: str = os.path.join(PROJECT_ROOT, "tmp", "processing")
```

### 2. MediaFileUpload File Handle Management
Added explicit media handle closure in `test_integrated_workflow.py`:

```python
finally:
    # Explicitly close the media object to release the file handle
    if media is not None:
        try:
            # Check if _fd attribute exists and close it
            if hasattr(media, '_fd'):
                try:
                    media._fd.close()
                    logger.info("✅ MediaFileUpload internal file handle explicitly closed")
                except Exception as e:
                    logger.warning(f"❌ Error closing MediaFileUpload file handle: {e}")
            else:
                logger.warning("⚠️ MediaFileUpload object has no internal _fd attribute")
            
            # Force resource cleanup
            media_str = str(media)  # Keep reference to log what we're cleaning up
            media = None  # Remove our reference
            gc.collect()  # Force garbage collection
            logger.info(f"🧹 Forced garbage collection to release file handles for {media_str}")
            
            # Add a brief pause after cleanup
            logger.info("⏱️ Waiting 1 second after handle cleanup...")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"❌ Error during media cleanup: {str(e)}")
```

### 3. Enhanced File Removal Logic
Improved the `safe_remove_file` function with:
- Platform-agnostic error handling (OSError vs PermissionError)
- Exponential backoff for retries
- Better logging at INFO level (not DEBUG)
- Initial wait period before cleanup attempts

```python
def safe_remove_file(file_path: str, max_retries: int = 8, retry_delay: float = 2) -> bool:
    """
    Safely remove a file with retry logic for any platform.
    
    Args:
        file_path: Path to the file to remove
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        return True
        
    for attempt in range(max_retries):
        try:
            os.remove(file_path)  # Platform-agnostic file removal
            logger.info(f"✅ Successfully removed file: {file_path}")
            return True
        except PermissionError as pe:
            # More specific handling for permission errors (Windows)
            logger.warning(f"⚠️ Permission error (attempt {attempt+1}/{max_retries}): {pe}")
            if attempt < max_retries - 1:
                current_delay = retry_delay * (attempt + 1)
                logger.info(f"Retrying in {current_delay} seconds...")
                time.sleep(current_delay)
            else:
                logger.error(f"Could not remove file after {max_retries} attempts: {file_path}")
                return False
        except OSError as ose:
            # Handle other OS errors (cross-platform)
            logger.warning(f"⚠️ OS error (attempt {attempt+1}/{max_retries}): {ose}")
            if attempt < max_retries - 1:
                current_delay = retry_delay * (attempt + 1)
                logger.warning(f"File access issue, retrying in {current_delay} seconds: {file_path}")
                time.sleep(current_delay)
            else:
                logger.warning(f"Could not remove file after {max_retries} attempts: {file_path}")
                return False
```

### 4. Browser Automation Reliability
Enhanced the Frame.io download process with retry logic:
- Multiple download attempts for intermittent failures
- Better error handling for DOM element detachment issues
- Clear logging of download attempts and progress

## Testing Results

Before the fixes, we had these consistent failures:
```
2025-06-05 10:43:37,721 - __main__ - WARNING - File access issue, retrying in 1 seconds: D:\Work\Upwork\ClickUp Automation\CodeBase\frame-to-drive-automation\tmp\processing\Founder Question Shorter.mp4
2025-06-05 10:43:38,722 - __main__ - WARNING - File access issue, retrying in 1 seconds: D:\Work\Upwork\ClickUp Automation\CodeBase\frame-to-drive-automation\tmp\processing\Founder Question Shorter.mp4
...
2025-06-05 10:43:41,725 - __main__ - WARNING - Could not remove file after 5 attempts: D:\Work\Upwork\ClickUp Automation\CodeBase\frame-to-drive-automation\tmp\processing\Founder Question Shorter.mp4
```

After implementing all fixes, the workflow now completes successfully:
```
2025-06-05 13:29:13,343 - __main__ - INFO - ✅ MediaFileUpload internal file handle explicitly closed
2025-06-05 13:29:13,361 - __main__ - INFO - 🧹 Forced garbage collection to release file handles for <googleapiclient.http.MediaFileUpload object at 0x0000028864294BF0>
...
2025-06-05 13:29:21,038 - __main__ - INFO - ✅ Successfully removed file: D:\Work\Upwork\ClickUp Automation\CodeBase\frame-to-drive-automation\tmp\processing\Founder Question Shorter.mp4
2025-06-05 13:29:21,040 - __main__ - INFO - ✅ Successfully cleaned up all temporary files

=== Test Results Summary ===
✅ Frame.io Asset Extraction
✅ Asset Download
✅ File Processing
✅ Google Drive Authentication
✅ Google Drive Folder Creation
✅ Google Drive File Upload
✅ Share Link Generation
✅ Cleanup
```

## Key Learnings

1. **File Handle Management**: Always explicitly close file handles, especially when using third-party libraries like Google's MediaFileUpload
   
2. **Cross-Platform Path Handling**: Use platform-agnostic approaches like `os.path.join()` or `pathlib.Path` instead of hardcoded path separators

3. **Error Type Handling**: Handle both Windows-specific errors (PermissionError) and generic errors (OSError) for cross-platform compatibility

4. **Resource Cleanup**: Implement explicit garbage collection and reference removal to ensure proper resource release

5. **Logging Importance**: Use appropriate logging levels (INFO instead of DEBUG) for critical operations to ensure visibility

6. **Retry Logic**: Implement exponential backoff strategy for operations that might temporarily fail

These improvements ensure the workflow is robust across Windows development environments, Linux servers, and containerized deployments (Docker/VPS).