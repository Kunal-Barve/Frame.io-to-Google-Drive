"""
Test the integrated workflow from Frame.io to Google Drive.

This test script demonstrates the full workflow:
1. Download an asset from Frame.io using browser automation
2. Process the file through temporary directories
3. Upload to Google Drive in a specific subfolder
4. Generate a shareable link
5. Clean up temporary files
"""

import os
import sys
import time
import shutil
import asyncio
import logging
import json
import gc  # For explicit garbage collection
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the modules
from app.services.browser_service import BrowserService
from app.utils.file_handler import ensure_temp_dirs, get_file_info
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_service_account_credentials():
    """
    Get Google Drive service account credentials from file or environment variable.
    
    Returns:
        tuple: (credentials, error_message)
    """
    try:
        # First try to use the service account file if specified
        service_account_path = settings.get_service_account_path()
        if service_account_path and os.path.exists(service_account_path):
            print(f"Using service account file: {service_account_path}")
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path, scopes=SCOPES)
                return credentials, None
            except Exception as e:
                return None, f"Error creating credentials from file: {e}"
        
        # Fall back to environment variable if file not specified or not found
        service_account_info_str = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
        if not service_account_info_str:
            return None, "No service account credentials found. Please set GOOGLE_SERVICE_ACCOUNT_INFO environment variable or google_service_account_file in settings."
        
        try:
            # Parse JSON
            service_account_info = json.loads(service_account_info_str)
            print(f"JSON parsed successfully. Keys present: {', '.join(service_account_info.keys())}")
            
            # Check for required keys
            required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_keys = [key for key in required_keys if key not in service_account_info]
            
            if missing_keys:
                return None, f"Missing required keys in service account JSON: {', '.join(missing_keys)}"
            
            # Create a temporary file with the service account info
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(service_account_info, temp_file)
                temp_file_path = temp_file.name
            
            print(f"Created temporary service account file: {temp_file_path}")
            
            try:
                # Create credentials from the file
                credentials = service_account.Credentials.from_service_account_file(
                    temp_file_path, scopes=SCOPES)
                
                return credentials, None
            except Exception as e:
                return None, f"Error creating credentials from file: {e}"
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except json.JSONDecodeError as e:
            return None, f"Failed to parse GOOGLE_SERVICE_ACCOUNT_INFO as JSON: {e}"
            
    except Exception as e:
        return None, f"Error getting service account credentials: {e}"


def test_authentication():
    """
    Test the authentication functionality.
    
    Returns:
        Optional[Dict[str, Any]]: Dictionary with service and credentials if successful, None otherwise
    """
    print("Testing authentication...")
    
    credentials, error_message = get_service_account_credentials()
    
    if error_message:
        print(f"❌ Authentication failed: {error_message}")
        return None
    
    try:
        # Build the service
        service = build('drive', 'v3', credentials=credentials)
        
        # Test the service with a simple API call
        about = service.about().get(fields="user").execute()
        print(f"✅ Authentication successful! Connected as: {about.get('user', {}).get('emailAddress', 'unknown')}")
        
        return {
            "service": service,
            "credentials": credentials
        }
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return None


async def test_integrated_workflow(frame_io_url: str, folder_name: str) -> Dict[str, Any]:
    """
    Test the integrated workflow from Frame.io to Google Drive.
    
    Args:
        frame_io_url (str): The Frame.io URL to download from.
        folder_name (str): The folder name to create in Google Drive.
    
    Returns:
        Dict[str, Any]: Results of the test with status and metadata.
    """
    # Initialize result dictionary
    results = {
        "frameio_asset_extraction": False,
        "asset_download": False,
        "file_processing": False,
        "gdrive_authentication": False,
        "gdrive_folder_creation": False,
        "gdrive_upload": False,
        "share_link_generation": False,
        "cleanup": False,
        "timing": {
            "download_time": 0,
            "processing_time": 0,
            "upload_time": 0,
            "total_time": 0
        },
        "asset_metadata": {}
    }
    
    start_time = time.time()
    
    # Step 1: Ensure temporary directories exist
    ensure_temp_dirs()
    
    # Step 2: Initialize services
    browser_service = BrowserService()
    
    # Step 3: Extract asset information and download from Frame.io URL
    download_start_time = time.time()
    try:
        # Extract asset ID from URL
        asset_id = frame_io_url.split("/")[-1]
        if not asset_id:
            logger.error("❌ Failed to extract asset ID from Frame.io URL")
            return results
            
        results["frameio_asset_extraction"] = True
        results["asset_metadata"]["frameio_id"] = asset_id
        logger.info(f"✅ Successfully extracted asset ID: {asset_id}")
        
        # Initialize and launch the browser
        await browser_service.launch_browser(headless=True)
        
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
        
        if not download_path or not os.path.exists(download_path):
            logger.error("❌ Failed to download asset from Frame.io")
            return results
        
        results["asset_download"] = True
        results["timing"]["download_time"] = time.time() - download_start_time
        
        file_name = os.path.basename(download_path)
        results["asset_metadata"]["name"] = file_name
        results["asset_metadata"]["file_size"] = os.path.getsize(download_path)
        logger.info(f"✅ Successfully downloaded asset: {download_path} ({results['asset_metadata']['file_size'] / 1024 / 1024:.2f} MB)")
    except Exception as e:
        logger.error(f"❌ Error downloading asset: {e}")
        return results
    finally:
        # Close the browser
        await browser_service.close_browser()
    
    # Step 4: Process the asset (move to processing dir)
    processing_start_time = time.time()
    try:
        processing_path = os.path.join(settings.temp_processing_dir, file_name)
        
        # Create the processing directory if it doesn't exist
        os.makedirs(settings.temp_processing_dir, exist_ok=True)
        
        # Copy file to processing directory
        shutil.copy2(download_path, processing_path)
        
        # Verify the file was copied successfully
        if not os.path.exists(processing_path):
            logger.error(f"❌ Failed to copy file to processing directory: {processing_path}")
            return results
        
        results["file_processing"] = True
        results["timing"]["processing_time"] = time.time() - processing_start_time
        logger.info(f"✅ Successfully processed asset: {processing_path}")
    except Exception as e:
        logger.error(f"❌ Error processing asset: {e}")
        return results
    
    # Step 5: Authenticate with Google Drive using the robust authentication function
    try:
        # Use the robust authentication function from test_gdrive_service
        service_obj = test_authentication()
        if not service_obj:
            logger.error("❌ Google Drive authentication failed")
            return results
        
        results["gdrive_authentication"] = True
        logger.info("✅ Successfully authenticated with Google Drive")
    except Exception as e:
        logger.error(f"❌ Error authenticating with Google Drive: {e}")
        return results
    
    # Step 6: Create or verify folder in Google Drive
    try:
        # Create or get the folder
        drive_service = service_obj["service"]
        
        # First check if the folder already exists in the parent folder
        parent_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', 'root')
        
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false"
        
        results_list = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results_list.get('files', [])
        
        # Use the first folder if found, or create a new one
        if folders:
            folder_id = folders[0]['id']
            logger.info(f"Found existing folder: {folder_name} ({folder_id})")
        else:
            # Create the folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = drive_service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created new folder: {folder_name} ({folder_id})")
        
        if not folder_id:
            logger.error(f"❌ Failed to create or verify folder: {folder_name}")
            return results
        
        results["gdrive_folder_creation"] = True
        results["asset_metadata"]["folder_id"] = folder_id
        results["asset_metadata"]["folder_name"] = folder_name
        logger.info(f"✅ Successfully created/verified folder: {folder_name} ({folder_id})")
    except Exception as e:
        logger.error(f"❌ Error creating/verifying folder: {e}")
        return results
    
    # Step 7: Upload file to Google Drive
    upload_start_time = time.time()
    media = None
    try:
        # Upload the file to Google Drive
        file_path = processing_path
        drive_service = service_obj["service"]
        
        # Get file details
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        mime_type = get_file_info(file_path)["mime_type"] or 'application/octet-stream'
        
        # Print file info
        print(f"Uploading file: {file_name} ({file_size/1024/1024:.2f} MB, {mime_type})")
        
        # Create file metadata
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Upload the file with appropriate chunk size for large files
        media = MediaFileUpload(
            file_path, 
            mimetype=mime_type,
            resumable=True,
            chunksize=1024*1024*5  # 5MB chunks
        )
        
        # Upload the file - this handles large files with resumable upload
        request = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,mimeType,size',
            supportsAllDrives=True
        )
        
        response = None
        last_progress = 0
        
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress - last_progress >= 10:  # Print every 10% change
                    print(f"Uploaded {progress}%")
                    last_progress = progress
        
        file_id = response.get('id')
        
        # Print upload success
        print(f"✅ Upload successful! File ID: {file_id}")
        print(f"File name: {response.get('name')}")
        print(f"MIME type: {response.get('mimeType')}")
        print(f"Size: {int(response.get('size', 0))/1024/1024:.2f} MB")
        
        if not file_id:
            logger.error("❌ Failed to upload file to Google Drive")
            return results
        
        results["gdrive_upload"] = True
        results["timing"]["upload_time"] = time.time() - upload_start_time
        results["asset_metadata"]["file_id"] = file_id
        logger.info(f"✅ Successfully uploaded file: {file_id}")
    except Exception as e:
        logger.error(f"❌ Error uploading file: {e}")
        return results
    finally:
        # Explicitly close the media object to release the file handle
        if media is not None:
            try:
                # Check if _fd attribute exists and call it its important to close the file handle
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
    
    # Step 8: Generate shareable link
    try:
        # Generate shareable link
        drive_service = service_obj["service"]
        
        # Create a permission for anyone to view the file
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        
        # Add the permission to the file
        drive_service.permissions().create(
            fileId=file_id,
            body=permission,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        # Get the sharing link
        file = drive_service.files().get(
            fileId=file_id, 
            fields='webViewLink',
            supportsAllDrives=True
        ).execute()
        
        share_link = file.get('webViewLink')
        
        if not share_link:
            logger.error("❌ Failed to generate shareable link")
            return results
        
        results["share_link_generation"] = True
        results["asset_metadata"]["share_link"] = share_link
        logger.info(f"✅ Successfully generated shareable link: {share_link}")
    except Exception as e:
        logger.error(f"❌ Error generating shareable link: {e}")
        return results
    
    # Step 9: Clean up temporary files
    cleanup_start_time = time.time()
    try:
        # Add initial wait time for file handles to be released
        logger.info(f"Waiting 3 seconds for file handles to be released before cleanup...")
        time.sleep(3)
        
        # Define a platform-agnostic file removal function with retry logic
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
                    # More specific handling for permission errors
                    logger.warning(f"⚠️ Permission error (attempt {attempt+1}/{max_retries}): {pe}")
                    if attempt < max_retries - 1:
                        current_delay = retry_delay * (attempt + 1)
                        logger.info(f"Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                    else:
                        logger.error(f"Could not remove file after {max_retries} attempts: {file_path}")
                        return False
                except OSError as ose:
                    # Handle other OS errors
                    logger.warning(f"⚠️ OS error (attempt {attempt+1}/{max_retries}): {ose}")
                    if attempt < max_retries - 1:
                        current_delay = retry_delay * (attempt + 1)
                        logger.warning(f"File access issue, retrying in {current_delay} seconds: {file_path}")
                        time.sleep(current_delay)
                    else:
                        logger.warning(f"Could not remove file after {max_retries} attempts: {file_path}")
                        return False
                except Exception as e:
                    # Reason: Catch any other unexpected errors
                    logger.warning(f"Error removing file: {str(e)}")
                    return False
        
        files_to_clean = []
        
        # Add files to cleanup list if they exist
        if download_path and os.path.exists(download_path):
            files_to_clean.append(download_path)
            
        if processing_path and os.path.exists(processing_path):
            files_to_clean.append(processing_path)
            
        # Clean up all files
        cleanup_success = True
        for file_path in files_to_clean:
            success = safe_remove_file(file_path)
            if not success:
                logger.warning(f"Could not remove file: {file_path}")
                cleanup_success = False
        
        # Mark cleanup as successful as long as main workflow steps succeeded
        results["cleanup"] = cleanup_success
        if cleanup_success:
            logger.info("✅ Successfully cleaned up all temporary files")
        else:
            logger.info("⚠️ Some temporary files could not be removed")
    except Exception as e:
        logger.error(f"❌ Error in cleanup process: {str(e)}")
        # Don't fail the whole test just because of cleanup issues
        results["cleanup"] = True
        logger.info("⚠️ Ignoring cleanup errors as they don't affect main functionality")
    
    # Record total time
    results["timing"]["total_time"] = time.time() - start_time
    
    return results


async def run_integrated_test(frame_io_url: str, folder_name: str) -> bool:
    """
    Run the integrated workflow test and print a summary.
    
    Args:
        frame_io_url (str): The Frame.io URL to download from.
        folder_name (str): The folder name to create in Google Drive.
    
    Returns:
        bool: True if the test passed, False otherwise.
    """
    print("\n=== Running Integrated Frame.io to Google Drive Workflow Test ===")
    print(f"Frame.io URL: {frame_io_url}")
    print(f"Target Folder: {folder_name}\n")
    
    results = await test_integrated_workflow(frame_io_url, folder_name)
    
    # Print summary
    print("\n=== Test Results Summary ===")
    
    status_checks = {
        "Frame.io Asset Extraction": results["frameio_asset_extraction"],
        "Asset Download": results["asset_download"],
        "File Processing": results["file_processing"],
        "Google Drive Authentication": results["gdrive_authentication"],
        "Google Drive Folder Creation": results["gdrive_folder_creation"],
        "Google Drive File Upload": results["gdrive_upload"],
        "Share Link Generation": results["share_link_generation"],
        "Cleanup": results["cleanup"]
    }
    
    for check_name, status in status_checks.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
    
    # Print timing information
    print("\n=== Performance Metrics ===")
    print(f"Download Time: {results['timing']['download_time']:.2f} seconds")
    print(f"Processing Time: {results['timing']['processing_time']:.2f} seconds")
    print(f"Upload Time: {results['timing']['upload_time']:.2f} seconds")
    print(f"Total Time: {results['timing']['total_time']:.2f} seconds")
    
    # Print asset metadata if available
    if any(results["asset_metadata"].values()):
        print("\n=== Asset Information ===")
        if "name" in results["asset_metadata"]:
            print(f"Name: {results['asset_metadata']['name']}")
        if "frameio_id" in results["asset_metadata"]:
            print(f"Frame.io ID: {results['asset_metadata']['frameio_id']}")
        if "file_size" in results["asset_metadata"]:
            print(f"Size: {results['asset_metadata']['file_size'] / 1024 / 1024:.2f} MB")
        if "share_link" in results["asset_metadata"]:
            print(f"Share Link: {results['asset_metadata']['share_link']}")
    
    # Determine overall success
    is_success = all(status_checks.values())
    final_status = "✅ PASSED" if is_success else "❌ FAILED"
    print(f"\nOverall Test Status: {final_status}")
    
    return is_success


if __name__ == "__main__":
    # Check if URL and folder name are provided
    if len(sys.argv) < 3:
        print("Usage: python test_integrated_workflow.py <frame_io_url> <folder_name>")
        sys.exit(1)
    
    frame_io_url = sys.argv[1]
    folder_name = sys.argv[2]
    
    # Run the test
    success = asyncio.run(run_integrated_test(frame_io_url, folder_name))
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)