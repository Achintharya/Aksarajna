# Varnika FastAPI Backend Documentation

## Overview

The Varnika FastAPI backend provides a RESTful API for AI-powered article generation. It supports asynchronous processing, job tracking, and comprehensive article management.

## Getting Started

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API keys in `config/.env`:
```env
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key
SERPER_API_KEY=your_serper_api_key
```

### Running the Server

```bash
python run_fastapi.py
```

The server will start on `http://localhost:8000`

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Core Endpoints

#### `GET /`
Returns API information and available endpoints.

#### `GET /health`
Health check endpoint for monitoring.

### Article Generation

#### `POST /api/generate`
Generate an article with the complete pipeline.

**Request Body:**
```json
{
  "query": "AI technology trends 2024",
  "article_type": "detailed",  // Options: "detailed", "summarized", "points"
  "filename": "ai_trends",      // Optional
  "skip_search": false          // Optional: Use existing context
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "message": "Article generation started for: AI technology trends 2024"
}
```

### Web Search

#### `POST /api/search`
Search and extract web content.

**Request Body:**
```json
{
  "query": "Python programming",
  "max_results": 5
}
```

### Job Management

#### `GET /api/jobs/{job_id}`
Get status of a specific job.

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "completed",  // Options: "pending", "processing", "completed", "failed"
  "message": "Article generated successfully",
  "progress": 100,
  "result": {
    "filename": "article.txt",
    "path": "./articles/article.txt",
    "query": "AI technology",
    "type": "detailed"
  },
  "error": null,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:00"
}
```

#### `GET /api/jobs`
List all jobs with pagination.

**Query Parameters:**
- `limit`: Number of results (default: 10)
- `offset`: Skip results (default: 0)

### Article Management

#### `GET /api/articles`
List all generated articles.

**Response:**
```json
{
  "articles": [
    {
      "filename": "article.txt",
      "size": 2048,
      "created": "2024-01-01T12:00:00",
      "modified": "2024-01-01T12:00:00"
    }
  ]
}
```

#### `GET /api/articles/{filename}`
Download a specific article.

#### `DELETE /api/articles/{filename}`
Delete a specific article.

### Context Management

#### `GET /api/context`
Get current context data (sources, extracted content, summarized context).

#### `POST /api/context/clear`
Clear all context data.

## Workflow Example

### Complete Article Generation

1. **Start generation job:**
```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Machine learning applications",
    "article_type": "detailed",
    "filename": "ml_applications"
  }'
```

2. **Check job status:**
```bash
curl "http://localhost:8000/api/jobs/{job_id}"
```

3. **Download generated article:**
```bash
curl "http://localhost:8000/api/articles/ml_applications.txt" -o article.txt
```

## Background Processing

The API uses FastAPI's `BackgroundTasks` for asynchronous processing:

1. **Web Extraction**: Searches and crawls relevant websites
2. **Summarization**: Processes extracted content using AI
3. **Article Generation**: Creates the final article

Each step updates the job status with progress information.

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `404`: Resource not found
- `422`: Validation error
- `500`: Internal server error

Error responses include detailed messages:
```json
{
  "detail": "Error description"
}
```

## Rate Limiting

The system automatically handles rate limiting:
- DuckDuckGo fallback to Serper API
- Exponential backoff for retries
- Graceful error handling

## CORS Configuration

CORS is enabled for all origins in development. For production, update the `allow_origins` in `src/fastapi_app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Generate article
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}'
```

### Using Python

```python
import requests

# Generate article
response = requests.post(
    "http://localhost:8000/api/generate",
    json={"query": "Python best practices"}
)
job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
print(status.json())
```

## Performance Considerations

- Background tasks prevent blocking
- Job status tracking for long operations
- Efficient file handling for articles
- Caching support for repeated queries

## Security Notes

1. **API Keys**: Store in environment variables
2. **File Access**: Restricted to articles directory
3. **Input Validation**: Pydantic models ensure type safety
4. **CORS**: Configure for production domains

## Deployment

For production deployment:

1. Use a production ASGI server:
```bash
gunicorn src.fastapi_app:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. Set environment variables:
```bash
export VARNIKA_ENV=production
```

3. Use a reverse proxy (nginx/Apache)

4. Enable HTTPS with SSL certificates

## Troubleshooting

### Common Issues

1. **Port already in use**: Change port in `run_fastapi.py`
2. **Module not found**: Ensure proper Python path
3. **API key errors**: Check `config/.env` file
4. **Slow processing**: Check API rate limits

### Logs

Check application logs in `logs/` directory for detailed error information.
