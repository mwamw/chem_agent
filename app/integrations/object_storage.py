from __future__ import annotations


class ObjectStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key

    async def put_text(self, bucket: str, key: str, content: str) -> dict:
        return {"bucket": bucket, "key": key, "size": len(content)}
