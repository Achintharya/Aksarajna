# Varnika - AI-Powered Article Generation

Varnika is an AI-powered article generation platform that extracts web content, summarizes it, and generates high-quality articles based on the extracted information.

## Features

- Web content extraction from search queries or specific URLs
- Context summarization using advanced AI models
- Article generation in different formats (detailed, summarized, bullet points)
- Modern React frontend with real-time progress tracking
- API for programmatic access
- Subscription-based access model (optional)
- Containerized deployment with Docker

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

### Running the Application

#### Development Mode

1. Build and run the React frontend:
   ```bash
   python run_react_app.py
   ```

2. Open your browser and navigate to http://localhost:5000

#### Production Mode

1. Using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Open your browser and navigate to http://localhost:5000

## Subscription Model Setup

The application includes a subscription model that can be enabled in production:

1. Edit the `config/production.json` file:
   ```json
   {
     "subscription": {
       "enabled": true,
       "free_tier_limit": 5,
       "basic_tier_limit": 20,
       "premium_tier_limit": 100
     }
   }
   ```

2. Set up environment variables for authentication:
   ```
   JWT_SECRET_KEY=your_secure_jwt_secret
   PASSWORD_SALT=your_secure_password_salt
   ```

3. Implement a payment processor integration (see below)

### Payment Processor Integration

The subscription model is prepared for integration with payment processors like Stripe:

1. Create a new file `src/services/payment_service.py` with your payment processor integration
2. Update the auth service to use the payment service for subscription updates
3. Add payment webhook endpoints in the API routes

## API Usage

The application provides a RESTful API for programmatic access:

### Authentication

```bash
# Register a new user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "User Name", "password": "password"}'

# Login and get a token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Article Generation

```bash
# Generate an article
curl -X POST http://localhost:5000/api/article/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"query": "AI advancements", "article_type": "detailed"}'
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
