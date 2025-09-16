#!/usr/bin/env python3
"""
Varnika - AI-Powered Article Generation System
Main application file with integrated FastAPI backend
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import os
import sys
import json
import uuid
import uvicorn
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the existing modules
from src.web_context_extract import extract as web_extract, file_manager, simple_extract, update_sources_file
from src.context_summarizer import summarize_context
from src.article_writer import start as generate_article

# Load environment variables from config/.env
load_dotenv('config/.env')

# ============================================================================
# FastAPI Application Setup
# ============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Varnika API",
    description="AI-Powered Article Generation System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models and Storage
# ============================================================================

# Store for tracking job status
job_store: Dict[str, Dict[str, Any]] = {}

# Pydantic models for request/response
class ArticleType(str, Enum):
    detailed = "detailed"
    summarized = "summarized"
    points = "points"

class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for web content extraction")
    max_results: Optional[int] = Field(5, description="Maximum number of search results")

class ArticleGenerationRequest(BaseModel):
    query: str = Field(..., description="Search query or topic for article generation")
    article_type: Optional[ArticleType] = Field(ArticleType.detailed, description="Type of article to generate")
    filename: Optional[str] = Field(None, description="Custom filename for the generated article")
    skip_search: Optional[bool] = Field(False, description="Skip web search and use existing context")

class JobStatus(BaseModel):
    job_id: str
    status: str
    message: str
    progress: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class JobResponse(BaseModel):
    job_id: str
    message: str

# ============================================================================
# Helper Functions
# ============================================================================

def update_job_status(job_id: str, status: str, message: str, progress: int, result: Any = None, error: str = None):
    """Update job status in the store"""
    if job_id in job_store:
        job_store[job_id].update({
            "status": status,
            "message": message,
            "progress": progress,
            "result": result,
            "error": error,
            "updated_at": datetime.now().isoformat()
        })

async def process_article_generation(job_id: str, query: str, article_type: str, filename: str, skip_search: bool):
    """Background task for article generation pipeline"""
    try:
        # Step 1: Web Context Extraction (if not skipped)
        if not skip_search:
            update_job_status(job_id, "processing", "Searching and extracting web content...", 20)
            await web_extract(query)
            update_job_status(job_id, "processing", "Web content extracted successfully", 40)
        
        # Step 2: Context Summarization
        update_job_status(job_id, "processing", "Summarizing extracted content...", 60)
        summarize_result = summarize_context()
        if summarize_result != 0:
            raise Exception("Context summarization failed")
        update_job_status(job_id, "processing", "Content summarized successfully", 80)
        
        # Step 3: Article Generation
        update_job_status(job_id, "processing", "Generating article...", 90)
        
        # Map article type to query
        article_queries = {
            "detailed": "Write a detailed comprehensive article based on the provided context",
            "summarized": "Write a concise summary article based on the provided context",
            "points": "Write an article in bullet points based on the provided context"
        }
        
        article_query = article_queries.get(article_type, article_queries["detailed"])
        
        # Generate filename if not provided
        if not filename:
            filename = f"article_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
        
        result = generate_article(query=article_query, filename=filename)
        
        if result == 0:
            article_path = f"./articles/{filename}.md"
            update_job_status(
                job_id, 
                "completed", 
                "Article generated successfully", 
                100,
                result={
                    "filename": f"{filename}.md",
                    "path": article_path,
                    "query": query,
                    "type": article_type
                }
            )
        else:
            raise Exception("Article generation failed")
            
    except Exception as e:
        update_job_status(job_id, "failed", "Processing failed", 0, error=str(e))

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Varnika API",
        "version": "1.0.0",
        "description": "AI-Powered Article Generation System",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "search": "/api/search",
            "generate": "/api/generate",
            "status": "/api/jobs/{job_id}",
            "articles": "/api/articles"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/search", response_model=JobResponse)
async def search_web_content(request: WebSearchRequest, background_tasks: BackgroundTasks):
    """
    Search and extract web content for a given query
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "message": "Web search job created",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Add background task
    background_tasks.add_task(
        web_extract,
        request.query
    )
    
    return JobResponse(
        job_id=job_id,
        message=f"Web search started for query: {request.query}"
    )

@app.post("/api/generate", response_model=JobResponse)
async def generate_article_endpoint(request: ArticleGenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate an article based on the provided query
    Runs the complete pipeline: search -> extract -> summarize -> generate
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "message": "Article generation job created",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Add background task for the complete pipeline
    background_tasks.add_task(
        process_article_generation,
        job_id,
        request.query,
        request.article_type,
        request.filename,
        request.skip_search
    )
    
    return JobResponse(
        job_id=job_id,
        message=f"Article generation started for: {request.query}"
    )

@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of a specific job
    """
    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    return JobStatus(**job_store[job_id])

@app.get("/api/jobs")
async def list_jobs(limit: int = 10, offset: int = 0):
    """
    List all jobs with pagination
    """
    jobs = list(job_store.values())
    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
        "jobs": jobs[offset:offset + limit]
    }

@app.get("/api/articles")
async def list_articles():
    """
    List all generated articles with enhanced debugging
    """
    # Get current working directory for debugging
    current_dir = os.getcwd()
    articles_dir = Path("./articles")
    
    # Debug information
    debug_info = {
        "current_directory": current_dir,
        "articles_path": str(articles_dir.absolute()),
        "articles_exists": articles_dir.exists(),
        "environment": os.getenv("ENVIRONMENT", "local")
    }
    
    print(f"🔍 Debug - Current directory: {current_dir}")
    print(f"🔍 Debug - Articles path: {articles_dir.absolute()}")
    print(f"🔍 Debug - Articles directory exists: {articles_dir.exists()}")
    
    if not articles_dir.exists():
        print("⚠️  Articles directory does not exist, creating it...")
        articles_dir.mkdir(parents=True, exist_ok=True)
        return {
            "articles": [],
            "debug": debug_info,
            "message": "Articles directory created"
        }
    
    articles = []
    # Look for both .txt and .md files
    for pattern in ["*.txt", "*.md"]:
        matching_files = list(articles_dir.glob(pattern))
        print(f"🔍 Debug - Found {len(matching_files)} files matching {pattern}")
        
        for file_path in matching_files:
            try:
                file_stat = file_path.stat()
                article_info = {
                    "filename": file_path.name,
                    "size": file_stat.st_size,
                    "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "path": str(file_path.absolute())
                }
                articles.append(article_info)
                print(f"✓ Found article: {file_path.name} ({file_stat.st_size} bytes)")
            except Exception as e:
                print(f"✗ Error reading file {file_path}: {e}")
    
    # Sort by modified date descending
    articles.sort(key=lambda x: x["modified"], reverse=True)
    
    print(f"📊 Total articles found: {len(articles)}")
    
    return {
        "articles": articles,
        "debug": debug_info,
        "total_count": len(articles)
    }

@app.get("/api/articles/{filename}")
async def get_article(filename: str):
    """
    Download a specific article or sources file with atomic operations and cache control
    """
    from fastapi import Response
    
    # Special handling for sources files
    if filename in ["sources.txt", "sources.md"]:
        try:
            # Use atomic file manager for thread-safe reading
            content = file_manager.read_with_lock("sources.md")
            
            # If sources.md is empty, try sources.txt for backward compatibility
            if not content:
                content = file_manager.read_with_lock("sources.txt")
            
            # Create response with cache-busting headers
            response = Response(
                content=content, 
                media_type="text/plain; charset=utf-8"
            )
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["ETag"] = f'"{hash(content)}"'
            response.headers["Last-Modified"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            return response
            
        except Exception as e:
            print(f"Error reading sources file: {e}")
            return Response(content="", media_type="text/plain")
    
    # Regular article handling
    file_path = Path(f"./articles/{filename}")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {filename} not found"
        )
    
    try:
        # Read article content with proper encoding
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Create response with appropriate headers
        response = Response(
            content=content, 
            media_type="text/plain; charset=utf-8"
        )
        
        # Add cache headers for articles (can be cached for a short time)
        file_stat = file_path.stat()
        response.headers["Last-Modified"] = datetime.fromtimestamp(file_stat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers["ETag"] = f'"{file_stat.st_mtime}-{file_stat.st_size}"'
        response.headers["Cache-Control"] = "public, max-age=300"  # Cache for 5 minutes
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read article: {str(e)}"
        )

@app.delete("/api/articles/{filename}")
async def delete_article(filename: str):
    """
    Delete a specific article
    """
    file_path = Path(f"./articles/{filename}")
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {filename} not found"
        )
    
    try:
        file_path.unlink()
        return {"message": f"Article {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete article: {str(e)}"
        )

@app.get("/api/context")
async def get_current_context():
    """
    Get the current context data (sources and extracted content)
    """
    context_data = {}
    
    # Read sources (try .md first, then .txt)
    sources_path = Path("./data/sources.md")
    if not sources_path.exists():
        sources_path = Path("./data/sources.txt")
    
    if sources_path.exists():
        with open(sources_path, "r", encoding="utf-8") as f:
            context_data["sources"] = f.read()
    
    # Read context JSON
    context_json_path = Path("./data/context.json")
    if context_json_path.exists():
        with open(context_json_path, "r", encoding="utf-8") as f:
            context_data["extracted_content"] = json.load(f)
    
    # Read summarized context
    context_txt_path = Path("./data/context.txt")
    if context_txt_path.exists():
        with open(context_txt_path, "r", encoding="utf-8") as f:
            context_data["summarized_context"] = f.read()
    
    return context_data

@app.post("/api/context/clear")
async def clear_context():
    """
    Clear the current context data
    """
    try:
        # Clear sources (both .md and .txt)
        for sources_file in ["sources.md", "sources.txt"]:
            sources_path = Path(f"./data/{sources_file}")
            if sources_path.exists():
                with open(sources_path, "w", encoding="utf-8") as f:
                    f.write("")
        
        # Clear context JSON
        context_json_path = Path("./data/context.json")
        if context_json_path.exists():
            with open(context_json_path, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        # Clear summarized context
        context_txt_path = Path("./data/context.txt")
        if context_txt_path.exists():
            with open(context_txt_path, "w", encoding="utf-8") as f:
                f.write("")
        
        return {"message": "Context cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear context: {str(e)}"
        )

class SourcesUpdateRequest(BaseModel):
    content: str = Field(..., description="New content for sources.md file")

@app.put("/api/sources")
async def update_sources(request: SourcesUpdateRequest):
    """
    Update the entire sources.md file content
    """
    try:
        # Use atomic file manager for thread-safe writing
        await file_manager.atomic_write("sources.md", request.content)
        
        return {
            "message": "Sources updated successfully",
            "content_length": len(request.content),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sources: {str(e)}"
        )

class SourcesAppendRequest(BaseModel):
    query: str = Field(..., description="Query/topic name for the new section")
    urls: List[str] = Field(..., description="List of URLs to add")

class ExtractFromUrlsRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to extract content from")
    query: Optional[str] = Field("Custom URLs", description="Query/topic name for context")
    save_to_sources: Optional[bool] = Field(True, description="Whether to save URLs to sources.md")

@app.post("/api/sources/append")
async def append_to_sources(request: SourcesAppendRequest):
    """
    Append a new section to sources.md file
    """
    try:
        # Format new content
        new_content = f"\n## {request.query}\n"
        for url in request.urls:
            new_content += f"- [{url}]({url})\n"
        new_content += "\n"
        
        # Use atomic file manager for thread-safe appending
        await file_manager.atomic_append("sources.md", new_content)
        
        return {
            "message": f"Added {len(request.urls)} sources for '{request.query}'",
            "query": request.query,
            "urls_added": len(request.urls),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to append to sources: {str(e)}"
        )

@app.delete("/api/sources")
async def clear_sources():
    """
    Clear the sources.md file
    """
    try:
        # Use atomic file manager to clear the file
        await file_manager.atomic_write("sources.md", "")
        
        return {
            "message": "Sources cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear sources: {str(e)}"
        )

@app.post("/api/extract/urls", response_model=JobResponse)
async def extract_from_urls(request: ExtractFromUrlsRequest, background_tasks: BackgroundTasks):
    """
    Extract content from a list of custom URLs
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "message": "URL extraction job created",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Add background task for URL extraction
    background_tasks.add_task(
        process_url_extraction,
        job_id,
        request.urls,
        request.query,
        request.save_to_sources
    )
    
    return JobResponse(
        job_id=job_id,
        message=f"Content extraction started for {len(request.urls)} URLs"
    )

async def process_url_extraction(job_id: str, urls: List[str], query: str, save_to_sources: bool):
    """Background task for URL content extraction"""
    try:
        update_job_status(job_id, "processing", "Starting content extraction from URLs...", 10)
        
        # Validate URLs
        valid_urls = []
        for url in urls:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                print(f"⚠️  Skipping invalid URL: {url}")
        
        if not valid_urls:
            raise Exception("No valid URLs provided")
        
        update_job_status(job_id, "processing", f"Extracting content from {len(valid_urls)} URLs...", 30)
        
        # Extract content using simple_extract function
        extracted_data = await simple_extract(valid_urls, query)
        
        update_job_status(job_id, "processing", "Content extraction completed", 70)
        
        # Save URLs to sources.md if requested
        if save_to_sources:
            update_job_status(job_id, "processing", "Saving URLs to sources.md...", 80)
            await update_sources_file(query, valid_urls)
        
        # Count successful extractions
        successful_extractions = sum(1 for item in extracted_data if not item.get("error", False))
        failed_extractions = len(extracted_data) - successful_extractions
        
        update_job_status(
            job_id, 
            "completed", 
            "URL extraction completed successfully", 
            100,
            result={
                "total_urls": len(valid_urls),
                "successful_extractions": successful_extractions,
                "failed_extractions": failed_extractions,
                "query": query,
                "saved_to_sources": save_to_sources,
                "extracted_data": extracted_data
            }
        )
        
    except Exception as e:
        update_job_status(job_id, "failed", f"URL extraction failed: {str(e)}", 0, error=str(e))

# ============================================================================
# Main Entry Point
# ============================================================================

def run_server():
    """Run the FastAPI application server"""
    print("\n" + "="*60)
    print("🚀 Starting Varnika - AI-Powered Article Generation System")
    print("="*60)
    print("\n📚 API Documentation:")
    print("   • Swagger UI: http://localhost:8000/docs")
    print("   • ReDoc:      http://localhost:8000/redoc")
    print("\n🔧 API Endpoints:")
    print("   • Health:     http://localhost:8000/health")
    print("   • Generate:   http://localhost:8000/api/generate")
    print("   • Articles:   http://localhost:8000/api/articles")
    print("\n💡 Tips:")
    print("   • Use /docs for interactive API testing")
    print("   • Check /api/jobs/{job_id} for generation status")
    print("   • Articles are saved in the ./articles directory")
    print("\n" + "="*60 + "\n")
    
    # Get configuration from environment variables
    host = os.getenv("VARNIKA_HOST", "0.0.0.0")
    port = int(os.getenv("VARNIKA_PORT", "8000"))
    reload = os.getenv("VARNIKA_RELOAD", "true").lower() == "true"
    log_level = os.getenv("VARNIKA_LOG_LEVEL", "info")
    
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "src.main:app",  # Updated to reference this file
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )

def main():
    """Main function - entry point for the application"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Varnika - AI-Powered Article Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                    # Run the server with default settings
  python src/main.py --port 8080        # Run on port 8080
  python src/main.py --no-reload        # Run without auto-reload
  python src/main.py --log-level debug  # Run with debug logging
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=True,
        help="Enable auto-reload on code changes (default: True)"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        default="info",
        help="Set the logging level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Override environment variables with command-line arguments
    if args.host:
        os.environ["VARNIKA_HOST"] = args.host
    if args.port:
        os.environ["VARNIKA_PORT"] = str(args.port)
    if args.no_reload:
        os.environ["VARNIKA_RELOAD"] = "false"
    elif args.reload:
        os.environ["VARNIKA_RELOAD"] = "true"
    if args.log_level:
        os.environ["VARNIKA_LOG_LEVEL"] = args.log_level
    
    # Run the server
    run_server()

if __name__ == "__main__":
    main()
