import json


def parse_sse(text: str) -> list[tuple[str, object]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def upload(client, path):
    with path.open("rb") as f:
        return client.post("/api/documents", files={"file": (path.name, f, "application/pdf")}).json()["id"]


def ask(client, question, ids, **extra):
    return client.post("/api/chat", json={"question": question, "document_ids": ids, **extra})
