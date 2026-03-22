import json
import logging
import mimetypes
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterable

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class S3StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.s3_bucket:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="S3 bucket is not configured",
            )
        if not settings.s3_endpoint:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="S3 endpoint is not configured",
            )
        if not settings.s3_access_key or not settings.s3_secret_key:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="S3 credentials are not configured",
            )

        self.bucket = settings.s3_bucket
        self.presign_expires = settings.s3_presign_expires

        endpoint = settings.s3_endpoint.rstrip("/")
        public_endpoint = (settings.s3_public_endpoint or "").strip()
        if public_endpoint:
            public_endpoint = public_endpoint.rstrip("/")
        else:
            public_endpoint = endpoint

        config_kwargs: dict[str, Any] = {
            "signature_version": "s3v4",
            "connect_timeout": settings.s3_connect_timeout_seconds,
            "read_timeout": settings.s3_read_timeout_seconds,
            "retries": {
                "max_attempts": settings.s3_max_attempts,
                "mode": "standard",
            },
        }
        if settings.s3_force_path_style:
            config_kwargs["s3"] = {"addressing_style": "path"}

        config = Config(**config_kwargs) if config_kwargs else None

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=config,
        )
        self.presign_client = (
            self.client
            if public_endpoint == endpoint
            else boto3.client(
                "s3",
                endpoint_url=public_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=config,
            )
        )

    def get_manifest(self, key: str) -> dict[str, Any]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read()
            return json.loads(body.decode("utf-8"))
        except (ClientError, BotoCoreError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to fetch manifest {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to fetch workspace manifest",
                details={"key": key, "error": str(exc)},
            ) from exc

    def get_text(self, key: str, *, encoding: str = "utf-8") -> str:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read()
            return body.decode(encoding)
        except (ClientError, BotoCoreError, UnicodeDecodeError) as exc:
            logger.error(f"Failed to fetch text object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to fetch text object",
                details={"key": key, "error": str(exc)},
            ) from exc

    def presign_get(
        self,
        key: str,
        *,
        expires_in: int | None = None,
        response_content_disposition: str | None = None,
        response_content_type: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"Bucket": self.bucket, "Key": key}
        if response_content_disposition:
            params["ResponseContentDisposition"] = response_content_disposition
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        try:
            return self.presign_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in or self.presign_expires,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to presign object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to sign workspace object",
                details={"key": key, "error": str(exc)},
            ) from exc

    def exists(self, key: str) -> bool:
        """Return whether the object exists in storage."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            error = exc.response.get("Error", {}) if hasattr(exc, "response") else {}
            code = str(error.get("Code", "")).strip()
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            logger.error(f"Failed to head object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to check object existence",
                details={"key": key, "error": str(exc)},
            ) from exc
        except BotoCoreError as exc:
            logger.error(f"Failed to head object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to check object existence",
                details={"key": key, "error": str(exc)},
            ) from exc

    def upload_fileobj(
        self,
        *,
        fileobj,
        key: str,
        content_type: str | None = None,
    ) -> None:
        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        try:
            if extra_args:
                self.client.upload_fileobj(
                    fileobj, self.bucket, key, ExtraArgs=extra_args
                )
            else:
                self.client.upload_fileobj(fileobj, self.bucket, key)
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to upload object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to upload file",
                details={"key": key, "error": str(exc)},
            ) from exc

    def upload_file(
        self, *, file_path: str, key: str, content_type: str | None = None
    ) -> None:
        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        try:
            if extra_args:
                self.client.upload_file(
                    file_path, self.bucket, key, ExtraArgs=extra_args
                )
            else:
                self.client.upload_file(file_path, self.bucket, key)
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to upload object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to upload file",
                details={"key": key, "file_path": file_path, "error": str(exc)},
            ) from exc

    def put_object(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"Bucket": self.bucket, "Key": key, "Body": body}
        if content_type:
            kwargs["ContentType"] = content_type
        try:
            self.client.put_object(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to put object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to upload file",
                details={"key": key, "error": str(exc)},
            ) from exc

    def list_objects(self, prefix: str) -> Iterable[str]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for item in page.get("Contents", []) or []:
                    key = item.get("Key")
                    if key:
                        yield key
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to list objects under {prefix}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to list files",
                details={"prefix": prefix, "error": str(exc)},
            ) from exc

    def download_file(self, *, key: str, destination: Path) -> None:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.bucket, key, str(destination))
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to download object {key}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to download file",
                details={"key": key, "error": str(exc)},
            ) from exc

    def download_prefix(self, *, prefix: str, destination_dir: Path) -> None:
        for key in self.list_objects(prefix):
            if key.endswith("/"):
                continue
            relative = key[len(prefix) :].lstrip("/")
            if not relative:
                continue
            target = self._safe_destination(destination_dir, relative)
            self.download_file(key=key, destination=target)

    def delete_prefix(self, *, prefix: str) -> int:
        keys = [key for key in self.list_objects(prefix) if key]
        if not keys:
            return 0

        deleted = 0
        try:
            for start in range(0, len(keys), 1000):
                chunk = keys[start : start + 1000]
                self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={
                        "Objects": [{"Key": key} for key in chunk],
                        "Quiet": True,
                    },
                )
                deleted += len(chunk)
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to delete objects under {prefix}: {exc}")
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to delete files",
                details={"prefix": prefix, "error": str(exc)},
            ) from exc

        return deleted

    def sync_directory(
        self,
        *,
        source_dir: Path,
        prefix: str,
        delete_missing: bool = True,
    ) -> int:
        if not source_dir.exists() or not source_dir.is_dir():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Source directory does not exist: {source_dir}",
            )

        normalized_prefix = prefix.strip().rstrip("/")
        if not normalized_prefix:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Storage prefix cannot be empty",
            )
        normalized_prefix = f"{normalized_prefix}/"

        desired_keys: set[str] = set()
        uploaded = 0
        base = source_dir.resolve()

        for file_path in sorted(source_dir.rglob("*")):
            if not file_path.is_file() or file_path.is_symlink():
                continue
            if "__pycache__" in file_path.parts or file_path.name == ".DS_Store":
                continue

            resolved = file_path.resolve()
            try:
                relative = resolved.relative_to(base).as_posix()
            except ValueError as exc:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Resolved path escapes source directory",
                    details={"path": str(file_path)},
                ) from exc

            key = f"{normalized_prefix}{relative}"
            content_type, _ = mimetypes.guess_type(file_path.name)
            self.upload_file(
                file_path=str(file_path),
                key=key,
                content_type=content_type,
            )
            desired_keys.add(key)
            uploaded += 1

        if delete_missing:
            existing_keys = set(self.list_objects(normalized_prefix))
            stale_keys = existing_keys - desired_keys
            if stale_keys:
                stale_keys_list = sorted(stale_keys)
                try:
                    for start in range(0, len(stale_keys_list), 1000):
                        chunk = stale_keys_list[start : start + 1000]
                        self.client.delete_objects(
                            Bucket=self.bucket,
                            Delete={
                                "Objects": [{"Key": key} for key in chunk],
                                "Quiet": True,
                            },
                        )
                except (ClientError, BotoCoreError) as exc:
                    logger.error(
                        f"Failed to delete stale objects under {normalized_prefix}: {exc}"
                    )
                    raise AppException(
                        error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                        message="Failed to sync files",
                        details={"prefix": normalized_prefix, "error": str(exc)},
                    ) from exc

        return uploaded

    def copy_prefix(
        self,
        *,
        source_prefix: str,
        destination_prefix: str,
        delete_missing: bool = True,
    ) -> int:
        normalized_source = source_prefix.strip().rstrip("/")
        normalized_destination = destination_prefix.strip().rstrip("/")
        if not normalized_source or not normalized_destination:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Source and destination prefixes cannot be empty",
            )

        normalized_source = f"{normalized_source}/"
        normalized_destination = f"{normalized_destination}/"

        copied = 0
        desired_keys: set[str] = set()

        try:
            for source_key in self.list_objects(normalized_source):
                if source_key.endswith("/"):
                    continue
                relative = source_key[len(normalized_source) :].lstrip("/")
                if not relative:
                    continue
                destination_key = f"{normalized_destination}{relative}"
                self.client.copy(
                    {"Bucket": self.bucket, "Key": source_key},
                    self.bucket,
                    destination_key,
                )
                desired_keys.add(destination_key)
                copied += 1
        except (ClientError, BotoCoreError) as exc:
            logger.error(
                f"Failed to copy objects from {normalized_source} to {normalized_destination}: {exc}"
            )
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to copy files",
                details={
                    "source_prefix": normalized_source,
                    "destination_prefix": normalized_destination,
                    "error": str(exc),
                },
            ) from exc

        if delete_missing:
            existing_keys = set(self.list_objects(normalized_destination))
            stale_keys = existing_keys - desired_keys
            if stale_keys:
                stale_keys_list = sorted(stale_keys)
                try:
                    for start in range(0, len(stale_keys_list), 1000):
                        chunk = stale_keys_list[start : start + 1000]
                        self.client.delete_objects(
                            Bucket=self.bucket,
                            Delete={
                                "Objects": [{"Key": key} for key in chunk],
                                "Quiet": True,
                            },
                        )
                except (ClientError, BotoCoreError) as exc:
                    logger.error(
                        f"Failed to delete stale copied objects under {normalized_destination}: {exc}"
                    )
                    raise AppException(
                        error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                        message="Failed to copy files",
                        details={
                            "destination_prefix": normalized_destination,
                            "error": str(exc),
                        },
                    ) from exc

        return copied

    @staticmethod
    def _safe_destination(destination_dir: Path, relative: str) -> Path:
        rel_path = PurePosixPath(relative)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Invalid object key path",
                details={"relative": relative},
            )
        base = destination_dir.resolve()
        target = (destination_dir / Path(rel_path.as_posix())).resolve()
        if base not in target.parents and target != base:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Resolved path escapes destination directory",
                details={"relative": relative},
            )
        return target
