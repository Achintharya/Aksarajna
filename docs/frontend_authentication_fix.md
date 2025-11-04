# Frontend Authentication Fix for Legacy Keys Disabled Error

## Problem
When users try to login on the frontend, they get "legacy keys are disabled" error because the frontend is using the old `anon` key format instead of the new `sb_publishable_*` key.

## Solution

### 1. Update Frontend Environment Variables

Replace the old keys in your frontend's `.env` or configuration:

**OLD (Legacy - Won't Work):**
```env
VITE_SUPABASE_URL=https://pvarvmjbazehivkiuosk.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJI...  # Old anon key format
```

**NEW (Required):**
```env
VITE_SUPABASE_URL=https://pvarvmjbazehivkiuosk.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...  # New publishable key format
```

### 2. Get Your New Publishable Key

You can find your new publishable key in:
1. Supabase Dashboard → Settings → API
2. Look for "Publishable anon key" (starts with `sb_publishable_`)
3. Copy this key to your frontend

### 3. Update Frontend Supabase Client Initialization

If your frontend code looks like this:
```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

Make sure `supabaseAnonKey` is using the new `sb_publishable_*` key.

### 4. Optional: Fetch Configuration from Backend

If you want the frontend to get configuration from the backend dynamically:

```javascript
// Frontend code to fetch config
async function getSupabaseConfig() {
  try {
    const response = await fetch('http://localhost:8000/api/config');
    const config = await response.json();
    
    if (config.error) {
      console.error('Config error:', config.message);
      return null;
    }
    
    return {
      url: config.supabaseUrl,
      anonKey: config.supabasePublishableKey // Use the new key
    };
  } catch (error) {
    console.error('Failed to fetch config:', error);
    return null;
  }
}

// Initialize Supabase with fetched config
const config = await getSupabaseConfig();
if (config) {
  const supabase = createClient(config.url, config.anonKey);
}
```

### 5. Backend API Config Endpoint

The backend now provides a `/api/config` endpoint that returns:
```json
{
  "supabaseUrl": "https://pvarvmjbazehivkiuosk.supabase.co",
  "supabaseAnonKey": "sb_publishable_...",
  "supabasePublishableKey": "sb_publishable_...",
  "apiUrl": "http://localhost:8000",
  "legacy_keys_disabled": true,
  "key_format": "new",
  "message": "Using new Supabase API keys (ES256 signing)"
}
```

## Key Points

1. **Legacy keys (old `anon` and `service_role` keys) are disabled** in your Supabase project
2. **You must use the new key format**:
   - Frontend: `sb_publishable_*` (public, safe for client-side)
   - Backend: `sb_secret_*` (secret, server-side only) or legacy `service_role` key for compatibility
3. **The Python backend works** because we configured it to use the `SUPABASE_SERVICE_ROLE_KEY` as a fallback
4. **The frontend fails** because it's still using the old `anon` key

## Testing

After updating the frontend keys:

1. Clear browser cache/storage
2. Restart your frontend development server
3. Try logging in again

The authentication should now work with the ES256-signed JWTs using the new key format.

## Environment Variables Summary

### Frontend (.env)
```env
VITE_SUPABASE_URL=https://pvarvmjbazehivkiuosk.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_xxx  # Get from Supabase Dashboard
```

### Backend (config/.env)
```env
SUPABASE_PROJECT_URL=https://pvarvmjbazehivkiuosk.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx  # Same as frontend anon key
SUPABASE_SECRET_KEY=sb_secret_xxx  # Server-side only
SUPABASE_SERVICE_ROLE_KEY=service_role_xxx  # Legacy key for Python client compatibility
