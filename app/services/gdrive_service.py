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
import logging
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
        # Try service account authentication first (better for server environments)
        if self.authenticate_with_service_account():
            return True
        
        # Fall back to OAuth authentication
        logger.info("Service account authentication failed, falling back to OAuth")
        return self.authenticate_with_oauth()
    
    def upload_file(self, file_path: str, name: Optional[str] = None, 
                   mime_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            name: Name to give the file in Google Drive (default: file's basename)
            mime_type: MIME type of the file (default: auto-detect)
            
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
            
            # Create file metadata
            file_metadata = {
                'name': name,
                'parents': [self.target_folder_id] if self.target_folder_id else None
            }
            
            # Remove None values
            file_metadata = {k: v for k, v in file_metadata.items() if v is not None}
            
            # Create media
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True  # Enable resumable uploads for large files
            )
            
            # Upload the file
            logger.info(f"Uploading file: {file_path} to Google Drive")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,webViewLink,size'
            ).execute()
            
            logger.info(f"File uploaded successfully: {file.get('name')} (ID: {file.get('id')})")
            return file
            
        except HttpError as e:
            logger.error(f"HTTP error during file upload: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None
    
    def create_share_link(self, file_id: str, role: str = 'reader', 
                         type: str = 'anyone') -> Optional[str]:
        """
        Create a share link for a file in Google Drive.
        
        Args:
            file_id: ID of the file to share
            role: Permission role to grant (reader, writer, commenter)
            type: Type of permission (user, group, domain, anyone)
            
        Returns:
            Optional[str]: Share link if successful, None otherwise
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Drive")
                return None
        
        try:
            # Create the permission
            permission = {
                'type': type,
                'role': role,
                'allowFileDiscovery': False
            }
            
            # Create the permission
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            ).execute()
            
            # Get the file to retrieve the webViewLink
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            share_link = file.get('webViewLink')
            logger.info(f"Share link created: {share_link}")
            return share_link
            
        except HttpError as e:
            logger.error(f"HTTP error creating share link: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating share link: {e}")
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
