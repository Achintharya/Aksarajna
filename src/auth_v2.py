#!/usr/bin/env python3
"""
Authentication module for Supabase JWT verification using JWKS
Supports both legacy JWT keys and new API keys with ES256 signing
"""

import os
import time
import logging
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_paths = [
    'config/.env',
    '../config/.env',
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'),
    '.env'
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        env_loaded = True
        logger.info(f"Loaded environment variables from: {env_path}")
        break

if not env_loaded:
    logger.info("No .env file found, using system environment variables (production mode)")
    load_dotenv()

# Supabase configuration - Support both legacy and new keys
SUPABASE_PROJECT_URL = os.getenv('SUPABASE_PROJECT_URL')

# New API Keys (preferred)
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')

# Legacy Keys (fallback during migration)
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

# Determine which keys to use
USE_NEW_KEYS = bool(SUPABASE_SECRET_KEY and SUPABASE_PUBLISHABLE_KEY)
if USE_NEW_KEYS:
    logger.info("Using new Supabase API keys (sb_secret_*, sb_publishable_*)")
    API_KEY_FOR_SERVER = SUPABASE_SECRET_KEY
    API_KEY_FOR_CLIENT = SUPABASE_PUBLISHABLE_KEY
else:
    logger.warning("Using legacy Supabase JWT keys - Migration to new keys recommended")
    API_KEY_FOR_SERVER = SUPABASE_SERVICE_ROLE_KEY
    API_KEY_FOR_CLIENT = SUPABASE_ANON_KEY

# Validate required configuration
if not SUPABASE_PROJECT_URL:
    error_msg = "SUPABASE_PROJECT_URL environment variable is required"
    logger.error(error_msg)
    if os.getenv('RENDER'):
        logger.error("Running on Render: Please set SUPABASE_PROJECT_URL in Render dashboard")
    raise ValueError(error_msg)

if not API_KEY_FOR_SERVER:
    error_msg = "Server API key is required (SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY)"
    logger.error(error_msg)
    raise ValueError(error_msg)

# Process legacy JWT secret if available
SUPABASE_JWT_SECRET_DECODED = None
if SUPABASE_JWT_SECRET:
    try:
        SUPABASE_JWT_SECRET_DECODED = base64.b64decode(SUPABASE_JWT_SECRET)
        logger.info(f"Decoded legacy JWT secret (length: {len(SUPABASE_JWT_SECRET_DECODED)} bytes)")
    except Exception as e:
        SUPABASE_JWT_SECRET_DECODED = SUPABASE_JWT_SECRET
        logger.info(f"Using JWT secret as-is: {e}")

# JWKS endpoint
SUPABASE_PROJECT_URL = SUPABASE_PROJECT_URL.rstrip('/')
JWKS_URL = f"{SUPABASE_PROJECT_URL}/auth/v1/.well-known/jwks.json"

# HTTP Bearer token scheme
security = HTTPBearer()

# JWKS cache
_jwks_cache = {
    'keys': None,
    'expires_at': 0
}

# Cache duration (10 minutes)
JWKS_CACHE_DURATION = 600

# Supported algorithms - ES256 preferred, with fallbacks
SUPPORTED_ALGORITHMS = ["ES256", "RS256", "HS256"]

async def fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Supabase with caching
    Supports both legacy and new API key formats
    """
    current_time = time.time()
    
    # Check cache validity
    if _jwks_cache['keys'] and current_time < _jwks_cache['expires_at']:
        logger.debug("Using cached JWKS")
        return _jwks_cache['keys']
    
    try:
        logger.info(f"Fetching JWKS from {JWKS_URL}")
        
        # Use appropriate headers based on key type
        headers = {
            "Content-Type": "application/json"
        }
        
        if USE_NEW_KEYS:
            # New API keys use different header format
            headers["apikey"] = API_KEY_FOR_SERVER
        else:
            # Legacy keys
            headers["apikey"] = API_KEY_FOR_SERVER
            headers["Authorization"] = f"Bearer {API_KEY_FOR_SERVER}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(JWKS_URL, headers=headers)
            response.raise_for_status()
            
        jwks_data = response.json()
        
        # Cache the JWKS
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        
        # Log key information
        keys = jwks_data.get('keys', [])
        logger.info(f"Fetched {len(keys)} keys from JWKS")
        for key in keys:
            alg = key.get('alg', 'unknown')
            kid = key.get('kid', 'unknown')
            logger.debug(f"  Key: alg={alg}, kid={kid[:8]}...")
        
        return jwks_data
        
    except httpx.TimeoutException:
        logger.error("Timeout while fetching JWKS")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable (timeout)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while fetching JWKS: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching JWKS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service error",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_signing_key_for_algorithm(token: str, jwks_data: Dict[str, Any], algorithm: str) -> Optional[str]:
    """
    Get the signing key for a JWT token from JWKS for a specific algorithm
    
    Args:
        token: JWT token string
        jwks_data: JWKS data
        algorithm: Algorithm to look for (ES256, RS256, etc.)
        
    Returns:
        Signing key for the token or None if not found
    """
    try:
        # Get token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        token_alg = unverified_header.get('alg')
        
        logger.debug(f"Token header: alg={token_alg}, kid={kid[:8] if kid else 'None'}...")
        
        # Look for matching key
        for key in jwks_data.get('keys', []):
            key_alg = key.get('alg')
            key_kid = key.get('kid')
            
            # Match by algorithm and optionally by kid
            if key_alg == algorithm:
                if not kid or key_kid == kid:
                    logger.debug(f"Found matching key: alg={key_alg}, kid={key_kid[:8] if key_kid else 'None'}...")
                    public_key = jwk.construct(key)
                    return public_key.to_pem().decode('utf-8')
        
        return None
        
    except Exception as e:
        logger.debug(f"Error getting signing key for {algorithm}: {str(e)}")
        return None

async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Supabase JWT token
    Supports ES256 (preferred), RS256, and HS256 (legacy) algorithms
    """
    # Inspect token without verification
    try:
        unverified = jwt.decode(token, key=None, options={"verify_signature": False})
        token_alg = jwt.get_unverified_header(token).get('alg')
        logger.info(f"Token algorithm: {token_alg}, aud: {unverified.get('aud')}")
    except Exception as e:
        logger.error(f"Failed to decode token header: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try JWKS-based verification first (ES256 and RS256)
    try:
        jwks_data = await fetch_jwks()
        
        if jwks_data.get('keys'):
            # Try algorithms in order of preference
            for algorithm in ["ES256", "RS256"]:
                signing_key = get_signing_key_for_algorithm(token, jwks_data, algorithm)
                if signing_key:
                    try:
                        logger.info(f"Attempting {algorithm} verification with JWKS")
                        payload = jwt.decode(
                            token,
                            signing_key,
                            algorithms=[algorithm],
                            options={
                                "verify_signature": True,
                                "verify_aud": False,  # Skip audience verification for flexibility
                                "verify_exp": True,
                                "verify_nbf": False,
                                "verify_iat": True,
                                "verify_iss": False,
                                "require_exp": True,
                                "require_iat": True,
                            }
                        )
                        
                        # Additional validation
                        if not validate_token_claims(payload):
                            continue
                            
                        logger.info(f"Successfully verified token with {algorithm}")
                        return payload
                        
                    except JWTError as e:
                        logger.debug(f"{algorithm} verification failed: {str(e)}")
                        continue
    
    except Exception as e:
        logger.warning(f"JWKS verification failed: {str(e)}")
    
    # Fallback to HS256 with legacy JWT secret
    if SUPABASE_JWT_SECRET_DECODED:
        try:
            logger.info("Attempting HS256 verification with legacy JWT secret")
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET_DECODED,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_aud": False,
                    "verify_exp": True,
                    "verify_nbf": False,
                    "verify_iat": True,
                    "verify_iss": False,
                    "require_exp": True,
                    "require_iat": True,
                }
            )
            
            if validate_token_claims(payload):
                logger.info("Successfully verified token with HS256 (legacy)")
                return payload
                
        except JWTError as e:
            logger.debug(f"HS256 verification failed: {str(e)}")
    
    # All verification methods failed
    logger.error("All token verification methods failed")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token verification failed",
        headers={"WWW-Authenticate": "Bearer"},
    )

def validate_token_claims(payload: Dict[str, Any]) -> bool:
    """
    Validate token claims for expiration and other requirements
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        True if claims are valid, False otherwise
    """
    current_time = time.time()
    
    # Check expiration
    exp = payload.get('exp')
    if exp and exp < current_time:
        logger.debug("Token has expired")
        return False
    
    # Check not before (if present)
    nbf = payload.get('nbf')
    if nbf and nbf > current_time:
        logger.debug("Token not yet valid")
        return False
    
    # Check for required user ID
    if not payload.get('sub'):
        logger.debug("Token missing user ID (sub)")
        return False
    
    return True

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = await verify_jwt_token(token)
    
    # Extract user information
    user_info = {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
        "aud": payload.get("aud"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "iss": payload.get("iss"),
        "app_metadata": payload.get("app_metadata", {}),
        "user_metadata": payload.get("user_metadata", {}),
    }
    
    if not user_info["id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    Optional dependency to get current user (doesn't raise error if no token)
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that requires admin role
    """
    user_role = current_user.get("role", "authenticated")
    app_metadata = current_user.get("app_metadata", {})
    
    # Check for admin role in multiple places
    is_admin = (
        user_role == "admin" or
        app_metadata.get("role") == "admin" or
        app_metadata.get("roles", []).count("admin") > 0
    )
    
    if not is_admin:
        logger.warning(f"Admin access denied for user: {current_user.get('email', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

# Utility functions
def get_api_key_type() -> str:
    """Get the type of API keys being used"""
    return "new" if USE_NEW_KEYS else "legacy"

def create_auth_headers(token: str) -> Dict[str, str]:
    """Create authorization headers for API requests"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Add API key header if using new keys
    if USE_NEW_KEYS:
        headers["apikey"] = API_KEY_FOR_SERVER
    
    return headers

def extract_user_id(current_user: Dict[str, Any]) -> str:
    """Extract user ID from current user info"""
    return current_user["id"]

def extract_user_email(current_user: Dict[str, Any]) -> str:
    """Extract user email from current user info"""
    return current_user.get("email", "")

def is_token_expired(current_user: Dict[str, Any]) -> bool:
    """Check if the current user's token is expired"""
    exp = current_user.get("exp")
    if not exp:
        return True
    return exp < time.time()

# Health check for authentication service
async def auth_health_check() -> Dict[str, Any]:
    """
    Health check for authentication service
    """
    try:
        # Try to fetch JWKS
        jwks_data = await fetch_jwks()
        keys = jwks_data.get('keys', [])
        
        # Analyze key types
        key_algorithms = {}
        for key in keys:
            alg = key.get('alg', 'unknown')
            key_algorithms[alg] = key_algorithms.get(alg, 0) + 1
        
        return {
            "status": "healthy",
            "jwks_url": JWKS_URL,
            "keys_count": len(keys),
            "key_algorithms": key_algorithms,
            "api_key_type": get_api_key_type(),
            "es256_available": "ES256" in key_algorithms,
            "cache_expires_at": datetime.fromtimestamp(_jwks_cache['expires_at']).isoformat() if _jwks_cache['expires_at'] else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "jwks_url": JWKS_URL,
            "api_key_type": get_api_key_type(),
            "timestamp": datetime.now().isoformat()
        }

# Migration status check
def get_migration_status() -> Dict[str, Any]:
    """
    Get the current migration status
    """
    return {
        "migration_phase": "in_progress" if not USE_NEW_KEYS else "completed",
        "using_new_keys": USE_NEW_KEYS,
        "new_keys_configured": bool(SUPABASE_SECRET_KEY and SUPABASE_PUBLISHABLE_KEY),
        "legacy_keys_configured": bool(SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY),
        "jwt_secret_configured": bool(SUPABASE_JWT_SECRET),
        "recommendations": [] if USE_NEW_KEYS else [
            "Create new API keys in Supabase Dashboard",
            "Set SUPABASE_PUBLISHABLE_KEY and SUPABASE_SECRET_KEY environment variables",
            "Create ES256 signing key in Supabase Dashboard",
            "Test authentication with new keys before removing legacy keys"
        ]
    }
