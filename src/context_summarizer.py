import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
import json

load_dotenv('config/.env')

def summarize_context():
    """
    Summarize the context from the JSON file and save it to a text file
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Load JSON file
        with open("data/context.json", "r") as file:
            json_data = json.load(file)
        
        if not json_data:
            print("Warning: No context data found to summarize.")
            return 1

        llm = LLM(model="groq/llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))

        summarizer = Agent(
            role='Summarizer', # Agent's job title/function
            goal='Create detailed llm readable detailed summaries of the given info without hallucination', # Agent's main objective
            backstory='Technical writer who excels at extracting and formatting all relevant useful data', # Agent's background/expertise
            llm=llm, 
            verbose=False # Show agent's thought process as it completes its task
        )

        summary_task = Task(
            description=f'Summarize the following data as text : {json.dumps(json_data)}',
            expected_output="only a clear, detailed summary in points with no json.",
            agent=summarizer,
            output_file="data/context.txt"
        )

        # Create crew to manage agents and task workflow
        crew = Crew(
            agents=[summarizer], # Agents to include in your crew
            tasks=[summary_task], # Tasks in execution order
            verbose=False
        )

        result = crew.kickoff()
        print("\nContext summarization completed successfully!")
        return 0
        
    except FileNotFoundError:
        print("Error: Context JSON file not found. Please run web context extraction first.")
        return 1
    except Exception as e:
        print(f"Error during context summarization: {e}")
        return 1

if __name__ == "__main__":
    exit_code = summarize_context()
    exit(exit_code)
