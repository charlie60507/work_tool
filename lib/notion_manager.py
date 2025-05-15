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

class NotionManager:
    def __init__(self, notion_token, database_id, tags_database_id, jira_user_name, jira_token):
        """Initialize NotionManager with authentication and configuration details"""
        self.notion_token = notion_token
        self.database_id = database_id
        self.tags_database_id = tags_database_id
        self.jira_user_name = jira_user_name
        self.jira_token = jira_token
        self.notion_headers = request_utils.make_headers(notion_token)
        self.jira_headers = {
            "Authorization": "Basic " + base64.b64encode(f"{jira_user_name}:{jira_token}".encode()).decode(),
            "Content-Type": "application/json"
        }
        # Verify the connection
        self.__verify_connection()

    def __verify_connection(self):
        """Verify the connection to Notion API"""
        url = f"https://api.notion.com/v1/databases/{self.database_id}"
        response = requests.get(url, headers=self.notion_headers)
        response.raise_for_status()

    def get_notion_work_record(self, sprint_name):
        """Get work records from Notion database for a specific sprint"""
        print(f"Getting work records for sprint: {sprint_name}")
        notion_query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        search_payload = {
            "filter": {
                "property": "Sprint",
                "select": {"equals": sprint_name}
            }
        }
        
        response = requests.post(notion_query_url, headers=self.notion_headers, json=search_payload)
        response.raise_for_status()
        return self.__format_record(response.json())

    def __format_record(self, work_record):
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

    def __get_tag_from_issue(self, issue):
        """Get tag from issue based on its type and parent"""
        fields = issue["fields"]
        if fields["issuetype"]["name"] == "Story":
            return f"Feat - {fields['parent']['fields']['summary']}" if "parent" in fields else ""
        return TYPE_TO_TAG_MAPPING.get(fields["issuetype"]["name"], fields["issuetype"]["name"])

    def __create_tag_page(self, tag_name):
        """Create a new page in the relation table for a tag"""
        print(f"Creating new tag page: {tag_name}")
        notion_url = "https://api.notion.com/v1/pages"
        
        request_data = {
            "parent": {"database_id": self.tags_database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": tag_name}}]}
            }
        }
        
        response = requests.post(notion_url, headers=self.notion_headers, json=request_data)
        response.raise_for_status()
        return response.json()["id"]

    def __get_tag_page_id(self, tag_name):
        """Get the page ID for a given tag name from the tags database"""
        notion_query_url = f"https://api.notion.com/v1/databases/{self.tags_database_id}/query"
        
        search_payload = {
            "filter": {
                "property": "Name",
                "title": {
                    "equals": tag_name
                }
            }
        }
        
        response = requests.post(notion_query_url, headers=self.notion_headers, json=search_payload)
        response.raise_for_status()
        data = response.json()
        
        if data["results"]:
            return data["results"][0]["id"]
        
        # If tag not found, create a new page
        return self.__create_tag_page(tag_name)

    def __insert_data_to_notion(self, title, key, status, sprint, tag):
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
            tag_page_id = self.__get_tag_page_id(tag)
            properties["Tags"] = {"relation": [{"id": tag_page_id}]}
        
        request_data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        response = requests.post(notion_url, headers=self.notion_headers, json=request_data)
        response.raise_for_status()
        print(f"Successfully inserted: {key} - {title}")

    def __update_notion_page(self, key, notion_page_id, status, tag):
        """Update an existing Notion page"""
        notion_update_url = f"https://api.notion.com/v1/pages/{notion_page_id}"
        
        current_page = requests.get(notion_update_url, headers=self.notion_headers)
        current_page.raise_for_status()
        current_data = current_page.json()
        
        # Initialize properties with required fields
        properties = {
            "Status": {"select": {"name": status}}
        }
        
        # Only update Tags if tag is not empty
        if tag:
            tag_page_id = self.__get_tag_page_id(tag)
            existing_relations = []
            if "Tags" in current_data["properties"] and "relation" in current_data["properties"]["Tags"]:
                existing_relations = current_data["properties"]["Tags"]["relation"]
            
            if not any(rel["id"] == tag_page_id for rel in existing_relations):
                existing_relations.append({"id": tag_page_id})
            
            properties["Tags"] = {"relation": existing_relations}
        
        request_data = {
            "properties": properties
        }
        
        response = requests.patch(notion_update_url, headers=self.notion_headers, json=request_data)
        response.raise_for_status()
        print(f"Updated Notion page for Jira ID: {key}, Status: {status}, Tag: {tag}")

    def __check_and_insert_notion_page(self, notion_query_url, summary, key, status, sprint, tag):
        """Check if a page exists and insert if it doesn't"""
        print(f"Checking page existence: {key}")
        search_payload = {
            "filter": {
                "and": [
                    {"property": "Sprint", "select": {"equals": sprint}},
                    {"property": "Jira Id", "rich_text": {"equals": key}}
                ]
            }
        }

        response = requests.post(notion_query_url, headers=self.notion_headers, json=search_payload)
        response.raise_for_status()
        search_data = response.json()

        if not search_data.get("results"):
            self.__insert_data_to_notion(summary, key, status, sprint, tag)

    def __update_from_jira(self, notion_query_url, sprint_name):
        """Update Notion pages based on Jira status"""
        search_payload = {
            "filter": {"property": "Sprint", "select": {"equals": sprint_name}}
        }

        response = requests.post(notion_query_url, headers=self.notion_headers, json=search_payload)
        response.raise_for_status()
        notion_data = response.json()

        for page in notion_data["results"]:
            jira_id = page["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
            notion_page_id = page["id"]

            jira_issue_url = f"https://gogotech.atlassian.net/rest/api/3/issue/{jira_id}"
            jira_response = requests.get(jira_issue_url, headers=self.jira_headers)
            jira_response.raise_for_status()
            jira_data = jira_response.json()
            status = STATUS_MAPPING.get(jira_data["fields"]["status"]["name"], jira_data["fields"]["status"]["name"]) # update status from Jira
            # TODO: add sp
            tag = self.__get_tag_from_issue(jira_data) # update tag from Jira

            self.__update_notion_page(jira_id, notion_page_id, status, tag)

    def update(self, jira_data, sprint_name):
        """Main function to sync Jira and Notion data"""
        print("Starting sync process...")
        notion_query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        # Insert new added tickets to Notion
        for issue in jira_data["issues"]:
            summary = issue["fields"]["summary"]
            key = issue["key"]
            status = STATUS_MAPPING.get(issue["fields"]["status"]["name"], issue["fields"]["status"]["name"])
            sprints = issue["fields"].get("customfield_10008", [])
            tag = self.__get_tag_from_issue(issue)

            for sprint in sprints:
                if sprint["state"] == "active":
                    self.__check_and_insert_notion_page(notion_query_url, summary, key, status, sprint_name, tag)

        # Update status from Jira into Notion
        if sprint_name:
            self.__update_from_jira(notion_query_url, sprint_name)
        
        print("Sync process completed")

