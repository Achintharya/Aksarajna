#!/usr/bin/env python3
"""
Authentication module for Supabase JWT verification using JWKS
"""

import os
import time
import logging
from typing import Optional, Dict, Any
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
# Try multiple possible paths for the .env file (for local development)
env_paths = [
    'config/.env',
    '../config/.env',
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'),
    '.env'  # Also try current directory
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
    load_dotenv()  # Load from system environment

# Supabase configuration from environment
SUPABASE_PROJECT_URL = os.getenv('SUPABASE_PROJECT_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')  # For HS256 fallback

if not SUPABASE_PROJECT_URL:
    # Print debug information for troubleshooting
    logger.error("SUPABASE_PROJECT_URL not found in environment variables")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Script directory: {os.path.dirname(__file__)}")
    logger.error(f"Available env vars starting with SUPABASE: {[k for k in os.environ.keys() if k.startswith('SUPABASE')]}")
    
    # In production, provide more helpful error message
    if os.getenv('RENDER'):  # Render sets this environment variable
        logger.error("Running on Render: Please set SUPABASE_PROJECT_URL in Render dashboard environment variables")
        raise ValueError("SUPABASE_PROJECT_URL environment variable must be set in Render dashboard")
    else:
        logger.error("Please ensure SUPABASE_PROJECT_URL is set in your .env file or system environment")
        raise ValueError("SUPABASE_PROJECT_URL environment variable is required")

if not SUPABASE_ANON_KEY:
    logger.error("SUPABASE_ANON_KEY not found in environment variables")
    if os.getenv('RENDER'):
        logger.error("Running on Render: Please set SUPABASE_ANON_KEY in Render dashboard environment variables")
        raise ValueError("SUPABASE_ANON_KEY environment variable must be set in Render dashboard")
    else:
        logger.error("Please ensure SUPABASE_ANON_KEY is set in your .env file or system environment")
        raise ValueError("SUPABASE_ANON_KEY environment variable is required")

# JWT_SECRET is optional but recommended for fallback
if not SUPABASE_JWT_SECRET:
    logger.warning("SUPABASE_JWT_SECRET not found - HS256 fallback will not be available")

# Remove trailing slash if present
SUPABASE_PROJECT_URL = SUPABASE_PROJECT_URL.rstrip('/')

# JWKS endpoint - Use correct Supabase JWKS URL
JWKS_URL = f"{SUPABASE_PROJECT_URL}/auth/v1/.well-known/jwks.json"

# HTTP Bearer token scheme
security = HTTPBearer()

# JWKS cache
_jwks_cache = {
    'keys': None,
    'expires_at': 0
}

# Cache duration (10 minutes)
JWKS_CACHE_DURATION = 600  # seconds

async def fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Supabase with caching
    
    Returns:
        JWKS dictionary
        
    Raises:
        HTTPException: If JWKS fetching fails
    """
    current_time = time.time()
    
    # Check if cache is still valid
    if _jwks_cache['keys'] and current_time < _jwks_cache['expires_at']:
        logger.debug("Using cached JWKS")
        return _jwks_cache['keys']
    
    try:
        logger.info(f"Fetching JWKS from {JWKS_URL}")
    
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",  # <-- add this too
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(JWKS_URL, headers=headers)
            response.raise_for_status()
            
        jwks_data = response.json()
        
        # Cache the JWKS
        _jwks_cache['keys'] = jwks_data
        _jwks_cache['expires_at'] = current_time + JWKS_CACHE_DURATION
        
        logger.info(f"Successfully fetched and cached JWKS with {len(jwks_data.get('keys', []))} keys")
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

def get_signing_key(token: str, jwks_data: Dict[str, Any]) -> str:
    """
    Get the signing key for a JWT token from JWKS
    
    Args:
        token: JWT token string
        jwks_data: JWKS data
        
    Returns:
        Signing key for the token
        
    Raises:
        HTTPException: If signing key not found
    """
    try:
        # Decode token header without verification to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID (kid)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Find the key with matching kid
        for key in jwks_data.get('keys', []):
            if key.get('kid') == kid:
                # Convert JWK to PEM format
                public_key = jwk.construct(key)
                return public_key.to_pem().decode('utf-8')
        
        # Key not found
        logger.warning(f"Signing key not found for kid: {kid}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: signing key not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except JWTError as e:
        logger.warning(f"JWT header decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Supabase JWT token using JWKS with HS256 fallback
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Fetch JWKS
        jwks_data = await fetch_jwks()
        
        # Check if JWKS has keys
        if jwks_data.get('keys') and len(jwks_data.get('keys', [])) > 0:
            # Use RS256 with JWKS
            logger.info("Using RS256 verification with JWKS")
            
            # Get signing key
            signing_key = get_signing_key(token, jwks_data)
            
            # Verify and decode the token with RS256
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience="authenticated",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "require_aud": True,
                    "require_exp": True,
                    "require_iat": True,
                }
            )
        else:
            # Fallback to HS256 with JWT_SECRET
            if not SUPABASE_JWT_SECRET:
                logger.error("JWKS is empty and no JWT_SECRET available for fallback")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service configuration error",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.info("JWKS is empty, falling back to HS256 verification with JWT_SECRET")
            
            # Verify and decode the token with HS256
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_nbf": False,  # HS256 tokens might not have nbf
                    "verify_iat": True,
                    "verify_iss": False,  # Issuer verification might differ
                    "require_aud": True,
                    "require_exp": True,
                    "require_iat": True,
                }
            )
        
        # Additional validation
        current_time = time.time()
        
        # Check expiration
        exp = payload.get('exp')
        if exp and exp < current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check not before (if present)
        nbf = payload.get('nbf')
        if nbf and nbf > current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not yet valid",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"Successfully verified token for user: {payload.get('email', 'unknown')}")
        return payload
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "signature" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User information from JWT payload
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = await verify_jwt_token(token)
    
    # Extract user information from payload
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
    
    Args:
        credentials: HTTP Authorization credentials (optional)
        
    Returns:
        User information if authenticated, None otherwise
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
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information if admin
        
    Raises:
        HTTPException: If user is not admin
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
def create_auth_headers(token: str) -> Dict[str, str]:
    """
    Create authorization headers for API requests
    
    Args:
        token: JWT token
        
    Returns:
        Headers dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {token}"}

def extract_user_id(current_user: Dict[str, Any]) -> str:
    """
    Extract user ID from current user info
    
    Args:
        current_user: Current user information
        
    Returns:
        User ID string
    """
    return current_user["id"]

def extract_user_email(current_user: Dict[str, Any]) -> str:
    """
    Extract user email from current user info
    
    Args:
        current_user: Current user information
        
    Returns:
        User email string
    """
    return current_user["email"]

def is_token_expired(current_user: Dict[str, Any]) -> bool:
    """
    Check if the current user's token is expired
    
    Args:
        current_user: Current user information
        
    Returns:
        True if token is expired, False otherwise
    """
    exp = current_user.get("exp")
    if not exp:
        return True
    
    return exp < time.time()

# Health check for authentication service
async def auth_health_check() -> Dict[str, Any]:
    """
    Health check for authentication service
    
    Returns:
        Health status information
    """
    try:
        # Try to fetch JWKS
        jwks_data = await fetch_jwks()
        keys_count = len(jwks_data.get('keys', []))
        
        return {
            "status": "healthy",
            "jwks_url": JWKS_URL,
            "keys_count": keys_count,
            "cache_expires_at": datetime.fromtimestamp(_jwks_cache['expires_at']).isoformat(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "jwks_url": JWKS_URL,
            "timestamp": datetime.now().isoformat()
        }
