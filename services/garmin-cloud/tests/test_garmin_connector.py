"""Tests for Garmin connector implementation."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from synheart_cloud_connector import WebhookError
from synheart_cloud_connector.vendor_types import VendorConfig, VendorType
from services.garmin_cloud.connector import GarminConnector


@pytest.fixture
def garmin_config():
    """Create Garmin config for testing."""
    return VendorConfig(
        vendor=VendorType.GARMIN,
        client_id="test_client_id",
        client_secret="test_client_secret",
        webhook_secret="test_webhook_secret",
        base_url="https://apis.garmin.com",
        auth_url="https://connect.garmin.com/oauthConfirm",
        token_url="https://connectapi.garmin.com/oauth-service/oauth/access_token",
        scopes=["WELLNESS_READ"],
    )


@pytest.fixture
def garmin_connector(garmin_config):
    """Create Garmin connector instance for testing."""
    token_store = MagicMock()
    queue = MagicMock()
    rate_limiter = MagicMock()

    return GarminConnector(
        config=garmin_config,
        token_store=token_store,
        queue=queue,
        rate_limiter=rate_limiter,
    )


class TestGarminConnector:
    """Tests for GarminConnector class."""

    def test_vendor_property(self, garmin_connector):
        """Test vendor property returns GARMIN."""
        assert garmin_connector.vendor == VendorType.GARMIN

    @pytest.mark.asyncio
    async def test_verify_webhook_valid_new_format(self, garmin_connector):
        """Test webhook verification with new Garmin-Signature header."""
        body = b'{"userId": "test_user", "summaries": []}'

        # Create valid signature
        signature = hmac.new(
            b"test_webhook_secret",
            body,
            hashlib.sha256,
        ).hexdigest()

        headers = {"Garmin-Signature": signature}

        result = await garmin_connector.verify_webhook(headers, body)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_webhook_valid_old_format(self, garmin_connector):
        """Test webhook verification with old X-Gfit-Signature header."""
        body = b'{"userId": "test_user", "summaries": []}'

        # Create valid signature
        signature = hmac.new(
            b"test_webhook_secret",
            body,
            hashlib.sha256,
        ).hexdigest()

        headers = {"X-Gfit-Signature": signature}

        result = await garmin_connector.verify_webhook(headers, body)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_webhook_missing_signature(self, garmin_connector):
        """Test webhook verification with missing signature."""
        headers = {}
        body = b'{"userId": "test_user"}'

        with pytest.raises(WebhookError) as exc_info:
            await garmin_connector.verify_webhook(headers, body)

        assert "Missing webhook signature header" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_webhook_invalid_signature(self, garmin_connector):
        """Test webhook verification with invalid signature."""
        headers = {"Garmin-Signature": "invalid_signature"}
        body = b'{"userId": "test_user"}'

        with pytest.raises(WebhookError) as exc_info:
            await garmin_connector.verify_webhook(headers, body)

        assert "SHA256 hash mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_event_daily_summary(self, garmin_connector):
        """Test parsing daily summary webhook event."""
        payload = {
            "userId": "user123",
            "userAccessToken": "token_abc",
            "summaries": [
                {
                    "summaryId": "daily-123",
                    "calendarDate": "2024-10-31",
                    "dataType": "DAILY",
                }
            ],
        }

        body = json.dumps(payload).encode()
        result = await garmin_connector.parse_event(body)

        assert result["user_id"] == "user123"
        assert result["type"] == "daily.updated"
        assert result["id"] == "daily-123"
        assert result["trace_id"] == "daily-123"

    @pytest.mark.asyncio
    async def test_parse_event_activity(self, garmin_connector):
        """Test parsing activity webhook event."""
        payload = {
            "userId": "user123",
            "userAccessToken": "token_abc",
            "activities": [
                {
                    "activityId": "12345",
                    "activityType": "RUNNING",
                    "startTimeInSeconds": 1698768000,
                }
            ],
        }

        body = json.dumps(payload).encode()
        result = await garmin_connector.parse_event(body)

        assert result["user_id"] == "user123"
        assert result["type"] == "activity.updated"
        assert result["id"] == "12345"

    @pytest.mark.asyncio
    async def test_parse_event_sleep(self, garmin_connector):
        """Test parsing sleep webhook event."""
        payload = {
            "userId": "user123",
            "userAccessToken": "token_abc",
            "sleeps": [
                {
                    "sleepId": "sleep-456",
                    "startTimeInSeconds": 1698768000,
                }
            ],
        }

        body = json.dumps(payload).encode()
        result = await garmin_connector.parse_event(body)

        assert result["user_id"] == "user123"
        assert result["type"] == "sleep.updated"
        assert result["id"] == "sleep-456"

    @pytest.mark.asyncio
    async def test_parse_event_missing_user_id(self, garmin_connector):
        """Test parsing event with missing userId."""
        payload = {"summaries": []}
        body = json.dumps(payload).encode()

        with pytest.raises(WebhookError) as exc_info:
            await garmin_connector.parse_event(body)

        assert "Missing required field: userId" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_event_invalid_json(self, garmin_connector):
        """Test parsing invalid JSON payload."""
        body = b"not valid json"

        with pytest.raises(WebhookError) as exc_info:
            await garmin_connector.parse_event(body)

        assert "Invalid JSON payload" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_dailies_success(self, garmin_connector):
        """Test fetching daily summaries."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "summaryId": "daily-123",
                "calendarDate": "2024-10-31",
                "totalSteps": 10000,
            }
        ]

        # Mock token refresh
        garmin_connector.refresh_if_needed = AsyncMock(
            return_value=MagicMock(access_token="test_token")
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await garmin_connector.fetch_dailies(
                user_id="user123",
                start_time_seconds=1698768000,
                end_time_seconds=1698854400,
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["summaryId"] == "daily-123"

    @pytest.mark.asyncio
    async def test_fetch_data_rate_limit(self, garmin_connector):
        """Test fetch_data handling rate limit."""
        from synheart_cloud_connector.exceptions import RateLimitError

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        garmin_connector.refresh_if_needed = AsyncMock(
            return_value=MagicMock(access_token="test_token")
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            with pytest.raises(RateLimitError) as exc_info:
                await garmin_connector.fetch_data("user123", "dailies")

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_fetch_data_no_data(self, garmin_connector):
        """Test fetch_data handling 204 No Content."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        garmin_connector.refresh_if_needed = AsyncMock(
            return_value=MagicMock(access_token="test_token")
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await garmin_connector.fetch_data("user123", "dailies")

            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_sleeps(self, garmin_connector):
        """Test fetching sleep data."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sleepId": "sleep-123",
                "sleepStartTimestampGMT": 1698768000,
            }
        ]

        garmin_connector.refresh_if_needed = AsyncMock(
            return_value=MagicMock(access_token="test_token")
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await garmin_connector.fetch_sleeps(
                user_id="user123",
                start_time_seconds=1698768000,
                end_time_seconds=1698854400,
            )

            assert isinstance(result, list)
            assert len(result) == 1
