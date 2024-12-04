
import requests
import base64
import os
from dotenv import load_dotenv
from lib.slack_manager import slack_manager
from lib.notion_manager import notion_manager

# Load environment variables from .env file
load_dotenv()

# Environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
JIRA_URL = os.getenv("JIRA_URL")

def main():
    None # TODO

if __name__ == "__main__":
    main()
