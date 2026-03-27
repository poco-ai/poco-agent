"""Tests for app/services/im_providers.py - TelegramClient, DingTalkClient, FeishuClient and helpers."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.im_providers import (
    DingTalkClient,
    FeishuClient,
    TelegramClient,
    _dingtalk_at_users_include_bot,
    _extract_feishu_leading_plain_mentions,
    _extract_feishu_sender_id,
    _extract_feishu_text,
    _feishu_has_explicit_mention,
    _feishu_leading_mentions_include_bot,
    _is_truthy,
    _normalize_im_text,
    _read_feishu_mention_ids,
    _split_text,
    parse_dingtalk_webhook_event,
    parse_feishu_stream_event,
    parse_feishu_webhook_event,
    parse_telegram_update,
)


class TestTelegramClientInit(unittest.TestCase):
    """Test TelegramClient initialization."""

    @patch("app.services.im_providers.get_settings")
    def test_init_with_token(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with valid token."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-token-123"
        mock_get_settings.return_value = settings

        client = TelegramClient()

        self.assertTrue(client.enabled)
        self.assertEqual(client.provider, "telegram")
        self.assertEqual(client.max_text_length, 3500)
        self.assertIn("test-token-123", client._base_url)

    @patch("app.services.im_providers.get_settings")
    def test_init_without_token(self, mock_get_settings: MagicMock) -> None:
        """Test initialization without token."""
        settings = MagicMock()
        settings.telegram_bot_token = None
        mock_get_settings.return_value = settings

        client = TelegramClient()

        self.assertFalse(client.enabled)

    @patch("app.services.im_providers.get_settings")
    def test_init_with_empty_token(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with empty token."""
        settings = MagicMock()
        settings.telegram_bot_token = "   "
        mock_get_settings.return_value = settings

        client = TelegramClient()

        self.assertFalse(client.enabled)

    @patch("app.services.im_providers.get_settings")
    def test_init_with_whitespace_token(self, mock_get_settings: MagicMock) -> None:
        """Test initialization strips whitespace from token."""
        settings = MagicMock()
        settings.telegram_bot_token = "  my-token  "
        mock_get_settings.return_value = settings

        client = TelegramClient()

        self.assertTrue(client.enabled)
        self.assertIn("my-token", client._base_url)


class TestTelegramClientSendText(unittest.TestCase):
    """Test TelegramClient.send_text method."""

    @patch("app.services.im_providers.get_settings")
    def test_send_text_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test send_text returns False when disabled."""
        settings = MagicMock()
        settings.telegram_bot_token = None
        mock_get_settings.return_value = settings

        client = TelegramClient()

        import asyncio

        result = asyncio.run(client.send_text(destination="chat-123", text="Hello"))
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful message send."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-token"
        mock_get_settings.return_value = settings

        client = TelegramClient()

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.is_success = True

        import asyncio

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(
                    destination="chat-123", text="Hello World"
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_failure(self, mock_get_settings: MagicMock) -> None:
        """Test message send failure."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-token"
        mock_get_settings.return_value = settings

        client = TelegramClient()

        # Mock httpx.AsyncClient with failed response
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = '{"ok": false, "description": "Bad Request"}'

        import asyncio

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="chat-123", text="Test")

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_http_error(self, mock_get_settings: MagicMock) -> None:
        """Test message send with HTTP error raises exception."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-token"
        mock_get_settings.return_value = settings

        client = TelegramClient()

        import asyncio

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=httpx.RequestError("Network error")
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(httpx.RequestError):
                    await client.send_text(destination="chat-123", text="Test")

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_send_text_payload_format(self, mock_get_settings: MagicMock) -> None:
        """Test that send_text sends correct payload."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-token"
        mock_get_settings.return_value = settings

        client = TelegramClient()

        mock_response = MagicMock()
        mock_response.is_success = True

        import asyncio

        async def run_test() -> dict:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await client.send_text(destination="chat-123", text="Test message")

                # Check the call
                call_args = mock_client.post.call_args
                return {
                    "url": call_args.args[0],
                    "json": call_args.kwargs.get("json"),
                }

        result = asyncio.run(run_test())
        self.assertEqual(result["url"], client._base_url + "/sendMessage")
        self.assertEqual(result["json"]["chat_id"], "chat-123")
        self.assertEqual(result["json"]["text"], "Test message")
        self.assertTrue(result["json"]["disable_web_page_preview"])


class TestParseTelegramUpdate(unittest.TestCase):
    """Test parse_telegram_update function."""

    def test_valid_message(self) -> None:
        """Test parsing valid Telegram update."""
        payload = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "chat": {"id": 789},
                "text": "Hello bot",
                "from": {"id": 111},
            },
        }

        result = parse_telegram_update(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.provider, "telegram")
        self.assertEqual(result.destination, "789")
        self.assertEqual(result.message_id, "456")
        self.assertEqual(result.sender_id, "111")
        self.assertEqual(result.text, "Hello bot")

    def test_edited_message(self) -> None:
        """Test parsing edited message."""
        payload = {
            "update_id": 123,
            "edited_message": {
                "message_id": 456,
                "chat": {"id": 789},
                "text": "Edited text",
            },
        }

        result = parse_telegram_update(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.text, "Edited text")

    def test_no_message(self) -> None:
        """Test payload without message."""
        result = parse_telegram_update({"update_id": 123})
        self.assertIsNone(result)

    def test_message_not_dict(self) -> None:
        """Test payload with non-dict message."""
        result = parse_telegram_update({"message": "not a dict"})
        self.assertIsNone(result)

    def test_no_chat(self) -> None:
        """Test message without chat."""
        result = parse_telegram_update({"message": {"text": "hello"}})
        self.assertIsNone(result)

    def test_no_chat_id(self) -> None:
        """Test chat without id."""
        result = parse_telegram_update({"message": {"chat": {}, "text": "hello"}})
        self.assertIsNone(result)

    def test_no_text(self) -> None:
        """Test message without text."""
        result = parse_telegram_update({"message": {"chat": {"id": 123}}})
        self.assertIsNone(result)

    def test_text_not_string(self) -> None:
        """Test message with non-string text."""
        result = parse_telegram_update({"message": {"chat": {"id": 123}, "text": 123}})
        self.assertIsNone(result)

    def test_no_sender(self) -> None:
        """Test message without sender."""
        payload = {
            "message": {
                "message_id": 456,
                "chat": {"id": 789},
                "text": "Hello",
            }
        }

        result = parse_telegram_update(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.sender_id)

    def test_sender_without_id(self) -> None:
        """Test sender without id."""
        payload = {
            "message": {
                "message_id": 456,
                "chat": {"id": 789},
                "text": "Hello",
                "from": {"name": "User"},
            }
        }

        result = parse_telegram_update(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.sender_id)

    def test_fallback_to_update_id(self) -> None:
        """Test message_id falls back to update_id."""
        payload = {
            "update_id": 999,
            "message": {
                "chat": {"id": 789},
                "text": "Hello",
            },
        }

        result = parse_telegram_update(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.message_id, "999")


class TestNormalizeImText(unittest.TestCase):
    """Test _normalize_im_text function."""

    def test_normal_text(self) -> None:
        """Test normal text unchanged."""
        result = _normalize_im_text("Hello World")
        self.assertEqual(result, "Hello World")

    def test_replaces_special_spaces(self) -> None:
        """Test replaces special Unicode spaces."""
        # U+2005 and U+2006 are special space characters
        result = _normalize_im_text("Hello\u2005World\u2006Test")
        self.assertEqual(result, "Hello World Test")

    def test_strips_whitespace(self) -> None:
        """Test strips leading/trailing whitespace."""
        result = _normalize_im_text("  Hello World  ")
        self.assertEqual(result, "Hello World")

    def test_empty_string(self) -> None:
        """Test empty string."""
        result = _normalize_im_text("")
        self.assertEqual(result, "")

    def test_none_returns_empty(self) -> None:
        """Test None returns empty string."""
        result = _normalize_im_text(None)  # type: ignore
        self.assertEqual(result, "")


class TestIsTruthy(unittest.TestCase):
    """Test _is_truthy function."""

    def test_true_values(self) -> None:
        """Test truthy values."""
        self.assertTrue(_is_truthy(True))
        self.assertTrue(_is_truthy(1))
        self.assertTrue(_is_truthy("true"))
        self.assertTrue(_is_truthy("True"))
        self.assertTrue(_is_truthy("TRUE"))
        self.assertTrue(_is_truthy("yes"))
        self.assertTrue(_is_truthy("Yes"))
        self.assertTrue(_is_truthy("y"))
        self.assertTrue(_is_truthy("Y"))
        self.assertTrue(_is_truthy("1"))

    def test_false_values(self) -> None:
        """Test falsy values."""
        self.assertFalse(_is_truthy(False))
        self.assertFalse(_is_truthy(0))
        self.assertFalse(_is_truthy("false"))
        self.assertFalse(_is_truthy("no"))
        self.assertFalse(_is_truthy("0"))
        self.assertFalse(_is_truthy(""))
        self.assertFalse(_is_truthy(None))
        self.assertFalse(_is_truthy("on"))  # "on" is not truthy
        self.assertFalse(_is_truthy("random"))


class TestSplitText(unittest.TestCase):
    """Test _split_text function."""

    def test_short_text(self) -> None:
        """Test text shorter than max length."""
        result = _split_text("Hello", max_len=100)
        self.assertEqual(result, ["Hello"])

    def test_exact_length(self) -> None:
        """Test text exactly at max length."""
        text = "x" * 10
        result = _split_text(text, max_len=10)
        self.assertEqual(result, [text])

    def test_long_text(self) -> None:
        """Test text longer than max length."""
        text = "x" * 25
        result = _split_text(text, max_len=10)
        self.assertEqual(len(result), 3)
        self.assertEqual("".join(result), text)

    def test_preserves_newlines(self) -> None:
        """Test preserves newlines in text."""
        text = "Line1\nLine2\nLine3"
        result = _split_text(text, max_len=100)
        self.assertEqual(result, [text])

    def test_empty_text(self) -> None:
        """Test empty text returns list with empty string."""
        result = _split_text("", max_len=10)
        self.assertEqual(result, [""])

    def test_splits_on_newline(self) -> None:
        """Test prefers splitting on newline."""
        text = "Line1\nLine2\nLine3"
        result = _split_text(text, max_len=10)
        # Should split at newlines
        self.assertIn("Line1", result[0])

    def test_splits_when_no_newline(self) -> None:
        """Test splits at max_len when no newline."""
        text = "xxxxxxxxxxxxxxxxx"  # 17 chars, no newline
        result = _split_text(text, max_len=10)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 10)


class TestReadField(unittest.TestCase):
    """Test _read_field function."""

    def test_dict_value(self) -> None:
        """Test reading from dict."""
        from app.services.im_providers import _read_field

        result = _read_field({"key": "value"}, "key")
        self.assertEqual(result, "value")

    def test_dict_missing_key(self) -> None:
        """Test reading missing key from dict."""
        from app.services.im_providers import _read_field

        result = _read_field({"key": "value"}, "other")
        self.assertIsNone(result)

    def test_none_value(self) -> None:
        """Test reading from None."""
        from app.services.im_providers import _read_field

        result = _read_field(None, "key")
        self.assertIsNone(result)

    def test_object_with_attribute(self) -> None:
        """Test reading attribute from object."""
        from app.services.im_providers import _read_field

        obj = MagicMock()
        obj.my_attr = "attr_value"
        result = _read_field(obj, "my_attr")
        self.assertEqual(result, "attr_value")


class TestParseReceiveTarget(unittest.TestCase):
    """Test _parse_receive_target function."""

    def test_chat_id_prefix(self) -> None:
        """Test chat_id prefix."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("chat_id:12345")
        self.assertEqual(prefix, "chat_id")
        self.assertEqual(value, "12345")

    def test_open_id_prefix(self) -> None:
        """Test open_id prefix."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("open_id:abc123")
        self.assertEqual(prefix, "open_id")
        self.assertEqual(value, "abc123")

    def test_user_id_prefix(self) -> None:
        """Test user_id prefix."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("user_id:xyz")
        self.assertEqual(prefix, "user_id")
        self.assertEqual(value, "xyz")

    def test_no_prefix(self) -> None:
        """Test value without prefix."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("12345")
        self.assertEqual(prefix, "chat_id")
        self.assertEqual(value, "12345")

    def test_empty_string(self) -> None:
        """Test empty string."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("")
        self.assertEqual(prefix, "chat_id")
        self.assertEqual(value, "")

    def test_unknown_prefix(self) -> None:
        """Test unknown prefix treated as no prefix."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("unknown:value")
        self.assertEqual(prefix, "chat_id")
        self.assertEqual(value, "unknown:value")

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace."""
        from app.services.im_providers import _parse_receive_target

        prefix, value = _parse_receive_target("  chat_id:123  ")
        self.assertEqual(prefix, "chat_id")
        self.assertEqual(value, "123")


class TestParsePositiveInt(unittest.TestCase):
    """Test _parse_positive_int function."""

    def test_positive_int(self) -> None:
        """Test positive integer."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int(42, default=0)
        self.assertEqual(result, 42)

    def test_zero_returns_default(self) -> None:
        """Test zero returns default."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int(0, default=10)
        self.assertEqual(result, 10)

    def test_negative_returns_default(self) -> None:
        """Test negative returns default."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int(-5, default=10)
        self.assertEqual(result, 10)

    def test_string_positive(self) -> None:
        """Test positive string."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int("42", default=0)
        self.assertEqual(result, 42)

    def test_invalid_string_returns_default(self) -> None:
        """Test invalid string returns default."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int("not a number", default=10)
        self.assertEqual(result, 10)

    def test_none_returns_default(self) -> None:
        """Test None returns default."""
        from app.services.im_providers import _parse_positive_int

        result = _parse_positive_int(None, default=10)
        self.assertEqual(result, 10)


class TestTryDumpDict(unittest.TestCase):
    """Test _try_dump_dict function."""

    def test_dict_input(self) -> None:
        """Test dict input returns itself."""
        from app.services.im_providers import _try_dump_dict

        result = _try_dump_dict({"key": "value"})
        self.assertEqual(result, {"key": "value"})

    def test_object_with_model_dump(self) -> None:
        """Test object with model_dump method."""
        from app.services.im_providers import _try_dump_dict

        obj = MagicMock()
        obj.model_dump = MagicMock(return_value={"dumped": "value"})
        result = _try_dump_dict(obj)
        self.assertEqual(result, {"dumped": "value"})

    def test_object_with_model_dump_exception(self) -> None:
        """Test object with model_dump that raises exception."""
        from app.services.im_providers import _try_dump_dict

        obj = MagicMock()
        obj.model_dump = MagicMock(side_effect=RuntimeError("error"))
        result = _try_dump_dict(obj)
        self.assertIsNone(result)

    def test_object_with_model_dump_non_dict(self) -> None:
        """Test object with model_dump returning non-dict."""
        from app.services.im_providers import _try_dump_dict

        obj = MagicMock()
        obj.model_dump = MagicMock(return_value="not a dict")
        # No to_dict method
        delattr(obj, "to_dict")
        result = _try_dump_dict(obj)
        self.assertIsNone(result)

    def test_object_with_to_dict(self) -> None:
        """Test object with to_dict method."""
        from app.services.im_providers import _try_dump_dict

        obj = MagicMock()
        delattr(obj, "model_dump")
        obj.to_dict = MagicMock(return_value={"to": "dict"})
        result = _try_dump_dict(obj)
        self.assertEqual(result, {"to": "dict"})

    def test_object_with_to_dict_exception(self) -> None:
        """Test object with to_dict that raises exception."""
        from app.services.im_providers import _try_dump_dict

        obj = MagicMock()
        delattr(obj, "model_dump")
        obj.to_dict = MagicMock(side_effect=RuntimeError("error"))
        result = _try_dump_dict(obj)
        self.assertIsNone(result)

    def test_object_without_methods(self) -> None:
        """Test object without dump methods."""
        from app.services.im_providers import _try_dump_dict

        obj = object()
        result = _try_dump_dict(obj)
        self.assertIsNone(result)


class TestDingTalkClientInit(unittest.TestCase):
    """Test DingTalkClient initialization."""

    @patch("app.services.im_providers.get_settings")
    def test_init_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test initialization when disabled."""
        settings = MagicMock()
        settings.dingtalk_enabled = False
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        self.assertFalse(client.enabled)
        self.assertFalse(client._openapi_enabled)

    @patch("app.services.im_providers.get_settings")
    def test_init_enabled_with_webhook(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with webhook only."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = "https://webhook.example.com"
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        self.assertTrue(client.enabled)
        self.assertEqual(client._fallback_webhook, "https://webhook.example.com")
        self.assertFalse(client._openapi_enabled)

    @patch("app.services.im_providers.get_settings")
    def test_init_enabled_with_openapi(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with OpenAPI configured."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        self.assertTrue(client.enabled)
        self.assertTrue(client._openapi_enabled)
        self.assertEqual(client._open_base_url, "https://api.dingtalk.com")

    @patch("app.services.im_providers.get_settings")
    def test_init_strips_whitespace(self, mock_get_settings: MagicMock) -> None:
        """Test that whitespace is stripped from config values."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = "  https://webhook.example.com  "
        settings.dingtalk_open_base_url = (
            "https://api.dingtalk.com/"  # rstrip only, not strip
        )
        settings.dingtalk_client_id = "  client-id  "
        settings.dingtalk_client_secret = "  client-secret  "
        settings.dingtalk_robot_code = "  robot-code  "
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        self.assertEqual(client._fallback_webhook, "https://webhook.example.com")
        self.assertEqual(client._open_base_url, "https://api.dingtalk.com")
        self.assertEqual(client._client_id, "client-id")


class TestDingTalkClientRefreshAccessToken(unittest.TestCase):
    """Test DingTalkClient._refresh_access_token method."""

    @patch("app.services.im_providers.get_settings")
    def test_refresh_without_openapi(self, mock_get_settings: MagicMock) -> None:
        """Test refresh raises error when OpenAPI not configured."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        settings.dingtalk_webhook_url = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(client._refresh_access_token())

        self.assertIn("not configured", str(ctx.exception))

    @patch("app.services.im_providers.get_settings")
    def test_refresh_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful token refresh."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "accessToken": "test-token",
            "expireIn": 7200,
        }

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await client._refresh_access_token()

                self.assertEqual(client._access_token, "test-token")
                self.assertGreater(client._token_expire_ts, time.time())

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_http_failure(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with HTTP failure."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 401

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_access_token()

                self.assertIn("HTTP 401", str(ctx.exception))

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_missing_token(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with missing token in response."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"expireIn": 7200}

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_access_token()

                self.assertIn("missing access token", str(ctx.exception))

        asyncio.run(run_test())


class TestDingTalkClientGetAccessToken(unittest.TestCase):
    """Test DingTalkClient._get_access_token method."""

    @patch("app.services.im_providers.get_settings")
    def test_get_token_from_cache(self, mock_get_settings: MagicMock) -> None:
        """Test getting token from cache."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "cached-token"
        client._token_expire_ts = time.time() + 3600

        async def run_test() -> str:
            return await client._get_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "cached-token")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_refreshes_expired(self, mock_get_settings: MagicMock) -> None:
        """Test token refresh when expired."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "expired-token"
        client._token_expire_ts = time.time() - 100  # Expired

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"accessToken": "new-token", "expireIn": 7200}

        async def run_test() -> str:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._get_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "new-token")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_lock_recheck(self, mock_get_settings: MagicMock) -> None:
        """Test token recheck after acquiring lock."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        # Set expired to trigger lock acquisition, but will be refreshed by another coroutine
        client._access_token = None
        client._token_expire_ts = 0

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"accessToken": "new-token", "expireIn": 7200}

        async def run_test() -> str:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._get_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "new-token")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_second_check_succeeds(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test second check inside lock succeeds (L138)."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        # First check fails (no token)
        client._access_token = None
        client._token_expire_ts = 0

        async def run_test() -> str:
            # Create a custom lock that sets the token when entering
            class MockLock:
                async def __aenter__(self) -> "MockLock":
                    # Simulate another coroutine setting the token
                    client._access_token = "token-from-other-coroutine"
                    client._token_expire_ts = time.time() + 3600
                    return self

                async def __aexit__(self, *args: object) -> None:
                    pass

            client._token_lock = MockLock()

            return await client._get_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "token-from-other-coroutine")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_empty_after_refresh(self, mock_get_settings: MagicMock) -> None:
        """Test error when token is empty after refresh."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = None
        client._token_expire_ts = 0

        # Mock response with empty token - this raises in _refresh_access_token
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"accessToken": "", "expireIn": 7200}

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._get_access_token()

                self.assertIn("missing access token", str(ctx.exception))

    @patch("app.services.im_providers.get_settings")
    def test_get_token_sets_empty_string(self, mock_get_settings: MagicMock) -> None:
        """Test error when refresh sets empty string token."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = None
        client._token_expire_ts = 0

        # Mock _refresh_access_token to set empty string
        async def mock_refresh() -> None:
            client._access_token = ""
            client._token_expire_ts = time.time() + 3600

        async def run_test() -> None:
            with patch.object(client, "_refresh_access_token", mock_refresh):
                with self.assertRaises(RuntimeError) as ctx:
                    await client._get_access_token()

                self.assertIn("token is empty", str(ctx.exception))

        asyncio.run(run_test())


class TestDingTalkClientSendViaWebhook(unittest.TestCase):
    """Test DingTalkClient._send_via_webhook method."""

    @patch("app.services.im_providers.get_settings")
    def test_webhook_send_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful webhook send."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_via_webhook(
                    url="https://webhook.example.com", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_webhook_send_failure(self, mock_get_settings: MagicMock) -> None:
        """Test webhook send failure."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = '{"errcode": 400}'

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_via_webhook(
                    url="https://webhook.example.com", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)


class TestDingTalkClientSendText(unittest.TestCase):
    """Test DingTalkClient.send_text method."""

    @patch("app.services.im_providers.get_settings")
    def test_send_text_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test send_text returns False when disabled."""
        settings = MagicMock()
        settings.dingtalk_enabled = False
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        result = asyncio.run(client.send_text(destination="chat-123", text="Hello"))
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_empty_destination(self, mock_get_settings: MagicMock) -> None:
        """Test send_text with empty destination."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        result = asyncio.run(client.send_text(destination="", text="Hello"))
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_webhook_url(self, mock_get_settings: MagicMock) -> None:
        """Test send_text with webhook URL as destination."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        mock_response = MagicMock()
        mock_response.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(
                    destination="https://webhook.example.com", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_fallback_webhook(self, mock_get_settings: MagicMock) -> None:
        """Test send_text uses fallback webhook when OpenAPI fails."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = "https://fallback.webhook.com"
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        # Mock OpenAPI failure, webhook success
        mock_response_fail = MagicMock()
        mock_response_fail.is_success = False
        mock_response_fail.status_code = 400
        mock_response_fail.text = "{}"

        mock_response_ok = MagicMock()
        mock_response_ok.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                # First call (token refresh), second call (group message fail),
                # third call (private message fail), fourth call (fallback webhook)
                mock_client.post = AsyncMock(
                    side_effect=[
                        MagicMock(
                            is_success=True,
                            json=lambda: {"accessToken": "token", "expireIn": 7200},
                        ),
                        mock_response_fail,
                        mock_response_fail,
                        mock_response_ok,
                    ]
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="chat-123", text="Hello")

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_no_route(self, mock_get_settings: MagicMock) -> None:
        """Test send_text with no route available."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        result = asyncio.run(client.send_text(destination="chat-123", text="Hello"))
        self.assertFalse(result)


class TestDingTalkClientSendViaOpenapi(unittest.TestCase):
    """Test DingTalkClient._send_via_openapi method."""

    @patch("app.services.im_providers.get_settings")
    def test_openapi_not_enabled(self, mock_get_settings: MagicMock) -> None:
        """Test OpenAPI send when not enabled."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = None
        settings.dingtalk_client_id = None
        settings.dingtalk_client_secret = None
        settings.dingtalk_robot_code = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        result = asyncio.run(
            client._send_via_openapi(conversation_id="chat-123", text="Hello")
        )
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_openapi_auth_error(self, mock_get_settings: MagicMock) -> None:
        """Test OpenAPI send with auth error."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()

        async def run_test() -> bool:
            # Mock _get_access_token to raise exception
            with patch.object(
                client, "_get_access_token", side_effect=RuntimeError("Auth failed")
            ):
                return await client._send_via_openapi(
                    conversation_id="chat-123", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_openapi_group_message_success(self, mock_get_settings: MagicMock) -> None:
        """Test OpenAPI group message send success."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "test-token"
        client._token_expire_ts = time.time() + 3600

        mock_response_ok = MagicMock()
        mock_response_ok.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response_ok)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_via_openapi(
                    conversation_id="chat-123", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_openapi_private_message_success(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test OpenAPI private message send success after group fails."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "test-token"
        client._token_expire_ts = time.time() + 3600

        mock_response_fail = MagicMock()
        mock_response_fail.is_success = False
        mock_response_fail.status_code = 400
        mock_response_fail.text = "{}"

        mock_response_ok = MagicMock()
        mock_response_ok.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=[mock_response_fail, mock_response_ok]
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_via_openapi(
                    conversation_id="chat-123", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_openapi_both_fail(self, mock_get_settings: MagicMock) -> None:
        """Test OpenAPI when both group and private message fail."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "test-token"
        client._token_expire_ts = time.time() + 3600

        mock_response_fail = MagicMock()
        mock_response_fail.is_success = False
        mock_response_fail.status_code = 400
        mock_response_fail.text = "{}"

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=[mock_response_fail, mock_response_fail]
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_via_openapi(
                    conversation_id="chat-123", text="Hello"
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)


class TestDingTalkClientSendTextOpenapiSuccess(unittest.TestCase):
    """Test DingTalkClient.send_text with OpenAPI success path."""

    @patch("app.services.im_providers.get_settings")
    def test_send_text_openapi_success(self, mock_get_settings: MagicMock) -> None:
        """Test send_text succeeds via OpenAPI."""
        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_webhook_url = None
        settings.dingtalk_open_base_url = "https://api.dingtalk.com"
        settings.dingtalk_client_id = "client-id"
        settings.dingtalk_client_secret = "client-secret"
        settings.dingtalk_robot_code = "robot-code"
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        client._access_token = "test-token"
        client._token_expire_ts = time.time() + 3600

        mock_response_ok = MagicMock()
        mock_response_ok.is_success = True

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response_ok)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="chat-123", text="Hello")

        result = asyncio.run(run_test())
        self.assertTrue(result)


class TestFeishuClientInit(unittest.TestCase):
    """Test FeishuClient initialization."""

    @patch("app.services.im_providers.get_settings")
    def test_init_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test initialization when disabled."""
        settings = MagicMock()
        settings.feishu_enabled = False
        settings.feishu_base_url = None
        settings.feishu_app_id = None
        settings.feishu_app_secret = None
        mock_get_settings.return_value = settings

        client = FeishuClient()

        self.assertFalse(client.enabled)

    @patch("app.services.im_providers.get_settings")
    def test_init_enabled(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with all config."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        self.assertTrue(client.enabled)
        self.assertEqual(client._base_url, "https://open.feishu.cn")
        self.assertEqual(client._app_id, "app-id")

    @patch("app.services.im_providers.get_settings")
    def test_init_missing_app_id(self, mock_get_settings: MagicMock) -> None:
        """Test initialization with missing app_id."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = None
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        self.assertFalse(client.enabled)

    @patch("app.services.im_providers.get_settings")
    def test_enabled_property_checks_all_config(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test enabled property requires all config."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = ""  # Empty
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        self.assertFalse(client.enabled)


class TestFeishuClientRefreshToken(unittest.TestCase):
    """Test FeishuClient._refresh_tenant_access_token method."""

    @patch("app.services.im_providers.get_settings")
    def test_refresh_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test refresh raises error when not configured."""
        settings = MagicMock()
        settings.feishu_enabled = False
        settings.feishu_base_url = None
        settings.feishu_app_id = None
        settings.feishu_app_secret = None
        mock_get_settings.return_value = settings

        client = FeishuClient()

        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(client._refresh_tenant_access_token())

        self.assertIn("not configured", str(ctx.exception))

    @patch("app.services.im_providers.get_settings")
    def test_refresh_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful token refresh."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test-token",
            "expire": 7200,
        }

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await client._refresh_tenant_access_token()

                self.assertEqual(client._tenant_access_token, "test-token")
                self.assertGreater(client._token_expire_ts, time.time())

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_http_failure(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with HTTP failure."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 401

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_tenant_access_token()

                self.assertIn("HTTP 401", str(ctx.exception))

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_invalid_json(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with invalid JSON response."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = "not a dict"

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_tenant_access_token()

                self.assertIn("invalid JSON", str(ctx.exception))

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_error_code(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with error code in response."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"code": 10003, "msg": "invalid app_id"}

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_tenant_access_token()

                self.assertIn("code=10003", str(ctx.exception))

        asyncio.run(run_test())

    @patch("app.services.im_providers.get_settings")
    def test_refresh_missing_token(self, mock_get_settings: MagicMock) -> None:
        """Test refresh with missing token in response."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"code": 0, "expire": 7200}

        async def run_test() -> None:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with self.assertRaises(RuntimeError) as ctx:
                    await client._refresh_tenant_access_token()

                self.assertIn("missing tenant_access_token", str(ctx.exception))

        asyncio.run(run_test())


class TestFeishuClientGetToken(unittest.TestCase):
    """Test FeishuClient._get_tenant_access_token method."""

    @patch("app.services.im_providers.get_settings")
    def test_get_token_from_cache(self, mock_get_settings: MagicMock) -> None:
        """Test getting token from cache."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        client._tenant_access_token = "cached-token"
        client._token_expire_ts = time.time() + 3600

        async def run_test() -> str:
            return await client._get_tenant_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "cached-token")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_refreshes_expired(self, mock_get_settings: MagicMock) -> None:
        """Test token refresh when expired."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        client._tenant_access_token = "expired-token"
        client._token_expire_ts = time.time() - 100  # Expired

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "new-token",
            "expire": 7200,
        }

        async def run_test() -> str:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._get_tenant_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "new-token")

    @patch("app.services.im_providers.get_settings")
    def test_get_token_second_check_succeeds(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test second check inside lock succeeds (L298)."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        # First check fails (no token)
        client._tenant_access_token = None
        client._token_expire_ts = 0

        async def run_test() -> str:
            # Create a custom lock that sets the token when entering
            class MockLock:
                async def __aenter__(self) -> "MockLock":
                    # Simulate another coroutine setting the token
                    client._tenant_access_token = "token-from-other-coroutine"
                    client._token_expire_ts = time.time() + 3600
                    return self

                async def __aexit__(self, *args: object) -> None:
                    pass

            client._token_lock = MockLock()  # type: ignore

            return await client._get_tenant_access_token()

        result = asyncio.run(run_test())
        self.assertEqual(result, "token-from-other-coroutine")


class TestFeishuClientSendTextOnce(unittest.TestCase):
    """Test FeishuClient._send_text_once method."""

    @patch("app.services.im_providers.get_settings")
    def test_send_text_once_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful text send."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"code": 0}

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_text_once(
                    tenant_access_token="token",
                    receive_id_type="open_id",
                    receive_id="ou_xxx",
                    text="Hello",
                )

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_once_http_failure(self, mock_get_settings: MagicMock) -> None:
        """Test text send with HTTP failure."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = "{}"

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_text_once(
                    tenant_access_token="token",
                    receive_id_type="open_id",
                    receive_id="ou_xxx",
                    text="Hello",
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_once_invalid_json(self, mock_get_settings: MagicMock) -> None:
        """Test text send with invalid JSON response."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = "not a dict"

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_text_once(
                    tenant_access_token="token",
                    receive_id_type="open_id",
                    receive_id="ou_xxx",
                    text="Hello",
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.logger")
    @patch("app.services.im_providers.get_settings")
    def test_send_text_once_error_code(
        self, mock_get_settings: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test text send with error code in response."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "invalid receive_id",
        }

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client._send_text_once(
                    tenant_access_token="token",
                    receive_id_type="open_id",
                    receive_id="invalid",
                    text="Hello",
                )

        result = asyncio.run(run_test())
        self.assertFalse(result)


class TestFeishuClientSendText(unittest.TestCase):
    """Test FeishuClient.send_text method."""

    @patch("app.services.im_providers.get_settings")
    def test_send_text_disabled(self, mock_get_settings: MagicMock) -> None:
        """Test send_text returns False when disabled."""
        settings = MagicMock()
        settings.feishu_enabled = False
        settings.feishu_base_url = None
        settings.feishu_app_id = None
        settings.feishu_app_secret = None
        mock_get_settings.return_value = settings

        client = FeishuClient()

        result = asyncio.run(client.send_text(destination="ou_xxx", text="Hello"))
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_empty_destination(self, mock_get_settings: MagicMock) -> None:
        """Test send_text with empty destination."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        result = asyncio.run(client.send_text(destination="", text="Hello"))
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_auth_error(self, mock_get_settings: MagicMock) -> None:
        """Test send_text with auth error."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        async def run_test() -> bool:
            with patch.object(
                client,
                "_get_tenant_access_token",
                side_effect=RuntimeError("Auth failed"),
            ):
                return await client.send_text(destination="ou_xxx", text="Hello")

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.get_settings")
    def test_send_text_success(self, mock_get_settings: MagicMock) -> None:
        """Test successful send_text."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        client._tenant_access_token = "test-token"
        client._token_expire_ts = time.time() + 3600

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"code": 0}

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="ou_xxx", text="Hello")

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.logger")
    @patch("app.services.im_providers.get_settings")
    def test_send_text_retry_success(
        self, mock_get_settings: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test send_text retries and succeeds on second attempt."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        # First call: auth success, send fails
        # Second call: auth success, send succeeds
        mock_auth_response = MagicMock()
        mock_auth_response.is_success = True
        mock_auth_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "new-token",
            "expire": 7200,
        }

        mock_fail_response = MagicMock()
        mock_fail_response.is_success = True
        mock_fail_response.json.return_value = {"code": 99991661}  # token expired

        mock_success_response = MagicMock()
        mock_success_response.is_success = True
        mock_success_response.json.return_value = {"code": 0}

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                # First auth, first send (fail), second auth, second send (success)
                mock_client.post = AsyncMock(
                    side_effect=[
                        mock_auth_response,  # first auth
                        mock_fail_response,  # first send fails
                        mock_auth_response,  # second auth
                        mock_success_response,  # second send succeeds
                    ]
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="ou_xxx", text="Hello")

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @patch("app.services.im_providers.logger")
    @patch("app.services.im_providers.get_settings")
    def test_send_text_retry_auth_error(
        self, mock_get_settings: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test send_text retries and fails on auth error."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        # First send attempt succeeds but returns token expired code
        mock_fail_response = MagicMock()
        mock_fail_response.is_success = True
        mock_fail_response.json.return_value = {"code": 99991661}  # token expired

        async def run_test() -> bool:
            # First _get_tenant_access_token returns token
            # Second _get_tenant_access_token raises exception
            call_count = [0]

            async def mock_get_token() -> str:
                call_count[0] += 1
                if call_count[0] == 1:
                    return "token"
                raise RuntimeError("Auth failed on retry")

            with patch.object(client, "_get_tenant_access_token", mock_get_token):
                with patch.object(
                    client, "_send_text_once", AsyncMock(return_value=False)
                ):
                    return await client.send_text(destination="ou_xxx", text="Hello")

        result = asyncio.run(run_test())
        self.assertFalse(result)

    @patch("app.services.im_providers.logger")
    @patch("app.services.im_providers.get_settings")
    def test_send_text_both_attempts_fail(
        self, mock_get_settings: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test send_text when both attempts fail."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()

        mock_auth_response = MagicMock()
        mock_auth_response.is_success = True
        mock_auth_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "token",
            "expire": 7200,
        }

        mock_fail_response = MagicMock()
        mock_fail_response.is_success = True
        mock_fail_response.json.return_value = {"code": 99991661}

        mock_second_fail = MagicMock()
        mock_second_fail.is_success = True
        mock_second_fail.json.return_value = {"code": 99991663}

        async def run_test() -> bool:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=[
                        mock_auth_response,
                        mock_fail_response,
                        mock_auth_response,
                        mock_second_fail,
                    ]
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                return await client.send_text(destination="ou_xxx", text="Hello")

        result = asyncio.run(run_test())
        self.assertFalse(result)


class TestNotificationGateway(unittest.TestCase):
    """Test NotificationGateway class."""

    def test_init_creates_providers(self) -> None:
        """Test __init__ creates provider instances."""
        from app.services.im_providers import NotificationGateway

        with (
            patch("app.services.im_providers.TelegramClient") as mock_telegram,
            patch("app.services.im_providers.DingTalkClient") as mock_dingtalk,
            patch("app.services.im_providers.FeishuClient") as mock_feishu,
        ):
            mock_telegram.return_value = MagicMock()
            mock_dingtalk.return_value = MagicMock()
            mock_feishu.return_value = MagicMock()

            gateway = NotificationGateway()

            mock_telegram.assert_called_once()
            mock_dingtalk.assert_called_once()
            mock_feishu.assert_called_once()
            assert "telegram" in gateway._providers
            assert "dingtalk" in gateway._providers
            assert "feishu" in gateway._providers

    def test_get_provider_returns_client(self) -> None:
        """Test get_provider returns correct client."""
        from app.services.im_providers import NotificationGateway

        mock_telegram = MagicMock()
        mock_dingtalk = MagicMock()
        mock_feishu = MagicMock()

        with (
            patch(
                "app.services.im_providers.TelegramClient", return_value=mock_telegram
            ),
            patch(
                "app.services.im_providers.DingTalkClient", return_value=mock_dingtalk
            ),
            patch("app.services.im_providers.FeishuClient", return_value=mock_feishu),
        ):
            gateway = NotificationGateway()

            assert gateway.get_provider("telegram") is mock_telegram
            assert gateway.get_provider("dingtalk") is mock_dingtalk
            assert gateway.get_provider("feishu") is mock_feishu

    def test_get_provider_returns_none_for_unknown(self) -> None:
        """Test get_provider returns None for unknown provider."""
        from app.services.im_providers import NotificationGateway

        with (
            patch("app.services.im_providers.TelegramClient"),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            assert gateway.get_provider("unknown") is None

    @patch("app.services.im_providers.logger")
    def test_send_text_unknown_provider(self, mock_logger: MagicMock) -> None:
        """Test send_text returns False for unknown provider."""
        from app.services.im_providers import NotificationGateway

        with (
            patch("app.services.im_providers.TelegramClient"),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            result = asyncio.run(
                gateway.send_text(provider="unknown", destination="dest", text="Hello")
            )

            self.assertFalse(result)
            mock_logger.warning.assert_called_once()

    @patch("app.services.im_providers.logger")
    def test_send_text_disabled_provider(self, mock_logger: MagicMock) -> None:
        """Test send_text returns False for disabled provider."""
        from app.services.im_providers import NotificationGateway

        mock_client = MagicMock()
        mock_client.enabled = False

        with (
            patch("app.services.im_providers.TelegramClient", return_value=mock_client),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            result = asyncio.run(
                gateway.send_text(provider="telegram", destination="dest", text="Hello")
            )

            self.assertFalse(result)
            mock_logger.warning.assert_called_once()

    def test_send_text_success_single_chunk(self) -> None:
        """Test send_text succeeds with single chunk."""
        from app.services.im_providers import NotificationGateway

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.max_text_length = 4096
        mock_client.send_text = AsyncMock(return_value=True)

        with (
            patch("app.services.im_providers.TelegramClient", return_value=mock_client),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            result = asyncio.run(
                gateway.send_text(provider="telegram", destination="dest", text="Hello")
            )

            self.assertTrue(result)
            mock_client.send_text.assert_called_once_with(
                destination="dest", text="Hello"
            )

    def test_send_text_success_multiple_chunks(self) -> None:
        """Test send_text splits long text into chunks."""
        from app.services.im_providers import NotificationGateway

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.max_text_length = 10
        mock_client.send_text = AsyncMock(return_value=True)

        with (
            patch("app.services.im_providers.TelegramClient", return_value=mock_client),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            # Text longer than max_text_length (10)
            result = asyncio.run(
                gateway.send_text(
                    provider="telegram", destination="dest", text="Hello World Test"
                )
            )

            self.assertTrue(result)
            # Should be called multiple times due to chunking
            self.assertGreater(mock_client.send_text.call_count, 1)

    def test_send_text_stops_on_failure(self) -> None:
        """Test send_text stops sending on failure."""
        from app.services.im_providers import NotificationGateway

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.max_text_length = 5  # Small to force multiple chunks
        mock_client.send_text = AsyncMock(side_effect=[True, False])

        with (
            patch("app.services.im_providers.TelegramClient", return_value=mock_client),
            patch("app.services.im_providers.DingTalkClient"),
            patch("app.services.im_providers.FeishuClient"),
        ):
            gateway = NotificationGateway()

            result = asyncio.run(
                gateway.send_text(
                    provider="telegram", destination="dest", text="Hello World"
                )
            )

            self.assertFalse(result)
            # Should stop after second chunk fails
            self.assertEqual(mock_client.send_text.call_count, 2)


class TestParseDingTalkWebhookEvent(unittest.TestCase):
    """Test parse_dingtalk_webhook_event function."""

    def test_returns_none_for_non_text_msgtype(self) -> None:
        """Test returns None when msgtype is not 'text'."""
        result = parse_dingtalk_webhook_event(
            {"msgtype": "picture", "conversationType": "1"}
        )
        self.assertIsNone(result)

    def test_returns_none_for_empty_msgtype(self) -> None:
        """Test returns None when msgtype is empty and conversationType is 2."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "",
                "conversationType": "2",
                "openConversationId": "conv-123",
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_no_explicit_mention(self) -> None:
        """Test returns None when no explicit mention in group chat."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "2",
                "isInAtList": False,
                "openConversationId": "conv-123",
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_missing_destination(self) -> None:
        """Test returns None when no conversation_id or sessionWebhook."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "@bot hello"},
                "conversationType": "1",
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_sender_is_bot(self) -> None:
        """Test returns None when sender is the bot itself."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "chatbotUserId": "bot-001",
                "senderStaffId": "bot-001",
            }
        )
        self.assertIsNone(result)

    def test_parses_valid_payload_with_text_content(self) -> None:
        """Test parses valid payload with text.content."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello world"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "sessionWebhook": "webhook-456",
                "msgId": "msg-789",
                "senderStaffId": "user-001",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.provider, "dingtalk")
        self.assertEqual(result.destination, "conv-123")
        self.assertEqual(result.send_address, "webhook-456")
        self.assertEqual(result.message_id, "msg-789")
        self.assertEqual(result.sender_id, "user-001")
        self.assertEqual(result.text, "hello world")

    def test_parses_valid_payload_with_content_field(self) -> None:
        """Test parses valid payload with content field."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "content": "direct content",
                "conversationType": "1",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.text, "direct content")

    def test_uses_msgtype_alias(self) -> None:
        """Test handles msgType (camelCase) as alias."""
        result = parse_dingtalk_webhook_event(
            {
                "msgType": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)

    def test_uses_conversation_id_alias(self) -> None:
        """Test handles conversationId as alias for openConversationId."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "conversationId": "conv-456",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.destination, "conv-456")

    def test_uses_session_webhook_as_destination_fallback(self) -> None:
        """Test uses sessionWebhook when openConversationId is missing."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "sessionWebhook": "webhook-789",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.destination, "webhook-789")

    def test_sets_default_help_when_text_empty(self) -> None:
        """Test sets text to /help when cleaned text is empty."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "   "},  # whitespace only
                "conversationType": "1",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.text, "/help")

    def test_uses_message_id_aliases(self) -> None:
        """Test uses messageId or createAt as message_id fallback."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "messageId": "msg-alias",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.message_id, "msg-alias")

        result2 = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "createAt": "1234567890",
            }
        )

        self.assertIsNotNone(result2)
        assert result2 is not None
        self.assertEqual(result2.message_id, "1234567890")

    def test_uses_sender_id_aliases(self) -> None:
        """Test uses senderId or senderNick as sender_id fallback."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "senderId": "sender-alias",
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.sender_id, "sender-alias")

        result2 = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "1",
                "openConversationId": "conv-123",
                "senderNick": "nickname",
            }
        )

        self.assertIsNotNone(result2)
        assert result2 is not None
        self.assertEqual(result2.sender_id, "nickname")

    def test_group_chat_with_is_in_at_list_true(self) -> None:
        """Test group chat passes when isInAtList is true."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "2",
                "isInAtList": True,
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)

    def test_group_chat_with_at_users_including_bot(self) -> None:
        """Test group chat passes when atUsers includes bot."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "2",
                "atUsers": [{"dingtalkId": "bot-001"}],
                "chatbotUserId": "bot-001",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)

    def test_group_chat_with_text_mention(self) -> None:
        """Test group chat passes when text starts with @mention."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "@bot-001 hello"},
                "conversationType": "2",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNotNone(result)

    def test_returns_none_for_group_chat_without_mention(self) -> None:
        """Test group chat returns None when no mention and not in at list."""
        result = parse_dingtalk_webhook_event(
            {
                "msgtype": "text",
                "text": {"content": "hello"},
                "conversationType": "2",
                "isInAtList": False,
                "atUsers": [],
                "chatbotUserId": "bot-001",
                "openConversationId": "conv-123",
            }
        )

        self.assertIsNone(result)

    def test_raw_payload_included(self) -> None:
        """Test raw payload is included in result."""
        payload = {
            "msgtype": "text",
            "text": {"content": "hello"},
            "conversationType": "1",
            "openConversationId": "conv-123",
            "customField": "customValue",
        }

        result = parse_dingtalk_webhook_event(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.raw, payload)


class TestParseFeishuWebhookEvent(unittest.TestCase):
    """Test parse_feishu_webhook_event function."""

    def test_returns_none_when_event_is_none(self) -> None:
        """Test returns None when event is None."""
        result = parse_feishu_webhook_event(
            {"header": {"event_type": "im.message.receive_v1"}, "event": None}
        )
        self.assertIsNone(result)

    def test_returns_none_for_wrong_event_type(self) -> None:
        """Test returns None for unsupported event type."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "other.event"},
                "event": {"message": {"chat_id": "oc_xxx"}},
            }
        )
        self.assertIsNone(result)

    def test_returns_none_when_message_is_none(self) -> None:
        """Test returns None when message is None."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {"message": None},
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_non_text_message_type(self) -> None:
        """Test returns None for non-text message type."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "image",
                    }
                },
            }
        )
        self.assertIsNone(result)

    def test_returns_none_when_chat_id_empty(self) -> None:
        """Test returns None when chat_id is empty."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "",
                        "message_type": "text",
                    }
                },
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_non_user_sender(self) -> None:
        """Test returns None when sender_type is not user."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                    },
                    "sender": {"sender_type": "app"},
                },
            }
        )
        self.assertIsNone(result)

    def test_returns_none_for_group_without_mention(self) -> None:
        """Test returns None for group chat without explicit mention."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "group",
                        "content": '{"text": "hello"}',
                    },
                    "sender": {"sender_type": "user"},
                },
            }
        )
        self.assertIsNone(result)

    def test_parses_valid_p2p_message(self) -> None:
        """Test parses valid p2p message."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                        "content": '{"text": "hello world"}',
                        "message_id": "msg_123",
                    },
                    "sender": {
                        "sender_type": "user",
                        "sender_id": {"open_id": "ou_123"},
                    },
                },
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.provider, "feishu")
        self.assertEqual(result.destination, "oc_xxx")
        self.assertEqual(result.message_id, "msg_123")
        self.assertEqual(result.sender_id, "ou_123")
        self.assertEqual(result.text, "hello world")

    def test_parses_group_message_with_at_mention(self) -> None:
        """Test parses group message with @mention."""
        with patch("app.services.im_providers.get_settings") as mock_settings:
            settings = MagicMock()
            settings.feishu_app_id = "ou_bot"
            settings.feishu_bot_user_id = None
            settings.feishu_bot_open_id = None
            settings.feishu_bot_union_id = None
            settings.feishu_bot_name = "Bot"
            mock_settings.return_value = settings

            result = parse_feishu_webhook_event(
                {
                    "header": {"event_type": "im.message.receive_v1"},
                    "event": {
                        "message": {
                            "chat_id": "oc_xxx",
                            "message_type": "text",
                            "chat_type": "group",
                            "content": '<at user_id="ou_bot">@Bot</at> hello',
                            "message_id": "msg_456",
                        },
                        "sender": {"sender_type": "user"},
                    },
                }
            )

            self.assertIsNotNone(result)

    def test_sets_default_help_when_text_empty(self) -> None:
        """Test sets text to /help when content is empty."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                        "content": '{"text": "   "}',
                    },
                    "sender": {"sender_type": "user"},
                },
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.text, "/help")

    def test_uses_event_id_as_message_id_fallback(self) -> None:
        """Test uses event_id as message_id when message_id is missing."""
        result = parse_feishu_webhook_event(
            {
                "header": {
                    "event_type": "im.message.receive_v1",
                    "event_id": "evt_789",
                },
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                    },
                    "sender": {"sender_type": "user"},
                },
            }
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.message_id, "evt_789")

    def test_accepts_p2_event_type(self) -> None:
        """Test accepts p2.im.message.receive_v1 event type."""
        result = parse_feishu_webhook_event(
            {
                "header": {"event_type": "p2.im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                    },
                    "sender": {"sender_type": "user"},
                },
            }
        )

        self.assertIsNotNone(result)

    def test_raw_payload_included(self) -> None:
        """Test raw payload is included in result."""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "chat_id": "oc_xxx",
                    "message_type": "text",
                    "chat_type": "p2p",
                },
                "sender": {"sender_type": "user"},
            },
            "custom": "value",
        }

        result = parse_feishu_webhook_event(payload)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.raw, payload)


class TestParseFeishuStreamEvent(unittest.TestCase):
    """Test parse_feishu_stream_event function."""

    def test_parses_dict_input(self) -> None:
        """Test parses dict input correctly."""
        result = parse_feishu_stream_event(
            {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "message": {
                        "chat_id": "oc_xxx",
                        "message_type": "text",
                        "chat_type": "p2p",
                    },
                    "sender": {"sender_type": "user"},
                },
            }
        )

        self.assertIsNotNone(result)

    def test_returns_none_when_event_missing(self) -> None:
        """Test returns None when event is missing."""
        result = parse_feishu_stream_event({"header": {}})
        self.assertIsNone(result)

    def test_handles_object_with_getattr(self) -> None:
        """Test handles object with getattr for _read_field."""

        class MockEvent:
            def __init__(self) -> None:
                self.message = MockMessage()
                self.sender = MockSender()

        class MockMessage:
            def __init__(self) -> None:
                self.chat_id = "oc_xxx"
                self.message_type = "text"
                self.chat_type = "p2p"

        class MockSender:
            def __init__(self) -> None:
                self.sender_type = "user"

        class MockHeader:
            def __init__(self) -> None:
                self.event_type = "im.message.receive_v1"

        class MockData:
            def __init__(self) -> None:
                self.header = MockHeader()
                self.event = MockEvent()

        result = parse_feishu_stream_event(MockData())

        self.assertIsNotNone(result)


class TestExtractFeishuText(unittest.TestCase):
    """Test _extract_feishu_text helper function."""

    def test_returns_empty_for_empty_string(self) -> None:
        """Test returns empty string for empty input (L640)."""
        result = _extract_feishu_text("")
        self.assertEqual(result, "")

    def test_returns_empty_for_whitespace_only(self) -> None:
        """Test returns empty string for whitespace-only input (L640)."""
        result = _extract_feishu_text("   ")
        self.assertEqual(result, "")

    def test_returns_stripped_when_json_text_is_not_string(self) -> None:
        """Test returns stripped content when JSON text field is not a string (L648)."""
        result = _extract_feishu_text('{"text": 123}')
        self.assertEqual(result, '{"text": 123}')

    def test_returns_stripped_when_json_text_is_null(self) -> None:
        """Test returns stripped content when JSON text field is null (L648)."""
        result = _extract_feishu_text('{"text": null}')
        self.assertEqual(result, '{"text": null}')

    def test_returns_stripped_when_json_has_no_text(self) -> None:
        """Test returns stripped content when JSON has no text field (L648)."""
        result = _extract_feishu_text('{"other": "value"}')
        self.assertEqual(result, '{"other": "value"}')

    def test_returns_text_from_dict_content(self) -> None:
        """Test returns text when content is a dict with text field (L652)."""
        result = _extract_feishu_text({"text": "hello world"})
        self.assertEqual(result, "hello world")

    def test_returns_empty_when_dict_text_not_string(self) -> None:
        """Test returns empty when dict text field is not a string (L654 via L652 miss)."""
        result = _extract_feishu_text({"text": 123})
        self.assertEqual(result, "")

    def test_returns_empty_when_dict_has_no_text(self) -> None:
        """Test returns empty when dict has no text field (L654)."""
        result = _extract_feishu_text({"other": "value"})
        self.assertEqual(result, "")

    def test_returns_empty_for_none_content(self) -> None:
        """Test returns empty for None content (L654)."""
        result = _extract_feishu_text(None)
        self.assertEqual(result, "")

    def test_returns_text_from_json_string(self) -> None:
        """Test returns text from valid JSON string."""
        result = _extract_feishu_text('{"text": "hello"}')
        self.assertEqual(result, "hello")

    def test_returns_plain_string_when_not_json(self) -> None:
        """Test returns plain string when not valid JSON (L644)."""
        result = _extract_feishu_text("plain text")
        self.assertEqual(result, "plain text")


class TestExtractFeishuSenderId(unittest.TestCase):
    """Test _extract_feishu_sender_id helper function."""

    def test_returns_sender_id_open_id(self) -> None:
        """Test returns open_id from sender_id dict."""
        result = _extract_feishu_sender_id({"sender_id": {"open_id": "ou_123"}})
        self.assertEqual(result, "ou_123")

    def test_returns_sender_id_user_id(self) -> None:
        """Test returns user_id from sender_id dict."""
        result = _extract_feishu_sender_id({"sender_id": {"user_id": "user_456"}})
        self.assertEqual(result, "user_456")

    def test_returns_sender_id_union_id(self) -> None:
        """Test returns union_id from sender_id dict."""
        result = _extract_feishu_sender_id({"sender_id": {"union_id": "on_789"}})
        self.assertEqual(result, "on_789")

    def test_returns_sender_open_id_when_sender_id_missing(self) -> None:
        """Test returns open_id from sender directly when sender_id missing (L667)."""
        result = _extract_feishu_sender_id({"open_id": "ou_direct"})
        self.assertEqual(result, "ou_direct")

    def test_returns_sender_user_id_when_sender_id_empty(self) -> None:
        """Test returns user_id from sender when sender_id has no valid fields (L667)."""
        result = _extract_feishu_sender_id({"sender_id": {}, "user_id": "user_direct"})
        self.assertEqual(result, "user_direct")

    def test_returns_sender_union_id_fallback(self) -> None:
        """Test returns union_id from sender as last resort (L667)."""
        result = _extract_feishu_sender_id(
            {"sender_id": {"open_id": ""}, "union_id": "on_fallback"}
        )
        self.assertEqual(result, "on_fallback")

    def test_returns_none_when_no_valid_sender_id(self) -> None:
        """Test returns None when no valid sender ID found (L669)."""
        result = _extract_feishu_sender_id({})
        self.assertIsNone(result)

    def test_returns_none_when_sender_id_has_empty_values(self) -> None:
        """Test returns None when sender_id has only empty values."""
        result = _extract_feishu_sender_id(
            {"sender_id": {"open_id": "", "user_id": "   ", "union_id": ""}}
        )
        self.assertIsNone(result)

    def test_returns_none_for_none_sender(self) -> None:
        """Test returns None for None sender."""
        result = _extract_feishu_sender_id(None)
        self.assertIsNone(result)


class TestFeishuHasExplicitMention(unittest.TestCase):
    """Test _feishu_has_explicit_mention function."""

    def test_returns_false_for_empty_text(self) -> None:
        """Test returns False when text is empty (L685)."""
        result = _feishu_has_explicit_mention(raw_text="", mentions=None)
        self.assertFalse(result)

    def test_returns_false_for_whitespace_only(self) -> None:
        """Test returns False when text is whitespace only (L685)."""
        result = _feishu_has_explicit_mention(raw_text="   ", mentions=None)
        self.assertFalse(result)

    def test_returns_false_when_no_leading_mentions(self) -> None:
        """Test returns False when no leading mentions found."""
        with patch("app.services.im_providers.get_settings") as mock_settings:
            settings = MagicMock()
            settings.feishu_app_id = "cli_xxx"
            settings.feishu_bot_user_id = None
            settings.feishu_bot_open_id = None
            settings.feishu_bot_union_id = None
            settings.feishu_bot_name = "Bot"
            mock_settings.return_value = settings

            result = _feishu_has_explicit_mention(raw_text="hello world", mentions=None)
            self.assertFalse(result)

    def test_returns_true_via_plain_mention(self) -> None:
        """Test returns True via plain @mention (L700)."""
        with patch("app.services.im_providers.get_settings") as mock_settings:
            settings = MagicMock()
            settings.feishu_app_id = None
            settings.feishu_bot_user_id = None
            settings.feishu_bot_open_id = None
            settings.feishu_bot_union_id = None
            settings.feishu_bot_name = "Bot"
            mock_settings.return_value = settings

            # Text starts with @Bot (plain mention, not <at> tag)
            result = _feishu_has_explicit_mention(raw_text="@Bot hello", mentions=None)
            self.assertTrue(result)

    def test_returns_true_via_at_tag(self) -> None:
        """Test returns True via <at> tag mention."""
        with patch("app.services.im_providers.get_settings") as mock_settings:
            settings = MagicMock()
            settings.feishu_app_id = "cli_xxx"
            settings.feishu_bot_user_id = None
            settings.feishu_bot_open_id = None
            settings.feishu_bot_union_id = None
            settings.feishu_bot_name = None
            mock_settings.return_value = settings

            result = _feishu_has_explicit_mention(
                raw_text='<at user_id="cli_xxx">@Bot</at> hello', mentions=None
            )
            self.assertTrue(result)


class TestExtractFeishuLeadingPlainMentions(unittest.TestCase):
    """Test _extract_feishu_leading_plain_mentions function."""

    def test_returns_empty_for_no_leading_at(self) -> None:
        """Test returns empty list when text doesn't start with @."""
        result = _extract_feishu_leading_plain_mentions("hello world")
        self.assertEqual(result, [])

    def test_extracts_single_mention(self) -> None:
        """Test extracts single @mention (L756-758)."""
        result = _extract_feishu_leading_plain_mentions("@Bot hello")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "bot")
        self.assertEqual(result[0]["ids"], "")

    def test_extracts_multiple_mentions(self) -> None:
        """Test extracts multiple @mentions (L761 loop)."""
        result = _extract_feishu_leading_plain_mentions("@Bot @User hello world")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "bot")
        self.assertEqual(result[1]["name"], "user")

    def test_handles_single_token_only(self) -> None:
        """Test handles text with single token only (L759-760)."""
        result = _extract_feishu_leading_plain_mentions("@Bot")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "bot")

    def test_handles_fullwidth_at_symbol(self) -> None:
        """Test handles fullwidth @ symbol (L754, \uff20)."""
        result = _extract_feishu_leading_plain_mentions("\uff20Bot hello")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "bot")

    def test_stops_at_non_mention(self) -> None:
        """Test stops extracting at non-mention token (L754-755)."""
        result = _extract_feishu_leading_plain_mentions("hello @Bot")
        self.assertEqual(result, [])


class TestFeishuLeadingMentionsIncludeBot(unittest.TestCase):
    """Test _feishu_leading_mentions_include_bot function."""

    def test_returns_true_when_id_matches(self) -> None:
        """Test returns True when mention ID matches bot (L775-776)."""
        leading = [{"name": "bot", "ids": "cli_xxx"}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=None, bot_ids={"cli_xxx"}, bot_names=set()
        )
        self.assertTrue(result)

    def test_returns_true_when_name_matches(self) -> None:
        """Test returns True when mention name matches bot (L777-778)."""
        leading = [{"name": "bot", "ids": ""}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=None, bot_ids=set(), bot_names={"bot"}
        )
        self.assertTrue(result)

    def test_returns_false_when_no_match(self) -> None:
        """Test returns False when no match in leading_mentions."""
        leading = [{"name": "other", "ids": "other_id"}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=None, bot_ids={"cli_xxx"}, bot_names={"bot"}
        )
        self.assertFalse(result)

    def test_returns_false_when_mentions_not_list(self) -> None:
        """Test returns False when mentions is not a list (L780-781)."""
        leading = [{"name": "other", "ids": ""}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions="not_a_list", bot_ids={"cli_xxx"}, bot_names={"bot"}
        )
        self.assertFalse(result)

    def test_checks_mentions_list_for_id_match(self) -> None:
        """Test checks mentions list for ID match (L786-787)."""
        leading = [{"name": "unknown", "ids": ""}]
        mentions = [{"id": {"user_id": "cli_xxx"}}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=mentions, bot_ids={"cli_xxx"}, bot_names=set()
        )
        self.assertTrue(result)

    def test_checks_mentions_list_for_name_match(self) -> None:
        """Test checks mentions list for name match (L788-789)."""
        leading = [{"name": "unknown", "ids": ""}]
        mentions = [{"name": "Bot"}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=mentions, bot_ids=set(), bot_names={"bot"}
        )
        self.assertTrue(result)

    def test_returns_false_when_mentions_exhausted(self) -> None:
        """Test returns False when no match in mentions list (L791)."""
        leading = [{"name": "unknown", "ids": ""}]
        mentions = [{"name": "Other"}]
        result = _feishu_leading_mentions_include_bot(
            leading, mentions=mentions, bot_ids={"cli_xxx"}, bot_names={"bot"}
        )
        self.assertFalse(result)


class TestReadFeishuMentionIds(unittest.TestCase):
    """Test _read_feishu_mention_ids function."""

    def test_extracts_user_id(self) -> None:
        """Test extracts user_id (L800-801)."""
        mention = {"user_id": "user_123"}
        result = _read_feishu_mention_ids(mention)
        self.assertIn("user_123", result)

    def test_extracts_open_id(self) -> None:
        """Test extracts open_id (L800-801)."""
        mention = {"open_id": "ou_456"}
        result = _read_feishu_mention_ids(mention)
        self.assertIn("ou_456", result)

    def test_extracts_union_id(self) -> None:
        """Test extracts union_id (L800-801)."""
        mention = {"union_id": "on_789"}
        result = _read_feishu_mention_ids(mention)
        self.assertIn("on_789", result)

    def test_extracts_from_nested_id(self) -> None:
        """Test extracts from nested id field (L797-801)."""
        mention = {"id": {"user_id": "nested_user"}}
        result = _read_feishu_mention_ids(mention)
        self.assertIn("nested_user", result)

    def test_extracts_from_both_levels(self) -> None:
        """Test extracts from both mention and mention.id."""
        mention = {"user_id": "top_user", "id": {"open_id": "nested_open"}}
        result = _read_feishu_mention_ids(mention)
        self.assertIn("top_user", result)
        self.assertIn("nested_open", result)

    def test_ignores_empty_values(self) -> None:
        """Test ignores empty or whitespace values (L800)."""
        mention = {"user_id": "", "open_id": "   "}
        result = _read_feishu_mention_ids(mention)
        self.assertEqual(result, set())

    def test_returns_empty_for_none(self) -> None:
        """Test returns empty set for None input."""
        result = _read_feishu_mention_ids(None)
        self.assertEqual(result, set())


class TestDingTalkTokenCache(unittest.TestCase):
    """Test DingTalkClient token cache behavior (L138)."""

    @patch("app.services.im_providers.get_settings")
    def test_returns_cached_token_when_valid(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test returns cached token when not expired (L138)."""
        import time

        settings = MagicMock()
        settings.dingtalk_enabled = True
        settings.dingtalk_base_url = "https://oapi.dingtalk.com"
        settings.dingtalk_app_key = "test-key"
        settings.dingtalk_app_secret = "test-secret"
        settings.dingtalk_access_token = None
        mock_get_settings.return_value = settings

        client = DingTalkClient()
        # Set cached token with future expiry
        client._access_token = "cached-token"
        client._token_expire_ts = time.time() + 3600

        # Should return cached token without calling refresh
        result = asyncio.run(client._get_access_token())
        self.assertEqual(result, "cached-token")


class TestFeishuTokenCache(unittest.TestCase):
    """Test FeishuClient token cache behavior (L298, L301)."""

    @patch("app.services.im_providers.get_settings")
    def test_returns_cached_token_when_valid(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test returns cached token when not expired (L298)."""
        import time

        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        # Set cached token with future expiry
        client._tenant_access_token = "cached-feishu-token"
        client._token_expire_ts = time.time() + 3600

        # Should return cached token without calling refresh
        result = asyncio.run(client._get_tenant_access_token())
        self.assertEqual(result, "cached-feishu-token")

    @patch("app.services.im_providers.get_settings")
    def test_raises_when_token_empty_after_refresh(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test raises RuntimeError when token empty after refresh (L301)."""
        settings = MagicMock()
        settings.feishu_enabled = True
        settings.feishu_base_url = "https://open.feishu.cn"
        settings.feishu_app_id = "app-id"
        settings.feishu_app_secret = "app-secret"
        mock_get_settings.return_value = settings

        client = FeishuClient()
        # Mock _refresh_tenant_access_token to not set token
        with patch.object(
            client,
            "_refresh_tenant_access_token",
            new_callable=AsyncMock,
        ) as mock_refresh:
            # Refresh does nothing, leaving token as None
            mock_refresh.return_value = None

            with self.assertRaises(RuntimeError) as context:
                asyncio.run(client._get_tenant_access_token())

            self.assertIn("empty", str(context.exception))


class TestDingtalkAtUsersIncludeBot(unittest.TestCase):
    """Test _dingtalk_at_users_include_bot function (L836)."""

    def test_returns_false_when_no_match(self) -> None:
        """Test returns False when bot_user_id not in at_users (L836)."""
        result = _dingtalk_at_users_include_bot(
            bot_user_id="bot-123",
            at_users=[
                {"dingtalkId": "user-456"},
                {"staffId": "user-789"},
            ],
        )
        self.assertFalse(result)

    def test_returns_false_when_at_users_empty(self) -> None:
        """Test returns False when at_users is empty list."""
        result = _dingtalk_at_users_include_bot(
            bot_user_id="bot-123",
            at_users=[],
        )
        self.assertFalse(result)

    def test_returns_false_when_no_matching_key(self) -> None:
        """Test returns False when users have no matching key."""
        result = _dingtalk_at_users_include_bot(
            bot_user_id="bot-123",
            at_users=[{"otherField": "some-value"}],
        )
        self.assertFalse(result)


class TestIsTruthyFallback(unittest.TestCase):
    """Test _is_truthy fallback for other types (L848)."""

    def test_list_truthy(self) -> None:
        """Test non-empty list is truthy (L848)."""
        self.assertTrue(_is_truthy([1, 2, 3]))

    def test_list_falsy(self) -> None:
        """Test empty list is falsy (L848)."""
        self.assertFalse(_is_truthy([]))

    def test_dict_truthy(self) -> None:
        """Test non-empty dict is truthy (L848)."""
        self.assertTrue(_is_truthy({"key": "value"}))

    def test_dict_falsy(self) -> None:
        """Test empty dict is falsy (L848)."""
        self.assertFalse(_is_truthy({}))

    def test_custom_object_truthy(self) -> None:
        """Test custom object with __bool__ (L848)."""

        class TruthyObj:
            def __bool__(self) -> bool:
                return True

        self.assertTrue(_is_truthy(TruthyObj()))

    def test_custom_object_falsy(self) -> None:
        """Test custom object with falsy __bool__ (L848)."""

        class FalsyObj:
            def __bool__(self) -> bool:
                return False

        self.assertFalse(_is_truthy(FalsyObj()))


if __name__ == "__main__":
    unittest.main()
