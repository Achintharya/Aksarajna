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
        """Get sources.md from configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._get_from_github("data/sources.md")
            else:
                return await self._get_from_local("data/sources.md")
        except Exception as e:
            print(f"Error getting sources: {e}")
            return None
    
    async def get_context(self) -> Optional[str]:
        """Get context.json from configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._get_from_github("data/context.json")
            else:
                return await self._get_from_local("data/context.json")
        except Exception as e:
            print(f"Error getting context: {e}")
            return None
    
    async def list_articles(self) -> List[Dict[str, Any]]:
        """List all articles from configured storage backend"""
        try:
            if self.storage_type == "github" and self.github_token and self.github_repo:
                return await self._list_from_github("articles/")
            else:
                return await self._list_from_local("articles/")
        except Exception as e:
            print(f"Error listing articles: {e}")
            return []
    
    # Local storage methods
    async def _save_to_local(self, filepath: str, content: str) -> bool:
        """Save content to local file system"""
        try:
            full_path = Path(filepath)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Saved to local: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Error saving to local {filepath}: {e}")
            return False
    
    async def _get_from_local(self, filepath: str) -> Optional[str]:
        """Get content from local file system"""
        try:
            full_path = Path(filepath)
            if not full_path.exists():
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error reading from local {filepath}: {e}")
            return None
    
    async def _list_from_local(self, directory: str) -> List[Dict[str, Any]]:
        """List files from local directory"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            
            files = []
            for file_path in dir_path.glob("*.md"):
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            return files
        except Exception as e:
            print(f"❌ Error listing local directory {directory}: {e}")
            return []
    
    # GitHub storage methods
    async def _save_to_github(self, filepath: str, content: str) -> bool:
        """Save content to GitHub repository"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/contents/{filepath}"
            
            # First, try to get the current file to get its SHA (for updates)
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Check if file exists
                async with session.get(url, headers=headers) as response:
                    sha = None
                    if response.status == 200:
                        data = await response.json()
                        sha = data.get("sha")
                
                # Prepare the content
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                
                payload = {
                    "message": f"Update {filepath}",
                    "content": encoded_content,
                    "branch": self.github_branch
                }
                
                if sha:
                    payload["sha"] = sha
                
                # Save/update the file
                async with session.put(url, headers=headers, json=payload) as response:
                    if response.status in [200, 201]:
                        print(f"✅ Saved to GitHub: {filepath}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ GitHub API error: {response.status} - {error_text}")
                        return False
        
        except Exception as e:
            print(f"❌ Error saving to GitHub {filepath}: {e}")
            return False
    
    async def _get_from_github(self, filepath: str) -> Optional[str]:
        """Get content from GitHub repository"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/contents/{filepath}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Decode base64 content
                        encoded_content = data.get("content", "")
                        return base64.b64decode(encoded_content).decode('utf-8')
                    elif response.status == 404:
                        return None
                    else:
                        error_text = await response.text()
                        print(f"❌ GitHub API error: {response.status} - {error_text}")
                        return None
        
        except Exception as e:
            print(f"❌ Error getting from GitHub {filepath}: {e}")
            return None
    
    async def _list_from_github(self, directory: str) -> List[Dict[str, Any]]:
        """List files from GitHub repository directory"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/contents/{directory}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        files = []
                        
                        for item in data:
                            if item.get("type") == "file" and item.get("name", "").endswith(".md"):
                                files.append({
                                    "filename": item.get("name"),
                                    "size": item.get("size", 0),
                                    "created": item.get("created_at", ""),
                                    "modified": item.get("updated_at", "")
                                })
                        
                        return files
                    elif response.status == 404:
                        return []
                    else:
                        error_text = await response.text()
                        print(f"❌ GitHub API error: {response.status} - {error_text}")
                        return []
        
        except Exception as e:
            print(f"❌ Error listing from GitHub {directory}: {e}")
            return []


# Global storage manager instance
storage_manager = StorageManager()
