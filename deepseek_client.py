import os
import json
import requests


def api_key():
    return os.environ["DEEPSEEK_API_KEY"]


def translate(text):
    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Translate to Chinese. Return only the translation."},
            {"role": "user", "content": text},
        ],
    }
    headers = {
        "authorization": "Bearer " + api_key(),
        "content-type": "application/json",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    data = resp.json()
    return data["choices"][0]["message"]["content"]
