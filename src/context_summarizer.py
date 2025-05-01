import os
import json
import argparse
from crewai import Agent, Task, Crew, LLM
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
        with open(context_json_path, "r") as file:
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
            goal='Create detailed llm readable detailed summaries of the given info without hallucination',  # Agent's main objective
            backstory='Technical writer who excels at extracting and formatting all relevant useful data',  # Agent's background/expertise
            llm=llm,
            verbose=False  # Show agent's thought process as it completes its task
        )
        
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
