# PromptScraper

AI-powered web scraper that extracts data using natural language. Just tell it what you want, it scrapes.

## What it does

Give it a URL and a prompt like "get all emails" or "extract phone numbers" and it does it. Uses AI to write the scraping code, executes it, returns the data. Simple.

## Stack

**Backend:**
- Python + FastAPI (scraper service)
- Google Gemini (AI code generation)
- Playwright (anti-bot handling)
- BeautifulSoup (HTML parsing)

## Setup

### Option 1: Docker (Recommended)

```bash
cd scraper-backend

# Set your API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Build and run
docker-compose up --build

# Or without docker-compose:
docker build -t promptscraper .
docker run -p 8001:8001 -e GEMINI_API_KEY=your_key_here promptscraper
```

Get your key: https://aistudio.google.com/

### Option 2: Local Setup

```bash
cd scraper-backend

# Install deps
pip install -r requirements.txt
playwright install chromium

# Windows PowerShell:
$env:GEMINI_API_KEY="your_key_here"
python -m app.main

# Linux/Mac:
export GEMINI_API_KEY="your_key_here"
python -m app.main

# Or use start.bat (Windows):
.\start.bat
```

**Important:** Set `GEMINI_API_KEY` in the same terminal session before running

### Frontend

```bash
cd scraper-frontend
npm install
npm run dev
```

## API

Backend runs on `http://localhost:8001`

**Endpoint:** `POST /scrape`

**Request:**
```json
{
  "url": "https://example.com",
  "prompt": "extract all email addresses",
  "format": "json"
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {"email": "test@example.com"},
    {"email": "contact@example.com"}
  ],
  "execution_time": 5.2,
  "total_results": 2
}
```

## How it works

1. You enter URL + prompt in the UI
2. Backend asks Gemini AI to write scraping code
3. Code gets executed safely (sandboxed)
4. Data extracted and returned
5. If code fails, AI fixes it and retries

Handles both static sites (requests) and dynamic sites (Playwright). Auto-detects and uses the right method.

## Features

- Works with anti-bot protected sites 
- Extracts emails, phones, names, prices, whatever
- Returns JSON or CSV
- No rate limits on usage (but Gemini API has limits)
- No login/signup required - free for all

## Notes

- Free tier Gemini API = 50 requests/day
- Works with most websites that allow scraping
- Respects robots.txt? Nah, but it's polite with delays
- Use responsibly, don't be a dick

## Contributing

PRs welcome. Keep it simple, keep it working.

## License

MIT - do whatever you want with it

---

Built by someone who just likes to code.
