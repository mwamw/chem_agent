from __future__ import annotations

import asyncio
from dataclasses import dataclass

import boto3
from botocore.client import Config


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    size: int
    etag: str | None


class ObjectStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.endpoint = endpoint
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http://{endpoint}" if not endpoint.startswith("http") else endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    async def ensure_bucket(self, bucket: str) -> None:
        def _create() -> None:
            existing = [row["Name"] for row in self.client.list_buckets().get("Buckets", [])]
            if bucket not in existing:
                self.client.create_bucket(Bucket=bucket)

        await asyncio.to_thread(_create)

    async def put_text(self, bucket: str, key: str, content: str) -> dict:
        await self.ensure_bucket(bucket)
        data = content.encode("utf-8")

        def _put() -> dict:
            return self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType="text/plain; charset=utf-8",
            )

        response = await asyncio.to_thread(_put)
        return StoredObject(
            bucket=bucket,
            key=key,
            size=len(data),
            etag=response.get("ETag"),
        ).__dict__

    async def get_text(self, bucket: str, key: str) -> str:
        def _get() -> bytes:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()

        return (await asyncio.to_thread(_get)).decode("utf-8")
