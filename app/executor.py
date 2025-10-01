"""
Secure code execution module for running generated scraping code.
"""
import os
import sys
import traceback
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
import tempfile
import subprocess
import json
from app.llm import GeminiLLM
from app.scraper import ScrapingUtils

logger = logging.getLogger(__name__)

class CodeExecutor:
    """Safely executes generated scraping code with retry logic."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.llm = GeminiLLM()
    
    def execute_scraping_code(self, code: str, url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Execute scraping code with retry logic.
        
        Args:
            code: Python code to execute
            url: Target URL
            
        Returns:
            Tuple of (results, error_message)
        """
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Executing scraping code (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Create a safe execution environment
                with self._create_safe_environment() as exec_globals:
                    # Add required imports and utilities
                    from bs4 import BeautifulSoup
                    from playwright.sync_api import sync_playwright
                    exec_globals.update({
                        '__name__': '__main__',
                        '__file__': 'scraping_code.py',
                        'url': url,
                        'requests': __import__('requests'),
                        'BeautifulSoup': BeautifulSoup,
                        'sync_playwright': sync_playwright,
                        'time': __import__('time'),
                        'random': __import__('random'),
                        're': __import__('re'),
                        'json': __import__('json'),
                        'ScrapingUtils': ScrapingUtils,
                        'results': [],
                    })
                    
                    # Execute the code
                    exec(code, exec_globals)
                    
                    # Extract results
                    results = exec_globals.get('results', [])
                    
                    if not results:
                        error_msg = "No results extracted from the scraping code"
                        logger.warning(error_msg)
                        
                        # Try Playwright fallback for anti-bot protection
                        try:
                            logger.info("Attempting Playwright fallback for anti-bot protection")
                            from playwright.sync_api import sync_playwright
                            from bs4 import BeautifulSoup
                            import re
                            
                            with sync_playwright() as p:
                                browser = p.chromium.launch(headless=True)
                                page = browser.new_page()
                                
                                # Set realistic browser context
                                page.set_extra_http_headers({
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                                    'Accept-Language': 'en-US,en;q=0.5',
                                    'Accept-Encoding': 'gzip, deflate',
                                    'Connection': 'keep-alive',
                                    'Upgrade-Insecure-Requests': '1',
                                })
                                
                                # Navigate to the page
                                page.goto(url, wait_until='networkidle', timeout=30000)
                                
                                # Wait for content to load
                                import time
                                import random
                                time.sleep(random.uniform(3, 5))
                                
                                # Get page content
                                content = page.content()
                                soup = BeautifulSoup(content, 'html.parser')
                                
                                # Extract data based on common patterns
                                extracted_data = []
                                
                                # Extract title
                                title = soup.find('title')
                                title_text = title.get_text().strip() if title else "No title found"
                                
                                # Extract phone numbers
                                text_content = soup.get_text()
                                phone_patterns = [
                                    r'\+?91[0-9]{10}',  # +91 followed by 10 digits
                                    r'[0-9]{10}',       # 10 digit numbers
                                    r'\+?[0-9]{10,12}', # International format
                                ]
                                
                                phone_numbers = []
                                for pattern in phone_patterns:
                                    matches = re.findall(pattern, text_content)
                                    phone_numbers.extend(matches)
                                
                                # Remove duplicates
                                unique_phones = list(set(phone_numbers))
                                
                                # Create result
                                result_item = {
                                    'title': title_text,
                                    'url': url,
                                    'phone_numbers': unique_phones,
                                    'total_phones': len(unique_phones),
                                    'status': 'playwright_fallback',
                                    'message': 'Used Playwright to bypass anti-bot protection'
                                }
                                
                                extracted_data.append(result_item)
                                
                                browser.close()
                                
                                results = extracted_data
                                logger.info(f"Playwright fallback successful, extracted {len(unique_phones)} phone numbers")
                            
                        except Exception as fallback_error:
                            logger.error(f"Playwright fallback also failed: {fallback_error}")
                            
                            # Final fallback - basic info
                            try:
                                import requests
                                from bs4 import BeautifulSoup
                                
                                headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                }
                                response = requests.get(url, headers=headers, timeout=10)
                                soup = BeautifulSoup(response.content, 'html.parser')
                                
                                title = soup.find('title')
                                title_text = title.get_text().strip() if title else "No title found"
                                
                                results = [{
                                    'title': title_text,
                                    'url': url,
                                    'status': 'basic_fallback',
                                    'message': 'All extraction methods failed, extracted basic page info'
                                }]
                                
                                logger.info("Basic fallback extraction successful")
                                
                            except Exception as basic_error:
                                logger.error(f"All extraction methods failed: {basic_error}")
                                
                                if attempt < self.max_retries:
                                    logger.info("Attempting to fix code...")
                                    code = self.llm.fix_scraping_code(code, error_msg, url)
                                    continue
                                else:
                                    return [], error_msg
                    
                    # Validate results
                    validated_results = ScrapingUtils.validate_results(results)
                    
                    if not validated_results:
                        error_msg = "All extracted results were empty or invalid"
                        logger.warning(error_msg)
                        
                        if attempt < self.max_retries:
                            logger.info("Attempting to fix code...")
                            code = self.llm.fix_scraping_code(code, error_msg, url)
                            continue
                        else:
                            return [], error_msg
                    
                    logger.info(f"Successfully extracted {len(validated_results)} results")
                    return validated_results, None
                    
            except Exception as e:
                error_msg = f"Code execution failed: {str(e)}"
                logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if attempt < self.max_retries:
                    logger.info("Attempting to fix code...")
                    try:
                        code = self.llm.fix_scraping_code(code, error_msg, url)
                    except Exception as fix_error:
                        logger.error(f"Failed to fix code: {str(fix_error)}")
                        return [], f"Code execution failed and could not be fixed: {str(e)}"
                else:
                    return [], error_msg
        
        return [], "Maximum retry attempts exceeded"
    
    @contextmanager
    def _create_safe_environment(self):
        """Create a safe execution environment with restricted access."""
        # Create a restricted globals dictionary
        safe_globals = {
            '__builtins__': {
                # Only allow safe built-in functions
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sorted': sorted,
                'min': min,
                'max': max,
                'sum': sum,
                'abs': abs,
                'round': round,
                'print': print,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'type': type,
                'repr': repr,
                'chr': chr,
                'ord': ord,
                'hex': hex,
                'oct': oct,
                'bin': bin,
                'any': any,
                'all': all,
                'reversed': reversed,
                'slice': slice,
                'property': property,
                'staticmethod': staticmethod,
                'classmethod': classmethod,
                'super': super,
                'object': object,
                'Exception': Exception,
                'ValueError': ValueError,
                'TypeError': TypeError,
                'AttributeError': AttributeError,
                'KeyError': KeyError,
                'IndexError': IndexError,
                'StopIteration': StopIteration,
                'None': None,
                'True': True,
                'False': False,
                'Ellipsis': Ellipsis,
                'NotImplemented': NotImplemented,
            }
        }
        
        # Block dangerous modules
        blocked_modules = {
            'os', 'sys', 'subprocess', 'shutil', 'glob', 'tempfile',
            'pickle', 'marshal', 'shelve', 'dbm', 'sqlite3',
            'socket', 'urllib', 'http', 'ftplib', 'smtplib',
            'poplib', 'imaplib', 'nntplib', 'telnetlib',
            'webbrowser', 'cgi', 'cgitb', 'wsgiref',
            'xml', 'html', 'email', 'mimetypes',
            'base64', 'binascii', 'quopri', 'uu',
            'codecs', 'locale', 'unicodedata',
            'stringprep', 'readline', 'rlcompleter',
            'cmd', 'shlex', 'configparser',
            'fileinput', 'linecache', 'filecmp',
            'stat', 'filemode', 'fnmatch',
            'pathlib', 'os.path', 'pathspec',
            'platform', 'getpass', 'pwd', 'grp',
            'crypt', 'spwd', 'termios', 'tty',
            'pty', 'fcntl', 'pipes', 'resource',
            'sysconfig', 'distutils', 'ensurepip',
            'venv', 'zipapp', 'zipfile', 'tarfile',
            'gzip', 'bz2', 'lzma', 'zlib',
            'hashlib', 'hmac', 'secrets',
            'uuid', 'itertools', 'functools', 'operator',
            'collections', 'heapq', 'bisect',
            'array', 'weakref', 'types',
            'copy', 'pprint', 'reprlib',
            'enum', 'numbers', 'math',
            'cmath', 'decimal', 'fractions',
            'statistics', 'datetime', 'calendar',
        }
        
        # Override __import__ to block dangerous modules
        original_import = __import__
        
        def safe_import(name, *args, **kwargs):
            if name in blocked_modules:
                raise ImportError(f"Module '{name}' is not allowed in scraping code")
            return original_import(name, *args, **kwargs)
        
        safe_globals['__builtins__']['__import__'] = safe_import
        
        try:
            yield safe_globals
        finally:
            pass
    
    def validate_code_safety(self, code: str) -> Tuple[bool, str]:
        """
        Validate that the code doesn't contain dangerous operations.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        dangerous_patterns = [
            r'import\s+os',
            r'import\s+sys',
            r'import\s+subprocess',
            r'import\s+shutil',
            r'import\s+glob',
            r'import\s+tempfile',
            r'import\s+pickle',
            r'import\s+marshal',
            r'import\s+socket',
            r'import\s+urllib',
            r'import\s+http',
            r'import\s+ftplib',
            r'import\s+smtplib',
            r'import\s+webbrowser',
            r'import\s+xml',
            r'import\s+email',
            r'import\s+base64',
            r'import\s+binascii',
            r'import\s+codecs',
            r'import\s+locale',
            r'import\s+unicodedata',
            r'import\s+platform',
            r'import\s+getpass',
            r'import\s+crypt',
            r'import\s+termios',
            r'import\s+tty',
            r'import\s+pty',
            r'import\s+fcntl',
            r'import\s+pipes',
            r'import\s+resource',
            r'import\s+sysconfig',
            r'import\s+distutils',
            r'import\s+ensurepip',
            r'import\s+venv',
            r'import\s+zipapp',
            r'import\s+zipfile',
            r'import\s+tarfile',
            r'import\s+gzip',
            r'import\s+bz2',
            r'import\s+lzma',
            r'import\s+zlib',
            r'import\s+hashlib',
            r'import\s+hmac',
            r'import\s+secrets',
            r'import\s+uuid',
            r'import\s+itertools',
            r'import\s+functools',
            r'import\s+operator',
            r'import\s+collections',
            r'import\s+heapq',
            r'import\s+bisect',
            r'import\s+array',
            r'import\s+weakref',
            r'import\s+types',
            r'import\s+copy',
            r'import\s+pprint',
            r'import\s+reprlib',
            r'import\s+enum',
            r'import\s+numbers',
            r'import\s+math',
            r'import\s+cmath',
            r'import\s+decimal',
            r'import\s+fractions',
            r'import\s+statistics',
            r'import\s+datetime',
            r'import\s+calendar',
            r'__import__\s*\(',
            r'eval\s*\(',
            r'exec\s*\(',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input\s*\(',
            r'execfile\s*\(',
            r'reload\s*\(',
            r'vars\s*\(',
            r'locals\s*\(',
            r'globals\s*\(',
            r'dir\s*\(',
            r'help\s*\(',
            r'quit\s*\(',
            r'exit\s*\(',
            r'copyright\s*\(',
            r'credits\s*\(',
            r'license\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        return True, ""
