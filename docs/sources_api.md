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
