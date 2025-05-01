import os
import json
import argparse
import sys
from crewai import Agent, Task, Crew, LLM

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from src.config import logger, config

def summarize_context():
    """
    Summarize the context from the JSON file and save it to a text file
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    context_json_path = config.get('paths.context_json')
    context_txt_path = config.get('paths.context_txt')
    
    logger.info(f"Starting context summarization from {context_json_path}")
    
    # Load JSON file
    try:
        with open(context_json_path, "r", encoding='utf-8') as file:
            json_data = json.load(file)
        
        if not json_data:
            logger.warning("Empty context data found in JSON file")
            print("Warning: No context data found to summarize.")
            return 1
            
        logger.info(f"Loaded {len(json_data)} context items from JSON file")
    except FileNotFoundError:
        logger.error(f"Context JSON file not found: {context_json_path}")
        print(f"Error: Context JSON file not found: {context_json_path}")
        print("Please run the web context extraction first.")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in context file: {e}")
        print(f"Error: Invalid JSON in context file: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error loading context JSON: {e}")
        print(f"Error loading context JSON: {e}")
        return 1

    # Get API key and model from configuration
    groq_api_key = config.get('api_keys.groq')
    if not groq_api_key:
        logger.error("Groq API key not found in configuration")
        print("Error: Groq API key not found. Please check your .env file.")
        return 1
    
    model_name = config.get('models.summarizer')
    logger.info(f"Using model: {model_name}")

    try:
        # Initialize LLM
        llm = LLM(model=model_name, api_key=groq_api_key)
        
        # Create summarizer agent
        summarizer = Agent(
            role='Summarizer',  # Agent's job title/function
            goal='Create detailed llm readable summaries of the given info without hallucination',  # Agent's main objective
            backstory='Technical writer who excels at extracting and formatting all relevant useful data',  # Agent's background/expertise
            llm=llm,
            verbose=False  # Show agent's thought process as it completes its task
        )
        
        try:
            # Create summarization task
            summary_task = Task(
                description=f'Summarize the following data as text : {json.dumps(json_data)}',
                expected_output="only a clear, detailed summary in points with no json.",
                agent=summarizer,
                output_file=context_txt_path
            )
            
            # Create crew to manage agents and task workflow
            crew = Crew(
                agents=[summarizer],  # Agents to include in your crew
                tasks=[summary_task],  # Tasks in execution order
                verbose=False
            )
            
            logger.info("Starting context summarization")
            print("Summarizing context data...")
            
            # Execute the summarization
            result = crew.kickoff()
            
            logger.info("Context summarization completed successfully")
            print("Context summarization completed successfully!")
        except Exception as e:
            logger.error(f"Error during LLM call: {e}")
            
            # If there's a rate limit error, try to provide a useful summary anyway
            if "rate_limit" in str(e).lower():
                logger.warning("Rate limit hit, creating a basic summary from the JSON data")
                
                # Create a basic summary from the JSON data
                basic_summary = "Here is a summary of the extracted information:\n\n"
                
                # Process each item in the JSON data
                for group_index, group in enumerate(json_data):
                    basic_summary += f"## Source Group {group_index + 1}\n\n"
                    
                    for item_index, item in enumerate(group):
                        if isinstance(item, dict) and "summary" in item:
                            basic_summary += f"* {item['summary']}\n"
                
                # Save the basic summary to the output file
                with open(context_txt_path, "w", encoding='utf-8') as file:
                    file.write(basic_summary)
                
                logger.info("Created basic summary from JSON data due to rate limit")
                print("Created basic summary from JSON data (rate limit reached)")
            else:
                # Re-raise the exception if it's not a rate limit error
                raise
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during context summarization: {e}")
        print(f"Error during context summarization: {e}")
        return 1

def main():
    """Main function to handle command-line arguments and run the summarization process"""
    parser = argparse.ArgumentParser(description="Context Summarization Tool")
    parser.parse_args()  # No arguments needed for now, but keeping for future extensibility
    
    return summarize_context()

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
