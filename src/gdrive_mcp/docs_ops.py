from __future__ import annotations


class DocsOpError(Exception):
    """Raised when a friendly op cannot be expanded."""


def expand_ops(ops: list[dict]) -> list[dict]:
    requests: list[dict] = []
    for op in ops:
        if "find" in op and "replace" in op:
            requests.append({
                "replaceAllText": {
                    "containsText": {"text": op["find"], "matchCase": True},
                    "replaceText": op["replace"],
                }
            })
        elif "insert_at" in op and "text" in op:
            requests.append({
                "insertText": {
                    "location": {"index": op["insert_at"]},
                    "text": op["text"],
                }
            })
        else:
            raise DocsOpError(f"unrecognized op: {op!r}")
    return requests
