import requests
import base64


STATUS_MAPPING = {
    "Open": "1. Open",
    "In Progress": "3. In Progress",
    "Code Review": "4. Code Review",
    "Ready for QA": "5. Ready for QA",
    "Reopened": "6. Reopened",
    "Closed": "7. Closed"
}

def get_sprint(jira_url, user_name, token):
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{user_name}:{token}".encode()).decode(),
        "Content-Type": "application/json"
    }
    response = requests.get(jira_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    for issue in data["issues"]:
        sprints = issue["fields"].get("customfield_10008", [])
        for sprint in sprints:
            if sprint["state"] == "active":
                return sprint["name"]
    return None


def update(jira_url, user_name, token):
    sprint_name = get_sprint()
    if not sprint_name:
        print("No active sprint found")
        return

    # Check and update Notion
    jira_headers = {
        "Authorization": "Basic " + base64.b64encode(f"{user_name}:{token}".encode()).decode(),
        "Content-Type": "application/json"
    }

    response = requests.get(jira_url, headers=jira_headers)
    response.raise_for_status()
    data = response.json()

    for issue in data["issues"]:
        summary = issue["fields"]["summary"]
        key = issue["key"]
        status = STATUS_MAPPING.get(issue["fields"]["status"]["name"], issue["fields"]["status"]["name"])
        sprints = issue["fields"].get("customfield_10008", [])

        for sprint in sprints:
            if sprint["state"] == "active":
                check_and_insert_notion_page(summary, key, status, sprint_name)

    if sprint_name:
        update_status_from_jira(sprint_name)
