import asyncio
import os
import json
import time
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from duckduckgo_search import DDGS
import time

load_dotenv(dotenv_path='./config/.env')

class PageSummary(BaseModel):
    summary: str = Field(..., description="Detailed page summary realted to query")
    
async def website_search(query: str, max_results: int = 5):

    try:
        with DDGS() as search:
            results = search.text(query, max_results=5)
            urls = [result["href"] for result in results if "href" in result]
            return list(urls)
    except Exception as e:
        print(f"Search failed: {e}")
        return []


# async def website_search(query: str, max_results: int = 9):
#     headers = {"Content-Type": "application/json", "X-API-KEY": os.getenv("SERPER_API_KEY")}
#     payload = {"q": query, "gl": "in", "num": max_results}  # Fetch extra results for better filtering

#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post("https://google.serper.dev/search", json=payload, headers=headers) as response:
#                 data = await response.json()

#                 # Extracting relevant results
#                 results = []
#                 for result in data.get("organic", []):
#                     if "link" in result and "youtube.com" not in result["link"] and "youtu.be" not in result["link"]:
#                         score = 0
#                         if query.lower() in result.get("title", "").lower():
#                             score += 2
#                         if query.lower() in result.get("snippet", "").lower():
#                             score += 1
#                         results.append((score, result["link"]))

#                 # Sort results by relevance (highest score first)
#                 results.sort(reverse=True, key=lambda x: x[0])

#                 await random_delay()
#                 return [link for _, link in results[:max_results]]

#     except Exception as e:
#         print(f"Search failed: {e}")
#         return []



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

async def extract(query: str):
    """Fetch URLs, configure the crawler, and extract structured information in parallel."""
    query=input("Enter search query: ")
    urls = await website_search(query)
    
    if not urls:
        print("No URLs found.")
        return

    browser_config = BrowserConfig(headless=True, verbose=True)

    extraction_strategy = LLMExtractionStrategy(
        provider="mistral/mistral-small-latest",
        api_token=os.getenv("MISTRAL_API_KEY"),
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
        print(f"Extracted Content: {urls}")
        
asyncio.run(extract(query=str))