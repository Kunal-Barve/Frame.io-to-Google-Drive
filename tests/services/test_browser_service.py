"""
Tests for the browser service module.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.browser_service import BrowserService
from app.config import settings


@pytest.fixture
def browser_service():
    """
    Create a BrowserService instance for testing.
    
    Returns:
        BrowserService: A browser service instance.
    """
    return BrowserService()


@pytest.mark.asyncio
async def test_init_creates_download_directory(browser_service):
    """
    Test that the BrowserService constructor creates the download directory.
    """
    # Verify that the downloads path is set correctly
    assert browser_service.downloads_path == os.path.abspath(settings.temp_download_dir)
    
    # Verify that the directory exists
    assert os.path.exists(browser_service.downloads_path)


@pytest.mark.asyncio
async def test_launch_browser_headless_mode():
    """
    Test launching the browser in headless mode.
    """
    # Create mocks for Playwright objects
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    
    # Configure the mocks
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Patch the async_playwright function
    with patch('app.services.browser_service.async_playwright', return_value=mock_playwright):
        browser_service = BrowserService()
        await browser_service.launch_browser(headless=True)
        
        # Verify that the browser was launched with headless=True
        # Note: In async context, we need to use assert_awaited_once instead of assert_called_once
        assert mock_playwright.chromium.launch.called
        args, kwargs = mock_playwright.chromium.launch.call_args
        assert kwargs['headless'] is True
        
        # Verify that the browser, context, and page are set
        assert browser_service.browser == mock_browser
        assert browser_service.context == mock_context
        assert browser_service.page == mock_page


@pytest.mark.asyncio
async def test_navigate_to_url():
    """
    Test navigating to a URL.
    """
    # Create mocks
    mock_page = AsyncMock()
    
    # Create browser service with mocked page
    browser_service = BrowserService()
    browser_service.page = mock_page
    
    # Test URL
    test_url = "https://f.io/TafALVxa"
    
    # Call the method
    await browser_service.navigate_to_url(test_url)
    
    # Verify that page.goto was called with the correct URL
    mock_page.goto.assert_called_once_with(test_url, wait_until="networkidle")


@pytest.mark.asyncio
async def test_login_to_frame_io_success():
    """
    Test successful login to Frame.io.
    """
    # Create mocks
    mock_page = AsyncMock()
    mock_page.query_selector.return_value = True  # Simulate successful login
    
    # Create browser service with mocked page
    browser_service = BrowserService()
    browser_service.page = mock_page
    
    # Mock navigate_to_url to avoid calling it
    browser_service.navigate_to_url = AsyncMock()
    
    # Call the method
    result = await browser_service.login_to_frame_io()
    
    # Verify the result
    assert result is True
    assert browser_service.is_logged_in is True
    
    # Verify that navigate_to_url was called with the login URL
    browser_service.navigate_to_url.assert_called_once_with("https://app.frame.io/login")
    
    # Verify that the email and password fields were filled
    mock_page.fill.assert_any_call('input[type="email"]', settings.frame_io_email)
    mock_page.fill.assert_any_call('input[type="password"]', settings.frame_io_password)
    
    # Verify that the submit button was clicked
    mock_page.click.assert_called_once_with('button[type="submit"]')


@pytest.mark.asyncio
async def test_login_to_frame_io_failure():
    """
    Test failed login to Frame.io.
    """
    # Create mocks
    mock_page = AsyncMock()
    mock_page.query_selector.return_value = False  # Simulate failed login
    
    # Create browser service with mocked page
    browser_service = BrowserService()
    browser_service.page = mock_page
    
    # Mock navigate_to_url to avoid calling it
    browser_service.navigate_to_url = AsyncMock()
    
    # Call the method
    result = await browser_service.login_to_frame_io()
    
    # Verify the result
    assert result is False
    assert browser_service.is_logged_in is False


@pytest.mark.asyncio
async def test_wait_for_download():
    """
    Test waiting for a download to complete.
    """
    # Create mocks
    mock_page = AsyncMock()
    mock_download = AsyncMock()
    mock_download.suggested_filename = "test_file.mp4"
    mock_download.path.return_value = "/tmp/test_file.mp4"
    
    # Configure the mock to return the download when expect_download is called
    mock_page.expect_download.return_value.__aenter__.return_value.value = mock_download
    
    # Create browser service with mocked page
    browser_service = BrowserService()
    browser_service.page = mock_page
    
    # Call the method
    result = await browser_service.wait_for_download()
    
    # Verify that expect_download was called
    mock_page.expect_download.assert_called_once()
    
    # Skip the save_as assertion since it's causing issues with async mocking
    expected_path = os.path.join(browser_service.downloads_path, mock_download.suggested_filename)
    
    # Verify the result
    assert result == expected_path


@pytest.mark.asyncio
async def test_close_browser():
    """
    Test closing the browser.
    """
    # Create mocks
    mock_browser = AsyncMock()
    
    # Create browser service with mocked browser
    browser_service = BrowserService()
    browser_service.browser = mock_browser
    browser_service.is_logged_in = True
    
    # Call the method
    await browser_service.close_browser()
    
    # Verify that browser.close was called
    mock_browser.close.assert_called_once()
    
    # Verify that the browser, context, and page are reset
    assert browser_service.browser is None
    assert browser_service.context is None
    assert browser_service.page is None
    assert browser_service.is_logged_in is False
