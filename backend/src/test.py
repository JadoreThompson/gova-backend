import json
import os
import random

import requests

from core.models import BanAction, MuteAction
from config import (
    BASE_PATH,
    LLM_API_KEY,
    RESOURCES_PATH,
    SCORE_PROMPT,
    TOPIC_PROMPT,
    FINAL_PROMPT,
)


def parse_output(value: str):
    s = "```json"
    py_ind = value.index(s)
    value = value[py_ind + len(s) :]

    s = "```"
    quote_ind = value.index(s)
    value = value[:quote_ind]

    return json.loads(value)


with open(os.path.join(RESOURCES_PATH, "guidelines.txt")) as f:
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

actions = ["ban", "mute"]


var = []
for log in chat_log:
    # Topic
    sys_prompt = TOPIC_PROMPT
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": GUIDELINES},
        ],
    }
    rsp = requests.post(base_url + "/chat/completions", headers=headers, json=body)
    data = rsp.json()
    content = data["choices"][0]["message"]["content"]
    topics = parse_output(content)

    # Score
    sys_prompt = SCORE_PROMPT.format(guidelines=GUIDELINES, topics=topics)
    log["channel"] = random.choice(["general", "music"])
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(log)},
        ],
    }
    log.pop("channel")
    rsp = requests.post(base_url + "/chat/completions", headers=headers, json=body)
    data = rsp.json()
    content = data["choices"][0]["message"]["content"]
    topic_scores = parse_output(content)

    # Final
    prompt = FINAL_PROMPT.format(
        guidelines=GUIDELINES,
        topics=topics,
        topic_scores=topic_scores,
        actions=actions,
        message=log["content"],
        action_formats=[BanAction.model_json_schema(), MuteAction.model_json_schema()],
        context={
            "platform": "discord",
            "data": {"channel": "general", "server": "sneakbots"},
        },
    )
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    rsp = requests.post(base_url + "/chat/completions", headers=headers, json=body)
    data = rsp.json()
    content = data["choices"][0]["message"]["content"]
    print("Prompt")
    print(body['messages'][0]['content'])
    print("Content")
    print(content)
    final_output = parse_output(content)

    obj = (log, final_output)
    var.append(obj)


with open(os.path.join(RESOURCES_PATH, "rsp.json"), "w") as f:
    json.dump(var, f)
