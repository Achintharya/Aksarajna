import subprocess
import os
import sys  
import asyncio

env = os.environ.copy()
env["PYTHONUTF8"] = "1"


async def run_script(command, query=None):
    if query:
        command.append(query)  # Append the query to the command
    print(f"Starting: {' '.join(command)}")  # Print before execution
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding="utf-8", env=env)

        print(f"Finished: {' '.join(command)}")
        print(f"Output: \n{result.stdout.strip()}")
        print(f"\n{result.stderr.strip()}\n")
        return result.stdout.strip()  # Return the output
    except subprocess.CalledProcessError as e:
        print(f"Error running {command}: \n{e.stderr or e.stdout}")

if __name__ == "__main__":

    # Run Python scripts with query
    asyncio.run(run_script(['python', 'src/web_context_extract.py'])) 

    asyncio.run(run_script(['python', 'src/context_summarizer.py']))

    # Run Node.js script
    asyncio.run(run_script(['node', 'src/writer.mjs']))

