import asyncio
import os
import json
import time
import requests
import random
import aiohttp
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from duckduckgo_search import DDGS
import time
import sys

load_dotenv(dotenv_path='./config/.env')

class PageSummary(BaseModel):
    summary: str = Field(..., description="Detailed page summary realted to query")
    
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
                if not isinstance(organic_results, list):  # Ensure it's a list
                    print("Unexpected API response format.")
                    return []
                results = []
                for result in organic_results:
                    if not isinstance(result, dict):
                        continue  # Skip invalid data

                    link = result.get("link")
                    if not link or "youtube.com" in link or "youtu.be" in link:
                        continue  # Ignore YouTube links and missing links

                    title = result.get("title", "")
                    snippet = result.get("snippet", "")

                    if not isinstance(title, str) or not isinstance(snippet, str):
                        continue  # Ensure title and snippet are strings

                    # Calculate a relevance score
                    score = 0
                    if query.lower() in title.lower():
                        score += 2
                    if query.lower() in snippet.lower():
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

async def extract():
    """Fetch URLs, configure the crawler, and extract structured information in parallel."""

    query = sys.argv[1]
    
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

    # Save URLs to sources.txt with query as subheading
    with open("./data/sources.txt", "a", encoding='utf-8') as f:
        f.write(f"\n## {query}\n")
        for url in urls:
            f.write(f"- {url}\n")
        f.write("\n")  # Add extra newline for readability

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

        
asyncio.run(extract())