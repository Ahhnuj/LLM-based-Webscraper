"""
LLM integration module using Google Gemini for generating scraping code.
"""
import os
import google.generativeai as genai
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GeminiLLM:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_scraping_code(self, prompt: str, url: str) -> str:
        """
        Generate Python scraping code based on the user's prompt and target URL.
        
        Args:
            prompt: Natural language description of what to scrape
            url: Target URL to scrape
            
        Returns:
            Generated Python code as string
        """
        system_prompt = """You are an expert Python web scraping assistant. Generate code that handles both static and dynamic websites with anti-bot protection.

STRATEGY:
1. First try requests + BeautifulSoup (fast for static sites)
2. If that fails with 403/blocked, use Playwright (handles anti-bot protection)
3. Always populate the 'results' list with extracted data

Requirements:
- Use these imports: requests, BeautifulSoup, time, random, re, json, playwright
- Use: from bs4 import BeautifulSoup
- Use: from playwright.sync_api import sync_playwright

CODE STRUCTURE:
```python
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from playwright.sync_api import sync_playwright

url = "TARGET_URL"
results = []

# Method 1: Try requests first (fast)
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract emails using regex
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, soup.get_text())
    
    # Add each email as a separate result
    for email in emails:
        results.append({
            'email': email,
            'url': url,
            'method': 'requests'
        })
    
except Exception as e:
    # Method 2: Use Playwright for anti-bot protection
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set realistic browser context
            page.set_extra_http_headers(headers)
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            time.sleep(random.uniform(2, 4))
            
            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Extract emails using regex
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
            emails = re.findall(email_pattern, soup.get_text())
            
            # Add each email as a separate result
            for email in emails:
                results.append({
                    'email': email,
                    'url': url,
                    'method': 'playwright'
                })
            
            browser.close()
    except Exception as e2:
        # Fallback: add error info to results
        results.append({
            'error': f'Both methods failed: {str(e)}, {str(e2)}',
            'url': url
        })

# ALWAYS ensure results list has data
if not results:
    results.append({
        'message': 'No data extracted',
        'url': url
    })

# Print results for debugging
print(f"Extracted {len(results)} items")
for i, result in enumerate(results, 1):
    print(f"Item {i}: {result}")
```

IMPORTANT: 
- Always populate the 'results' list with extracted data
- Handle both static and dynamic websites
- Use Playwright when requests fails
- Extract the specific data requested in the prompt

Return ONLY the Python code wrapped in triple backticks (```python ... ```)."""

        user_prompt = f"""
URL: {url}
User Request: {prompt}

Generate Python code that scrapes this URL and extracts the requested data.

IMPORTANT: 
- If requests fails with 403/Forbidden, immediately try Playwright
- Always extract the specific data requested in the prompt
- For phone numbers, look for patterns like +91, 10-digit numbers
- Make sure to populate the 'results' list with the extracted data
"""

        try:
            response = self.model.generate_content(
                f"{system_prompt}\n\n{user_prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=2048,
                )
            )
            
            # Extract code from response
            response_text = response.text
            if "```python" in response_text:
                start = response_text.find("```python") + 9
                end = response_text.find("```", start)
                if end == -1:
                    end = len(response_text)
                code = response_text[start:end].strip()
            else:
                # Fallback: use entire response if no code blocks found
                code = response_text.strip()
            
            logger.info(f"Generated scraping code for URL: {url}")
            return code
            
        except Exception as e:
            logger.error(f"Error generating scraping code: {str(e)}")
            raise Exception(f"Failed to generate scraping code: {str(e)}")
    
    def fix_scraping_code(self, original_code: str, error_message: str, url: str) -> str:
        """
        Fix existing scraping code based on error feedback.
        
        Args:
            original_code: The original code that failed
            error_message: Error message from execution
            url: Target URL
            
        Returns:
            Fixed Python code as string
        """
        fix_prompt = f"""
The following Python scraping code failed with an error. Please fix it:

Original Code:
```python
{original_code}
```

Error Message:
{error_message}

Target URL: {url}

Please provide the corrected code that addresses the error. Return ONLY the fixed Python code wrapped in triple backticks (```python ... ```).
"""

        try:
            response = self.model.generate_content(
                fix_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=2048,
                )
            )
            
            # Extract code from response
            response_text = response.text
            if "```python" in response_text:
                start = response_text.find("```python") + 9
                end = response_text.find("```", start)
                if end == -1:
                    end = len(response_text)
                code = response_text[start:end].strip()
            else:
                code = response_text.strip()
            
            logger.info(f"Fixed scraping code for URL: {url}")
            return code
            
        except Exception as e:
            logger.error(f"Error fixing scraping code: {str(e)}")
            raise Exception(f"Failed to fix scraping code: {str(e)}")
