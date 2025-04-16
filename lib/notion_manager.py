import requests
import base64
from lib import request_utils

# Constants
STATUS_MAPPING = {
    "Open": "1. Open",
    "In Progress": "3. In Progress",
    "Code Review": "4. Code Review",
    "Ready for QA": "5. Ready for QA",
    "Reopened": "6. Reopened",
    "Closed": "7. Closed"
}

TYPE_TO_TAG_MAPPING = {
    "Bug": "Fix"
}

# Helper functions
def _get_tag_from_issue(issue):
    """Get tag from issue based on its type and parent"""
    fields = issue["fields"]
    if fields["issuetype"]["name"] == "Story":
        return f"Feat - {fields['parent']['fields']['summary']}" if "parent" in fields else ""
    return TYPE_TO_TAG_MAPPING.get(fields["issuetype"]["name"], fields["issuetype"]["name"])

def _create_tag_page(tag_name, database_id, token):
    """Create a new page in the relation table for a tag"""
    print(f"Creating new tag page: {tag_name}")
    notion_url = "https://api.notion.com/v1/pages"
    headers = request_utils.make_headers(token)
    
    request_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": tag_name}}]}
        }
    }
    
    response = requests.post(notion_url, headers=headers, json=request_data)
    response.raise_for_status()
    return response.json()["id"]

def get_tag_page_id(tag_name, database_id, token):
    """Get the page ID for a given tag name from the tags database"""
    notion_query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = request_utils.make_headers(token)
    
    search_payload = {
        "filter": {
            "property": "Name",
            "title": {
                "equals": tag_name
            }
        }
    }
    
    response = requests.post(notion_query_url, headers=headers, json=search_payload)
    response.raise_for_status()
    data = response.json()
    
    if data["results"]:
        return data["results"][0]["id"]
    
    # If tag not found, create a new page
    return _create_tag_page(tag_name, database_id, token)

# Jira related functions
def get_sprint(jira_url, user_name, token):
    """Get the current active sprint name from Jira"""
    print("Getting active sprint from Jira...")
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

# Notion database operations
def get_notion_work_record(sprint_name, database_id, token):
    """Get work records from Notion database for a specific sprint"""
    print(f"Getting work records for sprint: {sprint_name}")
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
    """Format Notion work record into a standardized format"""
    formatted_work_records = []
    for record in work_record["results"]:
        jira_id = record["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
        title = record["properties"]["Title"]["title"][0]["text"]["content"]
        status = record["properties"]["Status"]["select"]["name"]
        jira_url = f"https://gogotech.atlassian.net/browse/{jira_id}"

        formatted_work_records.append({
            "jiraId": jira_id,
            "title": title,
            "status": status,
            "jiraUrl": jira_url
        })

    formatted_work_records.sort(key=lambda x: x["status"])
    return formatted_work_records

# Page operations
def insert_data_to_notion(title, key, status, sprint, tag, database_id, token, tags_database_id):
    """Insert a new page into Notion database"""
    print(f"Inserting new page: {key} - {title}")
    notion_url = "https://api.notion.com/v1/pages"
    url = f"https://gogotech.atlassian.net/browse/{key}"
    
    # Initialize properties with required fields
    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Jira Id": {"rich_text": [{"text": {"content": key, "link": {"url": url}}}]},
        "Status": {"select": {"name": status}},
        "Sprint": {"select": {"name": sprint}}
    }
    
    # Only add Tags if tag is not empty
    if tag:
        tag_page_id = get_tag_page_id(tag, tags_database_id, token)
        properties["Tags"] = {"relation": [{"id": tag_page_id}]}
    
    request_data = {
        "parent": {"database_id": database_id},
        "properties": properties
    }

    headers = request_utils.make_headers(token)
    response = requests.post(notion_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Successfully inserted: {key} - {title}")

def update_notion_page(key, notion_page_id, status, tag, token, tags_database_id):
    """Update an existing Notion page"""
    notion_update_url = f"https://api.notion.com/v1/pages/{notion_page_id}"
    
    headers = request_utils.make_headers(token)
    current_page = requests.get(notion_update_url, headers=headers)
    current_page.raise_for_status()
    current_data = current_page.json()
    
    # Initialize properties with required fields
    properties = {
        "Status": {"select": {"name": status}}
    }
    
    # Only update Tags if tag is not empty
    if tag:
        tag_page_id = get_tag_page_id(tag, tags_database_id, token)
        existing_relations = []
        if "Tags" in current_data["properties"] and "relation" in current_data["properties"]["Tags"]:
            existing_relations = current_data["properties"]["Tags"]["relation"]
        
        if not any(rel["id"] == tag_page_id for rel in existing_relations):
            existing_relations.append({"id": tag_page_id})
        
        properties["Tags"] = {"relation": existing_relations}
    
    request_data = {
        "properties": properties
    }
    
    response = requests.patch(notion_update_url, headers=headers, json=request_data)
    response.raise_for_status()
    print(f"Updated Notion page for Jira ID: {key}, Status: {status}, Tag: {tag}")

# Helper functions
def _check_and_insert_notion_page(notion_query_url, summary, key, status, sprint, tag, database_id, token, tags_database_id):
    """Check if a page exists and insert if it doesn't"""
    print(f"Checking page existence: {key}")
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
        insert_data_to_notion(summary, key, status, sprint, tag, database_id, token, tags_database_id)

def _update_status_from_jira(notion_query_url, sprint_name, user_name, jira_token, notion_token, tags_database_id):
    """Update Notion pages based on Jira status"""
    print(f"Updating status from Jira for sprint: {sprint_name}")
    headers = request_utils.make_headers(notion_token)
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
            "Authorization": "Basic " + base64.b64encode(f"{user_name}:{jira_token}".encode()).decode(),
            "Content-Type": "application/json"
        }

        jira_response = requests.get(jira_issue_url, headers=jira_headers)
        jira_response.raise_for_status()
        jira_data = jira_response.json()
        status = STATUS_MAPPING.get(jira_data["fields"]["status"]["name"], jira_data["fields"]["status"]["name"])
        tag = _get_tag_from_issue(jira_data)

        update_notion_page(jira_id, notion_page_id, status, tag, notion_token, tags_database_id)

# Main update function
def update(jira_url, user_name, database_id, jira_token, notion_token, tags_database_id):
    """Main function to sync Jira and Notion data"""
    print("Starting sync process...")
    notion_query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    sprint_name = get_sprint(jira_url, user_name, jira_token)
    if not sprint_name:
        print("No active sprint found")
        return

    print(f"Active sprint: {sprint_name}")

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
        tag = _get_tag_from_issue(issue)

        for sprint in sprints:
            if sprint["state"] == "active":
                _check_and_insert_notion_page(notion_query_url, summary, key, status, sprint_name, tag, database_id, notion_token, tags_database_id)

    if sprint_name:
        _update_status_from_jira(notion_query_url, sprint_name, user_name, jira_token, notion_token, tags_database_id)
    
    print("Sync process completed")

