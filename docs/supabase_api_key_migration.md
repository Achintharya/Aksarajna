# Supabase API Key Migration Guide

## From Legacy JWT to New API Keys with ES256 Signing

### Migration Overview

This document outlines the migration from Supabase's legacy JWT authentication model to the new API key system with ES256 signing keys.

**Migration Status**: 🟡 In Progress

### Legacy Keys (To Be Deprecated)

- `SUPABASE_ANON_KEY` - Anonymous/public key (JWT)
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key (JWT)
- `SUPABASE_JWT_SECRET` - Shared secret for HS256 signing

### New Keys (Target State)

- `SUPABASE_PUBLISHABLE_KEY` - Client-side key (starts with `sb_publishable_`)
- `SUPABASE_SECRET_KEY` - Server-side key (starts with `sb_secret_`)
- ES256 signing keys via JWKS endpoint

---

## 📋 Migration Checklist

### Phase 1: Preparation ⏳

- [ ] Access Supabase Dashboard
- [ ] Document current key usage in all environments
- [ ] Identify all services using legacy keys
- [ ] Set up secret management system (if not already in place)

### Phase 2: Create New Keys 🔑

- [ ] In Supabase Dashboard → Settings → API:
  - [ ] Generate publishable API key (`sb_publishable_*`)
  - [ ] Generate secret API key (`sb_secret_*`)
  - [ ] Store secret key in secure secret manager
- [ ] In Dashboard → Authentication → Signing Keys:
  - [ ] Create/Import ES256 signing key
  - [ ] Note the key ID (kid) for reference
  - [ ] DO NOT revoke legacy JWT secret yet

### Phase 3: Update Backend Code 💻

- [ ] Update environment variables:

  ```env
  # New keys (ADD - don't remove legacy yet)
  SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
  SUPABASE_SECRET_KEY=sb_secret_...
  
  # Keep legacy keys during migration
  SUPABASE_ANON_KEY=eyJ...
  SUPABASE_SERVICE_ROLE_KEY=eyJ...
  SUPABASE_JWT_SECRET=...
  ```

- [ ] Update `src/auth.py` to support both key types
- [ ] Update JWKS verification to support ES256
- [ ] Add fallback mechanism during migration

### Phase 4: Update Client Code 🌐

- [ ] Update frontend environment variables
- [ ] Replace `SUPABASE_ANON_KEY` with `SUPABASE_PUBLISHABLE_KEY`
- [ ] Update Supabase client initialization

### Phase 5: Testing 🧪

- [ ] Test authentication with new keys
- [ ] Test JWKS endpoint with ES256 tokens
- [ ] Run full integration test suite
- [ ] Monitor error logs for authentication failures

### Phase 6: Key Rotation 🔄

- [ ] In Supabase Dashboard, rotate signing keys
- [ ] Set ES256 key as primary
- [ ] Wait for token TTL + safety margin (typically 1-2 hours)
- [ ] Monitor for any authentication issues

### Phase 7: Cleanup 🧹

- [ ] Remove legacy keys from environment variables
- [ ] Remove legacy key handling from code
- [ ] Revoke legacy keys in Supabase Dashboard
- [ ] Update all documentation

---

## 🔐 Security Requirements

### Secret Management

1. **NEVER** commit secret keys to repository
2. Store `sb_secret_*` keys in:
   - Production: Environment variables or secret manager (e.g., AWS Secrets Manager, Vault)
   - Development: Local `.env` file (git-ignored)
3. Only use `sb_publishable_*` keys in client-side code

### Key Rotation Policy

- Rotate secret keys every 90 days
- Maintain key rotation logs for audit
- Test key rotation in staging before production

---

## 📝 Code Changes Required

### 1. Environment Configuration

```python
# config/.env (DO NOT COMMIT)
SUPABASE_PROJECT_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
```

### 2. Backend Authentication (src/auth.py)

```python
# Support both legacy and new keys during migration
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Fallback

# Use new key if available, fallback to legacy
API_KEY = SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY
```

### 3. JWKS Verification Updates

```python
# Update to support ES256 algorithm
algorithms = ["ES256", "RS256", "HS256"]  # Support all during migration
```

### 4. Frontend Updates (if applicable)

```javascript
// Use publishable key instead of anon key
const supabase = createClient(
  process.env.SUPABASE_PROJECT_URL,
  process.env.SUPABASE_PUBLISHABLE_KEY
)
```

---

## 🚨 Rollback Plan

If issues occur during migration:

1. **Immediate Rollback**:
   - Revert to using legacy keys
   - Keep both key sets active during transition

2. **Gradual Rollback**:
   - Monitor specific endpoints for failures
   - Route traffic based on authentication success

3. **Emergency Contacts**:
   - Supabase Support: <support@supabase.com>
   - Internal escalation: [Add your team contacts]

---

## 📊 Migration Timeline

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Preparation | 1 day | TBD | TBD | ⏳ |
| Create New Keys | 1 hour | TBD | TBD | ⏳ |
| Update Backend | 2 days | TBD | TBD | ⏳ |
| Update Client | 1 day | TBD | TBD | ⏳ |
| Testing | 2 days | TBD | TBD | ⏳ |
| Key Rotation | 4 hours | TBD | TBD | ⏳ |
| Cleanup | 1 day | TBD | TBD | ⏳ |

---

## 📚 References

- [Supabase API Keys Documentation](https://supabase.com/docs/guides/api)
- [JWT to API Keys Migration Guide](https://supabase.com/docs/guides/platform/migrating-to-new-api-keys)
- [ES256 vs HS256 Comparison](https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/)
- [JWKS Endpoint Documentation](https://supabase.com/docs/guides/auth/jwks)

---

## ✅ Verification Steps

After migration, verify:

1. **Authentication Works**:

   ```bash
   curl -H "Authorization: Bearer <token>" \
        -H "apikey: sb_secret_..." \
        https://your-project.supabase.co/rest/v1/your-endpoint
   ```

2. **JWKS Endpoint Returns ES256 Keys**:

   ```bash
   curl https://your-project.supabase.co/auth/v1/.well-known/jwks.json
   ```

3. **Token Verification**:
   - Decode a JWT and verify algorithm is ES256
   - Verify signature with public key from JWKS

---

## 📝 Audit Log

| Date | Action | Performed By | Notes |
|------|--------|--------------|-------|
| TBD | Migration Started | - | Initial setup |
| TBD | New Keys Created | - | - |
| TBD | Backend Updated | - | - |
| TBD | Testing Complete | - | - |
| TBD | Migration Complete | - | - |

---

**Document Version**: 1.0.0  
**Last Updated**: October 28, 2025  
**Next Review**: After migration completion
