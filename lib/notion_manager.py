import requests
import base64
from lib import request_utils

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

def update(jira_url, user_name, database_id, jira_token, notion_token):
    notion_query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    sprint_name = get_sprint(jira_url, user_name, jira_token)
    if not sprint_name:
        print("No active sprint found")
        return

    # Check and update Notion
    jira_headers = {
        "Authorization": "Basic " + base64.b64encode(f"{user_name}:{jira_token}".encode()).decode(),
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
                _check_and_insert_notion_page(notion_query_url, summary, key, status, sprint_name, database_id, notion_token)

    if sprint_name:
        _update_status_from_jira(notion_query_url, sprint_name, user_name, jira_token, notion_token)

def get_notion_work_record(sprint_name, database_id, token):
    notion_query_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    headers = request_utils.make_headers(token)
    search_payload = {
        "filter": {
            "property": "Sprint",
            "select": {"equals": sprint_name}
        }
    }
    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    return _format_record(response.json())
     
def _format_record(work_record):
    formatted_work_records = []
    for record in work_record["results"]:
        jira_id = record["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
        title = record["properties"]["Title"]["title"][0]["text"]["content"]
        status = record["properties"]["Status"]["select"]["name"]
        url = f"https://gogotech.atlassian.net/browse/{jira_id}"
        formatted_work_records.append({"jiraId": jira_id, "title": title, "status": status, "jiraUrl": url})

    # Sort by status
    formatted_work_records.sort(key=lambda x: x["status"])

    return "\n".join(
        f"- <{record['jiraUrl']}|{record['jiraId']}> {record['title']} `{record['status'].split('. ')[-1]}`"
        for record in formatted_work_records
    )

def _check_and_insert_notion_page(notion_query_url, summary, key, status, sprint, database_id, token):
    headers = request_utils.make_headers(token)

    search_payload = {
        "filter": {
            "and": [
                {"property": "Sprint", "select": {"equals": sprint}},
                {"property": "Jira Id", "rich_text": {"equals": key}}
            ]
        }
    }

    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    search_data = response.json()

    if not search_data.get("results"):
        insert_data_to_notion(summary, key, status, sprint, database_id, token)

def insert_data_to_notion(title, key, status, sprint, database_id, token):
    notion_url = "https://api.notion.com/v1/pages"
    url = f"https://gogotech.atlassian.net/browse/{key}"
    
    request_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "Jira Id": {"rich_text": [{"text": {"content": key, "link": {"url": url}}}]},
            "Status": {"select": {"name": status}},
            "Sprint": {"select": {"name": sprint}}
        }
    }

    headers = request_utils.make_headers(token)
    response = requests.post(notion_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Inserted to Notion: {key}, {title}")

def _update_status_from_jira(notion_query_url, sprint_name, user_name, jira_token, notion_token):

    # notion
    headers = request_utils.make_headers(notion_token)

    search_payload = {
        "filter": {"property": "Sprint", "select": {"equals": sprint_name}}
    }

    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    notion_data = response.json()

    for page in notion_data["results"]:

        # jira
        jira_id = page["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
        notion_page_id = page["id"]

        jira_issue_url = f"https://gogotech.atlassian.net/rest/api/3/issue/{jira_id}"
        jira_headers = {
            "Authorization": "Basic " + base64.b64encode(f"{user_name}:{jira_token}".encode()).decode(),
            "Content-Type": "application/json"
        }

        jira_response = requests.get(jira_issue_url, headers=jira_headers)
        jira_response.raise_for_status()
        jira_data = jira_response.json()
        status = STATUS_MAPPING.get(jira_data["fields"]["status"]["name"], jira_data["fields"]["status"]["name"])

        update_notion_page(jira_id, notion_page_id, status, notion_token)

def update_notion_page(key, notion_page_id, status, token):
    notion_update_url = f"https://api.notion.com/v1/pages/{notion_page_id}"
    request_data = {
        "properties": {
            "Status": {"select": {"name": status}}
        }
    }

    headers = request_utils.make_headers(token)
    response = requests.patch(notion_update_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Updated Notion page for Jira ID: {key}, Status: {status}")
