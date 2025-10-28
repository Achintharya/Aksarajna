#!/usr/bin/env python3
"""
Varnika - AI-Powered Article Generation System
Main application file with integrated FastAPI backend
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
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

# Use auth_v2 for migration to new API keys
# Once stable, rename auth_v2.py to auth.py and remove this conditional
USE_NEW_AUTH = os.getenv('USE_NEW_AUTH', 'true').lower() == 'true'

if USE_NEW_AUTH:
    from src.auth_v2 import (
        get_current_user, 
        get_optional_user, 
        require_admin, 
        auth_health_check,
        get_migration_status
    )
    print("✅ Using auth_v2 with new API key support")
else:
    from src.auth import get_current_user, get_optional_user, require_admin, auth_health_check
    get_migration_status = None  # Not available in old auth
    print("⚠️ Using legacy auth - migration to auth_v2 recommended")

from src.supabase_client import storage_manager, db_manager

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

@app.get("/auth/health")
async def auth_health():
    """Authentication service health check"""
    return await auth_health_check()

@app.get("/auth/migration-status")
async def auth_migration_status():
    """Check API key migration status"""
    if get_migration_status:
        return get_migration_status()
    else:
        return {
            "error": "Migration status not available",
            "message": "Using legacy auth module - switch to auth_v2 for migration status"
        }

# ============================================================================
# Admin API Endpoints
# ============================================================================

@app.get("/api/admin/users")
async def admin_list_users(current_user: Dict = Depends(require_admin)):
    """
    List all users (admin only)
    """
    try:
        # Use service role to bypass RLS
        from src.supabase_client import supabase
        
        # Query auth.users table
        result = supabase.auth.admin.list_users()
        
        if result.users:
            users = []
            for user in result.users:
                users.append({
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at,
                    "last_sign_in_at": user.last_sign_in_at,
                    "email_confirmed_at": user.email_confirmed_at
                })
            
            return {
                "users": users,
                "total_count": len(users)
            }
        else:
            return {"users": [], "total_count": 0}
            
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@app.delete("/api/admin/deleteUser")
async def admin_delete_user(request: dict, current_user: Dict = Depends(require_admin)):
    """
    Delete a user by ID (admin only)
    """
    try:
        user_id = request.get("userId")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required"
            )
        
        # Prevent admin from deleting themselves
        if user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Use service role to delete user
        from src.supabase_client import supabase
        
        # Delete user (this will cascade delete their articles due to foreign key)
        result = supabase.auth.admin.delete_user(user_id)
        
        return {"message": f"User {user_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

@app.get("/api/admin/articles")
async def admin_list_articles(current_user: Dict = Depends(require_admin)):
    """
    List all articles with user information (admin only)
    """
    try:
        # Use service role to bypass RLS
        from src.supabase_client import supabase
        
        # Query articles table with user email join
        result = supabase.table("articles").select("""
            id,
            user_id,
            filename,
            title,
            storage_path,
            content_length,
            created_at,
            updated_at
        """).execute()
        
        if result.data:
            # Get user emails for each article
            articles_with_users = []
            user_cache = {}  # Cache user emails to avoid repeated queries
            
            for article in result.data:
                user_id = article["user_id"]
                
                # Get user email from cache or fetch it
                if user_id not in user_cache:
                    try:
                        user_result = supabase.auth.admin.get_user_by_id(user_id)
                        user_cache[user_id] = user_result.user.email if user_result.user else "Unknown"
                    except:
                        user_cache[user_id] = "Unknown"
                
                article_with_user = {
                    **article,
                    "user_email": user_cache[user_id]
                }
                articles_with_users.append(article_with_user)
            
            # Sort by created_at descending
            articles_with_users.sort(key=lambda x: x["created_at"], reverse=True)
            
            return {
                "articles": articles_with_users,
                "total_count": len(articles_with_users)
            }
        else:
            return {"articles": [], "total_count": 0}
            
    except Exception as e:
        print(f"❌ Error fetching articles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch articles: {str(e)}"
        )

@app.delete("/api/admin/deleteArticle")
async def admin_delete_article(request: dict, current_user: Dict = Depends(require_admin)):
    """
    Delete an article by ID (admin only)
    """
    try:
        article_id = request.get("articleId")
        if not article_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article ID is required"
            )
        
        # Use service role to bypass RLS
        from src.supabase_client import supabase
        
        # First get article details
        article_result = supabase.table("articles").select("*").eq("id", article_id).execute()
        
        if not article_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        article = article_result.data[0]
        user_id = article["user_id"]
        filename = article["filename"]
        
        # Delete from storage
        storage_path = f"{user_id}/articles/{filename}"
        try:
            supabase.storage.from_("articles").remove([storage_path])
        except Exception as storage_error:
            print(f"Warning: Failed to delete from storage: {storage_error}")
        
        # Delete from database
        supabase.table("articles").delete().eq("id", article_id).execute()
        
        return {"message": f"Article {filename} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete article: {str(e)}"
        )

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
async def list_articles(current_user: Dict = Depends(get_current_user)):
    """
    List all generated articles for the current user from Supabase Storage
    """
    try:
        user_id = current_user["id"]
        print(f"🔍 Fetching articles for user: {user_id}")
        
        # Get user's articles from Supabase
        articles = await storage_manager.list_user_articles(user_id)
        
        # Transform database records to match frontend expectations
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "filename": article["filename"],
                "size": article.get("content_length", 0),
                "created": article["created_at"],
                "modified": article["updated_at"],
                "title": article.get("title", "Untitled Article"),
                "storage_path": article["storage_path"]
            })
        
        print(f"📊 Total articles found for user {user_id}: {len(formatted_articles)}")
        
        return {
            "articles": formatted_articles,
            "total_count": len(formatted_articles),
            "user_id": user_id,
            "storage": "supabase"
        }
        
    except Exception as e:
        print(f"❌ Error fetching articles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch articles: {str(e)}"
        )

@app.get("/api/articles/{filename}")
async def get_article(filename: str, current_user: Dict = Depends(get_current_user)):
    """
    Download a specific article from user's Supabase Storage
    """
    try:
        user_id = current_user["id"]
        
        # Special handling for sources files
        if filename in ["sources.txt", "sources.md"]:
            content = await storage_manager.get_sources(user_id)
            
            # Create response with cache-busting headers
            response = Response(
                content=content or "", 
                media_type="text/plain; charset=utf-8"
            )
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["ETag"] = f'"{hash(content or "")}"'
            response.headers["Last-Modified"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            return response
        
        # Regular article handling from Supabase Storage
        content = await storage_manager.get_article(user_id, filename)
        
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article {filename} not found"
            )
        
        # Create response with appropriate headers
        response = Response(
            content=content, 
            media_type="text/plain; charset=utf-8"
        )
        
        # Add cache headers for articles (can be cached for a short time)
        response.headers["Last-Modified"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers["ETag"] = f'"{hash(content)}"'
        response.headers["Cache-Control"] = "public, max-age=300"  # Cache for 5 minutes
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read article: {str(e)}"
        )

@app.delete("/api/articles/{filename}")
async def delete_article(filename: str, current_user: Dict = Depends(get_current_user)):
    """
    Delete a specific article from user's Supabase Storage
    """
    try:
        user_id = current_user["id"]
        
        # Delete article from Supabase Storage and database
        success = await storage_manager.delete_article(user_id, filename)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article {filename} not found or could not be deleted"
            )
        
        return {"message": f"Article {filename} deleted successfully"}
        
    except HTTPException:
        raise
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
async def update_sources(request: SourcesUpdateRequest, current_user: Dict = Depends(get_current_user)):
    """
    Update the entire sources.md file content for the current user
    """
    try:
        user_id = current_user["id"]
        
        # Upload sources to user's Supabase Storage
        result = await storage_manager.upload_sources(user_id, request.content)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload sources: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "message": "Sources updated successfully",
            "content_length": len(request.content),
            "timestamp": datetime.now().isoformat(),
            "storage": "supabase"
        }
    except HTTPException:
        raise
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

class GenerateFromUrlsRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to extract content from and generate article")
    query: Optional[str] = Field(None, description="Topic/title for the article (optional)")
    article_type: Optional[ArticleType] = Field(ArticleType.detailed, description="Type of article to generate")
    filename: Optional[str] = Field(None, description="Custom filename for the generated article")

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
async def clear_sources(current_user: Dict = Depends(get_current_user)):
    """
    Clear the sources.md file for the current user
    """
    try:
        user_id = current_user["id"]
        
        # Clear sources by uploading empty content
        result = await storage_manager.upload_sources(user_id, "")
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clear sources: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "message": "Sources cleared successfully",
            "timestamp": datetime.now().isoformat(),
            "storage": "supabase"
        }
    except HTTPException:
        raise
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

@app.post("/api/generate/from-urls", response_model=JobResponse)
async def generate_article_from_urls(request: GenerateFromUrlsRequest, background_tasks: BackgroundTasks):
    """
    Generate an article from a list of URLs
    Extracts content from URLs, then generates an article
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "message": "Article generation from URLs job created",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Add background task for URL-based article generation
    background_tasks.add_task(
        process_article_generation_from_urls,
        job_id,
        request.urls,
        request.query,
        request.article_type,
        request.filename
    )
    
    return JobResponse(
        job_id=job_id,
        message=f"Article generation from {len(request.urls)} URLs started"
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

async def process_article_generation_from_urls(job_id: str, urls: List[str], query: Optional[str], article_type: str, filename: Optional[str]):
    """Background task for article generation from URLs"""
    try:
        # Step 1: Validate URLs
        update_job_status(job_id, "processing", "Validating URLs...", 5)
        
        valid_urls = []
        for url in urls:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                print(f"⚠️  Skipping invalid URL: {url}")
        
        if not valid_urls:
            raise Exception("No valid URLs provided")
        
        # Use default query if none provided
        if not query:
            query = "Article from URLs"
        
        # Step 2: Extract content from URLs
        update_job_status(job_id, "processing", f"Extracting content from {len(valid_urls)} URLs...", 20)
        extracted_data = await simple_extract(valid_urls, query)
        
        # Count successful extractions
        successful_extractions = sum(1 for item in extracted_data if not item.get("error", False))
        if successful_extractions == 0:
            raise Exception("Failed to extract content from any URLs")
        
        update_job_status(job_id, "processing", f"Successfully extracted content from {successful_extractions} URLs", 40)
        
        # Step 3: Context Summarization
        update_job_status(job_id, "processing", "Summarizing extracted content...", 60)
        summarize_result = summarize_context()
        if summarize_result != 0:
            raise Exception("Context summarization failed")
        update_job_status(job_id, "processing", "Content summarized successfully", 80)
        
        # Step 4: Article Generation
        update_job_status(job_id, "processing", "Generating article...", 90)
        
        # Map article type to query - use generic prompts when no specific query
        if query == "Article from URLs":
            article_queries = {
                "detailed": "Write a detailed comprehensive article based on the provided context",
                "summarized": "Write a concise summary article based on the provided context", 
                "points": "Write an article in bullet points based on the provided context"
            }
        else:
            article_queries = {
                "detailed": f"Write a detailed comprehensive article about '{query}' based on the provided context",
                "summarized": f"Write a concise summary article about '{query}' based on the provided context",
                "points": f"Write an article in bullet points about '{query}' based on the provided context"
            }
        
        article_query = article_queries.get(article_type, article_queries["detailed"])
        
        # Generate filename if not provided
        if not filename:
            safe_query = query.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"article_{safe_query}_{datetime.now().strftime('%Y%m%d')}"
        
        result = generate_article(query=article_query, filename=filename)
        
        if result == 0:
            article_path = f"./articles/{filename}.md"
            update_job_status(
                job_id, 
                "completed", 
                "Article generated successfully from URLs", 
                100,
                result={
                    "filename": f"{filename}.md",
                    "path": article_path,
                    "query": query,
                    "type": article_type,
                    "source_urls": valid_urls,
                    "successful_extractions": successful_extractions,
                    "total_urls": len(valid_urls)
                }
            )
        else:
            raise Exception("Article generation failed")
            
    except Exception as e:
        update_job_status(job_id, "failed", f"Article generation from URLs failed: {str(e)}", 0, error=str(e))

# ============================================================================
# Writing Style API Endpoints
# ============================================================================

class WritingStyleUpdateRequest(BaseModel):
    content: str = Field(..., description="New content for writing_style.txt file")

@app.get("/api/writing-style")
async def get_writing_style(current_user: Dict = Depends(get_current_user)):
    """
    Get the current writing style content for the current user
    """
    try:
        user_id = current_user["id"]
        
        # Get writing style from user's Supabase Storage
        content = await storage_manager.get_writing_style(user_id)
        
        # Create response with cache-busting headers
        response = Response(
            content=content or "", 
            media_type="text/plain; charset=utf-8"
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["ETag"] = f'"{hash(content or "")}"'
        response.headers["Last-Modified"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read writing style: {str(e)}"
        )

@app.put("/api/writing-style")
async def update_writing_style(request: WritingStyleUpdateRequest, current_user: Dict = Depends(get_current_user)):
    """
    Update the writing style content for the current user
    """
    try:
        user_id = current_user["id"]
        
        # Upload writing style to user's Supabase Storage
        result = await storage_manager.upload_writing_style(user_id, request.content)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload writing style: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "message": "Writing style updated successfully",
            "content_length": len(request.content),
            "timestamp": datetime.now().isoformat(),
            "storage": "supabase"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update writing style: {str(e)}"
        )

@app.delete("/api/writing-style")
async def clear_writing_style(current_user: Dict = Depends(get_current_user)):
    """
    Clear the writing style content for the current user
    """
    try:
        user_id = current_user["id"]
        
        # Delete writing style from user's Supabase Storage
        success = await storage_manager.delete_writing_style(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear writing style"
            )
        
        return {
            "message": "Writing style cleared successfully",
            "timestamp": datetime.now().isoformat(),
            "storage": "supabase"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear writing style: {str(e)}"
        )

@app.get("/api/writing-style/info")
async def get_writing_style_info():
    """
    Get information about the writing style file
    """
    try:
        writing_style_path = Path("./data/writing_style.txt")
        
        if not writing_style_path.exists():
            return {
                "exists": False,
                "size": 0,
                "created": None,
                "modified": None,
                "content_preview": ""
            }
        
        file_stat = writing_style_path.stat()
        
        # Read first 200 characters for preview
        with open(writing_style_path, "r", encoding="utf-8") as f:
            content = f.read()
            preview = content[:200] + "..." if len(content) > 200 else content
        
        return {
            "exists": True,
            "size": file_stat.st_size,
            "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "content_length": len(content),
            "content_preview": preview
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get writing style info: {str(e)}"
        )

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
