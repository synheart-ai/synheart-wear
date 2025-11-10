"""WHOOP cloud connector implementation."""

import json
from typing import Any

import httpx

from synheart_cloud_connector import CloudConnectorBase, WebhookError
from synheart_cloud_connector.vendor_types import VendorType
from synheart_cloud_connector.webhooks import extract_signature_from_headers


class WhoopConnector(CloudConnectorBase):
    """
    WHOOP cloud connector.

    Implements WHOOP-specific OAuth, webhook verification, and data fetching.

    WHOOP API Documentation:
    - https://developer.whoop.com/api

    Supported data types:
    - Recovery (HRV, resting HR, recovery score)
    - Sleep (stages, quality, duration)
    - Workout (strain, calories, HR zones)
    - Cycle (daily summaries)
    """

    @property
    def vendor(self) -> VendorType:
        """Return WHOOP vendor type."""
        return VendorType.WHOOP

    async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        """
        Verify WHOOP webhook signature.

        WHOOP uses HMAC-SHA256 with timestamp for webhook verification.

        Headers:
        - X-WHOOP-Signature: HMAC signature
        - X-WHOOP-Signature-Timestamp: Unix timestamp

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

        # Extract signature and timestamp from headers
        signature, timestamp = extract_signature_from_headers(
            headers,
            signature_key="X-WHOOP-Signature",
            timestamp_key="X-WHOOP-Signature-Timestamp",
        )

        if not signature or not timestamp:
            raise WebhookError(
                "Missing signature or timestamp headers",
                vendor=self.vendor.value,
            )

        # Verify HMAC signature
        return self.webhook_verifier.verify_hmac_sha256(
            timestamp=timestamp,
            body=raw_body,
            signature=signature,
            vendor=self.vendor.value,
        )

    async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
        """
        Parse WHOOP webhook payload (v2 format).

        WHOOP v2 webhook format:
        {
            "id": "uuid-string",
            "user_id": 10129,
            "type": "recovery.updated",
            "trace_id": "e369c784-5100-49e8-8098-75d35c47b31b"
        }

        Note: v2 webhooks use UUID identifiers instead of integer IDs.

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
        required_fields = ["user_id", "type"]
        for field in required_fields:
            if field not in data:
                raise WebhookError(
                    f"Missing required field: {field}",
                    vendor=self.vendor.value,
                )

        return data

    async def fetch_data(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch data from WHOOP API v2.

        WHOOP API v2 endpoints:
        - /v2/recovery/{id} - Get recovery data
        - /v2/cycle/{id} - Get cycle data
        - /v2/activity/sleep/{id} - Get sleep data
        - /v2/activity/workout/{id} - Get workout data

        Args:
            user_id: User identifier
            resource_type: Type of resource (recovery, sleep, workout, cycle)
            resource_id: Specific resource ID (UUID in v2)

        Returns:
            Raw WHOOP data
        """
        # Check rate limit
        self.check_rate_limit(user_id)

        # Get valid access token
        tokens = await self.refresh_if_needed(user_id)

        # Build API URL
        base_url = self.config.base_url
        if resource_id:
            url = f"{base_url}/developer/v2/{resource_type}/{resource_id}"
        else:
            url = f"{base_url}/developer/v2/{resource_type}"

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                },
            )

            if response.status_code == 429:
                # Rate limited by WHOOP
                retry_after = int(response.headers.get("Retry-After", 60))
                from synheart_cloud_connector.exceptions import RateLimitError

                raise RateLimitError(
                    "WHOOP API rate limit exceeded",
                    vendor=self.vendor.value,
                    retry_after=retry_after,
                )

            if response.status_code != 200:
                from synheart_cloud_connector.exceptions import VendorAPIError

                raise VendorAPIError(
                    f"WHOOP API error: {response.status_code} {response.text}",
                    vendor=self.vendor.value,
                    status_code=response.status_code,
                )

            # Update last pull timestamp
            self.token_store.update_last_pull(self.vendor, user_id)

            return response.json()

    async def fetch_recovery(self, user_id: str, recovery_id: str) -> dict[str, Any]:
        """Fetch specific recovery record."""
        return await self.fetch_data(user_id, "recovery", recovery_id)

    async def fetch_sleep(self, user_id: str, sleep_id: str) -> dict[str, Any]:
        """Fetch specific sleep record."""
        return await self.fetch_data(user_id, "sleep", sleep_id)

    async def fetch_workout(self, user_id: str, workout_id: str) -> dict[str, Any]:
        """Fetch specific workout record."""
        return await self.fetch_data(user_id, "workout", workout_id)

    async def fetch_cycle(self, user_id: str, cycle_id: str) -> dict[str, Any]:
        """Fetch specific cycle (daily summary) record."""
        return await self.fetch_data(user_id, "cycle", cycle_id)

    def _normalize_date_for_whoop(self, date_str: str) -> str:
        """
        Normalize date to WHOOP-compatible RFC3339 format.
        
        WHOOP API expects: YYYY-MM-DDTHH:MM:SSZ (no microseconds, Z suffix)
        """
        from datetime import datetime, timezone
        
        # Parse the date string
        if isinstance(date_str, str):
            # Handle Z suffix and +00:00
            date_str = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str)
        else:
            dt = date_str
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Format as RFC3339: YYYY-MM-DDTHH:MM:SSZ (no microseconds)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    async def fetch_recovery_collection(
        self,
        user_id: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """
        Fetch collection of recovery records.

        Args:
            user_id: User identifier
            start: Start date (ISO8601 format)
            end: End date (ISO8601 format)
            limit: Maximum number of records (default 25)

        Returns:
            List of recovery records with pagination
        """
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        params = {"limit": limit}
        if start:
            params["start"] = self._normalize_date_for_whoop(start)
        if end:
            params["end"] = self._normalize_date_for_whoop(end)

        url = f"{self.config.base_url}/developer/v2/recovery"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                params=params,
            )

            if response.status_code == 200:
                self.token_store.update_last_pull(self.vendor, user_id)
                return response.json()

            # Enhanced error logging
            error_detail = f"WHOOP API error: {response.status_code}"
            if response.text:
                try:
                    error_body = response.json()
                    error_detail += f" - {error_body}"
                except:
                    error_detail += f" - {response.text[:500]}"
            
            from synheart_cloud_connector.exceptions import VendorAPIError
            raise VendorAPIError(
                error_detail,
                vendor=self.vendor.value,
                status_code=response.status_code,
            )

    async def fetch_sleep_collection(
        self,
        user_id: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Fetch collection of sleep records."""
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        params = {"limit": limit}
        if start:
            params["start"] = self._normalize_date_for_whoop(start)
        if end:
            params["end"] = self._normalize_date_for_whoop(end)

        url = f"{self.config.base_url}/developer/v2/activity/sleep"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                params=params,
            )

            if response.status_code == 200:
                self.token_store.update_last_pull(self.vendor, user_id)
                return response.json()

            # Enhanced error logging
            error_detail = f"WHOOP API error: {response.status_code}"
            if response.text:
                try:
                    error_body = response.json()
                    error_detail += f" - {error_body}"
                except:
                    error_detail += f" - {response.text[:500]}"
            
            from synheart_cloud_connector.exceptions import VendorAPIError
            raise VendorAPIError(
                error_detail,
                vendor=self.vendor.value,
                status_code=response.status_code,
            )

    async def fetch_workout_collection(
        self,
        user_id: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Fetch collection of workout records."""
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        params = {"limit": limit}
        if start:
            params["start"] = self._normalize_date_for_whoop(start)
        if end:
            params["end"] = self._normalize_date_for_whoop(end)

        url = f"{self.config.base_url}/developer/v2/activity/workout"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                params=params,
            )

            if response.status_code == 200:
                self.token_store.update_last_pull(self.vendor, user_id)
                return response.json()

            # Enhanced error logging
            error_detail = f"WHOOP API error: {response.status_code}"
            if response.text:
                try:
                    error_body = response.json()
                    error_detail += f" - {error_body}"
                except:
                    error_detail += f" - {response.text[:500]}"
            
            from synheart_cloud_connector.exceptions import VendorAPIError
            raise VendorAPIError(
                error_detail,
                vendor=self.vendor.value,
                status_code=response.status_code,
            )

    async def fetch_cycle_collection(
        self,
        user_id: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Fetch collection of cycle (daily summary) records."""
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        params = {"limit": limit}
        if start:
            params["start"] = self._normalize_date_for_whoop(start)
        if end:
            params["end"] = self._normalize_date_for_whoop(end)

        url = f"{self.config.base_url}/developer/v2/cycle"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                params=params,
            )

            if response.status_code == 200:
                self.token_store.update_last_pull(self.vendor, user_id)
                return response.json()

            # Enhanced error logging
            error_detail = f"WHOOP API error: {response.status_code}"
            if response.text:
                try:
                    error_body = response.json()
                    error_detail += f" - {error_body}"
                except:
                    error_detail += f" - {response.text[:500]}"
            
            from synheart_cloud_connector.exceptions import VendorAPIError
            raise VendorAPIError(
                error_detail,
                vendor=self.vendor.value,
                status_code=response.status_code,
            )

    async def fetch_user_profile(self, user_id: str) -> dict[str, Any]:
        """
        Fetch user profile information.

        Returns user's basic profile data from WHOOP.
        """
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        url = f"{self.config.base_url}/developer/v2/user/profile/basic"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )

            if response.status_code == 200:
                return response.json()

            from synheart_cloud_connector.exceptions import VendorAPIError
            raise VendorAPIError(
                f"WHOOP API error: {response.status_code}",
                vendor=self.vendor.value,
                status_code=response.status_code,
            )
