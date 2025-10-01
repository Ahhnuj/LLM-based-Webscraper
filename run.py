#!/usr/bin/env python3
"""
Startup script for PromptScraper.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed."""
    try:
        import fastapi
        import google.generativeai
        import requests
        import beautifulsoup4
        import playwright
        import pydantic
        import pandas
        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_playwright():
    """Check if Playwright browsers are installed."""
    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True
        )
        if "chromium" in result.stdout:
            print("✓ Playwright browsers are installed")
            return True
        else:
            print("⚠ Playwright browsers may not be installed")
            print("Run: playwright install chromium")
            return False
    except FileNotFoundError:
        print("⚠ Playwright not found, trying to install browsers...")
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            print("✓ Playwright browsers installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Playwright browsers")
            return False

def check_env_file():
    """Check if .env file exists."""
    if Path(".env").exists():
        print("✓ .env file found")
        return True
    else:
        print("⚠ .env file not found")
        print("Please copy .env.example to .env and configure your API keys")
        return False

def main():
    """Main startup function."""
    print("PromptScraper Startup Check")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Playwright
    if not check_playwright():
        print("⚠ Continuing without Playwright (dynamic sites may not work)")
    
    # Check environment file
    env_ok = check_env_file()
    
    print("\n" + "=" * 40)
    if env_ok:
        print("🚀 Starting PromptScraper...")
        print("API will be available at: http://localhost:8000")
        print("Press Ctrl+C to stop")
        print("-" * 40)
        
        # Start the application
        os.system("python -m app.main")
    else:
        print("❌ Please configure your .env file first")
        sys.exit(1)

if __name__ == "__main__":
    main()
