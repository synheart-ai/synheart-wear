"""Garmin Health API cloud connector implementation."""

import json
from typing import Any

import httpx

from synheart_cloud_connector import CloudConnectorBase, WebhookError
from synheart_cloud_connector.vendor_types import VendorType
from synheart_cloud_connector.webhooks import extract_signature_from_headers


class GarminConnector(CloudConnectorBase):
    """
    Garmin Health API cloud connector.

    Implements Garmin-specific OAuth, webhook verification, and data fetching.

    Garmin Health API Documentation:
    - https://developer.garmin.com/health-api/overview

    Supported data types:
    - Daily summaries (steps, calories, heart rate)
    - Sleep data (stages, quality, duration)
    - Activities (workouts, sports)
    - Body composition
    - Blood pressure
    - Pulse ox
    - Stress levels
    - HRV

    Note: Garmin Health API requires enterprise partnership.
    """

    @property
    def vendor(self) -> VendorType:
        """Return Garmin vendor type."""
        return VendorType.GARMIN

    async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        """
        Verify Garmin webhook signature.

        Garmin uses HMAC-SHA256 for webhook verification.

        Headers:
        - X-Gfit-Signature: HMAC signature (older format)
        - Garmin-Signature: HMAC signature (newer format)

        Args:
            headers: HTTP headers from webhook request
            raw_body: Raw request body

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If verification fails
        """
        if not self.webhook_verifier:
            raise WebhookError("Webhook verifier not configured", vendor=self.vendor.value)

        # Try newer format first
        signature = headers.get("Garmin-Signature") or headers.get("garmin-signature")

        # Fall back to older format
        if not signature:
            signature = headers.get("X-Gfit-Signature") or headers.get("x-gfit-signature")

        if not signature:
            raise WebhookError(
                "Missing webhook signature header",
                vendor=self.vendor.value,
            )

        # Garmin uses simple SHA256 hash (no timestamp)
        return self.webhook_verifier.verify_sha256_hash(
            body=raw_body,
            signature=signature,
            vendor=self.vendor.value,
        )

    async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
        """
        Parse Garmin webhook payload.

        Garmin webhook format:
        {
            "userId": "user-123",
            "userAccessToken": "token-abc",
            "summaries": [
                {
                    "summaryId": "daily-summary-456",
                    "calendarDate": "2024-10-31",
                    "dataType": "DAILY"
                }
            ]
        }

        Or activity format:
        {
            "userId": "user-123",
            "userAccessToken": "token-abc",
            "activities": [
                {
                    "activityId": "12345",
                    "activityType": "RUNNING",
                    "startTimeInSeconds": 1698768000
                }
            ]
        }

        Args:
            raw_body: Raw request body

        Returns:
            Parsed event data
        """
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as e:
            raise WebhookError(
                f"Invalid JSON payload: {e}",
                vendor=self.vendor.value,
            ) from e

        # Validate required fields
        if "userId" not in data:
            raise WebhookError(
                "Missing required field: userId",
                vendor=self.vendor.value,
            )

        # Normalize to our standard format
        event_type = "unknown"
        resource_id = None

        if "summaries" in data and len(data["summaries"]) > 0:
            summary = data["summaries"][0]
            event_type = f"{summary.get('dataType', 'daily').lower()}.updated"
            resource_id = summary.get("summaryId")

        elif "activities" in data and len(data["activities"]) > 0:
            activity = data["activities"][0]
            event_type = "activity.updated"
            resource_id = activity.get("activityId")

        elif "sleeps" in data and len(data["sleeps"]) > 0:
            sleep = data["sleeps"][0]
            event_type = "sleep.updated"
            resource_id = sleep.get("sleepId")

        return {
            "user_id": data["userId"],
            "type": event_type,
            "id": resource_id,
            "trace_id": resource_id or data["userId"],  # Use resource ID as trace
            "raw_data": data,
        }

    async def fetch_data(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch data from Garmin Health API.

        Garmin API endpoints:
        - /wellness/dailies/{uploadStartTimeInSeconds}/{uploadEndTimeInSeconds}
        - /wellness/sleeps/{uploadStartTimeInSeconds}/{uploadEndTimeInSeconds}
        - /wellness/activities
        - /wellness/stress
        - /wellness/bloodPressure
        - /wellness/bodyComps

        Args:
            user_id: User identifier (Garmin userId)
            resource_type: Type of resource (dailies, sleeps, activities, etc.)
            resource_id: Time range or specific resource ID

        Returns:
            Raw Garmin data
        """
        # Check rate limit
        self.check_rate_limit(user_id)

        # Get valid access token
        tokens = await self.refresh_if_needed(user_id)

        # Build API URL
        base_url = self.config.base_url
        url = f"{base_url}/wellness/{resource_type}"

        # Add resource_id if provided (usually time ranges)
        if resource_id:
            url += f"/{resource_id}"

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                },
            )

            if response.status_code == 429:
                # Rate limited by Garmin
                retry_after = int(response.headers.get("Retry-After", 60))
                from synheart_cloud_connector.exceptions import RateLimitError

                raise RateLimitError(
                    "Garmin API rate limit exceeded",
                    vendor=self.vendor.value,
                    retry_after=retry_after,
                )

            if response.status_code == 204:
                # No data available for this range
                return []

            if response.status_code != 200:
                from synheart_cloud_connector.exceptions import VendorAPIError

                raise VendorAPIError(
                    f"Garmin API error: {response.status_code} {response.text}",
                    vendor=self.vendor.value,
                    status_code=response.status_code,
                )

            # Update last pull timestamp
            self.token_store.update_last_pull(self.vendor, user_id)

            return response.json()

    async def fetch_dailies(
        self,
        user_id: str,
        start_time_seconds: int,
        end_time_seconds: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch daily summaries for a time range.

        Args:
            user_id: User identifier
            start_time_seconds: Start time (Unix timestamp)
            end_time_seconds: End time (Unix timestamp)

        Returns:
            List of daily summary records
        """
        time_range = f"{start_time_seconds}/{end_time_seconds}"
        data = await self.fetch_data(user_id, "dailies", time_range)
        return data if isinstance(data, list) else []

    async def fetch_sleeps(
        self,
        user_id: str,
        start_time_seconds: int,
        end_time_seconds: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch sleep data for a time range.

        Args:
            user_id: User identifier
            start_time_seconds: Start time (Unix timestamp)
            end_time_seconds: End time (Unix timestamp)

        Returns:
            List of sleep records
        """
        time_range = f"{start_time_seconds}/{end_time_seconds}"
        data = await self.fetch_data(user_id, "sleeps", time_range)
        return data if isinstance(data, list) else []

    async def fetch_activities(
        self,
        user_id: str,
        start_time_seconds: int | None = None,
        end_time_seconds: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch activities (workouts).

        Args:
            user_id: User identifier
            start_time_seconds: Optional start time filter
            end_time_seconds: Optional end time filter

        Returns:
            List of activity records
        """
        if start_time_seconds and end_time_seconds:
            time_range = f"{start_time_seconds}/{end_time_seconds}"
            data = await self.fetch_data(user_id, "activities", time_range)
        else:
            data = await self.fetch_data(user_id, "activities")

        return data if isinstance(data, list) else []

    async def fetch_stress(
        self,
        user_id: str,
        start_time_seconds: int,
        end_time_seconds: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch stress level data.

        Args:
            user_id: User identifier
            start_time_seconds: Start time (Unix timestamp)
            end_time_seconds: End time (Unix timestamp)

        Returns:
            List of stress records
        """
        time_range = f"{start_time_seconds}/{end_time_seconds}"
        data = await self.fetch_data(user_id, "stress", time_range)
        return data if isinstance(data, list) else []

    async def fetch_heart_rate(
        self,
        user_id: str,
        start_time_seconds: int,
        end_time_seconds: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch heart rate data.

        Args:
            user_id: User identifier
            start_time_seconds: Start time (Unix timestamp)
            end_time_seconds: End time (Unix timestamp)

        Returns:
            List of heart rate records
        """
        time_range = f"{start_time_seconds}/{end_time_seconds}"
        data = await self.fetch_data(user_id, "heartRates", time_range)
        return data if isinstance(data, list) else []
