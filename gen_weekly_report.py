import os
from datetime import datetime
from dotenv import load_dotenv
import lib.slack_manager as slack_manager
from lib.notion_manager import NotionManager
import lib.report_manager as report_manager
from lib.jira_manager import JiraManager


# Load environment variables from .env file
load_dotenv()

# Environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
JIRA_URL = os.getenv("JIRA_URL")
TYPES_DATABASE_ID = os.getenv("TYPES_DATABASE_ID")


def main():
    # Only run on Friday
    if datetime.utcnow().strftime('%A') != 'Friday':
        print("Not Friday. Task skipped.")
        return

    # Initialize managers
    jira_manager = JiraManager(JIRA_URL, JIRA_USER_NAME, JIRA_API_TOKEN)
    notion_manager = NotionManager(
        notion_token=NOTION_TOKEN,
        database_id=DATABASE_ID,
        tags_database_id=TYPES_DATABASE_ID,
        jira_user_name=JIRA_USER_NAME,
        jira_token=JIRA_API_TOKEN
    )

    # Get jira data
    jira_data = jira_manager.get_tickets()

    # Sync status from Jira and update notion
    notion_manager.update(jira_data, jira_manager.sprint_name)

    # Get work records and send to Slack
    work_record = notion_manager.get_notion_work_record(jira_manager.sprint_name)
    
    # Get weekly report
    report = report_manager.get_weekly_report(work_record)

    # Send message to slack
    slack_manager.send_to_slack(SLACK_WEBHOOK_URL, report)


if __name__ == "__main__":
    main()
