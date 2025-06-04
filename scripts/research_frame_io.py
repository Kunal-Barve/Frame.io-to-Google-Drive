"""
Script to research Frame.io login process and DOM structure.

This script launches a browser to analyze the Frame.io login page
and asset pages to understand their DOM structure for automation.
"""

import os
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get credentials from environment variables
FRAME_IO_EMAIL = os.getenv("FRAME_IO_EMAIL")
FRAME_IO_PASSWORD = os.getenv("FRAME_IO_PASSWORD")

# URLs to analyze
LOGIN_URL = "https://app.frame.io/login"
SAMPLE_ASSET_URL = "https://f.io/TafALVxa"  # Replace with a valid Frame.io asset URL

# Output directory for screenshots and DOM info
OUTPUT_DIR = Path("research_output")
OUTPUT_DIR.mkdir(exist_ok=True)


async def save_dom_info(page, filename):
    """
    Save DOM information to a file.
    
    Args:
        page: Playwright page object
        filename: Name of the file to save the DOM info to
    """
    # Get the HTML content
    html = await page.content()
    
    # Get all input fields
    input_fields = await page.evaluate("""
        () => {
            const inputs = Array.from(document.querySelectorAll('input'));
            return inputs.map(input => ({
                id: input.id,
                name: input.name,
                type: input.type,
                placeholder: input.placeholder,
                className: input.className
            }));
        }
    """)
    
    # Get all buttons
    buttons = await page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.map(button => ({
                id: button.id,
                text: button.textContent.trim(),
                className: button.className,
                disabled: button.disabled
            }));
        }
    """)
    
    # Get all forms
    forms = await page.evaluate("""
        () => {
            const forms = Array.from(document.querySelectorAll('form'));
            return forms.map(form => ({
                id: form.id,
                action: form.action,
                method: form.method,
                className: form.className
            }));
        }
    """)
    
    # Save the DOM info to a file
    dom_info = {
        "url": page.url,
        "title": await page.title(),
        "input_fields": input_fields,
        "buttons": buttons,
        "forms": forms
    }
    
    with open(OUTPUT_DIR / f"{filename}.json", "w") as f:
        json.dump(dom_info, f, indent=2)
    
    print(f"DOM info saved to {filename}.json")


async def take_screenshot(page, filename):
    """
    Take a screenshot of the page.
    
    Args:
        page: Playwright page object
        filename: Name of the file to save the screenshot to
    """
    await page.screenshot(path=OUTPUT_DIR / f"{filename}.png", full_page=True)
    print(f"Screenshot saved to {filename}.png")


async def analyze_login_page():
    """
    Analyze the Frame.io login page.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the login page
        print(f"Navigating to {LOGIN_URL}")
        await page.goto(LOGIN_URL)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"Warning: Timeout waiting for networkidle: {e}")
        
        # Take a screenshot and save DOM info
        await take_screenshot(page, "login_page")
        await save_dom_info(page, "login_page")
        
        # Analyze the login form
        print("Analyzing login form...")
        
        # Find the email and password fields
        email_field = await page.query_selector('input[type="email"]')
        password_field = await page.query_selector('input[type="password"]')
        
        if email_field and password_field:
            print("Found email and password fields")
            
            # Get the selectors
            email_selector = await page.evaluate("el => el.outerHTML", email_field)
            password_selector = await page.evaluate("el => el.outerHTML", password_field)
            
            print(f"Email field: {email_selector}")
            print(f"Password field: {password_selector}")
            
            # Find the login button
            login_button = await page.query_selector('button[type="submit"]')
            if login_button:
                login_button_html = await page.evaluate("el => el.outerHTML", login_button)
                print(f"Login button: {login_button_html}")
            else:
                print("Login button not found")
        else:
            print("Email or password field not found")
        
        # Close the browser
        await browser.close()


async def analyze_asset_page():
    """
    Analyze a Frame.io asset page.
    
    This requires logging in first, then navigating to the asset page.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the login page
        print(f"Navigating to {LOGIN_URL}")
        await page.goto(LOGIN_URL)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"Warning: Timeout waiting for networkidle: {e}")
        
        # Log in
        print("Logging in...")
        await page.fill('input[type="email"]', FRAME_IO_EMAIL)
        await page.fill('input[type="password"]', FRAME_IO_PASSWORD)
        await page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"Warning: Timeout waiting for networkidle after login: {e}")
        
        # Check if login was successful
        if "login" not in page.url:
            print("Login successful")
            
            # Navigate to the asset page
            print(f"Navigating to {SAMPLE_ASSET_URL}")
            await page.goto(SAMPLE_ASSET_URL)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"Warning: Timeout waiting for networkidle on asset page: {e}")
            
            # Take a screenshot and save DOM info
            await take_screenshot(page, "asset_page")
            await save_dom_info(page, "asset_page")
            
            # Look for download button
            print("Looking for download button...")
            
            # Try different selectors that might match the download button
            download_button_selectors = [
                'button:has-text("Download")',
                '[aria-label="Download"]',
                '[title="Download"]',
                '.download-button',
                '.btn-download'
            ]
            
            for selector in download_button_selectors:
                download_button = await page.query_selector(selector)
                if download_button:
                    download_button_html = await page.evaluate("el => el.outerHTML", download_button)
                    print(f"Found download button with selector '{selector}': {download_button_html}")
                    break
            else:
                print("Download button not found with common selectors")
                
                # Try to find all buttons and links on the page
                buttons = await page.query_selector_all("button")
                links = await page.query_selector_all("a")
                
                print(f"Found {len(buttons)} buttons and {len(links)} links on the page")
                
                # Look for elements that might be related to download
                for element in buttons + links:
                    text = await page.evaluate("el => el.textContent", element)
                    if "download" in text.lower():
                        element_html = await page.evaluate("el => el.outerHTML", element)
                        print(f"Found potential download element: {element_html}")
        else:
            print("Login failed")
        
        # Close the browser
        await browser.close()


async def main():
    """
    Main function to run the research.
    """
    print("Researching Frame.io login process and DOM structure...")
    
    # Analyze the login page
    await analyze_login_page()
    
    # Analyze an asset page
    await analyze_asset_page()
    
    print("Research completed. Check the research_output directory for results.")


if __name__ == "__main__":
    asyncio.run(main())
