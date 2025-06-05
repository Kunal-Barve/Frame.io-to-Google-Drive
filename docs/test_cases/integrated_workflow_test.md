# Integrated Workflow Test Case

## Overview
This test verifies the end-to-end workflow of downloading a media asset from Frame.io, processing it, uploading it to Google Drive (including Shared Drives), generating a shareable link, and cleaning up temporary files.

## Test File
`tests/services/test_integrated_workflow.py`

## Test Execution
```bash
python tests/services/test_integrated_workflow.py "https://f.io/ASSET_ID" "Target Folder Name"
```

## Test Steps
1. Extract asset ID from Frame.io URL
2. Launch browser and download asset from Frame.io
3. Process the downloaded file
4. Authenticate with Google Drive service account
5. Create or verify target folder in Google Drive
6. Upload processed file to Google Drive
7. Generate shareable link
8. Clean up temporary files

## Issues Encountered & Solutions

### 1. Cross-Platform Path Inconsistencies
**Issue**: The test used hard-coded Unix-style paths (`/tmp/downloads` and `/tmp/processing`) in the `config.py`, causing mixed path formats on Windows.

**Solution**: 
- Updated `config.py` to use platform-agnostic paths with `os.path.join()` and `PROJECT_ROOT`
- Changed from:
  ```python
  temp_download_dir: str = "/tmp/downloads"
  temp_processing_dir: str = "/tmp/processing"
  ```
- To:
  ```python
  temp_download_dir: str = os.path.join(PROJECT_ROOT, "tmp", "downloads")
  temp_processing_dir: str = os.path.join(PROJECT_ROOT, "tmp", "processing")
  ```

### 2. File Handle Leaks from MediaFileUpload
**Issue**: After uploading large video files to Google Drive, the `MediaFileUpload` object wasn't properly releasing file handles, causing file cleanup to fail with `[WinError 32] The process cannot access the file because it is being used by another process`.

**Solution**:
- Added explicit file handle closure for the `MediaFileUpload` object
- Directly accessed internal file descriptor via `_fd` attribute
- Implemented in a finally block to ensure execution regardless of upload success/failure
- Added garbage collection to force resource release
```python
finally:
    # Explicitly close the media object to release the file handle
    if media is not None:
        try:
            # Check if _fd attribute exists and call it
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

### 3. Browser Automation Timing Issues
**Issue**: Intermittent failures during Frame.io asset download with "Element is not attached to the DOM" errors, due to dynamic content and timing issues.

**Solution**:
- Implemented retry logic for browser automation downloads
- Added 3 attempts with increasing delays
- Added better error handling and logging
```python
# Download asset using browser automation with retry logic
max_download_attempts = 3
for attempt in range(max_download_attempts):
    try:
        logger.info(f"Download attempt {attempt+1}/{max_download_attempts}...")
        download_path = await browser_service.download_frame_io_asset(frame_io_url)
        
        if download_path and os.path.exists(download_path):
            break
        else:
            logger.warning(f"Download attempt {attempt+1} failed, retrying...")
            time.sleep(2)  # Wait before retry
    except Exception as e:
        logger.warning(f"Error during download attempt {attempt+1}: {str(e)}")
        if attempt < max_download_attempts - 1:
            logger.info("Retrying download...")
            time.sleep(2)  # Wait before retry
        else:
            logger.error(f"❌ Failed to download after {max_download_attempts} attempts: {str(e)}")
```

### 4. File Cleanup Reliability
**Issue**: File deletion was failing on Windows, especially for large video files.

**Solution**:
- Added initial wait period before cleanup starts
- Implemented exponential backoff for file deletion retries
- Improved error handling with specific exception types
- Enhanced logging to track deletion progress

## Key Learnings
1. Always use platform-agnostic paths with `os.path.join()` or `pathlib.Path`
2. Google API's `MediaFileUpload` doesn't automatically close file handles
3. Browser automation needs retry logic for reliable operation
4. Explicit resource cleanup (handle closing, garbage collection) is essential
5. Enhanced logging helps track issues in complex workflows

## Dependencies
- Playwright for browser automation
- Google Drive API v3
- Google OAuth2 service account credentials
- Python standard libraries for file operations and async handling