import asyncio
import os
import json
import time
import random
import aiohttp
import argparse
import sys
from pydantic import BaseModel, Field, ValidationError
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from duckduckgo_search import DDGS

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from src.config import logger, config, cache

class PageSummary(BaseModel):
    summary: str = Field(..., description="Detailed page summary related to query")

class SearchResult(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    score: int = 0

async def random_delay(min_delay=1, max_delay=3):
    """
    Implement a random delay to avoid rate limiting
    
    Args:
        min_delay (float): Minimum delay in seconds
        max_delay (float): Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Applying random delay of {delay:.2f} seconds")
    await asyncio.sleep(delay)

async def website_search_ddg(query: str, max_results: int = 5):
    """
    Search for websites using DuckDuckGo
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of URLs
    """
    cache_key = f"ddg_search_{query}_{max_results}"
    cached_results = cache.get(cache_key)
    
    if cached_results and config.get('cache.enabled'):
        logger.info(f"Using cached DuckDuckGo search results for '{query}'")
        return cached_results
    
    logger.info(f"Searching DuckDuckGo for '{query}'")
    try:
        with DDGS() as search:
            results = search.text(query, max_results=max_results)
            urls = [result["href"] for result in results if "href" in result]
            
            if urls:
                logger.info(f"Found {len(urls)} results from DuckDuckGo")
                if config.get('cache.enabled'):
                    cache.set(cache_key, urls)
                return urls
            else:
                logger.warning("No results found from DuckDuckGo search")
                return []
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []

async def website_search(query: str, max_results: int = 6) -> list:
    """
    Search for websites using Serper API with improved error handling and rate limiting
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of URLs
    """
    cache_key = f"serper_search_{query}_{max_results}"
    cached_results = cache.get(cache_key)
    
    if cached_results and config.get('cache.enabled'):
        logger.info(f"Using cached Serper search results for '{query}'")
        return cached_results
    
    logger.info(f"Searching Google (via Serper) for '{query}'")
    
    serper_api_key = config.get('api_keys.serper')
    if not serper_api_key:
        logger.error("Serper API key not found in configuration")
        return []
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": serper_api_key
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
                
                final_results = [link for score, link in results[:max_results]]
                
                if final_results:
                    logger.info(f"Found {len(final_results)} results from Serper")
                    if config.get('cache.enabled'):
                        cache.set(cache_key, final_results)
                    return final_results
                else:
                    logger.warning("No results found from Serper search")
                    return []

    except aiohttp.ClientResponseError as e:
        logger.error(f"Serper API response error: {e.status} - {e.message}")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"Network error during Serper search: {e}")
        return []
    except Exception as e:
        logger.error(f"Serper search failed: {e}")
        return []

async def make_request_with_backoff(url, session, max_retries=5):
    """
    Make an HTTP request with exponential backoff for rate limiting
    
    Args:
        url (str): URL to request
        session (aiohttp.ClientSession): aiohttp session
        max_retries (int): Maximum number of retries
        
    Returns:
        aiohttp.ClientResponse: Response object
    """
    retries = 0
    backoff_factor = config.get('web_crawling.backoff_factor', 1)
    timeout = aiohttp.ClientTimeout(total=config.get('web_crawling.timeout', 30))
    
    while retries < max_retries:
        try:
            response = await session.get(url, timeout=timeout)
            
            if response.status == 429:  # HTTP 429 Too Many Requests
                wait_time = backoff_factor * (2 ** retries)
                logger.warning(f"Rate limit hit for {url}. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                retries += 1
            else:
                return response
                
        except asyncio.TimeoutError:
            logger.warning(f"Request to {url} timed out")
            retries += 1
            if retries < max_retries:
                wait_time = backoff_factor * (2 ** retries)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            logger.error(f"Request to {url} failed: {e}")
            raise

    raise Exception(f"Max retries exceeded for {url}")

async def extract(query: str = None):
    """
    Fetch URLs, configure the crawler, and extract structured information in parallel.
    
    Args:
        query (str, optional): Search query. If None, will prompt the user.
    """
    # Validate query
    if not query:
        query = input("Enter search query: ")
    
    if not query or not query.strip():
        logger.error("Empty search query provided")
        return
    
    logger.info(f"Starting extraction process for query: '{query}'")
    
    # First try DuckDuckGo search
    urls = await website_search_ddg(query)
    
    # If DuckDuckGo search fails or returns no results, try Serper
    if not urls:
        logger.info("DuckDuckGo search returned no results, trying alternative search...")
        urls = await website_search(query)
    else:
        logger.info("Using DuckDuckGo search results...")
    
    if not urls:
        logger.error("No URLs found from either search method.")
        return

    # Save URLs to sources.txt with query as subheading
    sources_path = config.get('paths.sources')
    logger.info(f"Saving {len(urls)} URLs to {sources_path}")
    
    try:
        with open(sources_path, "a", encoding='utf-8') as f:
            f.write(f"\n## {query}\n")
            for url in urls:
                f.write(f"- {url}\n")
            f.write("\n")  # Add extra newline for readability
    except Exception as e:
        logger.error(f"Error saving URLs to file: {e}")

    # Configure browser and extraction strategy
    browser_config = BrowserConfig(headless=True, verbose=True)
    
    mistral_api_key = config.get('api_keys.mistral')
    if not mistral_api_key:
        logger.error("Mistral API key not found in configuration")
        return
    
    extraction_model = config.get('models.extraction')
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider=extraction_model, api_token=mistral_api_key),
        schema=PageSummary.model_json_schema()
    )

    logger.info(f"Starting web crawling for {len(urls)} URLs")
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Crawl all URLs concurrently
            results = await crawler.arun_many(urls=urls, config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=extraction_strategy
            ))

        # Process results and save to file
        context_json_path = config.get('paths.context_json')
        logger.info(f"Processing crawl results and saving to {context_json_path}")
        
        with open(context_json_path, "w", encoding='utf-8') as file:
            output_data = []  # Initialize a list to hold all summaries

            for url, result in zip(urls, results):
                if result.success:
                    try:
                        page_summary = json.loads(result.extracted_content)
                        output_data.append(page_summary)  # Append each summary to the list
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from {url}: {e}")
                else:
                    logger.warning(f"Crawl failed for {url}")

            # Write the entire list as a JSON array
            json.dump(output_data, file, indent=2, ensure_ascii=False)  # Use json.dump to write the list to the file

            logger.info(f"Successfully extracted information from {len(output_data)} URLs")
    
    except Exception as e:
        logger.error(f"Error during web crawling: {e}")
        raise

def main():
    """Main function to handle command-line arguments and run the extraction process"""
    parser = argparse.ArgumentParser(description="Web Context Extraction Tool")
    parser.add_argument("--query", type=str, help="Search query")
    args = parser.parse_args()
    
    try:
        asyncio.run(extract(query=args.query))
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
