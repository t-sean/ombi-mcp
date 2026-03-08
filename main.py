import logging
import requests
import os
from fastmcp import FastMCP

OMBI_API_KEY = os.getenv("OMBI_API_KEY")
OMBI_URL = os.getenv("OMBI_URL", "http://localhost:5379")
MCP_PORT = int(os.getenv("MCP_PORT", "7979"))
MCP_HOST = os.getenv("MCP_HOST", "localhost")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

if not OMBI_API_KEY:
    logging.error("OMBI_API_KEY environment variable is not set.")
    exit(1)

mcp = FastMCP()

def _make_api_request(endpoint: str, method: str = "GET", **kwargs) -> dict | list:
    """Make API request with consistent error handling."""
    try:
        response = requests.request(
            method,
            f"{OMBI_URL}/api/v1/{endpoint}",
            headers={"ApiKey": OMBI_API_KEY},
            **kwargs
        )
        
        # Handle empty responses (e.g., DELETE returning 200/204)
        if response.status_code == 204 or not response.content:
            return {"success": True}
        
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {e.response.status_code} {e.response.reason}" if hasattr(e, 'response') and e.response is not None else f"API request failed: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}

issue_status_map = {
    0: "Reported",
    1: "In Progress",
    2: "Completed"
}

@mcp.tool()
def get_issues() -> dict | list:
    """Fetch all issues from Ombi."""
    logging.info("Fetching issues from Ombi...")
    response = _make_api_request("Issues")
    
    # Handle error responses
    if isinstance(response, dict) and "error" in response:
        return response
    
    logging.info("Found %d issues.", len(response) if isinstance(response, list) else 0)
    # Map status codes to readable descriptions
    return [
        {
            "issueId": issue.get("id"),
            "title": issue.get("title"),
            "status": issue_status_map.get(issue.get("status"), "Unknown"),
            "created_at": issue.get("createdAt"),
            "subject": issue.get("subject"),
            "description": issue.get("description"),
            "category": issue.get("issueCategory", {}).get("value"),
            "comments": issue.get("comments", [])
        }
        for issue in response
    ]

@mcp.tool()
def set_issue_status(issue_id: int, status: int) -> dict:
    """Update the status of a specific issue. 0 for new, 1 for in progress, 2 for completed."""
    logging.info("Updating status of issue ID %d to %d...", issue_id, status)
    payload = {"status": status, "issueId": issue_id}
    response = _make_api_request(f"Issues/status", method="POST", json=payload)
    if "error" not in response:
        logging.info("Issue ID %d status updated successfully.", issue_id)
    return response

@mcp.tool()
def add_issue_comment(issue_id: int, comment: str) -> dict:
    """Add a comment to a specific issue."""
    logging.info("Adding comment to issue ID %d...", issue_id)
    payload = {"issueId": issue_id, "comment": comment}
    response = _make_api_request(f"Issues/comments", method="POST", json=payload)
    if "error" not in response:
        logging.info("Comment added to issue ID %d successfully.", issue_id)
    return response


if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
