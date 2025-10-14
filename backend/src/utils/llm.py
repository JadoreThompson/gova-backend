from json import loads


def parse_to_json(value: str) -> dict | list:
    s = "```json"
    ind = value.index(s)
    value = value[ind + len(s) :]

    s = "```"
    ind = value.index(s)
    value = value[:ind]

    return loads(value)
