 # Integrated Web Context and AI Writing Tool

This project combines a web context extraction tool and an AI-powered writing assistant. It searches for websites related to a given query, crawls the URLs, extracts structured information, and generates responses based on a given context and writing style.

## Features

### Web Context Extractor

- **Website Search**: Uses DuckDuckGo/google_serper to search for websites related to a given query.
- **Web Crawling**: Utilizes an asynchronous web crawler to fetch and process multiple URLs concurrently.
- **Content Extraction**: Employs a language model-based strategy to extract structured information from web pages.
- **Rate Limiting Handling**: Implements exponential backoff for handling HTTP 429 (Too Many Requests) responses.
- **Environment Configuration**: Loads configuration from a `.env` file.
- **Caching**: Implements caching for search results to reduce redundant API calls.

### AI Writer

- **Contextual Input**: Accepts context from a text file or an image(based on model used).
- **Writing Style Imitation**: Uses a predefined writing style to generate responses.
- **Save Responses**: Allows saving generated responses to a file.
- **Interactive CLI**: Provides an interactive command-line interface for user interaction.
- **Progress Indicators**: Shows progress bars for long-running operations.

### General Improvements

- **Centralized Configuration**: Uses a central configuration module to manage settings across all scripts.
- **Comprehensive Logging**: Implements a proper logging system for better debugging and monitoring.
- **Error Handling**: Includes comprehensive error handling with user-friendly messages.
- **Command-Line Arguments**: Supports command-line arguments for flexible usage.
- **Concurrent Execution**: Allows running components concurrently for improved performance.

## How It Works

1. **Web Context Extraction**:

   - The tool initiates a search using DuckDuckGo/google_serper to find websites related to the user's query.
   - It then uses an asynchronous web crawler to visit the URLs obtained from the search results.
   - The crawler fetches the web pages and processes them concurrently to improve efficiency.
   - A language model-based extraction strategy is applied to extract structured information from the fetched web pages.
   - The extracted information is saved to a file for further use or analysis.

2. **Context Summarization**:
   - The tool reads the extracted context from the JSON file.
   - It uses the CrewAI framework with a language model to summarize the context.
   - The summarized context is saved to a text file for use by the article writer.

3. **AI Writing Assistant**:
   - The program reads context from the summarized context file.
   - It uses the `ollama` library to generate responses based on the context and writing style.
   - Users can interact with the program through a command-line interface, providing queries and receiving AI-generated responses.
   - The generated articles are saved to files in the articles directory.

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the `config` directory based on the provided `.env.example`:
   ```
   cp config/.env.example config/.env
   ```

4. Edit the `.env` file to add your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   MISTRAL_API_KEY=your_mistral_api_key_here
   SERPER_API_KEY=your_serper_api_key_here
   ```

## Usage

### Web UI

The easiest way to use the tool is through the web interface:

```
python src/web_ui.py
```

This will start a web server at http://localhost:5000 where you can:
- Enter a search query
- Select which components to run
- Monitor the progress with a real-time progress bar
- View logs as they are generated
- Access the results when the process completes

### Command Line Interface

#### Running the Complete Pipeline

To run the complete pipeline (extraction, summarization, and article writing) sequentially:

```
python src/main.py --all
```

To run the components concurrently:

```
python src/main.py --all --concurrent
```

#### Running Individual Components

To run only the web context extraction:

```
python src/main.py --extract --query "your search query"
```

To run only the context summarization:

```
python src/main.py --summarize
```

To run only the article writer:

```
python src/main.py --write
```

#### Direct Component Execution

You can also run each component directly:

```
python src/web_context_extract.py --query "your search query"
python src/context_summarizer.py
python src/article_writer.py --query "Write an article about..."
```

## Configuration

The project uses a centralized configuration system. Default settings are defined in `src/config.py`, but you can override them by modifying the configuration values directly or by setting environment variables in the `.env` file.

## Directory Structure

- `src/`: Contains the source code for the project
  - `main.py`: Main entry point for the application
  - `web_context_extract.py`: Web context extraction module
  - `context_summarizer.py`: Context summarization module
  - `article_writer.py`: Article writing module
  - `config.py`: Centralized configuration module
  - `web_ui.py`: Web interface module
- `config/`: Contains configuration files
  - `.env.example`: Example environment variables file
- `data/`: Contains data files
  - `context.json`: Extracted context in JSON format
  - `context.txt`: Summarized context in text format
  - `sources.txt`: List of sources used for context extraction
  - `writing_style.txt`: Example writing style for the article writer
- `articles/`: Contains generated articles
- `templates/`: Contains HTML templates for the web interface
- `static/`: Contains static files for the web interface
  - `css/`: CSS stylesheets
  - `js/`: JavaScript files
- `logs/`: Contains application logs
  - `application.log`: Main application log file

## Requirements

- Python 3.8+
- See `requirements.txt` for a complete list of dependencies
