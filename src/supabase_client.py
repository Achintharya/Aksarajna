#!/usr/bin/env python3
"""
Supabase client configuration for storage and database operations
"""

import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime
import logging

# Load environment variables
load_dotenv('config/.env')

# Configure logging
logger = logging.getLogger(__name__)

# Supabase configuration - Using new API keys
SUPABASE_URL = os.getenv('SUPABASE_PROJECT_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY')  # Secret key for backend operations

if not SUPABASE_URL:
    raise ValueError("SUPABASE_PROJECT_URL environment variable is required")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_SECRET_KEY environment variable is required")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Storage bucket names
ARTICLES_BUCKET = "articles"
SOURCES_BUCKET = "sources" 
STYLES_BUCKET = "writing-styles"

class SupabaseStorageManager:
    """Manager class for Supabase Storage operations"""
    
    def __init__(self):
        self.client = supabase
        
    async def ensure_buckets_exist(self):
        """Ensure all required storage buckets exist"""
        buckets_to_create = [ARTICLES_BUCKET, SOURCES_BUCKET, STYLES_BUCKET]
        
        try:
            # Get existing buckets
            existing_buckets = self.client.storage.list_buckets()
            existing_names = [bucket.name for bucket in existing_buckets]
            
            # Create missing buckets
            for bucket_name in buckets_to_create:
                if bucket_name not in existing_names:
                    logger.info(f"Creating storage bucket: {bucket_name}")
                    self.client.storage.create_bucket(bucket_name, {"public": False})
                    
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
        
    async def upload_article(self, user_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Upload article content to user's storage"""
        try:
            file_path = self.get_user_article_path(user_id, filename)
            
            # Upload to storage
            result = self.client.storage.from_(ARTICLES_BUCKET).upload(
                file_path, 
                content.encode('utf-8'),
                {"content-type": "text/markdown"}
            )
            
            # Insert metadata into database
            article_data = {
                "user_id": user_id,
                "filename": filename,
                "title": self._extract_title_from_filename(filename),
                "storage_path": file_path,
                "content_length": len(content),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            db_result = self.client.table("articles").insert(article_data).execute()
            
            logger.info(f"Successfully uploaded article {filename} for user {user_id}")
            return {
                "success": True,
                "storage_result": result,
                "db_result": db_result,
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error uploading article: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_article(self, user_id: str, filename: str) -> Optional[str]:
        """Get article content from user's storage"""
        try:
            file_path = self.get_user_article_path(user_id, filename)
            
            # Download from storage
            result = self.client.storage.from_(ARTICLES_BUCKET).download(file_path)
            
            if result:
                return result.decode('utf-8')
            return None
            
        except Exception as e:
            logger.error(f"Error getting article: {e}")
            return None
            
    async def list_user_articles(self, user_id: str) -> List[Dict[str, Any]]:
        """List all articles for a specific user"""
        try:
            # Query database for user's articles
            result = self.client.table("articles").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing user articles: {e}")
            return []
            
    async def delete_article(self, user_id: str, filename: str) -> bool:
        """Delete article from user's storage and database"""
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
            
    async def upload_sources(self, user_id: str, content: str) -> Dict[str, Any]:
        """Upload sources content to user's storage"""
        try:
            file_path = self.get_user_sources_path(user_id)
            
            # Upload to storage
            result = self.client.storage.from_(SOURCES_BUCKET).upload(
                file_path,
                content.encode('utf-8'),
                {"content-type": "text/markdown", "upsert": "true"}
            )
            
            logger.info(f"Successfully uploaded sources for user {user_id}")
            return {"success": True, "result": result, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Error uploading sources: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_sources(self, user_id: str) -> Optional[str]:
        """Get sources content from user's storage"""
        try:
            file_path = self.get_user_sources_path(user_id)
            
            # Download from storage
            result = self.client.storage.from_(SOURCES_BUCKET).download(file_path)
            
            if result:
                return result.decode('utf-8')
            return ""
            
        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return ""
            
    async def upload_writing_style(self, user_id: str, content: str) -> Dict[str, Any]:
        """Upload writing style content to user's storage"""
        try:
            file_path = self.get_user_style_path(user_id)
            
            # Upload to storage
            result = self.client.storage.from_(STYLES_BUCKET).upload(
                file_path,
                content.encode('utf-8'),
                {"content-type": "text/plain", "upsert": "true"}
            )
            
            logger.info(f"Successfully uploaded writing style for user {user_id}")
            return {"success": True, "result": result, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Error uploading writing style: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_writing_style(self, user_id: str) -> Optional[str]:
        """Get writing style content from user's storage"""
        try:
            file_path = self.get_user_style_path(user_id)
            
            # Download from storage
            result = self.client.storage.from_(STYLES_BUCKET).download(file_path)
            
            if result:
                return result.decode('utf-8')
            return ""
            
        except Exception as e:
            logger.error(f"Error getting writing style: {e}")
            return ""
            
    async def delete_writing_style(self, user_id: str) -> bool:
        """Delete writing style from user's storage"""
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
        
        # Replace underscores with spaces and remove date patterns
        title = title.replace('_', ' ')
        
        # Remove date patterns (YYYYMMDD)
        import re
        title = re.sub(r'\d{8}', '', title).strip()
        
        # Capitalize first letter of each word
        title = ' '.join(word.capitalize() for word in title.split())
        
        return title or "Untitled Article"

# Global storage manager instance
storage_manager = SupabaseStorageManager()

# Database helper functions
class SupabaseDBManager:
    """Manager class for Supabase Database operations"""
    
    def __init__(self):
        self.client = supabase
        
    async def ensure_tables_exist(self):
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
        
        -- Policy: Users can only access their own articles
        CREATE POLICY "Users can access own articles" ON articles
            FOR ALL USING (auth.uid() = user_id);
        """
        
        logger.info("Database schema reference created. Please run this SQL in Supabase Dashboard:")
        logger.info(articles_schema)
        
    async def get_user_article_metadata(self, user_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get article metadata from database"""
        try:
            result = self.client.table("articles").select("*").eq("user_id", user_id).eq("filename", filename).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting article metadata: {e}")
            return None

# Global database manager instance
db_manager = SupabaseDBManager()
