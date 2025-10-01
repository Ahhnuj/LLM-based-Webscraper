"""
PromptScraper - FastAPI application for intelligent web scraping.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import pandas as pd
import io
import csv
from datetime import datetime
import uuid

# Import our modules
from app.llm import GeminiLLM
from app.scraper import ScrapingUtils
from app.executor import CodeExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PromptScraper",
    description="AI-powered web scraping with natural language prompts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm = GeminiLLM()
executor = CodeExecutor()

# Pydantic models
class ScrapeRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of what to scrape")
    format: str = Field(default="json", description="Output format: 'json' or 'csv'")
    url: str = Field(..., description="Target URL to scrape")

class ScrapeResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    message: Optional[str] = None
    execution_time: Optional[float] = None
    total_results: int

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PromptScraper"}

# Main scraping endpoint
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_data(request: ScrapeRequest):
    """
    Scrape data from a website using natural language prompts.
    
    This endpoint:
    1. Takes a natural language prompt and URL
    2. Generates Python scraping code using Google Gemini
    3. Safely executes the code to extract data
    4. Returns results in JSON or CSV format
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting scrape request for URL: {request.url}")
        logger.info(f"Prompt: {request.prompt}")
        
        # Validate URL format
        if not request.url.startswith(('http://', 'https://')):
            request.url = 'https://' + request.url
        
        # Generate scraping code using Gemini
        logger.info("Generating scraping code...")
        code = llm.generate_scraping_code(request.prompt, request.url)
        
        # Validate code safety
        is_safe, safety_error = executor.validate_code_safety(code)
        if not is_safe:
            raise HTTPException(
                status_code=400,
                detail=f"Generated code failed safety validation: {safety_error}"
            )
        
        # Execute the scraping code
        logger.info("Executing scraping code...")
        results, error = executor.execute_scraping_code(code, request.url)
        
        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Scraping failed: {error}"
            )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail="No data found matching the specified criteria"
            )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Scraping completed successfully. Found {len(results)} results in {execution_time:.2f}s")
        
        return ScrapeResponse(
            success=True,
            data=results,
            message=f"Successfully scraped {len(results)} items",
            execution_time=execution_time,
            total_results=len(results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# CSV download endpoint
@app.post("/scrape/csv")
async def scrape_data_csv(request: ScrapeRequest):
    """
    Scrape data and return as CSV file download.
    """
    try:
        # Use the main scrape endpoint to get data
        scrape_response = await scrape_data(request)
        
        if not scrape_response.success:
            raise HTTPException(
                status_code=500,
                detail=scrape_response.message or "Scraping failed"
            )
        
        # Convert to CSV
        if not scrape_response.data:
            raise HTTPException(
                status_code=404,
                detail="No data to export"
            )
        
        # Create CSV content
        df = pd.DataFrame(scrape_response.data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating CSV: {str(e)}"
        )

# Utility endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PromptScraper API",
        "version": "1.0.0",
        "description": "AI-powered web scraping with natural language prompts",
        "endpoints": {
            "POST /scrape": "Scrape data and return JSON",
            "POST /scrape/csv": "Scrape data and return CSV download",
            "GET /health": "Health check",
            "GET /": "This information"
        }
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=exc.detail,
            message=f"HTTP {exc.status_code}: {exc.detail}"
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="Internal server error",
            message="An unexpected error occurred"
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting PromptScraper on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
