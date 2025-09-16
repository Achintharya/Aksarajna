import asyncio
import os
import json
import time
import requests
import random
import aiohttp
import tempfile
import shutil
import platform
from pathlib import Path

# Cross-platform file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # Windows doesn't have fcntl, use msvcrt or threading locks
    HAS_FCNTL = False
    try:
        import msvcrt
        HAS_MSVCRT = True
    except ImportError:
        HAS_MSVCRT = False

import threading
from dotenv import load_dotenv
from pydantic import BaseModel, Field
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import time

# Load .env from config directory
load_dotenv('config/.env')

class PageSummary(BaseModel):
    summary: str = Field(..., description="Detailed page summary realted to query")

class AtomicFileManager:
    """Thread-safe atomic file operations with proper locking and versioning"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.lock_dir = self.base_path / ".locks"
        self.lock_dir.mkdir(exist_ok=True)
        self.backup_dir = self.base_path / ".backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def _get_lock_file(self, filename: str) -> Path:
        """Get lock file path for a given filename"""
        return self.lock_dir / f"{filename}.lock"
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of the file"""
        if not file_path.exists():
            return None
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        
        # Keep only last 10 backups
        backups = sorted(self.backup_dir.glob(f"{file_path.stem}_*{file_path.suffix}"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
        
        return backup_path
    
    def _acquire_lock(self, lock_file_handle):
        """Cross-platform file locking"""
        if HAS_FCNTL:
            # Unix/Linux/Mac
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif HAS_MSVCRT:
            # Windows
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            # Fallback - just continue without locking
            pass
    
    def _release_lock(self, lock_file_handle):
        """Cross-platform file lock release"""
        if HAS_FCNTL:
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
        elif HAS_MSVCRT:
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            pass

    async def atomic_write(self, filename: str, content: str, mode: str = "w", encoding: str = "utf-8"):
        """Atomically write content to a file with cross-platform locking"""
        file_path = self.base_path / filename
        lock_file = self._get_lock_file(filename)
        temp_file = None
        
        try:
            # Create lock file
            with open(lock_file, "w") as lock:
                # Try to acquire exclusive lock (non-blocking)
                try:
                    self._acquire_lock(lock)
                except (BlockingIOError, OSError):
                    # If lock is held, wait with exponential backoff
                    for attempt in range(5):
                        await asyncio.sleep(0.1 * (2 ** attempt))
                        try:
                            self._acquire_lock(lock)
                            break
                        except (BlockingIOError, OSError):
                            continue
                    else:
                        print(f"Warning: Could not acquire lock for {filename}, proceeding without lock")
                
                # Create backup if file exists
                backup_path = self._create_backup(file_path)
                
                # Create temporary file in same directory for atomic operation
                with tempfile.NamedTemporaryFile(
                    mode=mode, 
                    encoding=encoding, 
                    dir=file_path.parent, 
                    delete=False,
                    suffix=f".tmp_{filename}"
                ) as temp:
                    temp_file = Path(temp.name)
                    temp.write(content)
                    temp.flush()
                    if hasattr(os, 'fsync'):
                        os.fsync(temp.fileno())  # Force write to disk
                
                # Atomic move (rename) - this is atomic on most filesystems
                shutil.move(str(temp_file), str(file_path))
                
                print(f"✓ Atomically wrote {len(content)} characters to {filename}")
                if backup_path:
                    print(f"✓ Backup created: {backup_path.name}")
                
        except Exception as e:
            # Cleanup temp file if it exists
            if temp_file and temp_file.exists():
                temp_file.unlink()
            raise Exception(f"Atomic write failed for {filename}: {e}")
        
        finally:
            # Remove lock file
            if lock_file.exists():
                lock_file.unlink()
    
    async def atomic_append(self, filename: str, content: str, encoding: str = "utf-8"):
        """Atomically append content to a file"""
        file_path = self.base_path / filename
        
        # Read existing content
        existing_content = ""
        if file_path.exists():
            with open(file_path, "r", encoding=encoding) as f:
                existing_content = f.read()
        
        # Write combined content atomically
        combined_content = existing_content + content
        await self.atomic_write(filename, combined_content, encoding=encoding)
    
    def read_with_lock(self, filename: str, encoding: str = "utf-8") -> str:
        """Read file content with cross-platform shared lock"""
        file_path = self.base_path / filename
        
        if not file_path.exists():
            return ""
        
        try:
            # For reading, we can just read directly since our writes are atomic
            # The atomic write ensures consistency
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        
        except Exception as e:
            print(f"Warning: Could not read file {filename}: {e}")
            return ""

# Global file manager instance
file_manager = AtomicFileManager()

async def update_sources_file(query: str, urls: list):
    """Update sources.md file with atomic operations and proper formatting"""
    try:
        # Format new content
        new_content = f"\n## {query}\n"
        for url in urls:
            new_content += f"- [{url}]({url})\n"
        new_content += "\n"
        
        # Atomically append to sources.md
        await file_manager.atomic_append("sources.md", new_content)
        print(f"✓ Added {len(urls)} sources for query: {query}")
        
    except Exception as e:
        print(f"✗ Failed to update sources file: {e}")
        raise

async def save_context_data(data: list, filename: str = "context.json"):
    """Save context data with atomic operations"""
    try:
        content = json.dumps(data, indent=2, ensure_ascii=False)
        await file_manager.atomic_write(filename, content)
        print(f"✓ Saved {len(data)} context entries to {filename}")
        
    except Exception as e:
        print(f"✗ Failed to save context data: {e}")
        raise
    
async def random_delay():
    """Implement a random delay between 1 and 3 seconds to avoid rate limiting"""
    delay = random.uniform(1, 3)
    await asyncio.sleep(delay)

async def website_search_ddg(query: str, max_results: int = 5):
    try:
        with DDGS() as search:
            results = search.text(query, max_results=max_results)
            urls = [result["href"] for result in results if "href" in result]
            return list(urls)
    except Exception as e:
        print(f"Search failed: {e}")
        return []


async def website_search(query: str, max_results: int =6) -> list:
    """Search for websites using Serper API with improved error handling and rate limiting"""
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": os.getenv("SERPER_API_KEY")
    }
    payload = {"q": query, "gl": "in", "num": max_results}
    query_lower = query.lower()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://google.serper.dev/search", json=payload, headers=headers) as response:
                # Ensure we received a successful response
                response.raise_for_status()
                data = await response.json()

                organic_results = data.get("organic", [])
                results = []
                for result in organic_results:
                    link = result.get("link")
                    # Filter out YouTube links or if link is missing
                    if not link or "youtube.com" in link or "youtu.be" in link:
                        continue

                    # Calculate a relevance score based on the presence of the query in title and snippet
                    score = 0
                    title = result.get("title", "").lower()
                    snippet = result.get("snippet", "").lower()
                    if query_lower in title:
                        score += 2
                    if query_lower in snippet:
                        score += 1

                    if score > 0:
                        results.append((score, link))

                # Sort by score in descending order
                results.sort(key=lambda x: x[0], reverse=True)

                # Introduce a random delay to avoid rate limiting
                await random_delay()
                return [link for score, link in results[:max_results]]

    except aiohttp.ClientError as e:
        print(f"Network error during search: {e}")
        return []
    except Exception as e:
        print(f"Search failed: {e}")
        return []



async def make_request_with_backoff(url, headers, max_retries=5):
    retries = 0
    backoff_factor = 1

    while retries < max_retries:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:  # HTTP 429 Too Many Requests
            wait_time = backoff_factor * (2 ** retries)
            print(f"Rate limit hit. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            retries += 1
        else:
            return response

    raise Exception("Max retries exceeded")

async def simple_extract(urls, query):
    """Simple extraction without Playwright - fallback method"""
    output_data = []
    
    for url in urls:
        try:
            print(f"Extracting from: {url}")
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Limit text length and create summary
                text = text[:3000]  # First 3000 characters
                
                summary_data = {
                    "summary": f"Content from {url} about {query}: {text[:500]}...",  # First 500 chars as summary
                    "error": False
                }
                output_data.append(summary_data)
                print(f"✓ Extracted content from {url}")
            else:
                print(f"✗ Failed to fetch {url}: Status {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error extracting from {url}: {e}")
            output_data.append({
                "summary": f"Failed to extract from {url}",
                "error": True
            })
    
    # Save to context.json using atomic operations
    await save_context_data(output_data, "context.json")
    return output_data

async def extract(query: str = None):
    """Fetch URLs, configure the crawler, and extract structured information in parallel."""
    if not query:
        query = input("Enter search query: ")
    
    # First try DuckDuckGo search
    urls = await website_search_ddg(query)
    
    # If DuckDuckGo search fails or returns no results, try Serper
    if not urls:
        print("DuckDuckGo search returned no results, trying alternative search...")
        urls = await website_search(query)
    else:
        print("Using DuckDuckGo search results...")
    
    if not urls:
        print("No URLs found from either search method.")
        return

    # Save URLs to sources.md using atomic operations
    await update_sources_file(query, urls)

    # Try crawl4ai first if available
    if CRAWL4AI_AVAILABLE:
        try:
            browser_config = BrowserConfig(headless=True, verbose=True)

            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(provider="mistral/mistral-small-latest", api_token=os.getenv("MISTRAL_API_KEY")),
                schema=PageSummary.model_json_schema()
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Crawl all URLs concurrently
                results = await crawler.arun_many(urls=urls, config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    extraction_strategy=extraction_strategy
                ))

            # Process results and save to file
            with open("./data/context.json", "w") as file:
                output_data = []  # Initialize a list to hold all summaries

                for url, result in zip(urls, results):
                    if result.success:
                        page_summary = json.loads(result.extracted_content)
                        output_data.append(page_summary)  # Append each summary to the list
                    else:
                        print(f"Crawl failed for {url}\n")

                # Write the entire list as a JSON array
                json.dump(output_data, file, indent=2)  # Use json.dump to write the list to the file

                print("\nWrote extracted info to file")
        except Exception as e:
            print(f"Crawl4AI failed: {e}")
            print("Falling back to simple extraction...")
            await simple_extract(urls, query)
    else:
        print("Crawl4AI not available, using simple extraction...")
        await simple_extract(urls, query)

if __name__ == "__main__":
    asyncio.run(extract())
