import asyncio
import os
import argparse
import sys
import time
from tqdm import tqdm
import subprocess

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from src.config import logger, config

async def run_script(command, description=None):
    """
    Run a script asynchronously with proper error handling and progress indication.
    
    Args:
        command (list): Command to execute as a list of strings
        description (str, optional): Description of the command for logging
    
    Returns:
        bool: True if the script executed successfully, False otherwise
    """
    script_name = command[1].split('/')[-1] if len(command) > 1 else "unknown"
    description = description or f"Running {script_name}"
    
    logger.info(f"Starting: {' '.join(command)}")
    
    # Create progress bar
    progress = tqdm(total=100, desc=description, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        
        # Start the process
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        
        # Monitor the process
        progress.update(10)  # Initial progress
        
        # Wait for the process to complete while updating progress
        for i in range(9):
            if process.poll() is not None:
                break
            await asyncio.sleep(0.5)
            progress.update(10)
        
        # Get the output and error
        stdout, stderr = process.communicate()
        
        # Check if the process completed successfully
        if process.returncode != 0:
            # Special handling for context_summarizer.py
            if "context_summarizer.py" in command[1]:
                # Check if there's a rate limit error but a basic summary was created
                if "rate_limit" in stderr.lower() and "created basic summary" in stderr.lower():
                    logger.warning(f"Context summarizer hit rate limit but created basic summary")
                    progress.update(100 - progress.n)
                    progress.close()
                    logger.info(f"Successfully completed with fallback: {script_name}")
                    return True
                
            logger.error(f"Error running {script_name}: {stderr}")
            progress.close()
            return False
        
        # Complete the progress bar
        progress.update(100 - progress.n)
        progress.close()
        
        logger.info(f"Successfully completed: {script_name}")
        return True
    
    except Exception as e:
        logger.error(f"Exception running {script_name}: {str(e)}")
        progress.close()
        return False

async def main():
    """Main function to run the scripts based on command-line arguments"""
    parser = argparse.ArgumentParser(description="Integrated Web Context and AI Writing Tool")
    
    parser.add_argument("--extract", action="store_true", help="Run web context extraction")
    parser.add_argument("--summarize", action="store_true", help="Run context summarization")
    parser.add_argument("--write", action="store_true", help="Run article writer")
    parser.add_argument("--all", action="store_true", help="Run all components in sequence")
    parser.add_argument("--concurrent", action="store_true", help="Run selected components concurrently")
    parser.add_argument("--query", type=str, help="Search query for web extraction")
    parser.add_argument("--article-type", type=str, choices=["detailed", "summarized", "points"], 
                      default="detailed", help="Article type (detailed, summarized, points)")
    parser.add_argument("--article-filename", type=str, help="File name for the article (without extension)")
    
    args = parser.parse_args()
    
    # If no arguments are provided, show help
    if not (args.extract or args.summarize or args.write or args.all):
        parser.print_help()
        return
    
    # Determine which scripts to run
    scripts_to_run = []
    
    if args.all or args.extract:
        extract_cmd = ['python', 'src/web_context_extract.py']
        if args.query:
            extract_cmd.extend(['--query', args.query])
        scripts_to_run.append((extract_cmd, "Web Context Extraction"))
    
    if args.all or args.summarize:
        scripts_to_run.append((['python', 'src/context_summarizer.py'], "Context Summarization"))
    
    if args.all or args.write:
        article_writer_cmd = ['python', 'src/article_writer.py', '--type', args.article_type]
        if args.article_filename:
            article_writer_cmd.extend(['--filename', args.article_filename])
        scripts_to_run.append((article_writer_cmd, "Article Writing"))
    
    # Run the scripts
    if args.concurrent:
        # Run scripts concurrently
        tasks = [run_script(cmd, desc) for cmd, desc in scripts_to_run]
        results = await asyncio.gather(*tasks)
        
        # Check if all scripts completed successfully
        if all(results):
            logger.info("All tasks completed successfully")
        else:
            logger.error("Some tasks failed")
            sys.exit(1)
    else:
        # Run scripts sequentially
        for cmd, desc in scripts_to_run:
            success = await run_script(cmd, desc)
            if not success:
                logger.error(f"Task failed: {desc}")
                sys.exit(1)
        
        logger.info("All tasks completed successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)
