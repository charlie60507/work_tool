import requests

def send_to_slack(url, msg):
    payload = {"text": msg}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print("Message sent to Slack")