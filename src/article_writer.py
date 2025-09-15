import os
import json
import sys
import argparse
import requests
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv('config/.env')

def save_article_to_file(response, file_name):
    """
    Save the generated article to a file
    
    Args:
        response (str): The article content
        file_name (str): The file name to save the article to
    """
    try:
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(response)
        print(f"Article saved to '{file_name}'")
    except Exception as e:
        print(f"Error saving article to file: {e}")
        raise

def prompt_for_file_name():
    """
    Prompt the user for a file name to save the article
    
    Returns:
        str: The full file path
    """
    file_name = input('Enter the file name to save the article: ')
    if not file_name:
        print("Empty file name provided, using default")
        file_name = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Ensure the file has a .txt extension
    if not file_name.endswith('.txt'):
        file_name = f"{file_name}.txt"
    
    articles_dir = "./articles"
    return os.path.join(articles_dir, file_name)

def generate_chat_response(writing_style, context, query):
    """
    Generate a chat response using the Mistral API
    
    Args:
        writing_style (str): The writing style to imitate
        context (str): The context to use for generating the response
        query (str): The user query
        
    Returns:
        str: The generated response
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # Create a progress bar for the generation process
    progress = tqdm(total=100, desc="Generating article", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
    progress.update(10)  # Initial progress
    
    # Prepare the prompt message
    prompt_message = f"Current Date and Time: {current_date}, {current_time}\n" \
                     f"Writing Style Example: {writing_style}\n" \
                     f"Context: {context}\n" \
                     f"User Query: {query}"

    try:
        # Get the model and API key from environment
        model = "mistral-medium"
        api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            print("Mistral API key not found in environment")
            return "Error: Mistral API key not found. Please check your .env file."
        
        print(f"Using model: {model}")
        
        progress.update(20)  # Update progress
        
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "### You are an AI that imitates a writing style (without including any info from it) to write nonredundantly about the context provided, WITHOUT hallucination. NEVER use bold formatting ###"},
                {"role": "user", "content": prompt_message}
            ]
        }
        
        # Make the API request
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        
        progress.update(70)  # Update progress after generation
        progress.close()
        
        print("Article generation completed successfully")
        return response_data['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        progress.close()
        print(f"Mistral API request error: {e}")
        return f"Error generating response: {e}"
    except Exception as e:
        progress.close()
        print(f"Error generating response: {e}")
        return f"Sorry, I couldn't process your request: {e}"

def start(query=None, filename=None):
    """
    Start the article writing process
    
    Args:
        query (str, optional): The query to use for generating the article
        filename (str, optional): The file name to save the article to
    """
    try:
        # Read context and writing style
        context_path = "./data/context.txt"
        writing_style_path = "./data/writing_style.txt"
        
        print(f"Reading context from {context_path}")
        try:
            with open(context_path, "r", encoding='utf-8') as file:
                context = file.read()
        except FileNotFoundError:
            print(f"Context file not found: {context_path}")
            print("Please run the web context extraction and summarization first.")
            return 1
        except Exception as e:
            print(f"Error reading context file: {e}")
            return 1

        print(f"Reading writing style from {writing_style_path}")
        try:
            with open(writing_style_path, "r", encoding='utf-8') as file:
                writing_style = file.read()
        except FileNotFoundError:
            print(f"Writing style file not found: {writing_style_path}")
            writing_style = "Write in a clear, concise, and informative style."
        except Exception as e:
            print(f"Error reading writing style file: {e}")
            writing_style = "Write in a clear, concise, and informative style."

        if not context:
            print("Warning: No relevant context found. The article may lack specific information.")

        
        if not query:
            query = "Write a detailed comprehensive article based on the provided context"
            print(f"No query provided, using default: '{query}'")

        print(f"Generating article for: '{query}'")
        
        # Generate response
        response = generate_chat_response(writing_style, context, query)

        # Get the file name
        if filename:
            # Use the provided filename
            file_name = filename
            if not file_name.endswith('.txt'):
                file_name = f"{file_name}.txt"
            articles_dir = "./articles"
            file_path = os.path.join(articles_dir, file_name)
        else:
            # Prompt user for the file name
            file_path = prompt_for_file_name()
        
        save_article_to_file(response, file_path)
        
        print(f"The article has been saved to '{file_path}'.")
        return 0

    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        return 130
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1

def main():
    """Main function to handle command-line arguments and run the article writer"""
    parser = argparse.ArgumentParser(description="AI Article Writer")
    parser.add_argument("--type", type=str, choices=["detailed", "summarized", "points"], 
                      default="detailed", help="Article type (detailed, summarized, points)")
    parser.add_argument("--filename", type=str, help="File name for the article (without extension)")
    args = parser.parse_args()
    
    # Map article type to a query
    article_type_queries = {
        "detailed": "Write a detailed comprehensive article based on the provided context",
        "summarized": "Write a concise summary article based on the provided context",
        "points": "Write an article in bullet points based on the provided context"
    }
    
    query = article_type_queries.get(args.type, article_type_queries["detailed"])
    return start(query=query, filename=args.filename)

# Start the process
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
