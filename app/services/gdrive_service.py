"""
Google Drive service for Frame.io to Google Drive automation.

This module provides functionality for Google Drive operations, including:
- OAuth 2.0 authentication
- Service account authentication
- File upload to Google Drive
- Share link generation
"""

import os
import json
import time
import logging
import gc
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import google.oauth2.credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google Drive API scopes
# https://developers.google.com/drive/api/guides/api-specific-auth
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Per-file access to files created or opened by the app
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # View metadata for files
    'https://www.googleapis.com/auth/drive'
]


class GoogleDriveService:
    """
    Service for interacting with Google Drive API.
    
    This class provides methods for authenticating with Google Drive and
    performing operations such as uploading files and generating share links.
    """
    
    def __init__(self):
        """Initialize the GoogleDriveService."""
        self.credentials = None
        self.service = None
        self.target_folder_id = settings.google_drive_folder_id
        
        # Path to store token cache (for refreshing OAuth tokens)
        self.token_cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                           'tmp', 'tokens')
        self.token_path = os.path.join(self.token_cache_dir, 'google_token.json')
        
        # Create token cache directory if it doesn't exist
        os.makedirs(self.token_cache_dir, exist_ok=True)
    
    def authenticate_with_oauth(self) -> bool:
        """
        Authenticate with Google Drive using OAuth 2.0.
        
        This method uses the OAuth 2.0 flow to authenticate with Google Drive.
        It requires user interaction to authorize the application.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Check if we already have a valid token
            if os.path.exists(self.token_path):
                with open(self.token_path, 'r') as token:
                    self.credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(
                        json.load(token), SCOPES)
                
                # If credentials are expired and there's a refresh token, refresh them
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    try:
                        self.credentials.refresh(Request())
                        # Save refreshed credentials
                        with open(self.token_path, 'w') as token:
                            token.write(self.credentials.to_json())
                    except RefreshError:
                        # If refresh fails, we'll need to re-authenticate
                        self.credentials = None
            
            # If there are no (valid) credentials, create from environment variables
            if not self.credentials or not self.credentials.valid:
                # Check if required environment variables are available
                if not (settings.google_client_id and settings.google_client_secret):
                    logger.error("Missing Google OAuth credentials in environment variables")
                    return False
                
                # Create client config from environment variables
                client_config = {
                    "installed": {
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uris": [settings.google_redirect_uri, "http://localhost"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                }
                
                # Run the OAuth flow
                flow = InstalledAppFlow.from_client_config(
                    client_config, SCOPES, redirect_uri=settings.google_redirect_uri)
                self.credentials = flow.run_local_server(port=0)
                
                # Save the credentials for future use
                with open(self.token_path, 'w') as token:
                    token.write(self.credentials.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Successfully authenticated with Google Drive using OAuth")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive using OAuth: {e}")
            return False
    
    def authenticate_with_service_account(self) -> bool:
        """
        Authenticate with Google Drive using a service account.
        
        This method uses a service account to authenticate with Google Drive.
        It does not require user interaction, making it suitable for server environments.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Check if service account credentials are provided in environment variables
            service_account_info_str = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
            
            if not service_account_info_str:
                logger.error("GOOGLE_SERVICE_ACCOUNT_INFO environment variable not found")
                return False
            
            try:
                # Parse the JSON string from environment variable
                service_account_info = json.loads(service_account_info_str)
            except json.JSONDecodeError:
                logger.error("Failed to parse GOOGLE_SERVICE_ACCOUNT_INFO as JSON")
                return False
            
            # Authenticate using service account info from environment variable
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Successfully authenticated with Google Drive using service account")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive using service account: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive.
        
        This method attempts to authenticate with Google Drive using a service account first.
        If that fails, it falls back to OAuth 2.0 authentication.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        # Check if we already have a service
        if self.service:
            logger.info("Already authenticated with Google Drive")
            return True
            
        # Try to get service account credentials from file first
        service_account_path = settings.get_service_account_path()
        if service_account_path and os.path.exists(service_account_path):
            logger.info(f"Using service account file: {service_account_path}")
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    service_account_path, scopes=SCOPES)
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Successfully authenticated with Google Drive using service account file")
                return True
            except Exception as e:
                logger.error(f"Error authenticating with service account file: {e}")
        
        # Try service account authentication from environment variable
        if self.authenticate_with_service_account():
            return True
        
        # Fall back to OAuth authentication
        logger.info("Service account authentication failed, falling back to OAuth")
        return self.authenticate_with_oauth()
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None, name: Optional[str] = None, 
                   mime_type: Optional[str] = None, chunk_size: int = 5 * 1024 * 1024) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Google Drive with support for shared drives.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to (default: target folder ID)
            name: Name to give the file in Google Drive (default: file's basename)
            mime_type: MIME type of the file (default: auto-detect)
            chunk_size: Chunk size in bytes for resumable uploads (default: 5MB)
            
        Returns:
            Optional[Dict[str, Any]]: File metadata if upload was successful, None otherwise
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return None
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Use file's basename if name not provided
            if not name:
                name = os.path.basename(file_path)
                
            # Use target folder if folder_id not provided
            if not folder_id:
                folder_id = self.target_folder_id
            
            # Get file size for logging
            file_size = os.path.getsize(file_path)
            
            # Try to determine mime type if not provided
            if not mime_type:
                import mimetypes
                mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            
            # Create file metadata
            file_metadata = {
                'name': name
            }
            
            # Add parent folder if specified
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media with appropriate chunk size for large files
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True,  # Enable resumable uploads for large files
                chunksize=chunk_size  # Use specified chunk size
            )
            
            # Start upload timer
            start_time = time.time()
            
            # Upload the file with shared drive support and progress tracking
            logger.info(f"Uploading file: {file_path} ({file_size/1024/1024:.2f} MB, {mime_type}) to Google Drive")
            
            # Create the request but don't execute it yet (for progress tracking)
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,webViewLink,webContentLink,size',
                supportsAllDrives=True,  # For Shared Drives
                supportsTeamDrives=True  # For backward compatibility
            )
            
            # Execute the request with progress tracking
            response = None
            last_progress = 0
            
            # Process the upload in chunks with progress updates
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress - last_progress >= 5:  # Log every 5% change
                        logger.info(f"Upload progress: {progress}%")
                        last_progress = progress
            
            file = response
            
            # Calculate upload speed
            end_time = time.time()
            upload_time = end_time - start_time
            upload_speed = file_size / upload_time if upload_time > 0 else 0
            
            logger.info(f"File uploaded successfully: {file.get('name')} (ID: {file.get('id')})")
            logger.info(f"Upload time: {upload_time:.2f} seconds ({upload_speed/1024/1024:.2f} MB/s)")
            
            return file
            
        except HttpError as e:
            logger.error(f"HTTP error during file upload: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None
        finally:
            # Clean up the media object to prevent file handle leaks
            if 'media' in locals() and media is not None:
                try:
                    # Check if _fd attribute exists and close it 
                    if hasattr(media, '_fd'):
                        try:
                            media._fd.close()
                            logger.info("MediaFileUpload internal file handle explicitly closed")
                        except Exception as e:
                            logger.warning(f"Error closing MediaFileUpload file handle: {e}")
                    
                    # Force resource cleanup
                    media_str = str(media)  # Keep reference to log what we're cleaning up
                    media = None  # Remove our reference
                    import gc
                    gc.collect()  # Force garbage collection
                    logger.info(f"Forced garbage collection to release file handles for {media_str}")
                except Exception as e:
                    logger.warning(f"Error during media cleanup: {str(e)}")
    
    def create_share_link(self, file_id: str, role: str = 'reader', 
                         type: str = 'anyone') -> Optional[str]:
        """
        Create a shareable link for a file.
        
        Args:
            file_id: ID of the file to share
            role: Role to grant (reader, writer, commenter)
            type: Type of sharing (user, group, domain, anyone)
            
        Returns:
            str: Share link URL or None if error
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return None
        
        try:
            # Create permission
            permission = {
                'type': type,
                'role': role,
                'allowFileDiscovery': False
            }
            
            # Create the permission
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            # Get the file metadata including webViewLink
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink, webContentLink',
                supportsAllDrives=True
            ).execute()
            
            # Use webContentLink if available, otherwise use webViewLink
            share_link = file.get('webContentLink', file.get('webViewLink'))
            
            # Log success
            logger.info(f"Created share link for file {file_id}: {share_link}")
            
            return share_link
            
        except HttpError as e:
            logger.error(f"HTTP error creating share link: {e}")
            return None
            logger.error(f"Error creating share link: {e}")
            return None
    
    def find_or_create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder by name in the parent folder or create it if it doesn't exist.
        
        Args:
            folder_name: Name of the folder to find or create
            parent_folder_id: ID of the parent folder (default: target folder ID)
            
        Returns:
            Optional[str]: ID of the found or created folder, None if failed
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return None
        
        try:
            # Use target folder as parent if not specified
            if not parent_folder_id:
                parent_folder_id = self.target_folder_id
                
            # Build the query to find the folder
            query_parts = [f"name = '{folder_name}'"]
            query_parts.append("mimeType = 'application/vnd.google-apps.folder'")
            
            # Add parent folder condition if specified
            if parent_folder_id:
                query_parts.append(f"'{parent_folder_id}' in parents")
                
            # Add not trashed condition
            query_parts.append("trashed = false")
                
            query = " and ".join(query_parts)
            
            # Search for the folder
            results = self.service.files().list(
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
                logger.info(f"Found existing folder: {folder_name} (ID: {folder_id})")
                return folder_id
            
            # If folder doesn't exist, create it
            logger.info(f"Folder not found. Creating: {folder_name}")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # Add parent folder if specified
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
                
            # Create the folder
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name',
                supportsAllDrives=True,
                supportsTeamDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created new folder: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except HttpError as e:
            logger.error(f"HTTP error finding/creating folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Error finding/creating folder: {e}")
            return None
            
    def get_upload_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an uploaded file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Optional[Dict[str, Any]]: File metadata if successful, None otherwise
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return None
        
        try:
            # Get the file metadata
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,webViewLink,size,createdTime,modifiedTime'
            ).execute()
            
            return file
            
        except HttpError as e:
            logger.error(f"HTTP error getting file status: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file status: {e}")
            return None
    
    def list_files_in_folder(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in a Google Drive folder.
        
        Args:
            folder_id: ID of the folder (default: target folder)
            
        Returns:
            List[Dict[str, Any]]: List of file metadata
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return []
        
        try:
            # Use target folder if folder_id not provided
            if not folder_id:
                folder_id = self.target_folder_id
            
            if not folder_id:
                logger.error("No folder ID provided or configured")
                return []
            
            # Query for files in the folder
            query = f"'{folder_id}' in parents and trashed = false"
            
            # List the files
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, size, createdTime, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
            
        except HttpError as e:
            logger.error(f"HTTP error listing files: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing files in Google Drive folder: {e}")
            return []


# Example usage
def test_google_drive_service():
    """Test the GoogleDriveService functionality."""
    service = GoogleDriveService()
    
    # Authenticate
    if not service.authenticate():
        logger.error("Authentication failed")
        return
    
    # List files in target folder
    files = service.list_files_in_folder()
    for file in files:
        print(f"File: {file.get('name')} (ID: {file.get('id')})")


if __name__ == "__main__":
    # Run the test function
    test_google_drive_service()
