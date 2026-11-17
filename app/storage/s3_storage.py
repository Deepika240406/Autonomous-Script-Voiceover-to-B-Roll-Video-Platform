import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from app.storage.base import BaseStorage
from app.storage.local_storage import LocalStorage
from app.config import settings
from app.core.logging import logger


class S3Storage(BaseStorage):
    def __init__(self):
        self.local_cache = LocalStorage(settings.LOCAL_STORAGE_PATH)
        self.bucket = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        try:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
            )
            # Ensure bucket exists
            self._ensure_bucket()
            self.is_connected = True
        except Exception as e:
            logger.warning(f"S3 connection failed ({str(e)}). Falling back to LocalStorage.")
            self.is_connected = False

    def _ensure_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created S3 bucket '{self.bucket}'")
            except Exception as e:
                logger.warning(f"Could not create bucket '{self.bucket}': {e}")

    def save_file(self, relative_path: str, source_path: str) -> str:
        # Also cache locally
        self.local_cache.save_file(relative_path, source_path)
        if not self.is_connected:
            return self.local_cache.get_file_url(relative_path)
        try:
            s3_key = relative_path.replace("\\", "/").lstrip("/")
            self.s3_client.upload_file(source_path, self.bucket, s3_key)
            return self.get_file_url(relative_path)
        except Exception as e:
            logger.error(f"S3 upload error: {e}. Returning local URL.")
            return self.local_cache.get_file_url(relative_path)

    def save_bytes(self, relative_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        self.local_cache.save_bytes(relative_path, data, content_type)
        if not self.is_connected:
            return self.local_cache.get_file_url(relative_path)
        try:
            s3_key = relative_path.replace("\\", "/").lstrip("/")
            extra_args = {"ContentType": content_type} if content_type else {}
            self.s3_client.put_object(Bucket=self.bucket, Key=s3_key, Body=data, **extra_args)
            return self.get_file_url(relative_path)
        except Exception as e:
            logger.error(f"S3 save_bytes error: {e}. Returning local URL.")
            return self.local_cache.get_file_url(relative_path)

    def get_file_url(self, relative_path: str) -> str:
        if not self.is_connected:
            return self.local_cache.get_file_url(relative_path)
        try:
            s3_key = relative_path.replace("\\", "/").lstrip("/")
            # Return pre-signed or endpoint direct URL
            return f"{self.endpoint_url}/{self.bucket}/{s3_key}"
        except Exception:
            return self.local_cache.get_file_url(relative_path)

    def get_local_path(self, relative_path: str) -> str:
        return self.local_cache.get_local_path(relative_path)


def get_storage() -> BaseStorage:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
