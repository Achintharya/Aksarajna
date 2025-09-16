# Sources.md API Documentation

## Overview
The Varnika API provides endpoints to manage the `sources.md` file from the frontend. This allows users to view, edit, append to, and clear research sources dynamically.

## Endpoints

### 1. GET /api/articles/sources.md
**Description**: Retrieve the current content of sources.md file

**Method**: `GET`
**URL**: `http://localhost:8001/api/articles/sources.md`
**Headers**: None required

**Response**:
- **Content-Type**: `text/plain; charset=utf-8`
- **Body**: Raw markdown content of sources.md file
- **Cache Headers**: No-cache headers to ensure fresh data

**Example**:
```bash
curl -X GET http://localhost:8001/api/articles/sources.md
```

**Response Example**:
```markdown
# Research Sources

## Python Resources
- [https://python.org](https://python.org)
- [https://docs.python.org](https://docs.python.org)
```

---

### 2. PUT /api/sources
**Description**: Replace the entire content of sources.md file

**Method**: `PUT`
**URL**: `http://localhost:8001/api/sources`
**Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "content": "string"
}
```

**Response**:
```json
{
  "message": "Sources updated successfully",
  "content_length": 180,
  "timestamp": "2025-09-16T20:55:41.603393"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8001/api/sources \
  -H "Content-Type: application/json" \
  -d '{"content": "# My Sources\n\n## Topic\n- [https://example.com](https://example.com)"}'
```

**Features**:
- ✅ **Atomic operations** - Thread-safe writing
- ✅ **Automatic backups** - Creates timestamped backup before update
- ✅ **Cross-platform** - Works on Windows, Mac, Linux

---

### 3. POST /api/sources/append
**Description**: Append a new section to sources.md file

**Method**: `POST`
**URL**: `http://localhost:8001/api/sources/append`
**Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "query": "string",
  "urls": ["string", "string", ...]
}
```

**Response**:
```json
{
  "message": "Added 3 sources for 'Python Resources'",
  "query": "Python Resources",
  "urls_added": 3,
  "timestamp": "2025-09-16T20:55:45.710258"
}
```

**Example**:
```bash
curl -X POST http://localhost:8001/api/sources/append \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python Resources",
    "urls": [
      "https://python.org",
      "https://docs.python.org",
      "https://pypi.org"
    ]
  }'
```

**Generated Format**:
```markdown
## Python Resources
- [https://python.org](https://python.org)
- [https://docs.python.org](https://docs.python.org)
- [https://pypi.org](https://pypi.org)

```

---

### 4. DELETE /api/sources
**Description**: Clear the entire sources.md file

**Method**: `DELETE`
**URL**: `http://localhost:8001/api/sources`
**Headers**: None required

**Response**:
```json
{
  "message": "Sources cleared successfully",
  "timestamp": "2025-09-16T20:55:49.804740"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8001/api/sources
```

**Features**:
- ✅ **Backup created** - Creates backup before clearing
- ✅ **Atomic operation** - Thread-safe clearing

---

### 5. POST /api/extract/urls
**Description**: Extract content from a list of custom URLs and optionally save to sources.md

**Method**: `POST`
**URL**: `http://localhost:8001/api/extract/urls`
**Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "urls": ["string", "string", ...],
  "query": "string (optional)",
  "save_to_sources": boolean (optional)
}
```

**Response**:
```json
{
  "job_id": "8bb606b7-0086-49d7-9aa3-a724184aaad3",
  "message": "Content extraction started for 3 URLs"
}
```

**Example**:
```bash
curl -X POST http://localhost:8001/api/extract/urls \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "https://www.python.org/about/",
      "https://fastapi.tiangolo.com/"
    ],
    "query": "AI and Python Development",
    "save_to_sources": true
  }'
```

**Job Result Format**:
```json
{
  "total_urls": 3,
  "successful_extractions": 3,
  "failed_extractions": 0,
  "query": "AI and Python Development",
  "saved_to_sources": true,
  "extracted_data": [
    {
      "summary": "Content from URL about query...",
      "error": false
    }
  ]
}
```

**Features**:
- ✅ **Asynchronous processing** - Returns job ID for status tracking
- ✅ **URL validation** - Validates HTTP/HTTPS URLs
- ✅ **Content extraction** - Extracts and summarizes web content
- ✅ **Optional sources saving** - Can save URLs to sources.md
- ✅ **Progress tracking** - Real-time job status updates
- ✅ **Error handling** - Graceful handling of failed extractions

---

## Frontend Integration

### JavaScript Examples

#### 1. Get Sources
```javascript
async function getSources() {
  const response = await fetch('/api/articles/sources.md');
  const content = await response.text();
  return content;
}
```

#### 2. Update Sources
```javascript
async function updateSources(newContent) {
  const response = await fetch('/api/sources', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content: newContent })
  });
  return await response.json();
}
```

#### 3. Append Sources
```javascript
async function appendSources(query, urls) {
  const response = await fetch('/api/sources/append', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, urls })
  });
  return await response.json();
}
```

#### 4. Clear Sources
```javascript
async function clearSources() {
  const response = await fetch('/api/sources', {
    method: 'DELETE'
  });
  return await response.json();
}
```

#### 5. Extract Content from URLs
```javascript
async function extractFromUrls(urls, query = "Custom URLs", saveToSources = true) {
  const response = await fetch('/api/extract/urls', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      urls, 
      query, 
      save_to_sources: saveToSources 
    })
  });
  
  const jobData = await response.json();
  
  // Poll job status
  return new Promise((resolve, reject) => {
    const pollStatus = async () => {
      try {
        const statusResponse = await fetch(`/api/jobs/${jobData.job_id}`);
        const status = await statusResponse.json();
        
        if (status.status === 'completed') {
          resolve(status.result);
        } else if (status.status === 'failed') {
          reject(new Error(status.error));
        } else {
          // Continue polling
          setTimeout(pollStatus, 2000);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    pollStatus();
  });
}

// Usage example:
// const result = await extractFromUrls([
//   'https://example.com',
//   'https://another-site.com'
// ], 'My Research Topic');
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Success
- **400 Bad Request**: Invalid request body
- **500 Internal Server Error**: Server error

**Error Response Format**:
```json
{
  "detail": "Error message description"
}
```

---

## Security Features

### Atomic Operations
- **Thread-safe**: Multiple concurrent requests handled safely
- **Data integrity**: Atomic operations prevent corruption
- **Backup system**: Automatic backups before modifications

### File Locking
- **Cross-platform locking**: Uses appropriate locking mechanism per OS
- **Deadlock prevention**: Timeout mechanisms and proper cleanup
- **Graceful fallbacks**: Continues operation if locking fails

### Cache Control
- **No-cache headers**: Ensures frontend gets fresh data
- **ETag support**: Efficient cache validation
- **Last-Modified headers**: Proper HTTP caching

---

## Testing

Use the provided test script to verify all endpoints:

```bash
python test_api.py
```

**Expected Output**:
```
🎯 Overall: 6/6 tests passed
```

---

## Backup Management

Backups are automatically created in `./data/.backups/` with format:
- `sources_YYYYMMDD_HHMMSS.md`
- Only last 10 backups are kept
- Automatic cleanup of old backups

**Example Backup Files**:
```
./data/.backups/
├── sources_20250916_205541.md
├── sources_20250916_205545.md
└── sources_20250916_205549.md
