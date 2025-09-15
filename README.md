# Varnika - AI-Powered Article Generation System

An intelligent content generation system that automatically researches topics, extracts web content, and produces high-quality articles using AI.

## 🚀 Features

### Three-Step Pipeline
1. **Web Context Extraction** - Searches and extracts content from relevant websites
2. **Context Summarization** - Processes and summarizes the extracted information
3. **Article Generation** - Creates comprehensive articles based on the summarized context

### Smart Search Strategy
- **Primary Search**: DuckDuckGo (free, no API key required)
- **Fallback Search**: Serper API (when DuckDuckGo is rate-limited)
- **Automatic failover** between search providers
- **YouTube link filtering** for relevant content only

### AI-Powered Processing
- **Web Crawling**: Asynchronous crawling with Crawl4AI
- **Content Extraction**: LLM-based extraction using Mistral AI
- **Summarization**: Context processing with Groq's Llama model
- **Article Writing**: Professional content generation with Mistral

## 📋 Prerequisites

- Python 3.8 or higher
- API Keys (see Configuration section)

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/Achintharya/Varnika.git
cd Varnika
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API keys (see Configuration section)

## ⚙️ Configuration

### API Keys Setup

Create a `.env` file in the `config/` directory with your API keys:

```env
# Required for context summarization
GROQ_API_KEY=your_groq_api_key_here

# Required for article generation and web extraction
MISTRAL_API_KEY=your_mistral_api_key_here

# Optional: Used for web searches if DuckDuckGo fails
SERPER_API_KEY=your_serper_api_key_here
```

### Getting API Keys

- **Groq API**: Sign up at [console.groq.com](https://console.groq.com)
- **Mistral API**: Get your key from [console.mistral.ai](https://console.mistral.ai)
- **Serper API** (Optional): Register at [serper.dev](https://serper.dev)

## 🎯 Usage

### Full Pipeline Execution

Run all three steps automatically:

```bash
python src/main.py
```

You'll be prompted to:
1. Enter a search query
2. Wait for web extraction and summarization
3. Enter a filename for the generated article

### Individual Module Execution

#### 1. Web Context Extraction
```bash
python src/web_context_extract.py
```
- Searches for relevant URLs
- Extracts content from websites
- Saves to `data/context.json`

#### 2. Context Summarization
```bash
python src/context_summarizer.py
```
- Processes extracted content
- Creates readable summaries
- Saves to `data/context.txt`

#### 3. Article Generation
```bash
python src/article_writer.py [--type TYPE] [--filename FILENAME]
```

Options:
- `--type`: Article format (`detailed`, `summarized`, `points`)
- `--filename`: Output filename (without extension)

Example:
```bash
python src/article_writer.py --type detailed --filename my_article
```

### Testing the System

Run the test suite to verify all components:

```bash
python test_cli.py
```

## 📁 Project Structure

```
Varnika/
├── config/
│   ├── .env              # API keys configuration
│   └── .env.example      # Example configuration
├── data/
│   ├── context.json      # Raw extracted content
│   ├── context.txt       # Summarized context
│   ├── sources.txt       # URLs found during search
│   └── writing_style.txt # Writing style template
├── articles/             # Generated articles
├── src/
│   ├── web_context_extract.py  # Web search and extraction
│   ├── context_summarizer.py   # Content summarization
│   ├── article_writer.py       # Article generation
│   └── main.py                  # Full pipeline runner
└── test_cli.py           # Test suite
```

## 🔄 Search Flow

The web context extraction implements a robust two-tier search strategy:

1. **DuckDuckGo Search (Primary)**
   - Free, no API key required
   - Attempts first for all queries
   - Returns up to 5 results by default

2. **Serper API (Fallback)**
   - Activated when DuckDuckGo is rate-limited
   - Provides Google search results
   - Filters YouTube links automatically
   - Scores results by relevance

## 🐛 Troubleshooting

### Common Issues

**DuckDuckGo Rate Limiting**
- The system automatically falls back to Serper API
- Ensure your Serper API key is configured

**No URLs Found**
- Try a more specific search query
- Check your internet connection
- Verify API keys are correctly set

**API Key Errors**
- Ensure `.env` file is in the `config/` directory
- Verify API keys are valid and active
- Check API usage limits on provider dashboards

**File Not Found Errors**
- Run from the project root directory
- Ensure `data/` and `articles/` directories exist

### Logs

Check `logs/` directory for detailed error messages and debugging information.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

**Achintharya**

- GitHub: [@Achintharya](https://github.com/Achintharya)

## 🙏 Acknowledgments

- [Crawl4AI](https://github.com/unclecode/crawl4ai) for web crawling
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search) for search functionality
- [Mistral AI](https://mistral.ai) for content extraction and generation
- [Groq](https://groq.com) for context summarization
- [Serper](https://serper.dev) for Google search API
