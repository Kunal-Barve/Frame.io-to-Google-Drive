"""
Browser service for automating interactions with Frame.io.

This module provides functionality to launch and control a browser
for automating interactions with Frame.io, including login and
asset download operations.
"""

import os
import asyncio
import warnings
import signal
import gc
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from app.config import settings


# Filter specific warnings that we know are harmless
warnings.filterwarnings("ignore", message="unclosed transport")
warnings.filterwarnings("ignore", message="unclosed.*socket")
warnings.filterwarnings("ignore", message="I/O operation on closed pipe")


class BrowserService:
    """
    Service for browser automation using Playwright.
    
    This class provides methods for launching a browser, navigating to Frame.io,
    logging in, and performing various actions on the Frame.io platform.
    """
    
    def __init__(self):
        """Initialize the BrowserService."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in: bool = False
        self.playwright = None
        
        # Configure download directory
        self.downloads_path = os.path.abspath(settings.temp_download_dir)
        os.makedirs(self.downloads_path, exist_ok=True)
    
    async def launch_browser(self, headless: bool = True) -> None:
        """
        Launch a browser instance.
        
        Args:
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
        
        Raises:
            Exception: If there's an error launching the browser.
        """
        try:
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser (using Chromium)
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-dev-shm-usage",  # Useful for Docker containers
                    "--no-sandbox",  # Required for running in containers
                    "--disable-setuid-sandbox",
                ]
            )
            
            # Create a new browser context with download behavior configured
            self.context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            )
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Set default navigation timeout (30 seconds)
            self.page.set_default_navigation_timeout(30000)
            
            print("Browser launched successfully")
            
        except Exception as e:
            print(f"Error launching browser: {e}")
            # Clean up if browser was partially initialized
            await self.close_browser()
            raise
    
    async def navigate_to_url(self, url: str) -> None:
        """
        Navigate to a specific URL.
        
        Args:
            url (str): The URL to navigate to.
            
        Raises:
            Exception: If there's an error navigating to the URL.
        """
        if not self.page:
            raise Exception("Browser not initialized. Call launch_browser() first.")
        
        try:
            await self.page.goto(url, wait_until="networkidle")
            print(f"Navigated to {url}")
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            raise
    
    async def login_to_frame_io(self) -> bool:
        """
        Log in to Frame.io using credentials from settings.
        
        Returns:
            bool: True if login was successful, False otherwise.
            
        Raises:
            Exception: If there's an error during the login process.
        """
        if not self.page:
            raise Exception("Browser not initialized. Call launch_browser() first.")
        
        if self.is_logged_in:
            print("Already logged in to Frame.io")
            return True
        
        try:
            # Navigate to Frame.io login page
            await self.navigate_to_url("https://app.frame.io/login")
            
            # Wait for the login form to be visible
            await self.page.wait_for_selector('input[type="email"]', state="visible")
            
            # Fill in email and password
            await self.page.fill('input[type="email"]', settings.frame_io_email)
            await self.page.fill('input[type="password"]', settings.frame_io_password)
            
            # Click the login button
            await self.page.click('button[type="submit"]')
            
            # Wait for navigation to complete (dashboard should load)
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful (look for dashboard elements)
            if await self.page.query_selector('.dashboard, .projects, .home-page'):
                print("Successfully logged in to Frame.io")
                self.is_logged_in = True
                return True
            else:
                print("Login to Frame.io failed - dashboard elements not found")
                return False
                
        except Exception as e:
            print(f"Error logging in to Frame.io: {e}")
            return False
    
    async def wait_for_download(self, timeout: int = None) -> Optional[str]:
        """
        Wait for a download to complete and return the downloaded file path.
        
        Args:
            timeout (int, optional): Maximum time to wait for download in milliseconds.
                                    Defaults to None (uses settings.download_timeout_seconds).
                                    
        Returns:
            Optional[str]: Path to the downloaded file, or None if download failed.
            
        Raises:
            TimeoutError: If the download doesn't complete within the timeout period.
        """
        if not self.page:
            raise Exception("Browser not initialized. Call launch_browser() first.")
        
        if timeout is None:
            timeout = settings.download_timeout_seconds * 1000  # Convert to milliseconds
        
        try:
            # Create a download promise
            async with self.page.expect_download(timeout=timeout) as download_info:
                # The download will be automatically accepted due to accept_downloads=True
                # Return when the download starts
                download = await download_info.value
            
            # Wait for the download to complete
            path = await download.path()
            
            # Save the file to the configured download directory
            save_path = os.path.join(self.downloads_path, download.suggested_filename)
            await download.save_as(save_path)
            
            print(f"Download completed: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"Error waiting for download: {e}")
            return None
    
    async def download_frame_io_asset(self, asset_url: str) -> Optional[str]:
        """
        Download an asset from Frame.io.
        
        This method navigates to the Frame.io asset URL, logs in if necessary,
        clicks the download button, and waits for the download to complete.
        
        Args:
            asset_url (str): The Frame.io asset URL to download.
            
        Returns:
            Optional[str]: Path to the downloaded file, or None if download failed.
            
        Raises:
            Exception: If there's an error during the download process.
        """
        if not self.page:
            raise Exception("Browser not initialized. Call launch_browser() first.")
        
        try:
            # Navigate to the asset URL
            print(f"Navigating to Frame.io asset: {asset_url}")
            await self.navigate_to_url(asset_url)
            
            # Check if we need to log in
            if await self.page.query_selector('input[type="email"]'):
                print("Login required. Attempting to log in...")
                login_success = await self.login_to_frame_io()
                if not login_success:
                    raise Exception("Failed to log in to Frame.io")
                
                # Navigate back to the asset URL after login
                await self.navigate_to_url(asset_url)
            
            # Wait for the page to load
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"Warning: Timeout waiting for networkidle on asset page: {e}")
            
            # Look for the download button
            print("Looking for download button...")
            
            # Wait for the button to be visible
            try:
                await self.page.wait_for_selector('button:has-text("Download")', state="visible", timeout=10000)
            except Exception as e:
                print(f"Warning: Timeout waiting for download button: {e}")
            
            # Try different selectors for the download button
            download_button = None
            selectors = [
                'button:has-text("Download")',
                '.StyledButton-vapor__sc-fa0c084c-0',
                '[id^="react-aria"][id$="»"]:has-text("Download")',
                'button.kskmvJ',
                '[aria-label="Download"]',
                '[title="Download"]'
            ]
            
            for selector in selectors:
                try:
                    download_button = await self.page.query_selector(selector)
                    if download_button:
                        print(f"Found download button with selector: {selector}")
                        break
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
            
            if not download_button:
                # Try to find any button with "Download" text
                buttons = await self.page.query_selector_all('button')
                for button in buttons:
                    text = await self.page.evaluate('el => el.textContent', button)
                    if "download" in text.lower():
                        download_button = button
                        print(f"Found download button by text content: {text}")
                        break
            
            if not download_button:
                raise Exception("Download button not found on the page")
            
            # Click the download button and wait for the download to start
            print("Clicking download button...")
            
            # Set up the download wait and click the button
            print("Setting up download wait and clicking button...")
            
            # Use the wait_for_download method
            download_path = None
            try:
                # Click the download button to open the dropdown
                await download_button.click()
                
                # Wait for the dropdown menu to appear
                try:
                    # Wait a moment for the dropdown to fully appear
                    await asyncio.sleep(1)
                    
                    # Try to find the resolution options using various selectors
                    selectors = [
                        'div[data-test-id="Download original file"]',
                        'div[data-selected="true"]',
                        '.StyledMenuLabel-vapor__sc-a8465af0-3',
                        '.HoverContainer-vapor__sc-a8465af0-4',
                        'div.TextContent-vapor__sc-a8465af0-2',
                        'div[class*="MenuGroupHeader"] + div[role="none"]',
                        'text="1080×1920"',
                        'text="Original"'
                    ]
                    
                    resolution_option = None
                    for selector in selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            if elements and len(elements) > 0:
                                resolution_option = elements[0]  # Take the first one (usually highest quality)
                                print(f"Found resolution option with selector: {selector}")
                                
                                # Get the text content for debugging
                                text = await self.page.evaluate('el => el.textContent', resolution_option)
                                print(f"Resolution option text: {text}")
                                break
                        except Exception as e:
                            print(f"Error with selector {selector}: {e}")
                    
                    if resolution_option:
                        # Take a screenshot for debugging
                        await self.page.screenshot(path=os.path.join(self.downloads_path, "dropdown.png"))
                        
                        # Set up download promise before clicking
                        async with self.page.expect_download() as download_info:
                            # Click the resolution option
                            await resolution_option.click()
                            print("Clicked resolution option")
                            
                            # Wait for the download to start
                            download = await download_info.value
                    else:
                        # Try to find any element with "1080" in the text
                        elements = await self.page.query_selector_all('div')
                        for element in elements:
                            text = await self.page.evaluate('el => el.textContent', element)
                            if "1080" in text or "original" in text.lower():
                                print(f"Found element with resolution text: {text}")
                                
                                # Set up download promise before clicking
                                async with self.page.expect_download() as download_info:
                                    # Click the element
                                    await element.click()
                                    print(f"Clicked element with text: {text}")
                                    
                                    # Wait for the download to start
                                    download = await download_info.value
                                break
                        else:
                            raise Exception("Could not find resolution options in dropdown")
                except Exception as e:
                    print(f"Error selecting resolution: {e}")
                    
                    # If we can't find the resolution options, try clicking the download button directly
                    # This is a fallback in case the UI changes
                    async with self.page.expect_download() as download_info:
                        # Click the download button again
                        await download_button.click()
                        print("Clicked download button directly")
                        
                        # Wait for the download to start
                        download = await download_info.value
                
                # Wait for the download to complete
                path = await download.path()
                
                # Save the file to the configured download directory
                save_path = os.path.join(self.downloads_path, download.suggested_filename)
                await download.save_as(save_path)
                download_path = save_path
                print(f"Download completed: {save_path}")
            except Exception as e:
                print(f"Error during download process: {e}")
            
            if not download_path:
                raise Exception("Download failed or timed out")
            
            # Validate the downloaded file
            if not os.path.exists(download_path):
                raise Exception(f"Downloaded file not found at {download_path}")
            
            file_size = os.path.getsize(download_path)
            if file_size == 0:
                raise Exception(f"Downloaded file is empty: {download_path}")
            
            print(f"Successfully downloaded asset to {download_path} ({file_size} bytes)")
            return download_path
            
        except Exception as e:
            print(f"Error downloading Frame.io asset: {e}")
            return None
    
    async def close_browser(self) -> None:
        """
        Close the browser and clean up resources.
        
        This method properly closes the browser and cleans up resources to prevent
        asyncio warnings about unclosed transports on Windows.
        """
        try:
            # Suppress warnings during cleanup
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                
                if self.page:
                    # Close all pages first
                    await self.page.close()
                    self.page = None
                
                if self.context:
                    # Close the browser context
                    await self.context.close()
                    self.context = None
                
                if self.browser:
                    # Close the browser
                    await self.browser.close()
                    self.browser = None
                
                if self.playwright:
                    # Stop playwright
                    await self.playwright.stop()
                    self.playwright = None
                
                # Reset state
                self.is_logged_in = False
                
                print("Browser closed")
                
                # Force garbage collection to clean up lingering references
                gc.collect()
                
                # Give asyncio a chance to clean up resources
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"Error closing browser: {e}")


# Example usage
async def test_browser_service():
    """Test the BrowserService functionality."""
    browser_service = BrowserService()
    try:
        await browser_service.launch_browser(headless=False)
        await browser_service.navigate_to_url("https://app.frame.io")
        # Add more test steps as needed
    finally:
        await browser_service.close_browser()


if __name__ == "__main__":
    # Run the test function
    asyncio.run(test_browser_service())
