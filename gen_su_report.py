
import requests
import base64
import os
from dotenv import load_dotenv
import lib.slack_manager as slack_manager
import lib.notion_manager as notion_manager
import lib.report_manager as report_manager

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
    # get current sprint name
    sprint_name = notion_manager.get_sprint(JIRA_URL, JIRA_USER_NAME, JIRA_API_TOKEN)

    # sync status from Jira and update notion
    notion_manager.update(JIRA_URL, JIRA_USER_NAME, DATABASE_ID, JIRA_API_TOKEN, NOTION_TOKEN)

    # get work records and send to Slack
    work_record = notion_manager.get_notion_work_record(sprint_name, DATABASE_ID, NOTION_TOKEN)

    report = report_manager.get_su_report(work_record)
    
    # send message to slack
    slack_manager.send_to_slack(SLACK_WEBHOOK_URL, report)

if __name__ == "__main__":
    main()
