import asyncio
import os
import argparse
import sys
import time
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
        
        # Log initial progress
        logger.info(f"{description}: Started")
        
        # Read output line by line to monitor progress
        stdout_lines = []
        stderr_lines = []
        
        # Function to read from a pipe without blocking
        async def read_pipe(pipe, lines_list):
            while True:
                line = pipe.readline()
                if not line:
                    break
                line_text = line.strip()
                lines_list.append(line_text)
                # Log progress updates
                if "%" in line_text:
                    try:
                        percent = int(line_text.split('%')[0].split('|')[-1].strip())
                        logger.info(f"{description}: {percent}% complete")
                    except:
                        pass
                await asyncio.sleep(0.1)
        
        # Create tasks to read stdout and stderr
        stdout_task = asyncio.create_task(read_pipe(process.stdout, stdout_lines))
        stderr_task = asyncio.create_task(read_pipe(process.stderr, stderr_lines))
        
        # Wait for the process to complete
        while process.poll() is None:
            await asyncio.sleep(0.5)
        
        # Cancel the read tasks
        stdout_task.cancel()
        stderr_task.cancel()
        
        # Get any remaining output
        remaining_stdout, remaining_stderr = process.communicate()
        if remaining_stdout:
            stdout_lines.extend(remaining_stdout.strip().split('\n'))
        if remaining_stderr:
            stderr_lines.extend(remaining_stderr.strip().split('\n'))
        
        # Combine the output
        stdout = '\n'.join(stdout_lines)
        stderr = '\n'.join(stderr_lines)
        
        # Check if the process completed successfully
        if process.returncode != 0:
            # Special handling for context_summarizer.py
            if "context_summarizer.py" in command[1]:
                # Check if there's a rate limit error but a basic summary was created
                if "rate_limit" in stderr.lower() and "created basic summary" in stderr.lower():
                    logger.warning("Context summarizer hit rate limit but created basic summary")
                    logger.info(f"{description}: 100% complete")
                    logger.info(f"Successfully completed with fallback: {script_name}")
                    return True
                
            logger.error(f"Error running {script_name}: {stderr}")
            return False
        
        # Log completion
        logger.info(f"{description}: 100% complete")
        
        # Add a small delay to ensure file operations are complete
        await asyncio.sleep(1)
        
        logger.info(f"Successfully completed: {script_name}")
        return True
    
    except Exception as e:
        logger.error(f"Exception running {script_name}: {str(e)}")
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
    parser.add_argument("--urls", type=str, help="Comma-separated list of URLs to extract from")
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
        if args.urls:
            extract_cmd.extend(['--urls', args.urls])
        scripts_to_run.append((extract_cmd, "Web Context Extraction"))
    
    if args.all or args.summarize:
        scripts_to_run.append((['python', 'src/context_summarizer.py'], "Context Summarization"))
    
    if args.all or args.write:
        article_writer_cmd = ['python', 'src/article_writer.py', '--type', args.article_type]
        if args.article_filename:
            article_writer_cmd.extend(['--filename', args.article_filename])
        scripts_to_run.append((article_writer_cmd, "Article Writing"))
    
    # Run the scripts
    if args.concurrent and len(scripts_to_run) > 1:
        # Even with concurrent flag, we need to ensure proper order of execution
        # Extract -> Summarize -> Write
        
        # Group scripts by type
        extract_scripts = [s for s in scripts_to_run if "web_context_extract.py" in s[0][1]]
        summarize_scripts = [s for s in scripts_to_run if "context_summarizer.py" in s[0][1]]
        write_scripts = [s for s in scripts_to_run if "article_writer.py" in s[0][1]]
        
        # Run extraction scripts first (concurrently if multiple)
        if extract_scripts:
            extract_tasks = [run_script(cmd, desc) for cmd, desc in extract_scripts]
            extract_results = await asyncio.gather(*extract_tasks)
            if not all(extract_results):
                logger.error("Extraction task(s) failed")
                sys.exit(1)
        
        # Run summarization scripts next (concurrently if multiple)
        if summarize_scripts:
            summarize_tasks = [run_script(cmd, desc) for cmd, desc in summarize_scripts]
            summarize_results = await asyncio.gather(*summarize_tasks)
            if not all(summarize_results):
                logger.error("Summarization task(s) failed")
                sys.exit(1)
        
        # Run article writing scripts last (concurrently if multiple)
        if write_scripts:
            write_tasks = [run_script(cmd, desc) for cmd, desc in write_scripts]
            write_results = await asyncio.gather(*write_tasks)
            if not all(write_results):
                logger.error("Article writing task(s) failed")
                sys.exit(1)
        
        logger.info("All tasks completed successfully")
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
