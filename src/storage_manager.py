#!/usr/bin/env python3
"""
Storage Manager for Aksarajna - Handles persistent storage for cloud deployments
Supports both local file system and cloud storage (GitHub, S3, etc.)
"""

import os
import json
import asyncio
import aiohttp
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')

class StorageManager:
    """Unified storage manager that works with both local and cloud storage"""
    
    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "local")  # local, github, s3
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repo = os.getenv("GITHUB_REPO")  # format: "username/repo"
        self.github_branch = os.getenv("GITHUB_BRANCH", "main")
        
    async def save_article(self, filename: str, content: str) -> bool:
        """Save article to configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._save_to_github(f"articles/{filename}", content)
            else:
                return await self._save_to_local(f"articles/{filename}", content)
        except Exception as e:
            print(f"Error saving article {filename}: {e}")
            return False
    
    async def save_sources(self, content: str) -> bool:
        """Save sources.md to configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._save_to_github("data/sources.md", content)
            else:
                return await self._save_to_local("data/sources.md", content)
        except Exception as e:
            print(f"Error saving sources: {e}")
            return False
    
    async def save_context(self, content: str) -> bool:
        """Save context.json to configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._save_to_github("data/context.json", content)
            else:
                return await self._save_to_local("data/context.json", content)
        except Exception as e:
            print(f"Error saving context: {e}")
            return False
    
    async def get_article(self, filename: str) -> Optional[str]:
        """Get article from configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._get_from_github(f"articles/{filename}")
            else:
                return await self._get_from_local(f"articles/{filename}")
        except Exception as e:
            print(f"Error getting article {filename}: {e}")
            return None
    
    async def get_sources(self) -> Optional[str]:
