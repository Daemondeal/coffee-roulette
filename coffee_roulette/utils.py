import os
import requests

def send_slack_message(message: str):
    url = os.getenv("SLACK_HOOK_LINK", "")
    if url == "":
        return

    requests.post(url, json={"message": message})
