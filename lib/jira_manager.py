import requests
import base64
import sys
from lib import request_utils

class JiraManager:
    def __init__(self, jira_url, user_name, token):
        """Initialize JiraManager with authentication details"""
        self.jira_url = jira_url
        self.user_name = user_name
        self.token = token
        self._headers = {
            "Authorization": "Basic " + base64.b64encode(f"{user_name}:{token}".encode()).decode(),
            "Content-Type": "application/json"
        }
        self.sprint_name = self.__get_active_sprint()

    def __get_active_sprint(self):
        """Private method to get the current active sprint name from Jira"""
        print("Getting active sprint from Jira...")
        data = self.get_tickets()

        for issue in data["issues"]:
            sprints = issue["fields"].get("customfield_10008", [])
            for sprint in sprints:
                if sprint["state"] == "active":
                    print(f"Active sprint: {sprint['name']}")
                    return sprint["name"]
        print("No active sprint found")
        sys.exit(1)  # Exit the script with error code 1 when no active sprint is found

    def get_tickets(self):
        """Get tickets from Jira API"""
        response = requests.get(self.jira_url, headers=self._headers)
        response.raise_for_status()
        return response.json()