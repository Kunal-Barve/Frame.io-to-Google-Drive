"""
Script to test the Google Drive service functionality without browser interaction.

This script tests the gdrive_service.py module's functionality for Google Drive operations,
including authentication, file upload, and share link generation using a service account.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the modules
from app.utils.file_handler import ensure_temp_dirs, get_file_info
from app.config import settings

# Define the scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']


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
    """Test the authentication functionality."""
    print("\n=== Testing Google Drive Authentication ===")
    
    try:
        # Get credentials
        credentials, error = get_service_account_credentials()
        if error:
            print(f"❌ Authentication failed: {error}")
            return None
        
        # Build the service
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Authentication test passed")
        
        # Return a simple object with the service for other tests to use
        return {
            "credentials": credentials,
            "service": service,
            "target_folder_id": settings.google_drive_folder_id
        }
        
    except Exception as e:
        print(f"❌ Authentication test failed with error: {e}")
        return None


def test_file_upload(service_obj) -> Optional[Dict[str, Any]]:
    """
    Test the file upload functionality.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
        
    Returns:
        Optional[Dict[str, Any]]: File metadata if upload was successful, None otherwise
    """
    print("\n=== Testing Google Drive File Upload ===")
    
    if not service_obj:
        print("❌ File upload test skipped: No authenticated service")
        return None
    
    # Create a test file
    file_path = os.path.join(settings.temp_download_dir, "gdrive_test_upload.txt")
    create_test_file(file_path, 10)  # 10 KB
    
    try:
        # Create file metadata
        file_metadata = {
            'name': "Test Upload from Frame.io Automation",
        }
        
        # Only add parent folder if it exists
        if service_obj["target_folder_id"]:
            # First verify the folder exists
            try:
                folder = service_obj["service"].files().get(
                    fileId=service_obj["target_folder_id"],
                    fields="id,name"
                ).execute()
                print(f"Target folder found: {folder.get('name')} (ID: {folder.get('id')})")
                file_metadata['parents'] = [service_obj["target_folder_id"]]
            except Exception as e:
                print(f"Warning: Target folder not found or not accessible: {e}")
                print("Uploading to root folder instead")
        
        # Create media
        media = MediaFileUpload(
            file_path,
            mimetype='text/plain',
            resumable=True
        )
        
        # Upload the file
        file = service_obj["service"].files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,mimeType,webViewLink,size',
            supportsAllDrives=True,  # For Shared Drives
            supportsTeamDrives=True  # For backward compatibility
        ).execute()
        
        print(f"✅ File upload test passed: {file.get('name')} (ID: {file.get('id')})")
        return file
        
    except Exception as e:
        print(f"❌ File upload test failed with error: {e}")
        return None
    finally:
        # Clean up - use try/except to handle file in use errors
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except PermissionError:
            print(f"Warning: Could not delete test file {file_path} - it may be in use")


def test_share_link(service_obj, file_metadata: Dict[str, Any]) -> Optional[str]:
    """
    Test the share link generation functionality.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
        file_metadata: Metadata of the uploaded file
        
    Returns:
        Optional[str]: Share link if successful, None otherwise
    """
    print("\n=== Testing Google Drive Share Link Generation ===")
    
    if not service_obj or not file_metadata:
        print("❌ Share link test skipped: No authenticated service or file metadata")
        return None
    
    try:
        # Get the file ID
        file_id = file_metadata.get('id')
        
        # Create the permission
        permission = {
            'type': 'anyone',
            'role': 'reader',
            'allowFileDiscovery': False
        }
        
        # Create the permission
        service_obj["service"].permissions().create(
            fileId=file_id,
            body=permission,
            fields='id',
            supportsAllDrives=True,  # For Shared Drives
            supportsTeamDrives=True  # For backward compatibility
        ).execute()
        
        # Get the file to retrieve the webViewLink
        file = service_obj["service"].files().get(
            fileId=file_id,
            fields='webViewLink',
            supportsAllDrives=True,  # For Shared Drives
            supportsTeamDrives=True  # For backward compatibility
        ).execute()
        
        share_link = file.get('webViewLink')
        print(f"✅ Share link test passed: {share_link}")
        return share_link
        
    except Exception as e:
        print(f"❌ Share link test failed with error: {e}")
        return None


def test_list_files(service_obj):
    """
    Test the list files functionality.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
    """
    print("\n=== Testing Google Drive List Files ===")
    
    if not service_obj:
        print("❌ List files test skipped: No authenticated service")
        return
    
    try:
        folder_id = service_obj["target_folder_id"]
        
        if not folder_id:
            print("❌ List files test skipped: No target folder ID")
            # List files in root instead
            print("Listing files in root folder instead")
            query = "trashed = false"
        else:
            # First verify the folder exists
            try:
                folder = service_obj["service"].files().get(
                    fileId=folder_id,
                    fields="id,name"
                ).execute()
                print(f"Target folder found: {folder.get('name')} (ID: {folder.get('id')})")
                query = f"'{folder_id}' in parents and trashed = false"
            except Exception as e:
                print(f"Warning: Target folder not found or not accessible: {e}")
                print("Listing files in root folder instead")
                query = "trashed = false"
        
        # List the files
        results = service_obj["service"].files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, size, createdTime, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        print(f"✅ List files test passed: Found {len(files)} files")
        
        # Print the first 5 files
        for i, file in enumerate(files[:5]):
            print(f"  {i+1}. {file.get('name')} (ID: {file.get('id')})")
        
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
            
    except Exception as e:
        print(f"❌ List files test failed with error: {e}")


def test_media_upload(service_obj, file_path: str) -> Optional[Dict[str, Any]]:
    """
    Test the media file upload functionality.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
        file_path: Path to the media file to upload
        
    Returns:
        Optional[Dict[str, Any]]: File metadata if upload was successful, None otherwise
    """
    print(f"\n=== Testing Google Drive Media Upload: {os.path.basename(file_path)} ===")
    
    if not service_obj:
        print("❌ Media upload test skipped: No authenticated service")
        return None
    
    if not os.path.exists(file_path):
        print(f"❌ Media upload test failed: File not found at {file_path}")
        return None
    
    # Get file info
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Determine MIME type based on extension
    mime_type = "application/octet-stream"  # Default
    if file_ext in ['.mp4', '.mov', '.avi']:
        mime_type = f"video/{file_ext[1:]}"
    elif file_ext in ['.jpg', '.jpeg']:
        mime_type = "image/jpeg"
    elif file_ext in ['.png']:
        mime_type = "image/png"
    elif file_ext in ['.gif']:
        mime_type = "image/gif"
    
    print(f"File info: {file_name} ({file_size:.2f} MB, {mime_type})")
    
    try:
        # Create file metadata
        file_metadata = {
            'name': f"Test Upload - {file_name}",
        }
        
        # Only add parent folder if it exists
        if service_obj["target_folder_id"]:
            # First verify the folder exists
            try:
                folder = service_obj["service"].files().get(
                    fileId=service_obj["target_folder_id"],
                    fields="id,name",
                    supportsAllDrives=True # crucial as we are uploading to a shared drive
                ).execute()
                print(f"Target folder found: {folder.get('name')} (ID: {folder.get('id')})")
                file_metadata['parents'] = [service_obj["target_folder_id"]]
            except Exception as e:
                print(f"Warning: Target folder not found or not accessible: {e}")
                print("Uploading to root folder instead")
        
        # Create media with appropriate chunk size for larger files
        # Use 5MB chunks for files larger than 5MB
        chunk_size = 5 * 1024 * 1024 if file_size > 5 else 1024 * 1024
        
        print(f"Starting upload with {chunk_size/(1024*1024):.1f}MB chunks...")
        start_time = time.time()
        
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=chunk_size
        )
        
        # Upload the file
        file = service_obj["service"].files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,mimeType,webViewLink,size',
            supportsAllDrives=True,  # For Shared Drives
            supportsTeamDrives=True  # For backward compatibility
        ).execute()
        
        end_time = time.time()
        upload_time = end_time - start_time
        upload_speed = file_size / upload_time if upload_time > 0 else 0
        
        print(f"✅ Media upload test passed: {file.get('name')} (ID: {file.get('id')})")
        print(f"   Upload time: {upload_time:.2f} seconds ({upload_speed:.2f} MB/s)")
        print(f"   Web view link: {file.get('webViewLink')}")
        return file
        
    except Exception as e:
        print(f"❌ Media upload test failed with error: {e}")
        return None


def find_or_create_folder(service_obj, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    Find a folder by name in the parent folder or create it if it doesn't exist.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
        folder_name: Name of the folder to find or create
        parent_folder_id: ID of the parent folder (optional)
        
    Returns:
        Optional[str]: ID of the found or created folder, None if failed
    """
    try:
        # Build the query to find the folder
        query_parts = [f"name = '{folder_name}'", "mimeType = 'application/vnd.google-apps.folder'"]
        
        # Add parent folder condition if specified
        if parent_folder_id:
            query_parts.append(f"'{parent_folder_id}' in parents")
            
        query = " and ".join(query_parts)
        
        # Search for the folder
        results = service_obj["service"].files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            supportsTeamDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        
        # If folder exists, return its ID
        if folders:
            folder_id = folders[0].get('id')
            print(f"Found existing folder: {folder_name} (ID: {folder_id})")
            return folder_id
        
        # If folder doesn't exist, create it
        print(f"Folder not found. Creating: {folder_name}")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        # Add parent folder if specified
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
            
        # Create the folder
        folder = service_obj["service"].files().create(
            body=folder_metadata,
            fields='id, name',
            supportsAllDrives=True,
            supportsTeamDrives=True
        ).execute()
        
        folder_id = folder.get('id')
        print(f"Created new folder: {folder_name} (ID: {folder_id})")
        return folder_id
        
    except Exception as e:
        print(f"❌ Error finding/creating folder: {e}")
        return None


def test_folder_management(service_obj, folder_name: str) -> Optional[str]:
    """
    Test folder management functionality.
    
    Args:
        service_obj: Dictionary containing authenticated service and other info
        folder_name: Name of the folder to test with
        
    Returns:
        Optional[str]: ID of the found or created folder, None if failed
    """
    print(f"\n=== Testing Google Drive Folder Management: '{folder_name}' ===")
    
    if not service_obj:
        print("❌ Folder management test skipped: No authenticated service")
        return None
    
    try:
        parent_folder_id = service_obj["target_folder_id"]
        
        # Try to find or create the folder
        folder_id = find_or_create_folder(service_obj, folder_name, parent_folder_id)
        
        if folder_id:
            print(f"✅ Folder management test passed: Folder '{folder_name}' (ID: {folder_id})")
            return folder_id
        else:
            print("❌ Folder management test failed: Could not find or create folder")
            return None
    
    except Exception as e:
        print(f"❌ Folder management test failed with error: {e}")
        return None


def run_media_upload_test(media_file_path: str):
    """
    Run a test to upload a specific media file.
    
    Args:
        media_file_path: Path to the media file to upload
    """
    print(f"Starting Google Drive media upload test for: {media_file_path}")
    
    # Ensure the temporary directories exist
    ensure_temp_dirs()
    
    # Test authentication
    service_obj = test_authentication()
    
    # Test media upload
    if service_obj:
        file_metadata = test_media_upload(service_obj, media_file_path)
    
    # Test share link generation
    share_link = None
    if service_obj and file_metadata:
        share_link = test_share_link(service_obj, file_metadata)
    
    print("\nMedia upload test completed.")
    
    # Return results
    return {
        "service": service_obj is not None,
        "file_upload": file_metadata is not None,
        "share_link": share_link is not None
    }


def run_folder_upload_test(media_file_path: str, folder_name: str):
    """
    Run a test to upload a media file to a specific subfolder.
    
    This function demonstrates the complete workflow for the subfolder upload functionality:
    1. Authenticate with Google Drive
    2. Find or create a folder with the given name in the parent folder
    3. Upload the media file to that subfolder
    4. Generate a share link for the uploaded file
    
    Args:
        media_file_path: Path to the media file to upload
        folder_name: Name of the folder to upload to
        
    Returns:
        Dict with test results
    """
    print(f"Starting Google Drive subfolder upload test for: {media_file_path} in folder: {folder_name}")
    
    results = {
        "authentication": False,
        "folder_management": False,
        "media_upload": False,
        "share_link": False
    }
    
    # Ensure the temporary directories exist
    ensure_temp_dirs()
    
    # Test authentication
    service_obj = test_authentication()
    if not service_obj:
        print("❌ Authentication failed. Cannot proceed with test.")
        return results
        
    results["authentication"] = True
    
    # Test folder management - find or create the subfolder
    subfolder_id = test_folder_management(service_obj, folder_name)
    if not subfolder_id:
        print("❌ Folder management failed. Cannot proceed with test.")
        return results
        
    results["folder_management"] = True
    
    # Store the original target folder
    original_folder_id = service_obj["target_folder_id"]
    
    try:
        # Set the target folder to the subfolder for this upload
        service_obj["target_folder_id"] = subfolder_id
        print(f"Changed upload target from {original_folder_id} to subfolder: {subfolder_id}")
        
        # Test media upload to the subfolder
        file_metadata = test_media_upload(service_obj, media_file_path)
        if file_metadata:
            results["media_upload"] = True
            
            # Test share link generation
            share_link = test_share_link(service_obj, file_metadata)
            if share_link:
                results["share_link"] = True
    finally:
        # Restore the original target folder
        service_obj["target_folder_id"] = original_folder_id
    
    print("\nSubfolder upload test completed.")
    return results


def run_all_tests():
    """Run all tests."""
    print("Starting Google Drive service tests...")
    
    # Ensure the temporary directories exist
    ensure_temp_dirs()
    
    # Test authentication
    service_obj = test_authentication()
    
    # Test file upload
    file_metadata = None
    if service_obj:
        file_metadata = test_file_upload(service_obj)
    
    # Test share link generation
    share_link = None
    if service_obj and file_metadata:
        share_link = test_share_link(service_obj, file_metadata)
    
    # Test list files
    if service_obj:
        test_list_files(service_obj)
    
    # Test folder management
    if service_obj:
        test_folder_management(service_obj, "Test Folder")
    
    print("\nAll tests completed.")
    
    # Return results
    return {
        "service": service_obj is not None,
        "file_upload": file_metadata is not None,
        "share_link": share_link is not None
    }


if __name__ == "__main__":
    # Fix paths for Windows
    if os.name == 'nt':
        # Resolve relative paths for temporary directories
        downloads_dir = os.path.abspath(settings.temp_download_dir)
        processing_dir = os.path.abspath(settings.temp_processing_dir)
        settings.temp_download_dir = downloads_dir
        settings.temp_processing_dir = processing_dir
    
    # Check if a specific file path is provided as an argument
    if len(sys.argv) > 1:
        media_file_path = sys.argv[1]
        
        if not os.path.exists(media_file_path):
            print(f"Error: File not found at {media_file_path}")
            sys.exit(1)
            
        # If a second argument is provided, use it as folder name and run folder upload test
        if len(sys.argv) > 2:
            folder_name = sys.argv[2]
            results = run_folder_upload_test(media_file_path, folder_name)
        else:
            # Otherwise run regular media upload test
            results = run_media_upload_test(media_file_path)
            
        # Exit with appropriate code
        if results and all(results.values()):
            sys.exit(0)  # All tests passed
        else:
            sys.exit(1)  # Some tests failed
    else:
        # Run all tests
        results = run_all_tests()
        
        # Exit with appropriate code
        if all(results.values()):
            sys.exit(0)  # All tests passed
        else:
            sys.exit(1)  # Some tests failed
