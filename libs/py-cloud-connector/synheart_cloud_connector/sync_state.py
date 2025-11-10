"""
Sync State Management

Tracks last sync timestamps for incremental data pulls.
Stores cursors in DynamoDB for each user/vendor combination.

Usage:
    sync_state = SyncState(table_name="cloud_connector_tokens")

    # Get last sync time
    cursor = sync_state.get_cursor(VendorType.WHOOP, "user123")
    last_ts = cursor.last_sync_ts if cursor else None

    # Update after successful pull
    sync_state.update_cursor(VendorType.WHOOP, "user123", new_timestamp)

    # Reset cursor (force full sync)
    sync_state.reset_cursor(VendorType.WHOOP, "user123")
"""

import os
from datetime import datetime, timezone
from typing import Optional

# Lazy import boto3 - only import when actually needed
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    # Create dummy classes for type hints when boto3 is not available
    class ClientError(Exception):
        pass

from pydantic import BaseModel

from .vendor_types import VendorType
from .exceptions import CloudConnectorError


class SyncCursor(BaseModel):
    """
    Sync cursor model.

    Attributes:
        vendor: Vendor type
        user_id: User identifier
        last_sync_ts: Last successful sync timestamp (ISO8601 UTC)
        records_synced: Total records synced
        last_resource_id: Last resource ID synced (for pagination)
        created_at: Cursor creation timestamp
        updated_at: Last update timestamp
    """
    vendor: str
    user_id: str
    last_sync_ts: str  # ISO8601 UTC timestamp
    records_synced: int = 0
    last_resource_id: Optional[str] = None
    created_at: str
    updated_at: str


class SyncState:
    """
    Manages sync state cursors in DynamoDB.

    Uses the same DynamoDB table as tokens, but with different partition key:
    - pk: "SYNC#{vendor}#{user_id}"
    - sk: "CURSOR"

    This allows efficient queries for sync state per user/vendor.
    """

    def __init__(
        self,
        table_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """
        Initialize sync state manager.

        Args:
            table_name: DynamoDB table name (defaults to env var)
            region: AWS region (defaults to env var)
        """
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE", "cloud_connector_tokens")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        # Check if running in local mode
        self.local_mode = os.getenv("LOCAL_MODE", "false").lower() == "true"

        if self.local_mode:
            # Use in-memory storage for local testing
            self._local_cursors = {}
        else:
            # Initialize DynamoDB client (lazy import)
            if not HAS_BOTO3:
                raise ImportError(
                    "boto3 is required for SyncState. Install it with: pip install boto3\n"
                    "For local development, use LOCAL_MODE=true or MockSyncState instead."
                )
            import boto3  # Import here to ensure it's available
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)

    def _make_cursor_key(self, vendor: VendorType, user_id: str) -> tuple[str, str]:
        """Generate DynamoDB key for cursor."""
        pk = f"SYNC#{vendor.value}#{user_id}"
        sk = "CURSOR"
        return pk, sk

    def get_cursor(
        self,
        vendor: VendorType,
        user_id: str,
    ) -> Optional[SyncCursor]:
        """
        Get sync cursor for user/vendor.

        Args:
            vendor: Vendor type
            user_id: User identifier

        Returns:
            SyncCursor if exists, None otherwise
        """
        pk, sk = self._make_cursor_key(vendor, user_id)

        if self.local_mode:
            # Local mode: use in-memory storage
            key = f"{pk}#{sk}"
            cursor_data = self._local_cursors.get(key)
            if cursor_data:
                return SyncCursor(**cursor_data)
            return None

        try:
            # Get from DynamoDB
            response = self.table.get_item(
                Key={"pk": pk, "sk": sk}
            )

            if "Item" not in response:
                return None

            item = response["Item"]

            return SyncCursor(
                vendor=item["vendor"],
                user_id=item["user_id"],
                last_sync_ts=item["last_sync_ts"],
                records_synced=item.get("records_synced", 0),
                last_resource_id=item.get("last_resource_id"),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise CloudConnectorError(
                f"Failed to get sync cursor: {error_code}",
                vendor=vendor.value,
            ) from e

    def update_cursor(
        self,
        vendor: VendorType,
        user_id: str,
        last_sync_ts: str,
        records_synced: int = 0,
        last_resource_id: Optional[str] = None,
    ) -> SyncCursor:
        """
        Update sync cursor after successful pull.

        Args:
            vendor: Vendor type
            user_id: User identifier
            last_sync_ts: Timestamp of last sync (ISO8601 UTC)
            records_synced: Number of records synced (incremental)
            last_resource_id: Last resource ID synced (for pagination)

        Returns:
            Updated SyncCursor
        """
        pk, sk = self._make_cursor_key(vendor, user_id)
        now = datetime.now(timezone.utc).isoformat()

        # Get existing cursor to increment records_synced
        existing_cursor = self.get_cursor(vendor, user_id)
        total_records = (existing_cursor.records_synced if existing_cursor else 0) + records_synced

        cursor_data = {
            "vendor": vendor.value,
            "user_id": user_id,
            "last_sync_ts": last_sync_ts,
            "records_synced": total_records,
            "last_resource_id": last_resource_id,
            "created_at": existing_cursor.created_at if existing_cursor else now,
            "updated_at": now,
        }

        if self.local_mode:
            # Local mode: use in-memory storage
            key = f"{pk}#{sk}"
            self._local_cursors[key] = cursor_data
            return SyncCursor(**cursor_data)

        try:
            # Update in DynamoDB
            self.table.put_item(
                Item={
                    "pk": pk,
                    "sk": sk,
                    **cursor_data,
                }
            )

            return SyncCursor(**cursor_data)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise CloudConnectorError(
                f"Failed to update sync cursor: {error_code}",
                vendor=vendor.value,
            ) from e

    def reset_cursor(
        self,
        vendor: VendorType,
        user_id: str,
    ):
        """
        Reset sync cursor (forces full sync next time).

        Args:
            vendor: Vendor type
            user_id: User identifier
        """
        pk, sk = self._make_cursor_key(vendor, user_id)

        if self.local_mode:
            # Local mode: delete from in-memory storage
            key = f"{pk}#{sk}"
            self._local_cursors.pop(key, None)
            return

        try:
            # Delete from DynamoDB
            self.table.delete_item(
                Key={"pk": pk, "sk": sk}
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise CloudConnectorError(
                f"Failed to reset sync cursor: {error_code}",
                vendor=vendor.value,
            ) from e

    def list_cursors(
        self,
        vendor: Optional[VendorType] = None,
        limit: int = 100,
    ) -> list[SyncCursor]:
        """
        List sync cursors, optionally filtered by vendor.

        Args:
            vendor: Optional vendor filter
            limit: Maximum cursors to return

        Returns:
            List of SyncCursor objects
        """
        if self.local_mode:
            # Local mode: filter in-memory storage
            cursors = []
            for key, cursor_data in self._local_cursors.items():
                if vendor and cursor_data["vendor"] != vendor.value:
                    continue
                cursors.append(SyncCursor(**cursor_data))
                if len(cursors) >= limit:
                    break
            return cursors

        try:
            # Scan DynamoDB for SYNC# keys
            scan_params = {
                "Limit": limit,
            }

            if vendor:
                # Filter by vendor prefix
                scan_params["FilterExpression"] = "begins_with(pk, :prefix)"
                scan_params["ExpressionAttributeValues"] = {
                    ":prefix": f"SYNC#{vendor.value}#"
                }
            else:
                # Filter for all SYNC# keys
                scan_params["FilterExpression"] = "begins_with(pk, :prefix)"
                scan_params["ExpressionAttributeValues"] = {
                    ":prefix": "SYNC#"
                }

            response = self.table.scan(**scan_params)

            cursors = []
            for item in response.get("Items", []):
                cursors.append(SyncCursor(
                    vendor=item["vendor"],
                    user_id=item["user_id"],
                    last_sync_ts=item["last_sync_ts"],
                    records_synced=item.get("records_synced", 0),
                    last_resource_id=item.get("last_resource_id"),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                ))

            return cursors

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise CloudConnectorError(
                f"Failed to list sync cursors: {error_code}",
                vendor=vendor.value if vendor else "all",
            ) from e

    def get_last_sync_timestamp(
        self,
        vendor: VendorType,
        user_id: str,
    ) -> Optional[str]:
        """
        Convenience method to get just the last sync timestamp.

        Args:
            vendor: Vendor type
            user_id: User identifier

        Returns:
            Last sync timestamp (ISO8601 UTC) or None if never synced
        """
        cursor = self.get_cursor(vendor, user_id)
        return cursor.last_sync_ts if cursor else None

    def has_synced_before(
        self,
        vendor: VendorType,
        user_id: str,
    ) -> bool:
        """
        Check if user has synced before.

        Args:
            vendor: Vendor type
            user_id: User identifier

        Returns:
            True if user has synced before, False otherwise
        """
        return self.get_cursor(vendor, user_id) is not None
