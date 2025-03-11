import subprocess
import os
import asyncio

env = os.environ.copy()
env["PYTHONUTF8"] = "1"

async def run_script(command):
    print(f"Starting: {' '.join(command)}")  # Print before execution
    process = subprocess.Popen(command, env=env)
    await asyncio.sleep(0)  # Allow other tasks to run
    process.wait()  # Wait for the process to complete

if __name__ == "__main__":
    asyncio.run(run_script(['python', 'src/web_context_extract.py']))
    asyncio.run(run_script(['python', 'src/context_summarizer.py']))
    asyncio.run(run_script(['python', 'src/writer.py']))
