#!/usr/bin/env python3
"""
Supabase client configuration for storage and database operations
"""

import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import logging
import re

# Load environment variables
load_dotenv('config/.env')

# Configure logging
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_PROJECT_URL')

# Determine which key to use for supabase-py client compatibility
# Prefer SUPABASE_SERVICE_ROLE_KEY for server-side operations.
SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
NEW_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')  # New sb_secret_* format
LEGACY_KEY = SERVICE_ROLE_KEY  # legacy service_role_ key

SUPABASE_KEY = None

if LEGACY_KEY:
    # Use the legacy service role key when available (works with supabase-py)
    SUPABASE_KEY = LEGACY_KEY
    logger.info("Using SUPABASE_SERVICE_ROLE_KEY for Supabase client (recommended for server operations)")
else:
    # No service role key available; try the provided secret key
    if NEW_SECRET_KEY:
        if NEW_SECRET_KEY.startswith('sb_secret_'):
            # New key format detected
            logger.warning(
                "Detected new sb_secret_* key format. supabase-py may not fully support this format. "
                "Attempting to initialize client with the new key; if initialization fails, "
                "provide SUPABASE_SERVICE_ROLE_KEY (legacy service role) instead."
            )
            SUPABASE_KEY = NEW_SECRET_KEY
        else:
            # Key present but not new format — assume it's compatible
            SUPABASE_KEY = NEW_SECRET_KEY
            logger.info("Using provided SUPABASE_SECRET_KEY for Supabase client")
    else:
        # No usable key found
        raise ValueError(
            "Missing Supabase key. Set SUPABASE_SERVICE_ROLE_KEY (recommended) or SUPABASE_SECRET_KEY in your environment."
        )

# Validate final presence
if not SUPABASE_KEY:
    raise ValueError("Failed to determine a Supabase key to initialize the client.")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_PROJECT_URL environment variable is required")

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    raise

# Storage bucket names
ARTICLES_BUCKET = "articles"
SOURCES_BUCKET = "sources" 
STYLES_BUCKET = "writing-styles"

class SupabaseStorageManager:
    """Manager class for Supabase Storage operations (synchronous)"""
    
    def __init__(self):
        self.client = supabase
        
    def ensure_buckets_exist(self):
        """Ensure all required storage buckets exist"""
        buckets_to_create = [ARTICLES_BUCKET, SOURCES_BUCKET, STYLES_BUCKET]
        
        try:
            # Get existing buckets
            existing_buckets = self.client.storage.list_buckets()
            existing_names = [bucket.name for bucket in existing_buckets] if existing_buckets else []
            
            # Create missing buckets
            for bucket_name in buckets_to_create:
                if bucket_name not in existing_names:
                    logger.info(f"Creating storage bucket: {bucket_name}")
                    try:
                        self.client.storage.create_bucket(
                            id=bucket_name,
                            options={"public": False}
                        )
                    except Exception as e:
                        # Bucket might already exist or have different error
                        logger.warning(f"Could not create bucket {bucket_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error ensuring buckets exist: {e}")
            
    def get_user_article_path(self, user_id: str, filename: str) -> str:
        """Generate storage path for user article"""
        return f"{user_id}/articles/{filename}"
        
    def get_user_sources_path(self, user_id: str, filename: str = "sources.md") -> str:
        """Generate storage path for user sources"""
        return f"{user_id}/sources/{filename}"
        
    def get_user_style_path(self, user_id: str, filename: str = "writing_style.txt") -> str:
        """Generate storage path for user writing style"""
        return f"{user_id}/styles/{filename}"
        
    def upload_article(self, user_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Upload article content to user's storage (synchronous)"""
        try:
            file_path = self.get_user_article_path(user_id, filename)
            
            # Upload to storage
            result = self.client.storage.from_(ARTICLES_BUCKET).upload(
                path=file_path, 
                file=content.encode('utf-8'),
                file_options={"content-type": "text/markdown"}
            )
            
            # Insert metadata into database
            article_data = {
                "user_id": user_id,
                "filename": filename,
                "title": self._extract_title_from_filename(filename),
                "storage_path": file_path,
                "content_length": len(content),
                # Let database handle timestamps with defaults
            }
            
            db_result = self.client.table("articles").insert(article_data).execute()
            
            logger.info(f"Successfully uploaded article {filename} for user {user_id}")
            return {
                "success": True,
                "storage_path": file_path,
                "db_result": db_result.data if hasattr(db_result, 'data') else db_result
            }
            
        except Exception as e:
            logger.error(f"Error uploading article: {e}")
            return {"success": False, "error": str(e)}
            
    def get_article(self, user_id: str, filename: str) -> Optional[str]:
        """Get article content from user's storage (synchronous)"""
        try:
            file_path = self.get_user_article_path(user_id, filename)
            
            # Download from storage
            result = self.client.storage.from_(ARTICLES_BUCKET).download(file_path)
            
            # Handle different return types
            if isinstance(result, bytes):
                return result.decode('utf-8')
            elif isinstance(result, str):
                return result
            else:
                logger.warning(f"Unexpected download result type: {type(result)}")
                return str(result) if result else None
                
        except Exception as e:
            logger.error(f"Error getting article: {e}")
            return None
            
    def list_user_articles(self, user_id: str) -> List[Dict[str, Any]]:
        """List all articles for a specific user (synchronous)"""
        try:
            # Query database for user's articles
            result = self.client.table("articles").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
            
            if hasattr(result, 'data'):
                return result.data if result.data else []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error listing user articles: {e}")
            return []
            
    def delete_article(self, user_id: str, filename: str) -> bool:
        """Delete article from user's storage and database (synchronous)"""
        try:
            file_path = self.get_user_article_path(user_id, filename)
            
            # Delete from storage
            self.client.storage.from_(ARTICLES_BUCKET).remove([file_path])
            
            # Delete from database
            self.client.table("articles").delete().eq("user_id", user_id).eq("filename", filename).execute()
            
            logger.info(f"Successfully deleted article {filename} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting article: {e}")
            return False
            
    def upload_sources(self, user_id: str, content: str) -> Dict[str, Any]:
        """Upload sources content to user's storage (synchronous)"""
        try:
            file_path = self.get_user_sources_path(user_id)
            
            # Try to update first, then upload if doesn't exist
            try:
                # Delete existing file first
                self.client.storage.from_(SOURCES_BUCKET).remove([file_path])
            except:
                pass  # File might not exist
            
            # Upload new content
            result = self.client.storage.from_(SOURCES_BUCKET).upload(
                path=file_path,
                file=content.encode('utf-8'),
                file_options={"content-type": "text/markdown"}
            )
            
            logger.info(f"Successfully uploaded sources for user {user_id}")
            return {"success": True, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Error uploading sources: {e}")
            return {"success": False, "error": str(e)}
            
    def get_sources(self, user_id: str) -> Optional[str]:
        """Get sources content from user's storage (synchronous)"""
        try:
            file_path = self.get_user_sources_path(user_id)
            
            # Download from storage
            result = self.client.storage.from_(SOURCES_BUCKET).download(file_path)
            
            # Handle different return types
            if isinstance(result, bytes):
                return result.decode('utf-8')
            elif isinstance(result, str):
                return result
            else:
                return ""
                
        except Exception as e:
            # Sources might not exist yet, return empty string
            logger.debug(f"Sources not found or error: {e}")
            return ""
            
    def upload_writing_style(self, user_id: str, content: str) -> Dict[str, Any]:
        """Upload writing style content to user's storage (synchronous)"""
        try:
            file_path = self.get_user_style_path(user_id)
            
            # Try to delete existing file first
            try:
                self.client.storage.from_(STYLES_BUCKET).remove([file_path])
            except:
                pass  # File might not exist
            
            # Upload new content
            result = self.client.storage.from_(STYLES_BUCKET).upload(
                path=file_path,
                file=content.encode('utf-8'),
                file_options={"content-type": "text/plain"}
            )
            
            logger.info(f"Successfully uploaded writing style for user {user_id}")
            return {"success": True, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Error uploading writing style: {e}")
            return {"success": False, "error": str(e)}
            
    def get_writing_style(self, user_id: str) -> Optional[str]:
        """Get writing style content from user's storage (synchronous)"""
        try:
            file_path = self.get_user_style_path(user_id)
            
            # Download from storage
            result = self.client.storage.from_(STYLES_BUCKET).download(file_path)
            
            # Handle different return types
            if isinstance(result, bytes):
                return result.decode('utf-8')
            elif isinstance(result, str):
                return result
            else:
                return ""
                
        except Exception as e:
            # Writing style might not exist yet, return empty string
            logger.debug(f"Writing style not found or error: {e}")
            return ""
            
    def delete_writing_style(self, user_id: str) -> bool:
        """Delete writing style from user's storage (synchronous)"""
        try:
            file_path = self.get_user_style_path(user_id)
            
            # Delete from storage
            self.client.storage.from_(STYLES_BUCKET).remove([file_path])
            
            logger.info(f"Successfully deleted writing style for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting writing style: {e}")
            return False
            
    def _extract_title_from_filename(self, filename: str) -> str:
        """Extract a readable title from filename"""
        # Remove file extension and common prefixes
        title = filename.replace('.md', '').replace('.txt', '').replace('article_', '')
        
        # Replace underscores with spaces
        title = title.replace('_', ' ')
        
        # Remove date patterns (YYYYMMDD)
        title = re.sub(r'\d{8}', '', title).strip()
        
        # Capitalize first letter of each word
        title = ' '.join(word.capitalize() for word in title.split())
        
        return title or "Untitled Article"

# Global storage manager instance
storage_manager = SupabaseStorageManager()

# Compatibility wrappers for async calls in main.py
async def upload_article(user_id: str, filename: str, content: str) -> Dict[str, Any]:
    """Async wrapper for compatibility"""
    return storage_manager.upload_article(user_id, filename, content)

async def get_article(user_id: str, filename: str) -> Optional[str]:
    """Async wrapper for compatibility"""
    return storage_manager.get_article(user_id, filename)

async def list_user_articles(user_id: str) -> List[Dict[str, Any]]:
    """Async wrapper for compatibility"""
    return storage_manager.list_user_articles(user_id)

async def delete_article(user_id: str, filename: str) -> bool:
    """Async wrapper for compatibility"""
    return storage_manager.delete_article(user_id, filename)

async def upload_sources(user_id: str, content: str) -> Dict[str, Any]:
    """Async wrapper for compatibility"""
    return storage_manager.upload_sources(user_id, content)

async def get_sources(user_id: str) -> Optional[str]:
    """Async wrapper for compatibility"""
    return storage_manager.get_sources(user_id)

async def upload_writing_style(user_id: str, content: str) -> Dict[str, Any]:
    """Async wrapper for compatibility"""
    return storage_manager.upload_writing_style(user_id, content)

async def get_writing_style(user_id: str) -> Optional[str]:
    """Async wrapper for compatibility"""
    return storage_manager.get_writing_style(user_id)

async def delete_writing_style(user_id: str) -> bool:
    """Async wrapper for compatibility"""
    return storage_manager.delete_writing_style(user_id)

# Add compatibility methods to storage_manager for existing code
storage_manager.upload_article = upload_article
storage_manager.get_article = get_article
storage_manager.list_user_articles = list_user_articles
storage_manager.delete_article = delete_article
storage_manager.upload_sources = upload_sources
storage_manager.get_sources = get_sources
storage_manager.upload_writing_style = upload_writing_style
storage_manager.get_writing_style = get_writing_style
storage_manager.delete_writing_style = delete_writing_style

# Database helper functions
class SupabaseDBManager:
    """Manager class for Supabase Database operations (synchronous)"""
    
    def __init__(self):
        self.client = supabase
        
    def ensure_tables_exist(self):
        """Ensure all required database tables exist"""
        # Note: Tables should be created via Supabase Dashboard or migrations
        # This is just for reference of the expected schema
        
        articles_schema = """
        CREATE TABLE IF NOT EXISTS articles (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            title TEXT,
            storage_path TEXT NOT NULL,
            content_length INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, filename)
        );
        
        -- Enable Row Level Security
        ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Users can only access their own articles (corrected)
        CREATE POLICY "Users can access own articles" ON articles
            FOR ALL USING ((SELECT auth.uid()) = user_id);
        """
        
        logger.info("Database schema reference - please ensure this is set up in Supabase Dashboard")
        
    def get_user_article_metadata(self, user_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get article metadata from database (synchronous)"""
        try:
            result = self.client.table("articles").select("*").eq("user_id", user_id).eq("filename", filename).execute()
            
            if hasattr(result, 'data') and result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting article metadata: {e}")
            return None

# Global database manager instance
db_manager = SupabaseDBManager()

# Compatibility wrapper for async calls
async def get_user_article_metadata(user_id: str, filename: str) -> Optional[Dict[str, Any]]:
    """Async wrapper for compatibility"""
    return db_manager.get_user_article_metadata(user_id, filename)

# Add to db_manager for compatibility
db_manager.get_user_article_metadata = get_user_article_metadata
