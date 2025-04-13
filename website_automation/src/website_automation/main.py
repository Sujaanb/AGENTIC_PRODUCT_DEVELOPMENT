# src/website_automation/main.py
import os
from website_automation.crew import WebsiteAutomationCrew

# Ensure output directories exist
os.makedirs('src/website_automation/design', exist_ok=True)
os.makedirs('src/website_automation/output', exist_ok=True)

def run(user_prompt: str, docs_folder: str = "src/website_automation/knowledge"):
    """
    Run the multi-agent crew with the given user prompt and knowledge base folder.
    """
    # Prepare input for the crew. We pass the user prompt and optionally the path to documents.
    inputs = {
        "user_prompt": user_prompt,
        "docs_path": docs_folder
    }
    # Kick off the crew execution
    result = WebsiteAutomationCrew().crew().kickoff(inputs=inputs)
    print("\n=== Crew Execution Complete ===\n")
    # The final result is the output of the last task (fix_task or testing_task).
    print("Final Output:\n", result.raw if hasattr(result, 'raw') else result)
