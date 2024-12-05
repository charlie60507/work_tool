import requests

def send_to_slack(url, msg):
    payload = {"text": msg}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    print("\n" + "=" * 50)
    print("Message sent to Slack as following:\n")
    for line in msg.split("\n"):
        print(f"  {line}")
    print("=" * 50 + "\n")