import os
import json
import ollama
import sys
import argparse
from datetime import datetime
from tqdm import tqdm
from src.config import logger, config

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
        logger.info(f"Article saved to '{file_name}'")
    except Exception as e:
        logger.error(f"Error saving article to file: {e}")
        raise

def prompt_for_file_name():
    """
    Prompt the user for a file name to save the article
    
    Returns:
        str: The full file path
    """
    file_name = input('Enter the file name to save the article: ')
    if not file_name:
        logger.warning("Empty file name provided, using default")
        file_name = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Ensure the file has a .txt extension
    if not file_name.endswith('.txt'):
        file_name = f"{file_name}.txt"
    
    articles_dir = config.get('paths.articles_dir')
    return os.path.join(articles_dir, file_name)

def generate_chat_response(writing_style, context, query):
    """
    Generate a chat response using the Ollama API
    
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
        # Get the model from configuration
        model = config.get('models.article_writer', 'mistral')
        logger.info(f"Using model: {model}")
        
        progress.update(20)  # Update progress
        
        # Ensure the model parameter is a string and messages is a list
        response = ollama.chat(
            model=model,
            messages=[
                {'role': "system", 'content': "### You are an AI that imitates a writing style (without including any info from it) to write nonredundantly about the context provided, WITH NO HALLUCINATION. ###"},
                {'role': "user", 'content': prompt_message}
            ]
        )
        
        progress.update(70)  # Update progress after generation
        progress.close()
        
        logger.info("Article generation completed successfully")
        return response['message']['content']

    except ollama.ResponseError as e:
        progress.close()
        logger.error(f"Ollama API response error: {e}")
        return f"Error generating response: {e}"
    except Exception as e:
        progress.close()
        logger.error(f"Error generating response: {e}")
        return f"Sorry, I couldn't process your request: {e}"

def start(query=None):
    """
    Start the article writing process
    
    Args:
        query (str, optional): The query to use for generating the article
    """
    try:
        # Read context and writing style
        context_path = config.get('paths.context_txt')
        writing_style_path = config.get('paths.writing_style')
        
        logger.info(f"Reading context from {context_path}")
        try:
            with open(context_path, "r", encoding='utf-8') as file:
                context = file.read()
        except FileNotFoundError:
            logger.error(f"Context file not found: {context_path}")
            print(f"Error: Context file not found: {context_path}")
            print("Please run the web context extraction and summarization first.")
            return 1
        except Exception as e:
            logger.error(f"Error reading context file: {e}")
            print(f"Error reading context file: {e}")
            return 1

        logger.info(f"Reading writing style from {writing_style_path}")
        try:
            with open(writing_style_path, "r", encoding='utf-8') as file:
                writing_style = file.read()
        except FileNotFoundError:
            logger.warning(f"Writing style file not found: {writing_style_path}")
            writing_style = "Write in a clear, concise, and informative style."
        except Exception as e:
            logger.error(f"Error reading writing style file: {e}")
            writing_style = "Write in a clear, concise, and informative style."

        if not context:
            logger.warning("No relevant context found. Proceeding with minimal guidance.")
            print("Warning: No relevant context found. The article may lack specific information.")

        # Define the query if not provided
        if not query:
            query = input("Enter your article query (e.g., 'Write an informative article about electric vehicles'): ")
        
        if not query:
            query = "Write a brief informative article based on the provided context"
            logger.warning(f"No query provided, using default: '{query}'")

        logger.info(f"Generating article for query: '{query}'")
        print(f"Generating article for: '{query}'")
        
        # Generate response
        response = generate_chat_response(writing_style, context, query)

        # Prompt user for the file name
        file_name = prompt_for_file_name()
        save_article_to_file(response, file_name)
        
        print(f"The article has been saved to '{file_name}'.")
        return 0

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return 1

def main():
    """Main function to handle command-line arguments and run the article writer"""
    parser = argparse.ArgumentParser(description="AI Article Writer")
    parser.add_argument("--query", type=str, help="Article query")
    args = parser.parse_args()
    
    return start(query=args.query)

# Start the process
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
