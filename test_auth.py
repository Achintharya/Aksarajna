#!/usr/bin/env python3
"""
Test script to verify JWT authentication is working properly
"""

import asyncio
import httpx
import json
from src.auth import fetch_jwks, verify_jwt_token, JWKS_URL
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_jwks_fetch():
    """Test fetching JWKS from Supabase"""
    print("\n=== Testing JWKS Fetch ===")
    try:
        jwks_data = await fetch_jwks()
        print(f"✓ Successfully fetched JWKS from {JWKS_URL}")
        print(f"  Keys found: {len(jwks_data.get('keys', []))}")
        
        for key in jwks_data.get('keys', []):
            print(f"  - Algorithm: {key.get('alg')}, Kid: {key.get('kid', 'N/A')[:8]}...")
        
        # Check if ES256 key is present
        es256_keys = [k for k in jwks_data.get('keys', []) if k.get('alg') == 'ES256']
        if es256_keys:
            print(f"✓ ES256 key found: {len(es256_keys)} key(s)")
            for key in es256_keys:
                if key.get('kid') == 'f9a4bdc8-48ad-4084-9dfa-4cd6f7747d43':
                    print("✓ Expected ES256 key with correct kid found!")
        else:
            print("✗ No ES256 keys found in JWKS")
            
        return True
    except Exception as e:
        print(f"✗ Error fetching JWKS: {e}")
        return False

async def test_auth_health():
    """Test the auth health check endpoint"""
    print("\n=== Testing Auth Health Check ===")
    try:
        from src.auth import auth_health_check
        health = await auth_health_check()
        print(f"Status: {health.get('status')}")
        print(f"JWKS URL: {health.get('jwks_url')}")
        print(f"Keys count: {health.get('keys_count')}")
        print(f"Key algorithms: {health.get('key_algorithms')}")
        print(f"ES256 available: {health.get('es256_available')}")
        
        if health.get('status') == 'healthy':
            print("✓ Authentication service is healthy")
        else:
            print(f"✗ Authentication service unhealthy: {health.get('error')}")
            
        return health.get('status') == 'healthy'
    except Exception as e:
        print(f"✗ Error checking auth health: {e}")
        return False

async def test_token_verification(token: str = None):
    """Test token verification if a token is provided"""
    if not token:
        print("\n=== Token Verification Test ===")
        print("No token provided. To test token verification, run:")
        print("  python test_auth.py <your_jwt_token>")
        return True
        
    print("\n=== Testing Token Verification ===")
    try:
        # Decode without verification first to see what's in the token
        from jose import jwt
        unverified = jwt.decode(token, key=None, options={"verify_signature": False})
        header = jwt.get_unverified_header(token)
        
        print(f"Token algorithm: {header.get('alg')}")
        print(f"Token kid: {header.get('kid')}")
        print(f"Token sub (user ID): {unverified.get('sub')}")
        print(f"Token aud: {unverified.get('aud')}")
        
        # Now try to verify
        payload = await verify_jwt_token(token)
        print("✓ Token verified successfully!")
        print(f"  User ID: {payload.get('sub')}")
        print(f"  Email: {payload.get('email')}")
        print(f"  Role: {payload.get('role')}")
        return True
    except Exception as e:
        print(f"✗ Token verification failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("JWT Authentication Test Suite")
    print("=" * 50)
    
    # Get token from command line if provided
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run tests
    results = []
    results.append(await test_jwks_fetch())
    results.append(await test_auth_health())
    results.append(await test_token_verification(token))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Check the output above for details.")
        
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
