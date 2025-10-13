import json
import os

import requests

from config import BASE_PATH, LLM_API_KEY, SYSTEM_PROMPT


with open(os.path.join(BASE_PATH, "resources", "guidelines.txt")) as f:
    GUIDELINES = f.read()


chat_log = [
    {
        "userid": "user001",
        "content": "Hey everyone! Hope you're all doing great today! 😊",
    },  # follows
    {
        "userid": "user002",
        "content": "Stop spamming memes in #general, please.",
    },  # follows
    {
        "userid": "user003",
        "content": "OMG you're all so dumb lol",
    },  # violates (disrespect)
    {
        "userid": "user004",
        "content": "Can we organize a study session for tomorrow?",
    },  # follows
    {
        "userid": "user005",
        "content": "BUY CHEAP FOLLOWERS HERE 👉 fakewebsite.com",
    },  # violates (spam)
    {"userid": "user006", "content": "That's a great idea, count me in!"},  # follows
    {
        "userid": "user007",
        "content": "Moderator sucks, ban them!",
    },  # violates (harassment)
    {
        "userid": "user008",
        "content": "Anyone up for a gaming session later?",
    },  # follows
    {
        "userid": "user009",
        "content": "Let's keep politics out of this channel please.",
    },  # follows
    {
        "userid": "user010",
        "content": "You're such an idiot for liking that game.",
    },  # violates (personal attack)
]


sensitivity = 0

base_url = "https://api.mistral.ai/v1"
headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
model = "mistral-tiny"

var = []
for log in chat_log:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": log["content"]},
        ],
    }
    rsp = requests.post(base_url + "/chat/completions", headers=headers, json=body)
    data = rsp.json()
    obj = (log, rsp.json())
    var.append(obj)
    

with open("rsp.json", "w") as f:
    json.dump(var, f)
