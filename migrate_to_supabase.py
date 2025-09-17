#!/usr/bin/env python3
"""
Migration script to move existing local files to Supabase Storage
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')

# Import Supabase client
from src.supabase_client import storage_manager, supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default user ID for migration (you can change this)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"  # Replace with actual admin user ID

class MigrationManager:
    """Handles migration of local files to Supabase Storage"""
    
    def __init__(self, default_user_id: str = DEFAULT_USER_ID):
        self.default_user_id = default_user_id
        self.migration_stats = {
            "articles": {"success": 0, "failed": 0, "files": []},
            "sources": {"success": 0, "failed": 0, "files": []},
            "writing_styles": {"success": 0, "failed": 0, "files": []}
        }
    
    async def migrate_articles(self) -> None:
        """Migrate articles from ./articles directory"""
        articles_dir = Path("./articles")
        
        if not articles_dir.exists():
            logger.info("No articles directory found, skipping articles migration")
            return
        
        logger.info(f"🔍 Scanning articles directory: {articles_dir.absolute()}")
        
        # Find all article files
        article_files = []
        for pattern in ["*.md", "*.txt"]:
            article_files.extend(list(articles_dir.glob(pattern)))
        
        logger.info(f"📄 Found {len(article_files)} article files to migrate")
        
        for file_path in article_files:
            try:
                logger.info(f"📤 Migrating article: {file_path.name}")
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Upload to Supabase Storage
                result = await storage_manager.upload_article(
                    self.default_user_id, 
                    file_path.name, 
                    content
                )
                
                if result.get("success"):
                    self.migration_stats["articles"]["success"] += 1
                    self.migration_stats["articles"]["files"].append({
                        "filename": file_path.name,
                        "size": len(content),
                        "status": "success"
                    })
                    logger.info(f"✅ Successfully migrated: {file_path.name}")
                else:
                    self.migration_stats["articles"]["failed"] += 1
                    self.migration_stats["articles"]["files"].append({
                        "filename": file_path.name,
                        "size": len(content),
                        "status": "failed",
                        "error": result.get("error", "Unknown error")
                    })
                    logger.error(f"❌ Failed to migrate: {file_path.name} - {result.get('error')}")
                
            except Exception as e:
                self.migration_stats["articles"]["failed"] += 1
                self.migration_stats["articles"]["files"].append({
                    "filename": file_path.name,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"❌ Error migrating {file_path.name}: {e}")
    
    async def migrate_sources(self) -> None:
        """Migrate sources from ./data directory"""
        data_dir = Path("./data")
        
        if not data_dir.exists():
            logger.info("No data directory found, skipping sources migration")
            return
        
        logger.info(f"🔍 Scanning data directory for sources: {data_dir.absolute()}")
        
        # Look for sources files
        sources_files = []
        for filename in ["sources.md", "sources.txt"]:
            file_path = data_dir / filename
            if file_path.exists():
                sources_files.append(file_path)
        
        if not sources_files:
            logger.info("No sources files found, skipping sources migration")
            return
        
        # Use the first sources file found (prefer .md over .txt)
        sources_file = sources_files[0]
        logger.info(f"📄 Found sources file to migrate: {sources_file.name}")
        
        try:
            logger.info(f"📤 Migrating sources: {sources_file.name}")
            
            # Read file content
            with open(sources_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Upload to Supabase Storage
            result = await storage_manager.upload_sources(self.default_user_id, content)
            
            if result.get("success"):
                self.migration_stats["sources"]["success"] += 1
                self.migration_stats["sources"]["files"].append({
                    "filename": sources_file.name,
                    "size": len(content),
                    "status": "success"
                })
                logger.info(f"✅ Successfully migrated sources: {sources_file.name}")
            else:
                self.migration_stats["sources"]["failed"] += 1
                self.migration_stats["sources"]["files"].append({
                    "filename": sources_file.name,
                    "size": len(content),
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                })
                logger.error(f"❌ Failed to migrate sources: {sources_file.name} - {result.get('error')}")
                
        except Exception as e:
            self.migration_stats["sources"]["failed"] += 1
            self.migration_stats["sources"]["files"].append({
                "filename": sources_file.name,
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"❌ Error migrating sources {sources_file.name}: {e}")
    
    async def migrate_writing_styles(self) -> None:
        """Migrate writing styles from ./data directory"""
        data_dir = Path("./data")
        
        if not data_dir.exists():
            logger.info("No data directory found, skipping writing styles migration")
            return
        
        logger.info(f"🔍 Scanning data directory for writing styles: {data_dir.absolute()}")
        
        # Look for writing style file
        writing_style_file = data_dir / "writing_style.txt"
        
        if not writing_style_file.exists():
            logger.info("No writing style file found, skipping writing styles migration")
            return
        
        logger.info(f"📄 Found writing style file to migrate: {writing_style_file.name}")
        
        try:
            logger.info(f"📤 Migrating writing style: {writing_style_file.name}")
            
            # Read file content
            with open(writing_style_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Upload to Supabase Storage
            result = await storage_manager.upload_writing_style(self.default_user_id, content)
            
            if result.get("success"):
                self.migration_stats["writing_styles"]["success"] += 1
                self.migration_stats["writing_styles"]["files"].append({
                    "filename": writing_style_file.name,
                    "size": len(content),
                    "status": "success"
                })
                logger.info(f"✅ Successfully migrated writing style: {writing_style_file.name}")
            else:
                self.migration_stats["writing_styles"]["failed"] += 1
                self.migration_stats["writing_styles"]["files"].append({
                    "filename": writing_style_file.name,
                    "size": len(content),
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                })
                logger.error(f"❌ Failed to migrate writing style: {writing_style_file.name} - {result.get('error')}")
                
        except Exception as e:
            self.migration_stats["writing_styles"]["failed"] += 1
            self.migration_stats["writing_styles"]["files"].append({
                "filename": writing_style_file.name,
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"❌ Error migrating writing style {writing_style_file.name}: {e}")
    
    async def ensure_buckets_exist(self) -> None:
        """Ensure all required Supabase Storage buckets exist"""
        logger.info("🪣 Ensuring Supabase Storage buckets exist...")
        try:
            await storage_manager.ensure_buckets_exist()
            logger.info("✅ Storage buckets verified/created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to ensure buckets exist: {e}")
            raise
    
    def print_migration_summary(self) -> None:
        """Print a summary of the migration results"""
        logger.info("\n" + "="*60)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("="*60)
        
        total_success = 0
        total_failed = 0
        
        for category, stats in self.migration_stats.items():
            success = stats["success"]
            failed = stats["failed"]
            total_success += success
            total_failed += failed
            
            logger.info(f"\n📁 {category.upper()}:")
            logger.info(f"   ✅ Success: {success}")
            logger.info(f"   ❌ Failed:  {failed}")
            
            if stats["files"]:
                logger.info(f"   📄 Files:")
                for file_info in stats["files"]:
                    status_icon = "✅" if file_info["status"] == "success" else "❌"
                    size_info = f" ({file_info.get('size', 0)} bytes)" if file_info.get('size') else ""
                    error_info = f" - {file_info.get('error', '')}" if file_info.get('error') else ""
                    logger.info(f"      {status_icon} {file_info['filename']}{size_info}{error_info}")
        
        logger.info(f"\n🎯 TOTAL RESULTS:")
        logger.info(f"   ✅ Total Success: {total_success}")
        logger.info(f"   ❌ Total Failed:  {total_failed}")
        logger.info(f"   📊 Success Rate:  {(total_success / (total_success + total_failed) * 100):.1f}%" if (total_success + total_failed) > 0 else "   📊 Success Rate:  N/A")
        
        logger.info("\n" + "="*60)
        
        if total_failed > 0:
            logger.warning(f"⚠️  {total_failed} files failed to migrate. Please check the errors above.")
        else:
            logger.info("🎉 All files migrated successfully!")
    
    async def run_migration(self) -> None:
        """Run the complete migration process"""
        logger.info("🚀 Starting migration to Supabase Storage...")
        logger.info(f"👤 Default User ID: {self.default_user_id}")
        
        try:
            # Ensure buckets exist
            await self.ensure_buckets_exist()
            
            # Migrate each category
            await self.migrate_articles()
            await self.migrate_sources()
            await self.migrate_writing_styles()
            
            # Print summary
            self.print_migration_summary()
            
        except Exception as e:
            logger.error(f"💥 Migration failed with error: {e}")
            raise

async def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate local files to Supabase Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_to_supabase.py                                    # Use default user ID
  python migrate_to_supabase.py --user-id "your-user-id-here"     # Use specific user ID
  python migrate_to_supabase.py --dry-run                         # Preview what would be migrated
        """
    )
    
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User ID to assign migrated files to (default: {DEFAULT_USER_ID})"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be migrated without actually migrating"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be actually migrated")
        
        # Just scan and report what would be migrated
        articles_dir = Path("./articles")
        data_dir = Path("./data")
        
        logger.info("\n📊 MIGRATION PREVIEW:")
        
        # Articles
        if articles_dir.exists():
            article_files = []
            for pattern in ["*.md", "*.txt"]:
                article_files.extend(list(articles_dir.glob(pattern)))
            logger.info(f"📁 Articles: {len(article_files)} files found")
            for file_path in article_files:
                size = file_path.stat().st_size
                logger.info(f"   📄 {file_path.name} ({size} bytes)")
        else:
            logger.info(f"📁 Articles: No articles directory found")
        
        # Sources
        sources_files = []
        if data_dir.exists():
            for filename in ["sources.md", "sources.txt"]:
                file_path = data_dir / filename
                if file_path.exists():
                    sources_files.append(file_path)
        
        if sources_files:
            logger.info(f"📁 Sources: {len(sources_files)} files found")
            for file_path in sources_files:
                size = file_path.stat().st_size
                logger.info(f"   📄 {file_path.name} ({size} bytes)")
        else:
            logger.info(f"📁 Sources: No sources files found")
        
        # Writing Styles
        writing_style_file = data_dir / "writing_style.txt" if data_dir.exists() else None
        if writing_style_file and writing_style_file.exists():
            size = writing_style_file.stat().st_size
            logger.info(f"📁 Writing Styles: 1 file found")
            logger.info(f"   📄 {writing_style_file.name} ({size} bytes)")
        else:
            logger.info(f"📁 Writing Styles: No writing style file found")
        
        logger.info(f"\n👤 Target User ID: {args.user_id}")
        logger.info("\n🔄 Run without --dry-run to perform actual migration")
        
    else:
        # Perform actual migration
        migration_manager = MigrationManager(args.user_id)
        await migration_manager.run_migration()

if __name__ == "__main__":
    asyncio.run(main())
