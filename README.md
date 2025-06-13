# Work Record Bot

A Python-based automation tool that integrates Jira, Notion, and Slack to generate and send automated work reports. This tool helps track project progress by syncing data between Jira tickets and Notion databases, then generating formatted reports sent to Slack.

## Features

- **Jira Integration**: Fetches active sprint tickets and their status
- **Notion Sync**: Updates work records in Notion databases based on Jira data
- **Automated Reporting**: Generates weekly and sprint update reports
- **Slack Integration**: Sends formatted reports directly to Slack channels
- **Scheduled Execution**: Supports automated execution via Heroku workers

## Architecture

![Screenshot 2025-06-14 at 1 07 52 AM](https://github.com/user-attachments/assets/d9321aec-17ce-439d-9728-5be64700ef2f)

## Project Structure

```
work_tools/
├── lib/                    # Core modules
│   ├── jira_manager.py    # Jira API integration
│   ├── notion_manager.py  # Notion API integration
│   ├── report_manager.py  # Report generation logic
│   ├── slack_manager.py   # Slack webhook integration
│   └── request_utils.py   # HTTP request utilities
├── gen_su_report.py       # Sprint update report generator
├── gen_weekly_report.py   # Weekly report generator
├── requirements.txt       # Python dependencies
├── Procfile              # Heroku worker configuration
├── runtime.txt           # Python runtime version
└── .gitignore           # Git ignore rules
```

## Prerequisites

- Python 3.10.6
- Jira account with API access
- Notion account with API token
- Slack workspace with webhook URL
- Heroku account (for deployment)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd work_tools
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables by creating a `.env` file:
```bash
NOTION_TOKEN=your_notion_api_token
JIRA_API_TOKEN=your_jira_api_token
DATABASE_ID=your_notion_database_id
TYPES_DATABASE_ID=your_notion_types_database_id
JIRA_USER_NAME=your_jira_username
SLACK_WEBHOOK_URL=your_slack_webhook_url
JIRA_URL=your_jira_api_endpoint
```

## Configuration

### Environment Variables

- `NOTION_TOKEN`: Your Notion API integration token
- `JIRA_API_TOKEN`: Your Jira API token
- `DATABASE_ID`: ID of the main Notion database for work records
- `TYPES_DATABASE_ID`: ID of the Notion database for work types/tags
- `JIRA_USER_NAME`: Your Jira username
- `SLACK_WEBHOOK_URL`: Slack webhook URL for sending messages
- `JIRA_URL`: Jira API endpoint URL

### Jira Setup

1. Generate an API token from your Jira account settings
2. Ensure your Jira user has access to the relevant projects and sprints
3. Configure the JIRA_URL to point to your Jira instance's API

### Notion Setup

1. Create a Notion integration and get the API token
2. Create databases for work records and work types
3. Share the databases with your integration
4. Note down the database IDs from the URLs

### Slack Setup

1. Create a Slack app and enable incoming webhooks
2. Create a webhook for your target channel
3. Copy the webhook URL to your environment variables

## Usage

### Manual Execution

Run sprint update report:
```bash
python gen_su_report.py
```

Run weekly report (only works on Fridays):
```bash
python gen_weekly_report.py
```

### Automated Execution

The project is configured for Heroku deployment with automated workers:

- `worker`: Runs sprint update reports
- `worker_weekly`: Runs weekly reports (Fridays only)

## How It Works

1. **Data Fetching**: The tool connects to Jira API to fetch active sprint tickets
2. **Status Sync**: Updates work records in Notion based on current Jira ticket statuses
3. **Report Generation**: Creates formatted reports based on work records
4. **Slack Delivery**: Sends reports to specified Slack channel via webhook

### Report Types

- **Sprint Update Report**: Lists all tickets in the current sprint with their status
- **Weekly Report**: Categorizes tickets by status (On Going vs Completed) and provides a summary

## Dependencies

- `requests==2.31.0`: HTTP library for API calls
- `python-dotenv==1.0.1`: Environment variable management

## Deployment

### Heroku Deployment

1. Create a new Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy using Git:
```bash
heroku git:remote -a your-app-name
git push heroku main
```

4. Scale workers:
```bash
heroku ps:scale worker=1
heroku ps:scale worker_weekly=1
```

## Demo

https://github.com/user-attachments/assets/24887145-79e3-4762-b6c4-d7676e3ff27d

## License

This project is for internal use. Please ensure compliance with your organization's policies regarding API usage and data handling.
