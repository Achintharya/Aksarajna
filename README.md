# Varnika - AI-Powered Article Generation

Varnika is an AI-powered article generation platform that extracts web content, summarizes it, and generates high-quality articles based on the extracted information.

## Features

- Web content extraction from search queries or specific URLs
- Context summarization using advanced AI models
- Article generation in different formats (detailed, summarized, bullet points)
- Modern React frontend with real-time progress tracking (under construction).

## Architecture

The application is built with a modular architecture:

- **Frontend**: React with TypeScript, Bootstrap for styling
- **Backend**: Flask with Socket.IO for real-time updates
- **AI Components**: 
  - Web context extraction using crawl4ai
  - Context summarization using Groq API
  - Article writing using Mistral API

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for:
  - Mistral AI
  - Groq
  - Serper (optional, for enhanced web search)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/varnika.git
   cd varnika
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. Create a `.env` file in the config directory:
   ```bash
   cp config/.env.example config/.env
   ```

5. Edit the `.env` file and add your API keys:
   ```
   MISTRAL_API_KEY=your_mistral_api_key
   GROQ_API_KEY=your_groq_api_key
   SERPER_API_KEY=your_serper_api_key
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
