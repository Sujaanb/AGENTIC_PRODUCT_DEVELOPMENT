from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv
load_dotenv()  
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators
# src/website_automation/crew.py (top of file, before the Crew class)
import json, requests
from typing import Tuple, Union, Dict, Any
from requests.auth import HTTPBasicAuth
import os 

def validate_stories_json(result: Any) -> Tuple[bool, Any]:
    """Validate that the BA output is valid JSON.
    
    If the output is a TaskOutput, extract its raw content.
    """
    # If result is not str, check if it has a "raw" attribute.
    if not isinstance(result, (str, bytes, bytearray)):
        result = getattr(result, "raw", str(result))
    try:
        data = json.loads(result)  # parse JSON string
        return (True, data)        # valid JSON, return parsed data
    except json.JSONDecodeError as e:
        return (False, {"error": "Invalid JSON format", "code": "JSON_ERROR"})

def push_stories_to_jira(stories: list) -> None:
    """Create a JIRA issue for each user story in the list."""
    # Load JIRA credentials from environment variables
    jira_url = os.getenv("JIRA_BASE_URL")
    jira_user = os.getenv("JIRA_USER_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")
    if not jira_url or not jira_user or not jira_token:
        print("JIRA credentials not set. Skipping JIRA push.")
        return
    # Prepare JIRA issue payload for each story
    for story in stories:
        fields = {
            "project": {"key": "SCRUM"},      # TODO: replace with actual project key
            "summary": story.get("summary", "No summary provided"),
            "description": story.get("description", ""),
            "issuetype": {"name": "Story"}
        }
        response = requests.post(
            jira_url.rstrip("/") + "/rest/api/2/issue",
            json={"fields": fields},
            auth=HTTPBasicAuth(jira_user, jira_token),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 201:
            print(f"Created JIRA issue for story: {story.get('title')}")
        else:
            print(f"Failed to create JIRA issue for {story.get('title')}: {response.text}")


response_template = """
Please generate a JSON array of user stories following this structure:
{{ .Response }}
[
    {
        "number": <integer>,
        "summary": "<short title>",
        "description": "<detailed user story>"
    },
    ...
]
"""

# src/website_automation/crew.py
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai_tools import PDFSearchTool, FileReadTool, FileWriterTool


@CrewBase
class WebsiteAutomationCrew:
    """Crew that coordinates Manager, BA, Designer, Developer, Tester agents to build a website"""

    @agent
    def manager(self) -> Agent:
        return Agent(config=self.agents_config['manager'], verbose=True)
    
    @agent
    def business_analyst(self) -> Agent:
        # Equip BA with PDF search tool to read PDFs
        return Agent(
            config=self.agents_config['business_analyst'],
            response_template = response_template,
            verbose=True,
            tools=[PDFSearchTool()]   # allows semantic search in PDF files&#8203;:contentReference[oaicite:12]{index=12}
        )
    
    @agent
    def designer(self) -> Agent:
        return Agent(config=self.agents_config['designer'], verbose=True)
    
    @agent
    def developer(self) -> Agent:
        # Developer can write to files and also read files if needed
        return Agent(
            config=self.agents_config['developer'],
            verbose=True,
            tools=[FileWriterTool(), FileReadTool()]
        )
    
    @agent
    def tester(self) -> Agent:
        # Tester can read files to inspect the output code
        return Agent(
            config=self.agents_config['tester'],
            verbose=True,
            tools=[FileReadTool()]
        )

    @task
    def user_stories_task(self) -> Task:
        return Task(
            config=self.tasks_config['user_stories_task'],
            guardrail=validate_stories_json,   # validate JSON output
            max_retries=2,                     # retry BA task up to 2 times if JSON invalid
            # callback to push stories to JIRA after success:
            callback=self._after_stories
        )
    
    def _after_stories(self, output: Task) -> Task:
        """Callback after user_stories_task completes successfully."""
        try:
            # Convert the output (which should be JSON string) to list
            stories = output.json_dict or json.loads(output.raw)
            push_stories_to_jira(stories)   # push to JIRA
        except Exception as e:
            print(f"Error in after_stories callback: {e}")
        return output  # pass through output to next task
    
    @task
    def design_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_task'],
            output_file='design/design.txt'
        )
    
    @task
    def development_task(self) -> Task:
        return Task(
            config=self.tasks_config['development_task']
            # Developer will use FileWriterTool to actually write files, 
            # so we don't capture output in a single file here.
        )
    
    @task
    def testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['testing_task'],
            # If testing finds issues, we'll automatically trigger the fix task
            callback=self.fix_task
        )
    
    @task
    def fix_task(self) -> Task:
        return Task(
            config=self.tasks_config['fix_task'],
            callback=self._track_fix_iterations
        )
    
    def _track_fix_iterations(self, output: Task) -> Task:
        """Callback to handle looping of test->fix up to 4 tries."""
        # Initialize or increment the iteration counter
        self.fix_iteration = getattr(self, "fix_iteration", 0) + 1
        # Check tester's last output to see if issues were found
        if self.fix_iteration < 4 and "ISSUES FOUND:" in output.context.get('testing_task', '').upper():
            # If issues still present and under retry limit, run tests again
            return self.testing_task()
        else:
            # Either tests passed or max retries reached; end loop.
            return output

    @crew
    def crew(self) -> Crew:
        """Assemble the crew and set execution process."""
        return Crew(
            agents=self.agents,   # all agents defined above
            tasks=self.tasks,     # all tasks defined above
            process=Process.sequential,  # run tasks in sequence (with our callbacks handling loops)
            verbose=True
        )
print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
