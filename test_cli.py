#!/usr/bin/env python3
"""
Test script to verify the CLI components work properly.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_web_extraction():
    """Test web context extraction with a predefined query."""
    print("Testing web context extraction...")
    
    try:
        from web_context_extract import extract
        await extract("AI technology trends 2024")
        print("✅ Web context extraction completed successfully")
        return True
    except Exception as e:
        print(f"❌ Web context extraction failed: {e}")
        return False

def test_context_summarization():
    """Test context summarization."""
    print("Testing context summarization...")
    
    try:
        from context_summarizer import summarize_context
        result = summarize_context()
        if result == 0:
            print("✅ Context summarization completed successfully")
            return True
        else:
            print("❌ Context summarization failed with exit code:", result)
            return False
    except Exception as e:
        print(f"❌ Context summarization failed: {e}")
        return False

def test_article_writing():
    """Test article writing."""
    print("Testing article writing...")
    
    try:
        from article_writer import start
        result = start(query="Write a detailed article based on the provided context", filename="test_article")
        if result == 0:
            print("✅ Article writing completed successfully")
            return True
        else:
            print("❌ Article writing failed with exit code:", result)
            return False
    except Exception as e:
        print(f"❌ Article writing failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Starting CLI component tests...\n")
    
    # Test 1: Web Context Extraction
    web_success = await test_web_extraction()
    print()
    
    # Test 2: Context Summarization (only if web extraction succeeded)
    if web_success:
        context_success = test_context_summarization()
        print()
        
        # Test 3: Article Writing (only if summarization succeeded)
        if context_success:
            article_success = test_article_writing()
            print()
            
            if article_success:
                print("🎉 All CLI components are working correctly!")
                return 0
    
    print("❌ Some CLI components failed. Check the errors above.")
    return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
