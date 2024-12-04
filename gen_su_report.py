
import requests
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

STATUS_MAPPING = {
    "Open": "1. Open",
    "In Progress": "3. In Progress",
    "Code Review": "4. Code Review",
    "Ready for QA": "5. Ready for QA",
    "Reopened": "6. Reopened",
    "Closed": "7. Closed"
}

jira_url = "https://gogotech.atlassian.net/rest/api/3/search?jql=filter=11407"
notion_query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

def make_headers(auth_token):
    return {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Notion-Version": "2021-05-13"
    }

def get_sprint():
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{JIRA_USER_NAME}:{JIRA_API_TOKEN}".encode()).decode(),
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

def get_notion_work_record(sprint_name):
    headers = make_headers(NOTION_TOKEN)
    search_payload = {
        "filter": {
            "property": "Sprint",
            "select": {"equals": sprint_name}
        }
    }
    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    return response.json()

def get_formatted_work_record(work_record):
    formatted_work_records = []
    for record in work_record["results"]:
        jira_id = record["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
        title = record["properties"]["Title"]["title"][0]["text"]["content"]
        status = record["properties"]["Status"]["select"]["name"]
        jira_url = f"https://gogotech.atlassian.net/browse/{jira_id}"
        formatted_work_records.append({"jiraId": jira_id, "title": title, "status": status, "jiraUrl": jira_url})

    # Sort by status
    formatted_work_records.sort(key=lambda x: x["status"])

    return "\n".join(
        f"- <{record['jiraUrl']}|{record['jiraId']}> {record['title']} `{record['status'].split('. ')[-1]}`"
        for record in formatted_work_records
    )

def send_to_slack(msg):
    payload = {"text": msg}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    response.raise_for_status()
    print("Message sent to Slack")

def insert_data_to_notion(title, key, status, sprint):
    notion_url = "https://api.notion.com/v1/pages"
    url = f"https://gogotech.atlassian.net/browse/{key}"
    
    request_data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "Jira Id": {"rich_text": [{"text": {"content": key, "link": {"url": url}}}]},
            "Status": {"select": {"name": status}},
            "Sprint": {"select": {"name": sprint}}
        }
    }

    headers = make_headers(NOTION_TOKEN)
    response = requests.post(notion_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Inserted to Notion: {key}, {title}")

def check_and_insert_notion_page(summary, key, status, sprint):
    headers = make_headers(NOTION_TOKEN)

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
        insert_data_to_notion(summary, key, status, sprint)

def update_notion_page(key, notion_page_id, status):
    notion_update_url = f"https://api.notion.com/v1/pages/{notion_page_id}"
    request_data = {
        "properties": {
            "Status": {"select": {"name": status}}
        }
    }

    headers = make_headers(NOTION_TOKEN)
    response = requests.patch(notion_update_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Updated Notion page for Jira ID: {key}, Status: {status}")

def update_status_from_jira(sprint_name):
    headers = make_headers(NOTION_TOKEN)

    search_payload = {
        "filter": {"property": "Sprint", "select": {"equals": sprint_name}}
    }

    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    notion_data = response.json()

    for page in notion_data["results"]:
        jira_id = page["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
        notion_page_id = page["id"]

        jira_issue_url = f"https://gogotech.atlassian.net/rest/api/3/issue/{jira_id}"
        jira_headers = {
            "Authorization": "Basic " + base64.b64encode(f"{JIRA_USER_NAME}:{JIRA_API_TOKEN}".encode()).decode(),
            "Content-Type": "application/json"
        }

        jira_response = requests.get(jira_issue_url, headers=jira_headers)
        jira_response.raise_for_status()
        jira_data = jira_response.json()
        status = STATUS_MAPPING.get(jira_data["fields"]["status"]["name"], jira_data["fields"]["status"]["name"])

        update_notion_page(jira_id, notion_page_id, status)

def main():

    sprint_name = get_sprint()
    if not sprint_name:
        print("No active sprint found")
        return

    # Check and update Notion
    jira_url = "https://gogotech.atlassian.net/rest/api/3/search?jql=filter=11407"
    jira_headers = {
        "Authorization": "Basic " + base64.b64encode(f"{JIRA_USER_NAME}:{JIRA_API_TOKEN}".encode()).decode(),
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

    
    # Get work records and send to Slack
    work_record = get_notion_work_record(sprint_name)
    msg = get_formatted_work_record(work_record)
    send_to_slack(msg)

if __name__ == "__main__":
    main()
