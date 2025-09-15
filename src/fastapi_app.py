"""
FastAPI backend for Varnika - AI-Powered Article Generation System
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

# Import the existing modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web_context_extract import extract as web_extract
from src.context_summarizer import summarize_context
from src.article_writer import start as generate_article

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

# Helper functions
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
            filename = f"article_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = generate_article(query=article_query, filename=filename)
        
        if result == 0:
            article_path = f"./articles/{filename}.txt"
            update_job_status(
                job_id, 
                "completed", 
                "Article generated successfully", 
                100,
                result={
                    "filename": f"{filename}.txt",
                    "path": article_path,
                    "query": query,
                    "type": article_type
                }
            )
        else:
            raise Exception("Article generation failed")
            
    except Exception as e:
        update_job_status(job_id, "failed", "Processing failed", 0, error=str(e))

# API Endpoints
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
    List all generated articles
    """
    articles_dir = Path("./articles")
    if not articles_dir.exists():
        return {"articles": []}
    
    articles = []
    for file_path in articles_dir.glob("*.txt"):
        file_stat = file_path.stat()
        articles.append({
            "filename": file_path.name,
            "size": file_stat.st_size,
            "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        })
    
    # Sort by modified date descending
    articles.sort(key=lambda x: x["modified"], reverse=True)
    
    return {"articles": articles}

@app.get("/api/articles/{filename}")
async def get_article(filename: str):
    """
    Download a specific article
    """
    file_path = Path(f"./articles/{filename}")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {filename} not found"
        )
    
    return FileResponse(
        path=file_path,
        media_type="text/plain",
        filename=filename
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
    
    # Read sources
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
        # Clear sources
        sources_path = Path("./data/sources.txt")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
