#!/usr/bin/env python3
"""
FastAPI server startup script for Varnika
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables from config/.env
load_dotenv('config/.env')

def main():
    """Run the FastAPI application"""
    print("Starting Varnika FastAPI Server...")
    print("=" * 50)
    print("API Documentation: http://localhost:8000/docs")
    print("Alternative Docs: http://localhost:8000/redoc")
    print("=" * 50)
    
    # Run the FastAPI app
    uvicorn.run(
        "src.fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
