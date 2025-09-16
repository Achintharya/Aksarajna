#!/usr/bin/env python3
"""
Article Sync Script - Download articles from deployed backend to local backend
"""

import requests
import json
import os
from pathlib import Path
from datetime import datetime

# Configuration
DEPLOYED_BACKEND_URL = "https://varnika.onrender.com"  # Your deployed backend URL
LOCAL_ARTICLES_DIR = "./articles"

def sync_articles_from_deployed():
    """Download all articles from deployed backend to local storage"""
    
    print("🔄 Starting article sync from deployed backend...")
    print(f"📡 Deployed backend: {DEPLOYED_BACKEND_URL}")
    print(f"📁 Local articles directory: {LOCAL_ARTICLES_DIR}")
    
    # Create local articles directory if it doesn't exist
    Path(LOCAL_ARTICLES_DIR).mkdir(exist_ok=True)
    
    try:
        # Get list of articles from deployed backend
        print("\n📋 Fetching article list from deployed backend...")
        response = requests.get(f"{DEPLOYED_BACKEND_URL}/api/articles", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        print(f"✅ Found {len(articles)} articles on deployed backend:")
        for article in articles:
            print(f"   • {article['filename']} ({article['size']} bytes)")
        
        # Download each article
        downloaded_count = 0
        skipped_count = 0
        
        for article in articles:
            filename = article["filename"]
            local_path = Path(LOCAL_ARTICLES_DIR) / filename
            
            # Check if article already exists locally
            if local_path.exists():
                print(f"⏭️  Skipping {filename} (already exists locally)")
                skipped_count += 1
                continue
            
            # Download article content
            print(f"⬇️  Downloading {filename}...")
            try:
                article_response = requests.get(
                    f"{DEPLOYED_BACKEND_URL}/api/articles/{filename}", 
                    timeout=30
                )
                article_response.raise_for_status()
                
                # Save to local file
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(article_response.text)
                
                print(f"✅ Downloaded {filename} ({len(article_response.text)} characters)")
                downloaded_count += 1
                
            except Exception as e:
                print(f"❌ Failed to download {filename}: {e}")
        
        # Sync sources.md as well
        print(f"\n📄 Syncing sources.md...")
        try:
            sources_response = requests.get(f"{DEPLOYED_BACKEND_URL}/api/articles/sources.md", timeout=30)
            if sources_response.status_code == 200 and sources_response.text.strip():
                sources_path = Path("./data/sources.md")
                sources_path.parent.mkdir(exist_ok=True)
                
                with open(sources_path, "w", encoding="utf-8") as f:
                    f.write(sources_response.text)
                print(f"✅ Synced sources.md ({len(sources_response.text)} characters)")
            else:
                print("⚠️  No sources.md found on deployed backend")
        except Exception as e:
            print(f"❌ Failed to sync sources.md: {e}")
        
        # Summary
        print(f"\n📊 Sync Summary:")
        print(f"   • Downloaded: {downloaded_count} articles")
        print(f"   • Skipped: {skipped_count} articles (already exist)")
        print(f"   • Total on deployed: {len(articles)} articles")
        
        if downloaded_count > 0:
            print(f"\n🎉 Sync completed! Your local backend now has the deployed articles.")
            print(f"💡 Restart your local backend to see the changes: python src/main.py --port 8001")
        else:
            print(f"\n✨ All articles are already synced!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to deployed backend: {e}")
        print(f"💡 Make sure the deployed backend URL is correct: {DEPLOYED_BACKEND_URL}")
    except Exception as e:
        print(f"❌ Unexpected error during sync: {e}")

def check_local_articles():
    """Check what articles exist locally"""
    print(f"\n📁 Current local articles:")
    articles_dir = Path(LOCAL_ARTICLES_DIR)
    
    if not articles_dir.exists():
        print("   (No articles directory found)")
        return
    
    articles = list(articles_dir.glob("*.md")) + list(articles_dir.glob("*.txt"))
    
    if not articles:
        print("   (No articles found)")
    else:
        for article in articles:
            stat = article.stat()
            print(f"   • {article.name} ({stat.st_size} bytes)")

if __name__ == "__main__":
    print("🚀 Varnika Article Sync Tool")
    print("=" * 50)
    
    # Show current local articles
    check_local_articles()
    
    # Ask for confirmation
    print(f"\n❓ Do you want to sync articles from deployed backend?")
    print(f"   Deployed: {DEPLOYED_BACKEND_URL}")
    print(f"   Local: {LOCAL_ARTICLES_DIR}")
    
    confirm = input("\nProceed? (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        sync_articles_from_deployed()
    else:
        print("❌ Sync cancelled.")
