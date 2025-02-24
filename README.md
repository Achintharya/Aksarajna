# Integrated Web Context and AI Writing Tool

This project combines a web context extraction tool and an AI-powered writing assistant. It searches for websites related to a given query, crawls the URLs, extracts structured information, and generates responses based on a given context and writing style.

## Features

### Web Context Extractor

- **Website Search**: Uses DuckDuckGo to search for websites related to a given query.
- **Web Crawling**: Utilizes an asynchronous web crawler to fetch and process multiple URLs concurrently.
- **Content Extraction**: Employs a language model-based strategy to extract structured information from web pages.
- **Rate Limiting Handling**: Implements exponential backoff for handling HTTP 429 (Too Many Requests) responses.
- **Environment Configuration**: Loads configuration from a `.env` file.

### AI Writer

- **Contextual Input**: Accepts context from a text file or an image.
- **Writing Style Imitation**: Uses a predefined writing style to generate responses.
- **Save Responses**: Allows saving generated responses to a file.
- **Interactive CLI**: Provides an interactive command-line interface for user interaction.

## How It Works

1. **Web Context Extraction**:

   - The tool initiates a search using DuckDuckGo to find websites related to the user's query.
   - It then uses an asynchronous web crawler to visit the URLs obtained from the search results.
   - The crawler fetches the web pages and processes them concurrently to improve efficiency.
   - A language model-based extraction strategy is applied to extract structured information from the fetched web pages.
   - The extracted information is saved to a file for further use or analysis.

2. **AI Writing Assistant**:
   - The program reads context from a specified file or image.
   - It uses the `ollama` library to generate responses based on the context and writing style.
   - Users can interact with the program through a command-line interface, providing queries and receiving AI-generated responses.
