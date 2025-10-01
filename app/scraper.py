"""
Scraping utilities for detecting static vs dynamic sites and providing helper functions.
"""
import requests
import time
import random
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)

class ScrapingUtils:
    """Utility class for web scraping operations."""
    
    @staticmethod
    def get_polite_headers() -> Dict[str, str]:
        """Get polite headers for web requests."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    @staticmethod
    def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """Add a random delay to be respectful to websites."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def is_dynamic_site(url: str) -> bool:
        """
        Detect if a website is JavaScript-heavy (dynamic) or static.
        
        Args:
            url: URL to check
            
        Returns:
            True if site appears to be dynamic, False if static
        """
        try:
            headers = ScrapingUtils.get_polite_headers()
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for indicators of dynamic content
            indicators = [
                # Check for script tags with common JS frameworks
                soup.find_all('script', src=re.compile(r'(react|vue|angular|jquery)', re.I)),
                # Check for data attributes commonly used by SPAs
                soup.find_all(attrs={'data-reactroot': True}),
                soup.find_all(attrs={'ng-app': True}),
                soup.find_all(attrs={'id': re.compile(r'app|root|main', re.I)}),
                # Check for minimal content (common in SPAs)
                len(soup.get_text(strip=True)) < 100,
                # Check for common SPA patterns
                soup.find_all('div', class_=re.compile(r'app|root|main|container', re.I)),
            ]
            
            # Count positive indicators
            dynamic_score = sum(1 for indicator in indicators if indicator)
            
            # If we have multiple indicators or very little content, likely dynamic
            is_dynamic = dynamic_score >= 2 or len(soup.get_text(strip=True)) < 100
            
            logger.info(f"Site {url} detected as {'dynamic' if is_dynamic else 'static'}")
            return is_dynamic
            
        except Exception as e:
            logger.warning(f"Error detecting site type for {url}: {str(e)}")
            # Default to dynamic if we can't determine
            return True
    
    @staticmethod
    def scrape_static(url: str) -> BeautifulSoup:
        """
        Scrape a static website using requests and BeautifulSoup.
        
        Args:
            url: URL to scrape
            
        Returns:
            BeautifulSoup object
        """
        headers = ScrapingUtils.get_polite_headers()
        ScrapingUtils.random_delay()
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        logger.info(f"Successfully scraped static site: {url}")
        return soup
    
    @staticmethod
    def scrape_dynamic(url: str) -> BeautifulSoup:
        """
        Scrape a dynamic website using Playwright.
        
        Args:
            url: URL to scrape
            
        Returns:
            BeautifulSoup object
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set user agent
            page.set_extra_http_headers(ScrapingUtils.get_polite_headers())
            
            try:
                # Navigate to page
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait a bit for any remaining dynamic content
                ScrapingUtils.random_delay(2.0, 4.0)
                
                # Get page content
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                logger.info(f"Successfully scraped dynamic site: {url}")
                return soup
                
            finally:
                browser.close()
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return list(set(re.findall(email_pattern, text, re.IGNORECASE)))
    
    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """Extract phone numbers from text."""
        phone_patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}',
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        return list(set(phones))
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s@.-]', '', text)
        return text.strip()
    
    @staticmethod
    def validate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean scraping results.
        
        Args:
            results: List of dictionaries containing scraped data
            
        Returns:
            Cleaned and validated results
        """
        if not isinstance(results, list):
            logger.warning("Results is not a list, converting...")
            results = [results] if results else []
        
        validated_results = []
        for item in results:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item: {item}")
                continue
            
            # Clean string values
            cleaned_item = {}
            for key, value in item.items():
                if isinstance(value, str):
                    cleaned_item[key] = ScrapingUtils.clean_text(value)
                else:
                    cleaned_item[key] = value
            
            # Only include items with at least one non-empty value
            if any(v for v in cleaned_item.values() if v):
                validated_results.append(cleaned_item)
        
        logger.info(f"Validated {len(validated_results)} results from {len(results)} items")
        return validated_results
