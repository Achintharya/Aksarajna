import streamlit as st
import subprocess
import asyncio
import os

env = os.environ.copy()
env["PYTHONUTF8"] = "1"

st.title("📑 AI-Powered Context Summarizer & Writer")

# User input for search query
query = st.text_input("Enter the search query:", "")

async def run_script(command):
    print(f"Starting: {' '.join(command)}")  # Print before execution
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    await asyncio.sleep(0)  # Allow other tasks to run
    process.wait()  # Wait for the process to complete

if st.button("Run Extraction & Summarization"):
    if query:
        st.write("🔍 Extracting web data...")
        asyncio.run(run_script(['python', '../src/web_context_extract.py', query]))


        st.write("📄 Summarizing extracted data...")
        asyncio.run(run_script(['python', '../src/context_summarizer.py']))


        st.write("📝 Generating final article...")
        asyncio.run(run_script(['python', '../src/writer.py', query]))


        st.success("✅ Processes Completed!")
    else:
        st.warning("Please enter a search query.")

# Provide a download button for the generated article
article_path = "articles/generated_article.txt"
if os.path.exists(article_path):
    with open(article_path, "r", encoding="utf-8") as file:
        st.download_button("Download Generated Article", file, file_name="Generated_Article.txt")
