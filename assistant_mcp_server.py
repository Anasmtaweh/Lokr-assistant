import os
import json
import logging
import contextlib
import sys
import threading
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from modes.orchestrator import run_assistant

# Setup basic logging to stderr and a file
log_file = "/tmp/mcp_server_debug.log"
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Resolve absolute paths
_PROJECT_ROOT = Path(__file__).resolve().parent
_DEMO_APP_PATH = Path("/home/anas/MyProjects/pet-ai-project")

# Initialize FastMCP
mcp = FastMCP("Lokr Assistant Pipeline")

# Global TASKS dictionary to hold background task states
TASKS = {}

def _run_pipeline_background(task_id: str, user_input: str):
    """Background thread function to run the Lokr pipeline and update TASKS."""
    try:
        # Redirect stdout to stderr to prevent breaking the MCP JSON-RPC protocol
        with contextlib.redirect_stdout(sys.stderr):
            result = run_assistant(
                user_input=user_input,
                project_path=str(_DEMO_APP_PATH),
                model="accounts/fireworks/models/glm-5p3-flash",
                use_lokr=True,
                progress_callback=lambda msg: logger.info(f"Progress: {msg}"),
                api_type="openai",
                base_url="https://api.fireworks.ai/inference/v1",
                api_key=os.environ.get("API_KEY")
            )
        TASKS[task_id]["status"] = "done"
        TASKS[task_id]["result"] = result
    except Exception as e:
        logger.error(f"Pipeline error for task {task_id}: {e}")
        TASKS[task_id]["status"] = "error"
        TASKS[task_id]["error"] = str(e)


def _start_background_task(user_input: str) -> str:
    """Helper to start the background pipeline and return a task_id."""
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running"}
    thread = threading.Thread(target=_run_pipeline_background, args=(task_id, user_input))
    thread.daemon = True
    thread.start()
    return json.dumps({"task_id": task_id, "status": "running"})


@mcp.tool()
def run_repair(issue_description: str, target_file: str = "") -> str:
    """
    Run the Lokr Assistant pipeline in Repair mode to diagnose and fix a bug/vulnerability.
    This tool returns immediately with a task_id. You must use the check_task tool to poll for the actual result.
    
    Args:
        issue_description (str): Description of the bug, unexpected behavior, or security issue.
        target_file (str, optional): A target file path relative to lokr-demo-app to focus on.
    """
    user_input = f"Repair this issue:\n{issue_description}"
    if target_file:
        user_input += f"\nRelevant file: {target_file}"
    return _start_background_task(user_input)


@mcp.tool()
def run_review(diff_content: str) -> str:
    """
    Run the Lokr Assistant pipeline in Review mode to analyze a code diff.
    This tool returns immediately with a task_id. You must use the check_task tool to poll for the actual result.
    
    Args:
        diff_content (str): The code diff to review (unified diff format).
    """
    user_input = f"Review this diff:\n{diff_content}"
    return _start_background_task(user_input)


@mcp.tool()
def run_prevent(changes_summary: str) -> str:
    """
    Run the Lokr Assistant pipeline in Prevent mode to determine if changes are safe to deploy.
    This tool returns immediately with a task_id. You must use the check_task tool to poll for the actual result.
    
    Args:
        changes_summary (str): A summary of the changes or diff to check for deployment readiness.
    """
    user_input = f"Check if this change is safe to deploy:\n{changes_summary}"
    return _start_background_task(user_input)


@mcp.tool()
def check_task(task_id: str) -> str:
    """
    Check the status of a background Lokr Assistant pipeline task.
    You must poll this repeatedly (e.g., every 10-15 seconds) until the status is "done" or "error".
    A single run can take 2+ minutes including revision cycles, so do not call once and stop.
    
    Args:
        task_id (str): The ID of the task to check.
    """
    if task_id not in TASKS:
        return json.dumps({"status": "error", "error": f"Task ID {task_id} not found."})
    
    return json.dumps(TASKS[task_id], indent=2)


def main():
    logger.info("Starting Lokr Assistant MCP Server...")
    # FastMCP automatically configures stdio transport for the run() call
    mcp.run()

if __name__ == "__main__":
    main()
