# Frame.io to Google Drive Test Documentation

## Overview
This directory contains detailed documentation for all test cases in the Frame.io to Google Drive automation project. Each document describes test components, issues encountered, solutions implemented, and best practices for each functionality.

## Test Cases

### 1. [Integrated Workflow Test](./integrated_workflow_test.md)
End-to-end test of the complete workflow from Frame.io asset download to Google Drive upload and sharing. This is the main test that exercises all components of the system together.

### 2. [Google Drive Service Test](./gdrive_service_test.md)
Tests for Google Drive API operations including authentication, file upload, folder creation/management, and sharing functionality.

### 3. [Browser Service Test](./browser_service_test.md) 
Tests for browser automation functionality using Playwright, including browser initialization, navigation, Frame.io interactions, and download management.

### 4. [Asset Download Test](./asset_download_test.md)
Specialized test for downloading media assets from Frame.io using browser automation.

### 5. [Headless Download Test](./headless_download_test.md)
Specialized test for downloading media assets from Frame.io using a headless browser, designed for CI/CD pipelines and server environments without GUI.

## Key Issues and Solutions

### [Cross-Platform File Cleanup Fix](./file_cleanup_fix.md)
Detailed documentation of the file cleanup issues encountered on Windows and the solutions implemented to fix them.

## Best Practices

### Testing
- All tests are executable both individually and as part of a test suite
- Proper test fixtures and teardown to prevent test side effects
- Test docstrings include purpose, inputs, and expected outcomes
- Tests follow Pytest conventions for better reporting

### Error Handling
- Comprehensive error handling with meaningful error messages
- Retry logic with exponential backoff for transient failures
- Cross-platform error type handling (OSError and PermissionError)

### Logging
- Clear, consistent logging with emoji indicators for visual scanning
- Appropriate log levels for different types of information
- Detailed logs for tracking complex operations

### Resource Management
- Explicit resource cleanup in finally blocks
- Proper file handle management and closure
- Garbage collection to prevent memory and resource leaks

## Execution Environment
These tests are designed to run in both:
- Local development environments (Windows, macOS, Linux)
- CI/CD pipelines
- Docker containers 
- Virtual Private Servers (VPS)

## Maintainers
The Frame.io to Google Drive automation test suite is maintained by the team responsible for automating media workflow processes across platforms.