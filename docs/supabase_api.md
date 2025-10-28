# Supabase Storage API Documentation

## Overview

The Varnika API has been updated to use Supabase Storage for user-specific data isolation. All articles, sources, and writing styles are now stored in Supabase Storage with proper user authentication and isolation.

## Authentication

All endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

The JWT token is obtained from Supabase authentication and contains the user's ID for data isolation.

## Storage Architecture

### Supabase Storage Buckets

- `articles`: User articles stored as `{user_id}/articles/{filename}`
- `sources`: User sources stored as `{user_id}/sources/sources.md`
- `writing-styles`: User writing styles stored as `{user_id}/styles/writing_style.txt`

### Database Tables

- `articles`: Metadata for user articles with Row Level Security (RLS)

## API Endpoints

### Articles

#### List User Articles

```http
GET /api/articles
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "articles": [
    {
      "filename": "article_example_20250917.md",
      "size": 1024,
      "created": "2025-09-17T10:00:00Z",
      "modified": "2025-09-17T10:00:00Z",
      "title": "Example Article",
      "storage_path": "user123/articles/article_example_20250917.md"
    }
  ],
  "total_count": 1,
  "user_id": "user123",
  "storage": "supabase"
}
```

#### Get Article Content

```http
GET /api/articles/{filename}
Authorization: Bearer <jwt_token>
```

**Response:** Article content as plain text

#### Delete Article

```http
DELETE /api/articles/{filename}
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "message": "Article {filename} deleted successfully"
}
```

### Sources

#### Update Sources

```http
PUT /api/sources
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "content": "# My Sources\n\n## Topic 1\n- [URL 1](https://example.com)"
}
```

**Response:**

```json
{
  "message": "Sources updated successfully",
  "content_length": 45,
  "timestamp": "2025-09-17T10:00:00Z",
  "storage": "supabase"
}
```

#### Get Sources

```http
GET /api/articles/sources.md
Authorization: Bearer <jwt_token>
```

**Response:** Sources content as plain text

#### Clear Sources

```http
DELETE /api/sources
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "message": "Sources cleared successfully",
  "timestamp": "2025-09-17T10:00:00Z",
  "storage": "supabase"
}
```

### Writing Style

#### Get Writing Style

```http
GET /api/writing-style
Authorization: Bearer <jwt_token>
```

**Response:** Writing style content as plain text

#### Update Writing Style

```http
PUT /api/writing-style
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "content": "Write in a professional, informative tone..."
}
```

**Response:**

```json
{
  "message": "Writing style updated successfully",
  "content_length": 42,
  "timestamp": "2025-09-17T10:00:00Z",
  "storage": "supabase"
}
```

#### Clear Writing Style

```http
DELETE /api/writing-style
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "message": "Writing style cleared successfully",
  "timestamp": "2025-09-17T10:00:00Z",
  "storage": "supabase"
}
```

## Frontend Integration

### JavaScript Example

```javascript
// Get JWT token from Supabase
import { supabase } from './supabaseClient';

const getAuthHeaders = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token 
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
};

// Fetch user articles
const fetchArticles = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch('/api/articles', { headers });
  return response.json();
};

// Update sources
const updateSources = async (content) => {
  const headers = {
    ...await getAuthHeaders(),
    'Content-Type': 'application/json'
  };
  
  const response = await fetch('/api/sources', {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content })
  });
  
  return response.json();
};
```

## Error Handling

### HTTP Status Codes

- `200`: Success
- `401`: Unauthorized (invalid/missing JWT token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (article/resource not found)
- `500`: Internal Server Error

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### Authentication Errors

```json
{
  "detail": "Authorization header missing"
}
```

```json
{
  "detail": "Token has expired"
}
```

```json
{
  "detail": "Invalid token"
}
```

#### Resource Errors

```json
{
  "detail": "Article example.md not found"
}
```

## Migration from Local Storage

### Migration Script

Use the provided migration script to move existing files to Supabase:

```bash
# Preview migration
python migrate_to_supabase.py --dry-run

# Migrate with default user ID
python migrate_to_supabase.py

# Migrate with specific user ID
python migrate_to_supabase.py --user-id "your-user-id-here"
```

### Migration Process

1. **Backup**: Create backups of existing files
2. **Environment**: Set up Supabase environment variables
3. **Buckets**: Ensure storage buckets exist
4. **Database**: Create articles table with RLS
5. **Migrate**: Run migration script
6. **Verify**: Test API endpoints with authentication

## Security Features

### Row Level Security (RLS)

The `articles` table uses RLS to ensure users can only access their own data:

```sql
CREATE POLICY "Users can access own articles" ON articles
    FOR ALL USING (auth.uid() = user_id);
```

### Storage Policies

Supabase Storage buckets are configured as private with user-specific paths to prevent cross-user access.

### JWT Verification

- Uses Supabase JWKS for modern public key cryptography
- Automatic token expiration and refresh
- Comprehensive claim validation

## Performance Considerations

### Caching

- Articles can be cached for 5 minutes (Cache-Control: public, max-age=300)
- Sources and writing styles use cache-busting headers
- JWKS keys are cached for 10 minutes

### Database Queries

- Efficient queries with proper indexing on user_id
- Pagination support for large article lists
- Optimized metadata storage

## Development Setup

### Environment Variables

```bash
# Supabase Configuration
SUPABASE_PROJECT_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Existing API Keys
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key
SERPER_API_KEY=your_serper_api_key
```

### Database Schema

```sql
-- Create articles table
CREATE TABLE articles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    title TEXT,
    storage_path TEXT NOT NULL,
    content_length INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, filename)
);

-- Enable Row Level Security
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- Create policy for user access
CREATE POLICY "Users can access own articles" ON articles
    FOR ALL USING (auth.uid() = user_id);
```

### Storage Buckets

Create the following buckets in Supabase Storage:

- `articles` (private)
- `sources` (private)
- `writing-styles` (private)

## Testing

### Unit Tests

Test user isolation by creating multiple test users and verifying they cannot access each other's data.

### Integration Tests

Test the complete flow from authentication to file operations.

### Load Tests

Test performance with multiple concurrent users and large files.

## Deployment

### Production Checklist

1. ✅ Set up Supabase project
2. ✅ Configure environment variables
3. ✅ Create database tables and policies
4. ✅ Set up storage buckets
5. ✅ Run migration script
6. ✅ Test authentication flow
7. ✅ Verify user isolation
8. ✅ Monitor performance

### Monitoring

- Monitor Supabase Storage usage
- Track API response times
- Monitor authentication success rates
- Set up alerts for errors

## Support

For issues or questions:

1. Check the error logs for detailed error messages
2. Verify Supabase configuration and connectivity
3. Test authentication tokens and user permissions
4. Review storage bucket policies and RLS settings
