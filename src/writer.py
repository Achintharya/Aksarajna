import os
import json
import ollama
import sys  # Import sys to read command line arguments
from datetime import datetime

# Function to save the article to a file
def save_article_to_file(response, file_name):
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(response)
    print(f"The article has been saved to '{file_name}'.")

# Function to prompt for file name
def prompt_for_file_name(query):
    # Use the query to create a file name
    file_name = query.replace(" ", "_")  # Replace spaces with underscores for the file name
    return f"../articles/{file_name}.txt"

# Function to generate a chat response
def generate_chat_response(writing_style, context, query):
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    prompt_message = f"Current Date and Time: {current_date}, {current_time}\n" \
                     f"Writing Style Example: {writing_style}\n" \
                     f"Context: {context}\n" \
                     f"User Query: {query}"

    try:
        # Ensure the model parameter is a string and messages is a list
        response = ollama.chat(
            model='mistral',
            messages=[
                {'role': "system", 'content': "### You are an AI that imitates a writing style (without including any info from it) to write nonredundantly about the context provided, WITH NO HALLUCINATION. ###"},
                {'role': "user", 'content': prompt_message}
            ]
        )

        return response['message']['content']

    except Exception as error:
        print(f"Error generating response: {error}")
        return "Sorry, I couldn't process your request."

def start():
    try:
        # Read context and writing style
        with open("../data/context.txt", "r", encoding='utf-8') as file:
            context = file.read()

        with open("../data/writing_style.txt", "r", encoding='utf-8') as file:
            writing_style = file.read()

        if not context:
            print("No relevant context found. Proceeding with minimal guidance.")

        # Get the query from command line arguments
        query = sys.argv[1]

        # Generate response
        response = generate_chat_response(writing_style, context, query)

        # Prompt user for the file name using the query
        file_name = prompt_for_file_name(query)  
        save_article_to_file(response, file_name)

    except Exception as error:
        print(f"An error occurred: {error}")

# Start the process
if __name__ == "__main__":
    start()
