# Google Drive Service Test Case

## Overview
This test validates the Google Drive API operations using a service account, including authentication, file upload, folder creation/management, and sharing functionality. It ensures the Google Drive integration works correctly without browser interaction.

## Test File
`tests/services/test_gdrive_service.py`

## Test Execution
```bash
python tests/services/test_gdrive_service.py [optional_media_file_path] [optional_folder_name]
```

## Test Components

### 1. Authentication
- Tests service account authentication using both JSON environment variables and file paths
- Validates credential loading and Google Drive API connection
- Ensures proper error handling for missing or invalid credentials

### 2. File Operations
- Creates test files of specified sizes for testing upload functionality
- Tests basic file upload with progress tracking
- Tests media file upload with support for large files
- Validates file metadata after upload

### 3. Folder Management
- Tests finding existing folders in Google Drive
- Tests creating new folders when they don't exist
- Validates parent-child folder relationships
- Supports Google Shared Drives with appropriate API parameters

### 4. Share Link Generation
- Tests generating publicly shareable links for uploaded files
- Validates link format and permissions
- Ensures proper error handling

### 5. File Listing
- Tests listing files in Google Drive folders
- Validates file metadata retrieval

## Key Improvements Made

### Service Account Authentication
- Added robust authentication logic that works with both environment variables and file paths
- Implemented proper error handling for authentication failures
- Created reusable authentication function that's shared with the integrated workflow test

### File Handle Management
- Identified and fixed resource leaks in the `MediaFileUpload` object
- Implemented explicit file descriptor closing to prevent file locks
- Added garbage collection to ensure resources are properly released

### Platform Compatibility
- Ensured code works across Windows, Linux, and Docker environments
- Fixed path handling issues for cross-platform compatibility
- Added special handling for Windows-specific file access patterns

### Error Handling & Logging
- Enhanced error reporting for authentication and API calls
- Added structured logging for better debugging
- Implemented retry mechanisms for transient failures

## Dependencies
- Google Drive API v3
- Google OAuth2 service account credentials
- `google-auth`, `google-api-python-client` libraries

## Configuration Requirements
- `GOOGLE_SERVICE_ACCOUNT_INFO` environment variable or `credentials/service_account.json` file
- `GOOGLE_DRIVE_FOLDER_ID` for the parent folder in Google Drive (optional)

## Security Considerations
- Service account credentials are loaded securely from environment variables or files
- No hardcoded credentials in the codebase
- Proper permission scoping for Google Drive API access