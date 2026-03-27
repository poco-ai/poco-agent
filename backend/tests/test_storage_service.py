"""Tests for app/services/storage_service.py."""

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.storage_service import S3StorageService


def _create_mock_settings() -> MagicMock:
    """Create mock settings with default S3 configuration."""
    settings = MagicMock()
    settings.s3_bucket = "test-bucket"
    settings.s3_endpoint = "https://s3.example.com"
    settings.s3_public_endpoint = None
    settings.s3_access_key = "access-key"
    settings.s3_secret_key = "secret-key"
    settings.s3_region = "us-east-1"
    settings.s3_presign_expires = 3600
    settings.s3_connect_timeout_seconds = 10
    settings.s3_read_timeout_seconds = 30
    settings.s3_max_attempts = 3
    settings.s3_force_path_style = False
    return settings


class TestS3StorageServiceInit(unittest.TestCase):
    """Test S3StorageService initialization."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_init_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful initialization."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        self.assertEqual(service.bucket, "test-bucket")
        self.assertEqual(service.presign_expires, 3600)
        mock_boto3.client.assert_called()

    @patch("app.services.storage_service.get_settings")
    def test_init_missing_bucket(self, mock_get_settings: MagicMock) -> None:
        """Test initialization fails without bucket."""
        settings = _create_mock_settings()
        settings.s3_bucket = None
        mock_get_settings.return_value = settings

        with self.assertRaises(AppException) as ctx:
            S3StorageService()

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)
        self.assertIn("bucket", ctx.exception.message.lower())

    @patch("app.services.storage_service.get_settings")
    def test_init_missing_endpoint(self, mock_get_settings: MagicMock) -> None:
        """Test initialization fails without endpoint."""
        settings = _create_mock_settings()
        settings.s3_endpoint = None
        mock_get_settings.return_value = settings

        with self.assertRaises(AppException) as ctx:
            S3StorageService()

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)
        self.assertIn("endpoint", ctx.exception.message.lower())

    @patch("app.services.storage_service.get_settings")
    def test_init_missing_credentials(self, mock_get_settings: MagicMock) -> None:
        """Test initialization fails without credentials."""
        settings = _create_mock_settings()
        settings.s3_access_key = None
        settings.s3_secret_key = "secret"
        mock_get_settings.return_value = settings

        with self.assertRaises(AppException) as ctx:
            S3StorageService()

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)
        self.assertIn("credentials", ctx.exception.message.lower())

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_init_with_public_endpoint(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test initialization with separate public endpoint."""
        settings = _create_mock_settings()
        settings.s3_endpoint = "https://s3.internal.example.com"
        settings.s3_public_endpoint = "https://s3.public.example.com"
        mock_get_settings.return_value = settings

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        S3StorageService()

        # Should create two clients when public_endpoint differs
        self.assertEqual(mock_boto3.client.call_count, 2)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_init_with_path_style(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test initialization with path style addressing."""
        settings = _create_mock_settings()
        settings.s3_force_path_style = True
        mock_get_settings.return_value = settings

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        S3StorageService()
        # Verify Config was created with s3 addressing style
        mock_boto3.client.assert_called()


class TestS3StorageServiceGetManifest(unittest.TestCase):
    """Test get_manifest method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_manifest_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful manifest retrieval."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        manifest_data = {"version": "1.0", "files": []}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(manifest_data).encode("utf-8")
        mock_client.get_object.return_value = {"Body": mock_body}

        result = service.get_manifest("manifests/test.json")

        self.assertEqual(result, manifest_data)
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="manifests/test.json"
        )

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_manifest_client_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test get_manifest with client error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "get_object"
        )

        with self.assertRaises(AppException) as ctx:
            service.get_manifest("manifests/missing.json")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_manifest_json_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test get_manifest with invalid JSON."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_body = MagicMock()
        mock_body.read.return_value = b"not valid json"
        mock_client.get_object.return_value = {"Body": mock_body}

        with self.assertRaises(AppException) as ctx:
            service.get_manifest("manifests/invalid.json")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceGetText(unittest.TestCase):
    """Test get_text method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_text_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful text retrieval."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_body = MagicMock()
        mock_body.read.return_value = b"Hello, World!"
        mock_client.get_object.return_value = {"Body": mock_body}

        result = service.get_text("files/hello.txt")

        self.assertEqual(result, "Hello, World!")

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_text_with_encoding(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test text retrieval with custom encoding."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        text = "Hello, World!"
        mock_body = MagicMock()
        mock_body.read.return_value = text.encode("utf-8")
        mock_client.get_object.return_value = {"Body": mock_body}

        result = service.get_text("files/hello.txt", encoding="utf-8")

        self.assertEqual(result, text)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_get_text_unicode_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test get_text with unicode decode error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_body = MagicMock()
        mock_body.read.return_value = b"\xff\xfe"  # Invalid UTF-8
        mock_client.get_object.return_value = {"Body": mock_body}

        with self.assertRaises(AppException) as ctx:
            service.get_text("files/binary.bin")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServicePresignGet(unittest.TestCase):
    """Test presign_get method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_presign_get_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful presigned URL generation."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.generate_presigned_url.return_value = (
            "https://s3.example.com/signed-url"
        )

        result = service.presign_get("files/document.pdf")

        self.assertEqual(result, "https://s3.example.com/signed-url")
        mock_client.generate_presigned_url.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_presign_get_with_content_disposition(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test presigned URL with content disposition."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.generate_presigned_url.return_value = (
            "https://s3.example.com/signed-url"
        )

        service.presign_get(
            "files/document.pdf",
            response_content_disposition='attachment; filename="doc.pdf"',
        )

        call_args = mock_client.generate_presigned_url.call_args
        params = call_args.kwargs["Params"]
        self.assertIn("ResponseContentDisposition", params)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_presign_get_with_content_type(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test presigned URL with content type."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.generate_presigned_url.return_value = (
            "https://s3.example.com/signed-url"
        )

        service.presign_get(
            "files/document.pdf", response_content_type="application/pdf"
        )

        call_args = mock_client.generate_presigned_url.call_args
        params = call_args.kwargs["Params"]
        self.assertIn("ResponseContentType", params)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_presign_get_custom_expires(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test presigned URL with custom expiration."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.generate_presigned_url.return_value = (
            "https://s3.example.com/signed-url"
        )

        service.presign_get("files/document.pdf", expires_in=7200)

        call_args = mock_client.generate_presigned_url.call_args
        self.assertEqual(call_args.kwargs["ExpiresIn"], 7200)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_presign_get_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test presigned URL generation error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "generate_presigned_url",
        )

        with self.assertRaises(AppException) as ctx:
            service.presign_get("files/document.pdf")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceExists(unittest.TestCase):
    """Test exists method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_exists_true(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test exists returns True for existing object."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.head_object.return_value = {"ContentLength": 100}

        result = service.exists("files/document.pdf")

        self.assertTrue(result)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_exists_false_404(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test exists returns False for 404 error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        error = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}}, "head_object"
        )
        mock_client.head_object.side_effect = error

        result = service.exists("files/missing.pdf")

        self.assertFalse(result)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_exists_false_no_such_key(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test exists returns False for NoSuchKey error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "head_object"
        )
        mock_client.head_object.side_effect = error

        result = service.exists("files/missing.pdf")

        self.assertFalse(result)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_exists_error_other(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test exists raises for other client errors."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "head_object",
        )
        mock_client.head_object.side_effect = error

        with self.assertRaises(AppException) as ctx:
            service.exists("files/document.pdf")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_exists_botocore_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test exists handles BotoCoreError."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.head_object.side_effect = BotoCoreError()

        with self.assertRaises(AppException) as ctx:
            service.exists("files/document.pdf")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceUploadFileobj(unittest.TestCase):
    """Test upload_fileobj method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_fileobj_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful file object upload."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        fileobj = BytesIO(b"test content")
        service.upload_fileobj(fileobj=fileobj, key="uploads/test.txt")

        mock_client.upload_fileobj.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_fileobj_with_content_type(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test file object upload with content type."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        fileobj = BytesIO(b"test content")
        service.upload_fileobj(
            fileobj=fileobj, key="uploads/test.txt", content_type="text/plain"
        )

        call_args = mock_client.upload_fileobj.call_args
        self.assertIn("ExtraArgs", call_args.kwargs)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_fileobj_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test file object upload error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "upload_fileobj",
        )

        fileobj = BytesIO(b"test content")
        with self.assertRaises(AppException) as ctx:
            service.upload_fileobj(fileobj=fileobj, key="uploads/test.txt")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceUploadFile(unittest.TestCase):
    """Test upload_file method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_file_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful file upload."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        service.upload_file(file_path="/tmp/test.txt", key="uploads/test.txt")

        mock_client.upload_file.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_file_with_content_type(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test file upload with content type."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        service.upload_file(
            file_path="/tmp/test.txt", key="uploads/test.txt", content_type="text/plain"
        )

        call_args = mock_client.upload_file.call_args
        self.assertIn("ExtraArgs", call_args.kwargs)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_upload_file_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test file upload error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "upload_file",
        )

        with self.assertRaises(AppException) as ctx:
            service.upload_file(file_path="/tmp/test.txt", key="uploads/test.txt")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServicePutObject(unittest.TestCase):
    """Test put_object method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_put_object_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful object put."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        service.put_object(key="uploads/test.txt", body=b"test content")

        mock_client.put_object.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_put_object_with_content_type(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test object put with content type."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        service.put_object(
            key="uploads/test.txt", body=b"test content", content_type="text/plain"
        )

        call_args = mock_client.put_object.call_args
        self.assertIn("ContentType", call_args.kwargs)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_put_object_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test object put error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "put_object",
        )

        with self.assertRaises(AppException) as ctx:
            service.put_object(key="uploads/test.txt", body=b"test content")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceListObjects(unittest.TestCase):
    """Test list_objects method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_list_objects_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful object listing."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "prefix/file1.txt"}, {"Key": "prefix/file2.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        result = list(service.list_objects("prefix/"))

        self.assertEqual(result, ["prefix/file1.txt", "prefix/file2.txt"])

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_list_objects_empty(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test object listing with no objects."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        mock_client.get_paginator.return_value = mock_paginator

        result = list(service.list_objects("prefix/"))

        self.assertEqual(result, [])

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_list_objects_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test object listing error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "get_paginator",
        )

        with self.assertRaises(AppException) as ctx:
            list(service.list_objects("prefix/"))

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceDownloadFile(unittest.TestCase):
    """Test download_file method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_download_file_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful file download."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with patch.object(Path, "mkdir"):
            service.download_file(
                key="files/test.txt", destination=Path("/tmp/test.txt")
            )

        mock_client.download_file.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_download_file_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test file download error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_client.download_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "download_file"
        )

        with patch.object(Path, "mkdir"):
            with self.assertRaises(AppException) as ctx:
                service.download_file(
                    key="files/missing.txt", destination=Path("/tmp/test.txt")
                )

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceSafeDestination(unittest.TestCase):
    """Test _safe_destination static method."""

    def test_safe_destination_success(self) -> None:
        """Test safe destination path."""
        result = S3StorageService._safe_destination(
            Path("/tmp/output"), "subdir/file.txt"
        )
        self.assertEqual(result, Path("/tmp/output/subdir/file.txt").resolve())

    def test_safe_destination_absolute_path(self) -> None:
        """Test rejection of absolute path."""
        with self.assertRaises(AppException) as ctx:
            S3StorageService._safe_destination(Path("/tmp/output"), "/etc/passwd")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)

    def test_safe_destination_path_traversal(self) -> None:
        """Test rejection of path traversal."""
        with self.assertRaises(AppException) as ctx:
            S3StorageService._safe_destination(Path("/tmp/output"), "../etc/passwd")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)

    def test_safe_destination_escaped_path(self) -> None:
        """Test rejection of path escaping destination."""
        with self.assertRaises(AppException) as ctx:
            S3StorageService._safe_destination(
                Path("/tmp/output"), "subdir/../../etc/passwd"
            )

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceDownloadPrefix(unittest.TestCase):
    """Test download_prefix method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_download_prefix_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful prefix download."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Mock list_objects to return keys
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "prefix/file1.txt"},
                    {"Key": "prefix/subdir/file2.txt"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        # Mock download_file to avoid actual download
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(service, "download_file") as mock_download:
                service.download_prefix(prefix="prefix/", destination_dir=Path(tmpdir))

                # Should call download_file for each non-directory key
                self.assertEqual(mock_download.call_count, 2)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_download_prefix_skips_directories(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test that directory keys are skipped."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Mock list_objects with directory keys
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "prefix/subdir/"}, {"Key": "prefix/file.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(service, "download_file") as mock_download:
                service.download_prefix(prefix="prefix/", destination_dir=Path(tmpdir))

                # Should only download the file, not the directory
                self.assertEqual(mock_download.call_count, 1)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_download_prefix_empty_prefix_match(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test skip when relative path is empty."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Key exactly matches prefix
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "prefix"}]}]
        mock_client.get_paginator.return_value = mock_paginator

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(service, "download_file") as mock_download:
                service.download_prefix(prefix="prefix", destination_dir=Path(tmpdir))

                # No download for exact prefix match
                mock_download.assert_not_called()


class TestS3StorageServiceDeletePrefix(unittest.TestCase):
    """Test delete_prefix method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_delete_prefix_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful prefix deletion."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Mock list_objects
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "prefix/file1.txt"}, {"Key": "prefix/file2.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.delete_prefix(prefix="prefix/")

        self.assertEqual(result, 2)
        mock_client.delete_objects.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_delete_prefix_empty(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete with no objects."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.delete_prefix(prefix="prefix/")

        self.assertEqual(result, 0)
        mock_client.delete_objects.assert_not_called()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_delete_prefix_chunks_large_batch(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete chunks requests in batches of 1000."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Create 2500 keys to test batching
        keys = [{"Key": f"prefix/file{i}.txt"} for i in range(2500)]
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": keys}]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.delete_prefix(prefix="prefix/")

        self.assertEqual(result, 2500)
        # Should be called 3 times: 1000 + 1000 + 500
        self.assertEqual(mock_client.delete_objects.call_count, 3)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_delete_prefix_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete_prefix with client error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "prefix/file.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        mock_client.delete_objects.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "delete_objects",
        )

        with self.assertRaises(AppException) as ctx:
            service.delete_prefix(prefix="prefix/")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


class TestS3StorageServiceSyncDirectory(unittest.TestCase):
    """Test sync_directory method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful directory sync."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create test files
            (tmp_path / "file1.txt").write_text("content1")
            (tmp_path / "subdir").mkdir()
            (tmp_path / "subdir" / "file2.txt").write_text("content2")

            # Mock list_objects (for delete_missing)
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [{}]
            mock_client.get_paginator.return_value = mock_paginator

            with patch.object(service, "upload_file") as mock_upload:
                result = service.sync_directory(source_dir=tmp_path, prefix="test")

                self.assertEqual(result, 2)
                self.assertEqual(mock_upload.call_count, 2)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_nonexistent(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test sync with nonexistent source directory."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"

            with self.assertRaises(AppException) as ctx:
                service.sync_directory(source_dir=nonexistent, prefix="test")

            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_empty_prefix(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test sync with empty prefix."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file.txt").write_text("content")

            with self.assertRaises(AppException) as ctx:
                service.sync_directory(source_dir=tmp_path, prefix="")

            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_skips_special_files(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test that __pycache__ and .DS_Store are skipped."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create various files
            (tmp_path / "file.txt").write_text("content")
            (tmp_path / ".DS_Store").write_text("store")
            (tmp_path / "__pycache__").mkdir()
            (tmp_path / "__pycache__" / "module.pyc").write_text("bytecode")

            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [{}]
            mock_client.get_paginator.return_value = mock_paginator

            with patch.object(service, "upload_file"):
                result = service.sync_directory(source_dir=tmp_path, prefix="test")

                # Only file.txt should be uploaded
                self.assertEqual(result, 1)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_delete_missing(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete_missing removes stale files."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file.txt").write_text("content")

            # Mock list_objects to return stale keys
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [
                {"Contents": [{"Key": "test/file.txt"}, {"Key": "test/stale.txt"}]}
            ]
            mock_client.get_paginator.return_value = mock_paginator

            with patch.object(service, "upload_file"):
                service.sync_directory(
                    source_dir=tmp_path, prefix="test", delete_missing=True
                )

                # Should delete stale file
                mock_client.delete_objects.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_no_delete_missing(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test with delete_missing=False."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file.txt").write_text("content")

            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [
                {"Contents": [{"Key": "test/stale.txt"}]}
            ]
            mock_client.get_paginator.return_value = mock_paginator

            with patch.object(service, "upload_file"):
                service.sync_directory(
                    source_dir=tmp_path, prefix="test", delete_missing=False
                )

                # Should not delete anything
                mock_client.delete_objects.assert_not_called()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_sync_directory_delete_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete_missing error handling."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file.txt").write_text("content")

            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [
                {"Contents": [{"Key": "test/file.txt"}, {"Key": "test/stale.txt"}]}
            ]
            mock_client.get_paginator.return_value = mock_paginator

            mock_client.delete_objects.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "delete_objects",
            )

            with patch.object(service, "upload_file"):
                with self.assertRaises(AppException) as ctx:
                    service.sync_directory(source_dir=tmp_path, prefix="test")

                self.assertEqual(
                    ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR
                )


class TestS3StorageServiceCopyPrefix(unittest.TestCase):
    """Test copy_prefix method."""

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_success(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test successful prefix copy."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "src/file1.txt"}, {"Key": "src/file2.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.copy_prefix(
            source_prefix="src", destination_prefix="dst", delete_missing=False
        )

        self.assertEqual(result, 2)
        self.assertEqual(mock_client.copy.call_count, 2)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_empty_source(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test copy with empty source prefix."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with self.assertRaises(AppException) as ctx:
            service.copy_prefix(source_prefix="", destination_prefix="dst")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_empty_destination(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test copy with empty destination prefix."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        with self.assertRaises(AppException) as ctx:
            service.copy_prefix(source_prefix="src", destination_prefix="  ")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_skips_directories(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test that directory keys are skipped."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "src/subdir/"}, {"Key": "src/file.txt"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.copy_prefix(
            source_prefix="src", destination_prefix="dst", delete_missing=False
        )

        self.assertEqual(result, 1)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test copy_prefix with client error."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "src/file.txt"}]}]
        mock_client.get_paginator.return_value = mock_paginator

        mock_client.copy.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "copy"
        )

        with self.assertRaises(AppException) as ctx:
            service.copy_prefix(source_prefix="src", destination_prefix="dst")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_delete_missing(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete_missing removes stale files at destination."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        # Source has file.txt, destination has file.txt and stale.txt
        mock_paginator = MagicMock()
        # First call for source listing
        mock_paginator.paginate.side_effect = [
            [{"Contents": [{"Key": "src/file.txt"}]}],  # source
            [
                {"Contents": [{"Key": "dst/file.txt"}, {"Key": "dst/stale.txt"}]}
            ],  # destination
        ]
        mock_client.get_paginator.return_value = mock_paginator

        result = service.copy_prefix(
            source_prefix="src", destination_prefix="dst", delete_missing=True
        )

        self.assertEqual(result, 1)
        mock_client.delete_objects.assert_called_once()

    @patch("app.services.storage_service.boto3")
    @patch("app.services.storage_service.get_settings")
    def test_copy_prefix_delete_error(
        self, mock_get_settings: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """Test delete_missing error during copy."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        service = S3StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = [
            [{"Contents": [{"Key": "src/file.txt"}]}],  # source
            [
                {"Contents": [{"Key": "dst/file.txt"}, {"Key": "dst/stale.txt"}]}
            ],  # destination
        ]
        mock_client.get_paginator.return_value = mock_paginator

        mock_client.delete_objects.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "delete_objects",
        )

        with self.assertRaises(AppException) as ctx:
            service.copy_prefix(source_prefix="src", destination_prefix="dst")

        self.assertEqual(ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR)


if __name__ == "__main__":
    unittest.main()
