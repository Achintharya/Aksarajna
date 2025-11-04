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

# Supabase configuration - New API Keys Only
SUPABASE_PROJECT_URL = os.getenv('SUPABASE_PROJECT_URL')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')

# Load HS256 verification keys once at module level
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

# Set API keys for use
API_KEY_FOR_SERVER = SUPABASE_SECRET_KEY
API_KEY_FOR_CLIENT = SUPABASE_PUBLISHABLE_KEY
USE_NEW_KEYS = True

logger.info("Using new Supabase API keys (sb_secret_*, sb_publishable_*)")

# Validate required configuration
if not SUPABASE_PROJECT_URL:
    error_msg = "SUPABASE_PROJECT_URL environment variable is required"
    logger.error(error_msg)
    if os.getenv('RENDER'):
        logger.error("Running on Render: Please set SUPABASE_PROJECT_URL in Render dashboard")
    raise ValueError(error_msg)

if not API_KEY_FOR_SERVER:
    error_msg = "SUPABASE_SECRET_KEY environment variable is required"
    logger.error(error_msg)
    raise ValueError(error_msg)

if not API_KEY_FOR_CLIENT:
    error_msg = "SUPABASE_PUBLISHABLE_KEY environment variable is required"
    logger.error(error_msg)
    raise ValueError(error_msg)

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

# Known ES256 key for this project (hardcoded as fallback)
KNOWN_ES256_KEY = {
    "x": "D4CUqMVV0-g_eler2HWk-X1gT_WDO1sWKX7FxxACjgI",
    "y": "l11q0r-HDj9VRv0PmT_Ky1QDmJc28fQt6kyh6ff5w7M",
    "alg": "ES256",
    "crv": "P-256",
    "ext": True,
    "kid": "f9a4bdc8-48ad-4084-9dfa-4cd6f7747d43",
    "kty": "EC",
    "key_ops": ["verify"]
}

async def fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Supabase with caching
    JWKS endpoint is public and doesn't require authentication
    """
    current_time = time.time()
    
    # Check cache validity
    if _jwks_cache['keys'] and current_time < _jwks_cache['expires_at']:
        logger.debug("Using cached JWKS")
        return _jwks_cache['keys']
    
    try:
        logger.info(f"Fetching JWKS from {JWKS_URL}")
        
        # JWKS endpoint is public, no authentication needed
        headers = {
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(JWKS_URL, headers=headers)
            response.raise_for_status()
            
        jwks_data = response.json()
        
        # If no keys found or error, use the known ES256 key as fallback
        if not jwks_data.get('keys'):
            logger.warning("No keys in JWKS response, using known ES256 key")
            jwks_data = {'keys': [KNOWN_ES256_KEY]}
        
        # Cache the JWKS
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        
        # Log key information
        keys = jwks_data.get('keys', [])
        logger.info(f"Fetched {len(keys)} keys from JWKS")
        for key in keys:
            alg = key.get('alg', 'unknown')
            kid = key.get('kid', 'unknown')
            logger.info(f"  Key: alg={alg}, kid={kid[:8]}...")
        
        return jwks_data
        
    except httpx.TimeoutException:
        logger.error("Timeout while fetching JWKS, using known ES256 key")
        # Use known key as fallback
        jwks_data = {'keys': [KNOWN_ES256_KEY]}
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        return jwks_data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while fetching JWKS: {e.response.status_code}, using known ES256 key")
        # Use known key as fallback
        jwks_data = {'keys': [KNOWN_ES256_KEY]}
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        return jwks_data
    except Exception as e:
        logger.error(f"Unexpected error while fetching JWKS: {str(e)}, using known ES256 key")
        # Use known key as fallback
        jwks_data = {'keys': [KNOWN_ES256_KEY]}
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        return jwks_data

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

async def verify_via_supabase_api(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify token via Supabase Auth API endpoint (recommended approach)
    This delegates verification to Supabase and avoids local secret management
    """
    if not SUPABASE_SERVICE_ROLE_KEY and not API_KEY_FOR_SERVER:
        logger.debug("No service role key available for Supabase API verification")
        return None
    
    try:
        logger.info("Attempting token verification via Supabase Auth API")
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY or API_KEY_FOR_SERVER
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SUPABASE_PROJECT_URL}/auth/v1/user",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info("Successfully verified token via Supabase Auth API")
                
                # Convert Supabase API response to our expected format
                return {
                    "sub": user_data.get("id"),
                    "email": user_data.get("email"),
                    "role": user_data.get("role", "authenticated"),
                    "aud": user_data.get("aud"),
                    "exp": user_data.get("exp"),
                    "iat": user_data.get("iat"),
                    "iss": user_data.get("iss"),
                    "app_metadata": user_data.get("app_metadata", {}),
                    "user_metadata": user_data.get("user_metadata", {}),
                }
            elif response.status_code == 401:
                logger.warning("Token rejected by Supabase Auth API (401)")
                return None
            else:
                logger.warning(f"Supabase Auth API returned {response.status_code}: {response.text}")
                return None
                
    except httpx.TimeoutException:
        logger.warning("Timeout while verifying token via Supabase Auth API")
        return None
    except Exception as e:
        logger.warning(f"Error verifying token via Supabase Auth API: {str(e)}")
        return None

async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Supabase JWT token
    Tries multiple verification methods:
    1. Supabase Auth API (recommended, delegates to Supabase)
    2. JWKS-based verification (ES256/RS256)
    3. HS256 with local secrets (fallback)
    """
    # Try Supabase Auth API first (most secure, future-proof)
    api_payload = await verify_via_supabase_api(token)
    if api_payload:
        return api_payload
    # Inspect token without verification
    try:
        unverified = jwt.decode(token, key=None, options={"verify_signature": False})
        token_alg = jwt.get_unverified_header(token).get('alg')
        token_kid = jwt.get_unverified_header(token).get('kid')
        logger.info(f"Token algorithm: {token_alg}, kid: {token_kid}, aud: {unverified.get('aud')}, sub: {unverified.get('sub')}")
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
            # Prioritize the token's algorithm, then try others
            algorithms_to_try = []
            if token_alg in ["ES256", "RS256"]:
                algorithms_to_try.append(token_alg)
            algorithms_to_try.extend([alg for alg in ["ES256", "RS256"] if alg != token_alg])
            
            for algorithm in algorithms_to_try:
                signing_key = get_signing_key_for_algorithm(token, jwks_data, algorithm)
                if signing_key:
                    try:
                        logger.info(f"Attempting {algorithm} verification with JWKS (key found)")
                        
                        # More lenient verification options for Supabase JWTs
                        payload = jwt.decode(
                            token,
                            signing_key,
                            algorithms=[algorithm],
                            options={
                                "verify_signature": True,
                                "verify_aud": False,  # Supabase uses different audiences
                                "verify_exp": True,
                                "verify_nbf": False,
                                "verify_iat": False,  # Some Supabase tokens don't have iat
                                "verify_iss": False,  # Issuer verification can be flexible
                                "require_exp": True,
                                "require_iat": False,  # Don't require iat
                            }
                        )
                        
                        # Additional validation - more lenient
                        if not validate_token_claims(payload):
                            logger.warning(f"Token claims validation failed for {algorithm}")
                            continue
                            
                        logger.info(f"Successfully verified token with {algorithm}")
                        return payload
                        
                    except JWTError as e:
                        logger.warning(f"{algorithm} verification failed: {str(e)}")
                        continue
                else:
                    logger.warning(f"No signing key found for {algorithm}")
    
    except Exception as e:
        logger.error(f"JWKS verification error: {str(e)}")
    
    # HS256 fallback for standard Supabase access tokens
    # Most Supabase tokens are HS256 signed with the project JWT secret
    if token_alg == "HS256":
        # Prioritize service role key if present
        if SUPABASE_SERVICE_ROLE_KEY:
            try:
                logger.info("Attempting HS256 verification using SUPABASE_SERVICE_ROLE_KEY (priority)")
                
                # For HS256, the key might be base64 encoded
                try:
                    decoded_key = base64.b64decode(SUPABASE_SERVICE_ROLE_KEY)
                    secret_key = decoded_key
                    logger.debug("Successfully base64 decoded service role key")
                except Exception as e:
                    # Use as-is if not base64
                    secret_key = SUPABASE_SERVICE_ROLE_KEY
                    logger.debug(f"Using service role key as-is (base64 decode failed: {type(e).__name__})")
                
                payload = jwt.decode(
                    token,
                    secret_key,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_aud": False,  # Supabase uses different audiences
                        "verify_exp": True,
                        "verify_nbf": False,
                        "verify_iat": False,
                        "verify_iss": False,
                        "require_exp": True,
                        "require_iat": False,
                    }
                )
                
                if validate_token_claims(payload):
                    logger.info("Successfully verified token with HS256 using service role key")
                    return payload
                else:
                    logger.warning("HS256 token claims validation failed")
                    
            except JWTError as e:
                logger.warning(f"HS256 verification with service role key failed: {str(e)}")
        
        # Try with the secret key (in case it contains the JWT secret)
        if SUPABASE_SECRET_KEY and SUPABASE_SECRET_KEY != SUPABASE_SERVICE_ROLE_KEY:
            try:
                logger.info("Attempting HS256 verification using SUPABASE_SECRET_KEY")
                
                # For HS256, the key might be base64 encoded
                try:
                    decoded_key = base64.b64decode(SUPABASE_SECRET_KEY)
                    secret_key = decoded_key
                    logger.debug("Successfully base64 decoded secret key")
                except Exception as e:
                    # Use as-is if not base64
                    secret_key = SUPABASE_SECRET_KEY
                    logger.debug(f"Using secret key as-is (base64 decode failed: {type(e).__name__})")
                
                payload = jwt.decode(
                    token,
                    secret_key,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_aud": False,
                        "verify_exp": True,
                        "verify_nbf": False,
                        "verify_iat": False,
                        "verify_iss": False,
                        "require_exp": True,
                        "require_iat": False,
                    }
                )
                
                if validate_token_claims(payload):
                    logger.info("Successfully verified token with HS256 using secret key")
                    return payload
                else:
                    logger.warning("HS256 token claims validation failed with secret key")
                    
            except JWTError as e:
                logger.warning(f"HS256 verification with secret key failed: {str(e)}")
        
        # Try with the JWT secret environment variable if available
        if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET not in [SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SECRET_KEY]:
            try:
                logger.info("Attempting HS256 verification using SUPABASE_JWT_SECRET")
                
                # For HS256, the key might be base64 encoded
                try:
                    decoded_key = base64.b64decode(SUPABASE_JWT_SECRET)
                    secret_key = decoded_key
                    logger.debug("Successfully base64 decoded JWT secret")
                except Exception as e:
                    # Use as-is if not base64
                    secret_key = SUPABASE_JWT_SECRET
                    logger.debug(f"Using JWT secret as-is (base64 decode failed: {type(e).__name__})")
                
                payload = jwt.decode(
                    token,
                    secret_key,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_aud": False,
                        "verify_exp": True,
                        "verify_nbf": False,
                        "verify_iat": False,
                        "verify_iss": False,
                        "require_exp": True,
                        "require_iat": False,
                    }
                )
                
                if validate_token_claims(payload):
                    logger.info("Successfully verified token with HS256 using JWT secret")
                    return payload
                else:
                    logger.warning("HS256 token claims validation failed with JWT secret")
                    
            except JWTError as e:
                logger.warning(f"HS256 verification with JWT secret failed: {str(e)}")
    
    # All verification methods failed
    logger.error(f"Token verification failed - no valid signing key found for algorithm: {token_alg}")
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
    has_service_role = bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    has_jwt_secret = bool(os.getenv('SUPABASE_JWT_SECRET'))
    
    return {
        "migration_phase": "completed",
        "using_new_keys": True,
        "new_keys_configured": bool(SUPABASE_SECRET_KEY and SUPABASE_PUBLISHABLE_KEY),
        "hs256_support": True,  # Now supports HS256 tokens
        "es256_support": True,  # Also supports ES256 tokens
        "service_role_key_available": has_service_role,
        "jwt_secret_available": has_jwt_secret,
        "supported_algorithms": ["ES256", "RS256", "HS256"],
        "recommendations": []
    }
